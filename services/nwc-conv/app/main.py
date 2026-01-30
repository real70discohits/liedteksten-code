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

from nwc_convert import ( 
    verify_tools 
)

app = FastAPI(
    title="Noteworthy Composer (NWCTXT) > MIDI > WAV > FLAC Conversion API",
    description="API for converting NWCTXT files to FLAC",
    version="1.0.0"
)

# Security: restrict working directories
WORK_DIR = Path("/tmp/nwc-work")
OUTPUT_DIR = Path("/tmp/audio-output")

# Ensure directories exist
WORK_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Maximum file sizes
MAX_FLAC_SIZE = 30 * 1024 * 1024  # 30MB


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "nwc-conversie-api"}


@app.get("/hello")
async def hello():
    """
    Say 'hello'
    """
    return JSONResponse(
        content={
            "answer": "hello too"
        }
    )

@app.post("/convert")
async def convert_nwctxt(
    nwctxt_file: UploadFile = File(..., description="NoteWorthy .nwctxt file to convert"),
):
    """
    Converts an .nwctxt noteworthy composer file to audio (.flac)
    """
    if not verify_tools():
        raise HTTPException(status_code=500, detail="Tools are not installed or \
configured properly on the server")
    
    return JSONResponse(
        content={
            "answer": "Verified tools. No conversions yet."
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
