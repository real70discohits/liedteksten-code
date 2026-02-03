"""
FastAPI application for nwctxt (noteworthy composer) to audio conversie service.
"""

import os
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse, JSONResponse
import aiofiles
from typing import List

from nwc_utils import (
    NwcFile,
    print_wd,
    print_wd_contents,
    print_directory_contents,
    extract_song_title_from_filename,
    verify_soundfont_file
)

from nwc_convert import (
    verify_tools,
    run_conversion_step
)

app = FastAPI(
    title="Noteworthy Composer (NWCTXT) > MIDI > WAV > FLAC Conversion API",
    description="API for converting NWCTXT files to FLAC",
    version="1.0.0"
)

# Security: restrict working directories
WORK_DIR = Path("/tmp/nwc-work")
OUTPUT_DIR = Path("/tmp/audio-output")


# Maximum file sizes
MAX_NWCTXT_SIZE = 200 * 1024   # 200 Kb (normale .nwctxt is 30-50 Kb)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "nwc-conversie-api"}


async def write_uploaded_file_to_disk(uploaded_file, target_path):
    """Writes uploaded file to the current working directory or a subdirectory"""
    try:
        # `UploadFile.file` is een SpooledTemporaryFile – we kopiëren de bytes
        with target_path.open("wb") as buffer:
            # async copy – geschikt voor grote bestanden
            while chunk := await uploaded_file.read(1024 * 1024):  # 1 MiB per chunk
                buffer.write(chunk)
    finally:
        # Zorg dat de tijdelijke upload‑buffer wordt gesloten
        await uploaded_file.close()


@app.post("/convert")
async def convert_nwctxt(
    nwctxt_file: UploadFile = File(..., description="NoteWorthy .nwctxt file to convert"),
    staff_names: Optional[str] = Form(default="", description="Staff names to convert separately \
(default: all staffs). Example: Bass Ritme")
):
    """
    Converts an .nwctxt noteworthy composer file to audio (.flac)
    """

    print()
    print("=" * 60)
    print("       New Conversion Request .NWCTXT => FLAC")
    print("=" * 60 + "\n")


    # Validate nwctxt file
    if not nwctxt_file.filename.endswith('.nwctxt'):
        raise HTTPException(status_code=400, detail="Only .nwctxt files are allowed \
for nwctxt_file")

    try:
        # ❌ INLEZEN VEROORZAAKT DAT STAFFS UITLEZEN FOUT GAAT, NOG UITZOEKEN
        # Read nwctxt file
        nwctxt_content = await nwctxt_file.read()
        if len(nwctxt_content) > MAX_NWCTXT_SIZE:
            raise HTTPException(status_code=400, detail=f"tex_file too \
                                large (max {MAX_NWCTXT_SIZE/1024}KB)")

        # Reset file pointer to beginning for subsequent reads (else they will
        # fail, because the read() set the pointer to the end of the file)
        await nwctxt_file.seek(0)

        # ===== VALIDATE TOOLS AND SOUNDFONT =====
        if not verify_tools():
            raise HTTPException(status_code=500, detail="Tools are not installed or \
    configured properly on the server")

        if not verify_soundfont_file():
            raise HTTPException(status_code=500, detail="Soundfont file not found at expected \
    location on the server")
        
        # Extract song title
        song_title = extract_song_title_from_filename(nwctxt_file.filename)
        print(f"Detected song title: {song_title}")

        # Ensure directories exist and are empty
        # ℹ️ Note that I cannot do this at the end, since it may interfere with the return.
        if WORK_DIR.is_dir():
            shutil.rmtree(WORK_DIR)
        if OUTPUT_DIR.is_dir():
            shutil.rmtree(OUTPUT_DIR)

        WORK_DIR.mkdir(exist_ok=True)
        OUTPUT_DIR.mkdir(exist_ok=True)

        # Save the uploaded file in that folder
        target_path = WORK_DIR / nwctxt_file.filename  # behoud originele bestandsnaam
        await write_uploaded_file_to_disk(nwctxt_file, target_path)

        # ===== PARSE NWCTXT FILE AND DETERMINE STAFFS TO CONVERT =====
        print("=" * 60)
        print("Parsing NWC file and determining staffs...")
        print("=" * 60 + "\n")

        nwc_file = NwcFile(target_path)
        print(f"Found {len(nwc_file.staffs)} staff(s) in file:")
        for i, staff in enumerate(nwc_file.staffs, 1):
            print(f"  {i}. {staff.name if staff.name else '(unnamed)'}")
        print()

        # Determine which staffs to convert
        if staff_names:
            # User specified staff names
            requested = staff_names.split() # set(staff_names)
            requested = set(requested)
            available = {s.name for s in nwc_file.staffs if s.name}
            missing = requested - available

            if missing:
                print(f"⚠️  WARNING: Staff name(s) not found: {', '.join(missing)}")
                print(f"Available staffs: {', '.join(sorted(available))}\n")

            staffs_to_convert = [s for s in nwc_file.staffs if s.name in staff_names]

            if not staffs_to_convert:
                print("❌ ERROR: None of the requested staffs exist")
                raise HTTPException(status_code=400, detail="None of the requested staffs exist")
        else:
            # Convert all staffs
            staffs_to_convert = nwc_file.staffs

        print(f"Converting {len(staffs_to_convert)} staff(s)...\n")

        # ===== CONVERT EACH STAFF SEPARATELY =====
        print("=" * 60)
        print("Starting multi-staff conversion pipeline...")
        print("=" * 60 + "\n")

        flac_outputs = []

        for staff_index, staff in enumerate(staffs_to_convert, 1):
            print(f"{'=' * 60}")
            print(f"Processing staff {staff_index}/{len(staffs_to_convert)}: {staff.name}")
            print(f"{'=' * 60}\n")

            # 1. Create temporary copy of NWC file
            temp_path = OUTPUT_DIR / f"{song_title}_temp.nwctxt"

            # 2. Parse fresh copy, mute all, unmute only this staff
            temp_nwc = NwcFile(target_path)
            temp_nwc.set_all_staffs_muted(True, volume=127)
            temp_nwc.set_staff_muted_by_name(staff.name, False, volume=127)
            temp_nwc.write_to_file(temp_path)

            print(f"Created temporary file with only '{staff.name}' unmuted\n")

            # 3. Generate output paths with staff name
            midi_path = OUTPUT_DIR / f"{song_title} {staff.name}.mid"
            wav_path = OUTPUT_DIR / f"{song_title} {staff.name}.wav"
            flac_path = OUTPUT_DIR / f"{song_title} {staff.name}.flac"

            # 4. Run conversion pipeline (3 steps)
            # STEP 1: NWC → MIDI
            cmd1 = f'wine nwc-conv "{temp_path}" "{midi_path}" -1'
            if not run_conversion_step(
                1,
                f"Converting {staff.name} to MIDI",
                cmd1,
                midi_path
            ):
                temp_path.unlink(missing_ok=True)
                raise HTTPException(status_code=500, detail="ERR: conversion nwctxt to midi failed")

            # STEP 2: MIDI → WAV
            soundfont_path = os.getenv("FLUIDSYNTH_SOUNDFONT")
            cmd2 = f'fluidsynth -n -F "{wav_path}" "{soundfont_path}" "{midi_path}"'
            if not run_conversion_step(
                2,
                f"Converting {staff.name} MIDI to WAV",
                cmd2,
                wav_path
            ):
                temp_path.unlink(missing_ok=True)
                raise HTTPException(status_code=500, detail="ERR: conversion midi to wav failed")

            # STEP 3: WAV → FLAC
            cmd3 = f'ffmpeg -y -i "{wav_path}" "{flac_path}"'
            if not run_conversion_step(
                3,
                f"Converting {staff.name} WAV to FLAC",
                cmd3,
                flac_path
            ):
                temp_path.unlink(missing_ok=True)
                raise HTTPException(status_code=500, detail="ERR: conversion wav to flac failed")

            # 5. Remove temporary NWC file (unless --no-cleanup)
            temp_path.unlink(missing_ok=True)
            print(f"Removed temporary file: {temp_path.name}\n")

            flac_outputs.append(flac_path)

            print(f"[DEBUG] Flac outputs: {flac_outputs}")

        print("=" * 60)
        print("Cleaning up intermediate files...")
        print("=" * 60 + "\n")

        removed_count = 0
        for mid_file in OUTPUT_DIR.glob("*.mid"):
            mid_file.unlink()
            print(f"  Removed: {mid_file.name}")
            removed_count += 1

        for wav_file in OUTPUT_DIR.glob("*.wav"):
            wav_file.unlink()
            print(f"  Removed: {wav_file.name}")
            removed_count += 1

        if removed_count > 0:
            print(f"\nRemoved {removed_count} intermediate file(s)\n")

        # ===== SUCCESS =====
        print("=" * 60)
        print("✅ SUCCESS: All conversions completed!")
        print("=" * 60)
        print(f"\nFinal output ({len(flac_outputs)} file(s)):")
        for flac_file in flac_outputs:
            print(f"  {flac_file}")
        print()

        # Create ZIP file
        zip_path = OUTPUT_DIR / f"{os.urandom(8).hex()}.zip"

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add FLACs
            for flac_path in flac_outputs:
                zipf.write(flac_path, flac_path.name)

            # Clean up temp files (PDF source files)
            # for flac_path in result.pdf_files:
            #     if flac_path.exists():
            #         # Get the temp root directory and clean it up
            #         temp_root = flac_path.parent.parent
            #         if temp_root.exists() and temp_root.name.startswith("ltgen_"):
            #             shutil.rmtree(temp_root, ignore_errors=True)



        print_wd_contents()

        print_directory_contents(WORK_DIR)

        print_directory_contents(OUTPUT_DIR)

        print()
        print("=" * 60)
        print("                END                ")
        print("=" * 60)

        # Schedule cleanup of ZIP file after response
        # Note: FastAPI will handle this, but we can also use background tasks
        # For now, we accept that old ZIPs will accumulate in OUTPUT_DIR
        # In production, you'd want a cleanup task

        # Generate filename with timestamp: "Such A Beauty (6)_AUDIO_20260102_153045.zip"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_filename = f"{song_title}_AUDIO_{timestamp}.zip"

        # Return ZIP
        response = FileResponse(
            path=zip_path,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{download_filename}"'
            }
        )

        return response

    except Exception as e:
        print("EXCEPTION:", type(e).__name__, str(e))
        raise HTTPException(status_code=500, detail=f"Internal serverrr error: {str(e)}") from e


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
