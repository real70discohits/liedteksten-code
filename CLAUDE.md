# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Overview

This is a Python-based toolkit for managing and generating files related to
pop songs such as lyrics, lyrics with guitar tabs and chords, but also
helper files that map lyrics to measures and structure files that show lied
statistics and structure or 'composition' in terms of order of sections
('lieddelen') and their inner structure of chords and measures.

Per song ('lied') the system has 2 files as input, which it processes to generate
derived files. The single-source-of-truth is a NoteWorthy Composer (.nwctxt) file
and for the exact lyrics text the source of truth is the .tex (LaTeX) file
from which the system generates PDFs with multiple variants (with/without tabs,
chords, measure numbers).

The purpose of the system is to automate the tedious manual song creation and
maintenance workflow. A few
examples: when the tempo is changed in the .nwctxt file and script nwc-concat
is run, it updates the tempo mentioned in the .tex file as well (so no manual
action needed). Much more rewarding is that, by the same script, from the
.nwctxt file a labeltrack for Audacity (Tenacity) is generated which can be
easily imported into Audacity: when now the tempo has changed, in the old days
I had to adjust manually all the positions of the labels in the labeltrack.
Imagine what that means when I'm figuring out the right tempo and try several
settings. With this automated, the only thing I need to do is rerun the script
and import the labeltrack: done in a few seconds. Another example is that in the
old days for some songs I had a few variants: some with different chords
(transpositions) or some with guitarchords and -tabs or without. These were
all in separate MS Word documents, so imagine what happened when after some
months I decided to change a single word in the lyrics: I had to go through
all those files. With these python scripts, per song I have a single
sourcefile from which I can generate multiple outputs: I only have to change
the lyrics in one place. That's not entirely true, btw, because it's best
that I update it in the .nwctxt file as well, but that is not necessary. I hope
it's understandable how happy I am with this automation.

## Complete Workflow

The typical workflow for creating/updating a song (visualized in `project/schema.pu`):

1. **Create music notation** (Manual)
   - Use NoteWorthy Composer GUI to create individual .nwctxt files for each
   song section (intro, verse, chorus, etc.)
   - Store in git repository: `<input_folder>/<Song Title>/nwc/`
   - Create `volgorde.jsonc` to define section sequence

2. **Run nwc-concat.py**
   - Creates merged .nwctxt file → **build folder**
   - Creates analysis.txt (lyrics mapped to measures) → **build folder**
   - Creates structuur.tex (song structure/statistics) → **build folder**
   - Updates tempo and time signature in liedtekst .tex → **git repository**
   - Creates labeltrack.txt (for Tenacity/Audacity) → **audio_output_folder**

3. **Run nwc-convert.py** (optional, for audio demos)
   - Converts each staff separately to individual .flac files
   - For each staff: creates temp .nwctxt with only that staff unmuted
   - Calls nwc-conv.exe: .nwctxt → .mid
   - Calls fluidsynth.exe: .mid → .wav
   - Calls ffmpeg.exe: .wav → .flac → **audio_output_folder**
   - Cleans up intermediate files (.mid, .wav), keeps only .flac
   - Output: `{song_title} {staff_name}.flac` for each staff

4. **Create/update lyrics** (Manual)
   - Create or update liedtekst .tex file in git repository
   - Use analysis.txt (from build folder) as reference for measure numbers and structure

5. **Run lt-generate.py**
   - Renders liedtekst PDFs (all variants) → **distribution folder**
   - Renders structuur.pdf → **distribution folder**

6. **Run lt-upload.ps1** (optional)
   - Uploads generated PDFs from dist folder to PDrive (cloud storage)

7. **Create audio recording** (Manual)
   - Import individual staff .flac files as separate tracks into Tenacity (from audio_output_folder)
   - Import labeltrack.txt into Tenacity (from audio_output_folder)
   - Make recording with properly labeled sections

### Storage Locations

- **git repository** (`input_folder`): Source files (.tex, .nwctxt,
volgorde.jsonc, lt-config.jsonc)
- **build folder** (`build_folder`): Intermediate files (merged .nwctxt,
analysis.txt, structuur.tex)
- **distribution folder** (`distributie_folder`): Final PDFs ready for distribution
- **audio_output_folder**: Audio files (one .flac per staff: `{song} {staff}.flac`)
and labeltrack.txt for Tenacity. Intermediate .mid and .wav files are automatically
cleaned up after conversion.
- **PDrive**: Cloud backup of generated PDFs (via lt-upload.ps1)

## Core Architecture

### Processing Pipeline

The workflow follows three main paths:

1. **NWC → Audio**: `nwc-concat.py` → `nwc-convert.py`
   - Concatenates song sections from individual .nwctxt files
   - Converts to MIDI → WAV → FLAC for audio playback

2. **LaTeX → PDF**: `lt-generate.py`
   - Compiles .tex files into PDFs with various display options
   - Generates multiple variants per song (5+ combinations)
   - Applies song-specific layout configurations

3. **Analysis**: `nwc_analyze.py`
   - Maps lyrics to measure numbers
   - Extracts metadata from .nwctxt files

### Path Configuration System

All scripts use `pathconfig.py` to load paths from `paths.jsonc`:

- Input folder: Contains song folders with .tex and nwc/ subdirectories
- Build folder: Intermediate files (merged .nwctxt, analysis.txt, structuur.tex)
- Distribution folder: Final PDFs ready for distribution
- Audio output folder: MIDI/WAV/FLAC files

**Important**: Paths can be relative (to paths.jsonc) or absolute. Use
`load_and_resolve_paths()` at the start of script `main()` functions.

### Song Folder Structure

```txt
<input_folder>/
  <Song Title>/
    <Song Title>.tex                    # LaTeX lyrics with chords/tabs
    lt-config.jsonc                     # Optional layout overrides
    nwc/
      <Song Title> intro.nwctxt         # Individual song sections
      <Song Title> verse.nwctxt
      <Song Title> volgorde.jsonc       # Defines section sequence
```

## Key Commands

### Build/Generate PDFs

```bash
# Generate all variants for all songs
python lt-generate.py

# Generate for specific songs
python lt-generate.py "song1" "song2"

# Generate only specific variant (1=basic, 2=maten, 3=chords, 4=maten+chords, 5=all)
python lt-generate.py "song" --only 3

# Keep auxiliary files for debugging
python lt-generate.py "song" --no-cleanup

# Custom tab orientation
python lt-generate.py "song" --tab-orientation right
```

### Process NWC Files

```bash
# Concatenate song sections and generate structure
python nwc-concat.py "Song Title"

# Keep tempo markings in all sections (default: only first)
python nwc-concat.py "Song Title" --keep-tempi

# Convert to audio formats (all staffs separately)
python nwc-convert.py "song.nwctxt"

# Convert only specific staffs
python nwc-convert.py "song.nwctxt" --staff-names Bass Ritme

# Keep intermediate files for debugging
python nwc-convert.py "song.nwctxt" --no-cleanup

# Custom output and soundfont
python nwc-convert.py "song" --out "C:\output" --soundfont "path\to\font.sf2"

# Analyze lyrics mapping
python nwc_analyze.py "path\to\song.nwctxt"
```

### Environment Setup

```bash
# Initialize virtual environment (git bash)
python -m venv .venv
source .venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt
```

## Important Implementation Details

### LaTeX Compilation Process

`lt-generate.py` compiles each .tex file **twice** to resolve references:

- First pass: Build initial PDF, keep auxiliary files
- Second pass: Final PDF with correct page numbers/references
- Cleanup only happens after second pass (unless `--no-cleanup`)

The script also generates "structuur" PDFs from auto-generated .tex
files in the build folder. **Note**: structuur.tex files are NOT
deleted after successful compilation (changed from previous behavior).

### Transposition System

Songs can specify transpositions in .tex files using
`\newcommand{\transpositions}{2, 3}`. The system:

- Always generates transpose=0 version
- Plus additional transpositions specified
- Updates output filename with key and transposition info
- Uses German note names (Cis=C#, Des=Db, etc.)

The `transpose()` function in `lt-generate.py` preserves chord
extensions and handles both sharps (is) and flats (es).

### Configuration Matching

`lt_configloader.py` provides layout override system:

- Song-specific `lt-config.jsonc` files define conditions (song ID, display
options) and actions (margin/fontsize adjustments)
- Matching uses wildcards: `null` values in conditions match any setting
- **First match wins**: Order matters in config arrays

### NWC File Processing

NWC files have:

- Header section (file metadata)
- Multiple staffs (Bass, Zang, etc.)
- Each staff has properties, notes, bars, tempo, etc.

Key concepts:

- **Begintel** (pickup measure): Detected when `StartingBar:0` and first Rest
- before first Bar
- **Vooraf** measures: Count before "liedstart" marker (minus begintel if present)
- **Measure counting**: Uses Bar markers and Dur: elements to determine measure boundaries

`nwc_utils.py` provides:

- `NwcFile` class: Parse and access staffs by name or index
  - `get_staff_by_name(name)`: Get staff by name
  - `get_staff_by_index(index)`: Get staff by zero-based index
  - `write_to_file(filepath)`: Write modified NwcFile to disk
  - `set_all_staffs_muted(muted, volume)`: Mute/unmute all staffs with specified volume
  - `set_staff_muted_by_name(name, muted, volume)`: Mute/unmute specific staff
- `NwcStaff` class: Represents individual staff with name extraction
  - `set_muted_and_volume(muted, volume)`: Modify Muted and Volume properties in
    the second StaffProperties line (after AddStaff)
- `parse_nwctxt()`: Legacy function for backward compatibility

**Staff Structure**: Each staff has three property lines:
1. `|AddStaff|Name:"..."|...`
2. `|StaffProperties|EndingBar:...|Visible:...|...`
3. `|StaffProperties|Muted:Y/N|Volume:0-127|...` ← Target for mute/volume operations

### Multi-Staff Audio Conversion

`nwc-convert.py` converts each staff to a separate .flac file for multi-track recording:

**Process:**
1. Parse .nwctxt file and identify all staffs (or use `--staff-names` to filter)
2. For each staff:
   - Create temporary .nwctxt copy
   - Mute all staffs (set Muted:Y, Volume:127)
   - Unmute only the current staff (set Muted:N, Volume:127)
   - Convert: temp.nwctxt → .mid → .wav → .flac
   - Delete temporary .nwctxt file
3. Clean up all intermediate .mid and .wav files
4. Keep only final .flac files (one per staff)

**Usage:**
- `--staff-names Bass Ritme`: Convert only specified staffs
- No `--staff-names`: Convert all staffs in the file
- `--no-cleanup`: Keep intermediate files (.mid, .wav, temp .nwctxt) for debugging
- Warns if requested staff names don't exist, but continues with valid ones

**Output:** Creates `{song_title} {staff_name}.flac` files in song-specific subfolder

### Duration Calculation

`nwc-concat.py` calculates timing for label tracks:

- Reads tempo (BPM) and time signature from first section
- Calculates measure duration based on beats per measure
- Tracks cumulative start times for each section
- Handles pickup beats (anacrusis) at song start
- Generates label track files for Tenacity/Audacity

## External Dependencies

The system requires these external tools (verified by `nwc-convert.py`):

- **nwc-conv**: NoteWorthy Composer converter (NWCTXT → MIDI)
- **fluidsynth**: MIDI synthesizer (MIDI → WAV with soundfont)
- **ffmpeg**: Audio converter (WAV → FLAC)
- **pdflatex**: LaTeX compiler (TEX → PDF)

All must be in PATH or specified explicitly.

## Code Organization Principles

### Shared Modules

- `constants.py`: Centralized string constants (prefixes, file extensions,
- staff names)
- `pathconfig.py`: Path resolution and validation utilities
- `nwc_utils.py`: NWC file parsing classes
- `lt_configloader.py`: Configuration loading with dataclasses

### Error Handling Pattern

Scripts use consistent validation:

- `validate_file_exists()`: Check file presence and readability
- `validate_folder_exists()`: Check folder access
- `ensure_folder_writable()`: Create if needed, verify write access
- Always print descriptive errors with file paths
- Use `sys.exit(1)` on fatal errors

### File Naming Conventions

Generated files include metadata in names:

**PDF outputs:**
- `{title} ({id})`: Basic song
- `{title} ({id}) in {key} transp({+/-n})`: Transposed version
- `{title} ({id}) met akkoorden`: With chords
- `{title} ({id}) met maatnummers, akkoorden en gitaargrepen`: Full version
- `{title} structuur.tex/.pdf`: Song structure analysis

**Audio outputs:**
- `{title} {staff_name}.flac`: One file per staff (e.g., "Example Song Bass.flac")
- Intermediate .mid and .wav files are automatically cleaned up

## Testing Considerations

When testing changes:

- Always test with `--no-cleanup` to inspect auxiliary files
- Check both single-song and multi-song processing
- Verify all 5 variants generate correctly (`--only 1` through `--only 5`)
- Test path resolution with both relative and absolute paths
- Validate generated filenames don't contain invalid characters

## Cloud API (Docker Container)

The system includes a Docker-based REST API for cloud deployment, allowing remote PDF generation without local LaTeX installation.

### Architecture

**Local vs Cloud:**
- **Local**: Uses `lt-generate.py` directly with `paths.jsonc` configuration
- **Cloud**: Uses Docker container with FastAPI endpoints that wrap `lt-generate.py` functionality

**Key differences:**
- Cloud API accepts file uploads instead of local file paths
- Config files are cached in-memory (or persistent volume if mounted)
- Multiple PDFs are returned as ZIP file with timestamp
- No `paths.jsonc` needed - API manages temporary directories internally

### Docker Structure

```
app/
  main.py                    # FastAPI application with endpoints
  lt_generate_api.py         # API-specific wrapper around lt-generate.py
  lt_generate.py             # Original script (imported, not modified)
  lt_configloader.py         # Config loader
  pathconfig.py              # Path utilities (imported but not used in API)
  liedbasis.sty             # LaTeX package
  cache/
    configs/                 # Cached lt-config.jsonc files (keyed by song title)
```

### API Endpoints

**`POST /compile`**
- Upload .tex file → returns ZIP with PDFs
- Optional: config_file (also caches for future use)
- Optional: sty_file (custom liedbasis.sty override)
- Parameters: `only` (0/-1/1-5), `tab_orientation` (left/right/traditional)
- Response filename: `{song_title}_{YYYYMMDD_HHMMSS}.zip`
- Automatically detects structuur files (filename ends with " structuur.tex")

**`GET /config/{song_title}`**
- Retrieve cached config for a song

**`POST /config/{song_title}`**
- Upload/update config without compiling

**`DELETE /config/{song_title}`**
- Remove cached config

**`GET /configs`**
- List all cached song titles

**`GET /health`**
- Health check endpoint

### API Workflow

**Single request (with config):**
```bash
curl -X POST http://api-url/compile \
  -F "tex_file=@Such A Beauty (6).tex" \
  -F "config_file=@lt-config.jsonc" \
  -F "only=5" \
  -OJ
```

**Pre-cache configs:**
```bash
# Upload config once
curl -X POST http://api-url/config/Such%20A%20Beauty%20(6) \
  -F "config_file=@lt-config.jsonc"

# Later: compile without config (uses cache)
curl -X POST http://api-url/compile \
  -F "tex_file=@Such A Beauty (6).tex" \
  -OJ
```

### Config Caching Mechanism

**Cache key:** Song title extracted from .tex filename
- `"Such A Beauty (6).tex"` → cache key: `"Such A Beauty (6)"`
- Stored as: `/app/cache/configs/Such A Beauty (6).jsonc`

**Cache behavior:**
- If config uploaded in request: use immediately + cache for future
- If no config in request: try to load from cache
- Cache persists for container lifetime (use volume mount for persistence)

**Pre-loading configs in image:**
- Existing configs can be copied to `app/cache/configs/` during Docker build
- Useful for rarely-changing configs

### Response Format

**Success:**
```
ZIP file containing:
  - All generated PDFs (including transpositions)
  - console.log (captured stdout/stderr)
```

**Failure:**
```
ZIP file containing:
  - error.txt (error message + console output)
  - *.log (LaTeX log files)
  - console.log (captured stdout/stderr)
```

### LaTeX Packages in Docker

The Docker image includes TinyTeX with these packages:
- **Core**: collection-latex, collection-fontsrecommended, collection-latexrecommended
- **Graphics/Layout**: pgf, tikz-cd, currfile, lastpage, anyfontsize, xstring, savesym
- **Music**: gchords, leadsheets, translations, musixtex, musixtex-fonts, musixguit
- **L3**: l3kernel, l3packages, l3experimental
- **Utilities**: xcolor, etoolbox, metafont

### Docker Commands

**Build:**
```bash
docker build -t liedteksten-api .
```

**Run:**
```bash
# Basic
docker run -p 8000:8000 liedteksten-api

# With persistent config cache
docker run -p 8000:8000 \
  -v /path/to/configs:/app/cache/configs \
  liedteksten-api
```

**Deploy to cloud:**
- Scaleway, Azure Container Apps, Google Cloud Run, etc.
- Ensure volume mount for `/app/cache/configs` if persistence needed
- No special environment variables required

### API Implementation Details

**`lt_generate_api.py` functions:**
- `compile_for_api()`: Main entry point, creates temp directories and orchestrates compilation
- `compile_liedtekst_variants()`: Generates all variants (1-5) based on `only` parameter
- `compile_tex_variant()`: Compiles single variant with specific parameters (adapted from original `compile_tex_file()`)
- `compile_tex_simple()`: For structuur documents (no variants)
- `extract_song_title_from_filename()`: Extracts cache key from filename
- `is_structuur_file()`: Checks if filename ends with " structuur.tex"
- `create_temp_structure()`: Creates required directory structure for compilation

**Console output capture:**
- Uses `io.StringIO` to redirect `sys.stdout` and `sys.stderr`
- Captured output included in ZIP as `console.log`
- Allows debugging without SSH access to container

**Temporary directory management:**
- Each request gets unique temp dir: `/tmp/ltgen_{uuid}/`
- Structure: `input/{song_title}/{song_title}.tex` + optional config
- Cleaned up after ZIP creation (success or failure)

**Custom .sty handling:**
- If uploaded: placed in temp root, TEXINPUTS updated to include temp root
- LaTeX searches current dir first, then system tree → uploaded .sty takes precedence
- Default liedbasis.sty installed at: `/home/pdfgen/.TinyTeX/texmf-dist/tex/latex/local/`

### Security Considerations

- Container runs as non-root user `pdfgen` (UID 1001)
- File size limits: .tex (10MB), .jsonc (1MB), .sty (5MB)
- pdflatex runs with `-no-shell-escape` (prevents arbitrary code execution)
- Temporary directories isolated per request
- No access to host filesystem (except mounted volumes)

### Differences from Local Workflow

**What's the same:**
- Same LaTeX compilation (pdflatex, twice for references)
- Same variant generation logic (1-5)
- Same transposition handling
- Same config matching system
- Same output filename conventions

**What's different:**
- No `paths.jsonc` - API manages temp directories
- Song title from filename, not command-line argument
- Config identified by song title, not folder location
- Multiple PDFs packaged as ZIP instead of separate files
- Console output captured and included in response
- No `--no-structuur` option - structuur files uploaded separately

### Troubleshooting

**"Module not found" errors:**
- Ensure `lt-generate.py` renamed to `lt_generate.py` (no hyphen) in app/ folder

**"File not found" LaTeX errors:**
- Check Dockerfile has all required packages
- Rebuild image after package changes

**Config not found:**
- Verify song title extraction matches cache key
- Check `/app/cache/configs/` contents with `docker exec`

**Large response times:**
- First compilation takes longer (font cache generation)
- Subsequent compilations faster
- Consider pre-warming container with dummy compile

For complete API documentation, see `API-README.md`.
