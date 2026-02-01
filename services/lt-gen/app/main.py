"""
FastAPI application for lt-generate PDF compilation service.
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

from lt_generate_api import (
    compile_for_api,
    extract_song_title_from_filename,
    get_cached_config,
    save_config_to_cache,
    delete_cached_config,
    list_cached_configs
)

app = FastAPI(
    title="Liedteksten PDF Generation API",
    description="API for generating PDF files from LaTeX song lyrics",
    version="1.0.0"
)

# Security: restrict working directories
WORK_DIR = Path("/tmp/tex-work")
OUTPUT_DIR = Path("/tmp/pdf-output")

# Ensure directories exist
WORK_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Maximum file sizes
MAX_TEX_SIZE = 10 * 1024 * 1024  # 10MB
MAX_CONFIG_SIZE = 1 * 1024 * 1024  # 1MB
MAX_STY_SIZE = 5 * 1024 * 1024  # 5MB


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "liedteksten-pdf-api"}


@app.post("/compile")
async def compile_tex(
    tex_file: UploadFile = File(..., description="LaTeX .tex file to compile"),
    config_file: Optional[UploadFile] = File(None, description="Optional lt-config.jsonc file"),
    sty_file: Optional[UploadFile] = File(None, description="Optional custom liedbasis.sty file"),
    only: int = Form(default=0, description="Variant to generate: 0=all, -1=configured only, 1-5=specific variant"),
    tab_orientation: str = Form(default="left", description="Guitar tab orientation: left, right, or traditional"),
    large_print: bool = Form(default=False, description="Optimize PDF output for readability: true/false")
):
    """
    Compile a .tex file to PDF(s).

    The .tex filename determines the song title and whether it's a structuur document:
    - Regular liedtekst: "Such A Beauty (6).tex"
    - Structuur document: "Such A Beauty (6) structuur.tex"

    Returns a ZIP file containing:
    - On success: all generated PDFs + console.log
    - On failure: error.txt + any .log files + console.log

    If config_file is provided, it will be cached for future requests.
    If not provided, the API checks for a cached config.
    """
    # Validate tex file
    if not tex_file.filename.endswith('.tex'):
        raise HTTPException(status_code=400, detail="Only .tex files are allowed for tex_file")

    # Validate tab_orientation
    if tab_orientation not in ['left', 'right', 'traditional']:
        raise HTTPException(status_code=400, detail="tab_orientation must \
                            be 'left', 'right', or 'traditional'")

    # Validate only parameter
    if only < -1 or only > 5:
        raise HTTPException(status_code=400, detail="only must be between -1 and 5")

    # Extract song title
    song_title = extract_song_title_from_filename(tex_file.filename)

    try:
        # Read tex file
        tex_content = await tex_file.read()
        if len(tex_content) > MAX_TEX_SIZE:
            raise HTTPException(status_code=400, detail=f"tex_file too \
                                large (max {MAX_TEX_SIZE/1024/1024}MB)")
        tex_content = tex_content.decode('utf-8')

        # Handle config file
        config_content = None
        if config_file:
            # Validate config file
            if not config_file.filename.endswith('.jsonc'):
                raise HTTPException(status_code=400, detail="config_file must be a .jsonc file")

            config_bytes = await config_file.read()
            if len(config_bytes) > MAX_CONFIG_SIZE:
                raise HTTPException(status_code=400, detail=f"config_file too \
                                    large (max {MAX_CONFIG_SIZE/1024/1024}MB)")

            config_content = config_bytes.decode('utf-8')

            # Save to cache
            save_config_to_cache(song_title, config_content)
        else:
            # Try to get from cache
            config_content = get_cached_config(song_title)

        # Handle custom sty file
        sty_content = None
        if sty_file:
            # Validate sty file
            if not sty_file.filename.endswith('.sty'):
                raise HTTPException(status_code=400, detail="sty_file must be a .sty file")

            sty_bytes = await sty_file.read()
            if len(sty_bytes) > MAX_STY_SIZE:
                raise HTTPException(status_code=400, detail=f"sty_file too \
                                    large (max {MAX_STY_SIZE/1024/1024}MB)")

            sty_content = sty_bytes.decode('utf-8')

        # Compile
        result = compile_for_api(
            tex_filename=tex_file.filename,
            tex_content=tex_content,
            config_content=config_content,
            sty_content=sty_content,
            only=only,
            tab_orientation=tab_orientation,
            large_print=large_print
        )

        # Create ZIP file
        zip_path = OUTPUT_DIR / f"{os.urandom(8).hex()}.zip"

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if result.success:
                # Add PDFs
                for pdf_file in result.pdf_files:
                    zipf.write(pdf_file, pdf_file.name)

                # Add console output
                zipf.writestr("console.log", result.console_output)

                # Clean up temp files (PDF source files)
                for pdf_file in result.pdf_files:
                    if pdf_file.exists():
                        # Get the temp root directory and clean it up
                        temp_root = pdf_file.parent.parent
                        if temp_root.exists() and temp_root.name.startswith("ltgen_"):
                            shutil.rmtree(temp_root, ignore_errors=True)
            else:
                # Add error info
                error_text = "Compilation failed\n\n"
                if result.error_message:
                    error_text += f"Error: {result.error_message}\n\n"
                error_text += f"Console output:\n{result.console_output}"
                zipf.writestr("error.txt", error_text)

                # Add log files
                for log_file in result.log_files:
                    if log_file.exists():
                        zipf.write(log_file, log_file.name)

                # Add console output
                zipf.writestr("console.log", result.console_output)

                # Clean up temp files
                if result.log_files:
                    temp_root = result.log_files[0].parent.parent
                    if temp_root.exists() and temp_root.name.startswith("ltgen_"):
                        shutil.rmtree(temp_root, ignore_errors=True)

        # Generate filename with timestamp: "Such A Beauty (6)_20260102_153045.zip"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_filename = f"{song_title}_LIEDTEKST_{timestamp}.zip"

        # Return ZIP
        response = FileResponse(
            path=zip_path,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{download_filename}"'
            }
        )

        # Schedule cleanup of ZIP file after response
        # Note: FastAPI will handle this, but we can also use background tasks
        # For now, we accept that old ZIPs will accumulate in OUTPUT_DIR
        # In production, you'd want a cleanup task

        return response

    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Files must be UTF-8 encoded")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/config/{song_title}")
async def get_config(song_title: str):
    """
    Get cached configuration for a song.

    Returns the lt-config.jsonc content as JSON if found.
    """
    config_content = get_cached_config(song_title)

    if config_content is None:
        raise HTTPException(status_code=404, detail=f"No cached config found for '{song_title}'")

    return JSONResponse(
        content={"song_title": song_title, "config": config_content},
        media_type="application/json"
    )


@app.post("/config/{song_title}")
async def upload_config(
    song_title: str,
    config_file: UploadFile = File(..., description="lt-config.jsonc file to cache")
):
    """
    Upload and cache a configuration file for a song.

    This allows pre-caching configs without compiling.
    """
    # Validate config file
    if not config_file.filename.endswith('.jsonc'):
        raise HTTPException(status_code=400, detail="config_file must be a .jsonc file")

    try:
        config_bytes = await config_file.read()
        if len(config_bytes) > MAX_CONFIG_SIZE:
            raise HTTPException(status_code=400, detail=f"config_file too \
                                large (max {MAX_CONFIG_SIZE/1024/1024}MB)")

        config_content = config_bytes.decode('utf-8')

        # Save to cache
        save_config_to_cache(song_title, config_content)

        return JSONResponse(
            content={
                "message": f"Config cached successfully for '{song_title}'",
                "song_title": song_title
            },
            status_code=201
        )

    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Config file must be UTF-8 encoded")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cache config: {str(e)}")


@app.delete("/config/{song_title}")
async def delete_config(song_title: str):
    """
    Delete cached configuration for a song.
    """
    deleted = delete_cached_config(song_title)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"No cached config found for '{song_title}'")

    return JSONResponse(
        content={
            "message": f"Config deleted successfully for '{song_title}'",
            "song_title": song_title
        }
    )


@app.get("/configs")
async def list_configs():
    """
    List all cached configurations.

    Returns a list of song titles that have cached configs.
    """
    configs = list_cached_configs()

    return JSONResponse(
        content={
            "count": len(configs),
            "configs": sorted(configs)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
