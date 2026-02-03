#!/usr/bin/env python3
"""
NWCTXT to FLAC converter: NWCTXT → MIDI → WAV → FLAC

Try out:
    python nwc-convert.py bla
    (this will give you a sense of what happens and of course it fails)

Usage:
    python nwc-convert.py myfile
    python nwc-convert.py path/to/myfile.nwctxt
    python nwc-convert.py myfile --out D:\audio
    python nwc-convert.py myfile --soundfont path/to/soundfont.sf2

Dependencies:
- noteworthy composer (nwc), specifically nwc-conv.exe
- fluidsynth
- ffmpeg
For more info on these tools and usage see these docs on Proton Drive:
- MIDI omzetten naar AUDIO
- Werkproces demo's maken
- Versiebeheer op NWC bestanden: .NWCTXT
- MIDI afspelen
"""

import sys
import subprocess
from pathlib import Path
import argparse
# from pathconfig import load_and_resolve_paths
from nwc_utils import NwcFile


def verify_tools():
    """
    Verify that all required tools are available and working.
    Checks: nwc-conv, fluidsynth, ffmpeg
    """
    tools = {
        # next line has changed: specific for linux instead of local windows
        # 'nwc-conv': ('wine nwc-conv.exe -v', 'nwc-conv: version'),
        'fluidsynth': ('fluidsynth -V', 'FluidSynth runtime version'),
        'ffmpeg': ('ffmpeg', 'ffmpeg version')
    }

    print("=" * 60)
    print("Verifying required tools...")
    print("=" * 60)

    for tool_name, (cmd, expected_output) in tools.items():
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout + result.stderr

            if expected_output.lower() in output.lower():
                print(f"✓ {tool_name:15} is available")
            else:
                print(f"✗ {tool_name:15} verification failed")
                print(f"  Expected output containing: '{expected_output}'")
                print(f"  Got: {output[:150]}")
                return False

        except subprocess.TimeoutExpired:
            print(f"✗ {tool_name:15} verification timed out")
            return False
        except Exception as e:
            print(f"✗ {tool_name:15} failed: {e}")
            return False

    print()
    return True


def get_input_file_path(input_arg, base_folder=None):
    """Process input argument to get a valid file path.

    Args:
        input_arg: Input file path or name
        base_folder: Base folder to search in (default: current directory)

    Returns:
        Resolved Path object

    Behavior:
        - If input_arg is absolute path, use as-is
        - If no extension, assume .nwctxt
        - If no path specified, look in base_folder (default: current directory)
    """
    path = Path(input_arg)

    # If absolute path, use as-is (just add extension if missing)
    if path.is_absolute():
        if path.suffix == '':
            path = path.with_suffix('.nwctxt')
        return path

    # For relative paths, use base_folder
    if base_folder is None:
        base_folder = Path.cwd()
    else:
        base_folder = Path(base_folder)

    # Construct path in base folder
    path = base_folder / input_arg

    # If no extension, add .nwctxt
    if path.suffix == '':
        path = path.with_suffix('.nwctxt')

    return path


def get_output_path(input_path, output_dir, extension):
    """Generate output file path with new extension."""
    output_filename = input_path.stem + extension
    return Path(output_dir) / output_filename


def run_conversion_step(step_num, description, command, output_file):
    """
    Run a single conversion step.

    Args:
        step_num: Step number for display (1, 2, 3)
        description: Human-readable description of what's happening
        command: Shell command to execute
        output_file: Expected output file path

    Returns:
        True if successful, False otherwise
    """
    print(f"Step {step_num}/3: {description}")
    print(f"Command: {command}\n")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per step
        )

        print("STDERR:", result.stderr)
        print("STDOUT:", result.stdout)
        print("Return code:", result.returncode)
        
        if result.returncode != 0:
            print(f"❌ Command failed with return code {result.returncode}")
            if result.stderr:
                print(f"\nSTDERR:\n{result.stderr}")
            if result.stdout:
                print(f"\nSTDOUT:\n{result.stdout}")
            return False

        if not output_file.exists():
            print(f"❌ Expected output file was not created: {output_file}")
            return False

        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"✅ Success! Created: {output_file.name} ({file_size_mb:.2f} MB)\n")
        return True

    except subprocess.TimeoutExpired:
        print(f"❌ Command timed out (exceeded 5 minutes)")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    """Main entry point for nwc-convert script.

    Loads path configuration and converts NWCTXT files to FLAC format.
    """
    # Load and resolve path configuration
    paths = load_and_resolve_paths()

    # Determine defaults from config
    default_out = str(paths.audio_output_folder)
    default_soundfont = 'FluidR3_GM_GS.sf2'  # Default filename

    # If soundfont_path is configured, use it
    if paths.soundfont_path:
        default_soundfont = str(paths.soundfont_path)

    parser = argparse.ArgumentParser(
        description='Convert NWCTXT file to FLAC via MIDI and WAV formats',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python nwc-convert.py myfile
    python nwc-convert.py C:\\music\\piece.nwctxt
    python nwc-convert.py myfile --out C:\\output
    python nwc-convert.py myfile --soundfont C:\\sf2\\font.sf2
    """
    )

    parser.add_argument(
        'input',
        help='Input NWCTXT file (assumes .nwctxt extension if not specified)'
    )
    parser.add_argument(
        '--out',
        default=default_out,
        help=f'Output directory (default: {default_out})'
    )
    parser.add_argument(
        '--soundfont',
        default=default_soundfont,
        help=f'Path to FluidSynth soundfont file (default: {default_soundfont})'
    )
    parser.add_argument(
        '--staff-names',
        nargs='*',
        default=None,
        help='Staff names to convert separately (default: all staffs). Example: --staff-names Bass Ritme'
    )
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='Keep intermediate files (.mid, .wav, temp .nwctxt) for debugging'
    )

    args = parser.parse_args()

    # ===== VERIFY TOOLS =====
    if not verify_tools():
        print("❌ ERROR: Tool verification failed.")
        print("\nPlease ensure the following are installed and accessible via PATH:")
        print("  - nwc-conv (NoteWorthy Composer converter)")
        print("  - fluidsynth (MIDI to audio synthesizer)")
        print("  - ffmpeg (audio format converter)")
        sys.exit(1)

    # ===== VALIDATE INPUT FILE =====
    print("=" * 60)
    print("Processing input file...")
    print("=" * 60 + "\n")

    input_path = get_input_file_path(args.input, paths.build_folder)

    if not input_path.exists():
        print("❌ ERROR: Input file not found:")
        print(f"  {input_path}")
        print("\nPlease verify the file path and try again.")
        sys.exit(1)

    print(f"Input file: {input_path}")
    print(f"File size: {input_path.stat().st_size / 1024:.1f} KB\n")

    # ===== ENSURE OUTPUT DIRECTORY =====
    output_dir = Path(args.out)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"❌ ERROR: Could not create output directory:")
        print(f"  {output_dir}")
        print(f"  {e}")
        sys.exit(1)

    # ===== CREATE SONG-SPECIFIC SUBFOLDER =====
    # Extract song title from input filename (without extension)
    song_title = input_path.stem
    song_output_dir = output_dir / song_title
    try:
        song_output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"❌ ERROR: Could not create song output directory:")
        print(f"  {song_output_dir}")
        print(f"  {e}")
        sys.exit(1)

    print(f"Output directory: {song_output_dir}\n")

    # ===== VALIDATE SOUNDFONT =====
    soundfont_path = Path(args.soundfont)
    if not soundfont_path.exists():
        print(f"❌ ERROR: Soundfont file not found:")
        print(f"  {soundfont_path}")
        print(f"\nSpecify an existing soundfont with: --soundfont <path>")
        sys.exit(1)

    print(f"Soundfont: {soundfont_path}\n")

    # ===== PARSE NWCTXT FILE AND DETERMINE STAFFS TO CONVERT =====
    print("=" * 60)
    print("Parsing NWC file and determining staffs...")
    print("=" * 60 + "\n")

    nwc_file = NwcFile(input_path)
    print(f"Found {len(nwc_file.staffs)} staff(s) in file:")
    for i, staff in enumerate(nwc_file.staffs, 1):
        print(f"  {i}. {staff.name if staff.name else '(unnamed)'}")
    print()

    # Determine which staffs to convert
    if args.staff_names:
        # User specified staff names
        requested = set(args.staff_names)
        available = {s.name for s in nwc_file.staffs if s.name}
        missing = requested - available

        if missing:
            print(f"⚠️  WARNING: Staff name(s) not found: {', '.join(missing)}")
            print(f"Available staffs: {', '.join(sorted(available))}\n")

        staffs_to_convert = [s for s in nwc_file.staffs if s.name in args.staff_names]

        if not staffs_to_convert:
            print("❌ ERROR: None of the requested staffs exist")
            sys.exit(1)
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
        temp_path = song_output_dir / f"{song_title}_temp.nwctxt"

        # 2. Parse fresh copy, mute all, unmute only this staff
        temp_nwc = NwcFile(input_path)
        temp_nwc.set_all_staffs_muted(True, volume=127)
        temp_nwc.set_staff_muted_by_name(staff.name, False, volume=127)
        temp_nwc.write_to_file(temp_path)

        print(f"Created temporary file with only '{staff.name}' unmuted\n")

        # 3. Generate output paths with staff name
        midi_path = song_output_dir / f"{song_title} {staff.name}.mid"
        wav_path = song_output_dir / f"{song_title} {staff.name}.wav"
        flac_path = song_output_dir / f"{song_title} {staff.name}.flac"

        # 4. Run conversion pipeline (3 steps)
        # STEP 1: NWC → MIDI
        cmd1 = f'nwc-conv "{temp_path}" "{midi_path}" -1'
        if not run_conversion_step(
            1,
            f"Converting {staff.name} to MIDI",
            cmd1,
            midi_path
        ):
            if not args.no_cleanup:
                temp_path.unlink(missing_ok=True)
            sys.exit(1)

        # STEP 2: MIDI → WAV
        cmd2 = f'fluidsynth -n -F "{wav_path}" "{soundfont_path}" "{midi_path}"'
        if not run_conversion_step(
            2,
            f"Converting {staff.name} MIDI to WAV",
            cmd2,
            wav_path
        ):
            if not args.no_cleanup:
                temp_path.unlink(missing_ok=True)
            sys.exit(1)

        # STEP 3: WAV → FLAC
        cmd3 = f'ffmpeg -y -i "{wav_path}" "{flac_path}"'
        if not run_conversion_step(
            3,
            f"Converting {staff.name} WAV to FLAC",
            cmd3,
            flac_path
        ):
            if not args.no_cleanup:
                temp_path.unlink(missing_ok=True)
            sys.exit(1)

        # 5. Remove temporary NWC file (unless --no-cleanup)
        if not args.no_cleanup:
            temp_path.unlink(missing_ok=True)
            print(f"Removed temporary file: {temp_path.name}\n")
        else:
            print(f"Kept temporary file: {temp_path} (--no-cleanup)\n")

        flac_outputs.append(flac_path)

    # ===== CLEANUP: REMOVE INTERMEDIATE FILES =====
    if not args.no_cleanup:
        print("=" * 60)
        print("Cleaning up intermediate files...")
        print("=" * 60 + "\n")

        removed_count = 0
        for mid_file in song_output_dir.glob("*.mid"):
            mid_file.unlink()
            print(f"  Removed: {mid_file.name}")
            removed_count += 1

        for wav_file in song_output_dir.glob("*.wav"):
            wav_file.unlink()
            print(f"  Removed: {wav_file.name}")
            removed_count += 1

        if removed_count > 0:
            print(f"\nRemoved {removed_count} intermediate file(s)\n")
    else:
        print("=" * 60)
        print("Skipping cleanup (--no-cleanup specified)")
        print("=" * 60 + "\n")
        print("Intermediate files kept:")
        print(f"  - Temporary .nwctxt files: {song_output_dir}/*_temp.nwctxt")
        print(f"  - MIDI files: {song_output_dir}/*.mid")
        print(f"  - WAV files: {song_output_dir}/*.wav\n")

    # ===== SUCCESS =====
    print("=" * 60)
    print("✅ SUCCESS: All conversions completed!")
    print("=" * 60)
    print(f"\nFinal output ({len(flac_outputs)} file(s)):")
    for flac_file in flac_outputs:
        print(f"  {flac_file}")
    print()


if __name__ == '__main__':
    main()
