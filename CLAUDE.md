# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
   - Use NoteWorthy Composer GUI to create individual .nwctxt files for each song section (intro, verse, chorus, etc.)
   - Store in git repository: `<input_folder>/<Song Title>/nwc/`
   - Create `volgorde.jsonc` to define section sequence

2. **Run nwc-concat.py**
   - Creates merged .nwctxt file → **build folder**
   - Creates analysis.txt (lyrics mapped to measures) → **build folder**
   - Creates structuur.tex (song structure/statistics) → **build folder**
   - Updates tempo and time signature in liedtekst .tex → **git repository**
   - Creates labeltrack.txt (for Tenacity/Audacity) → **audio_output_folder**

3. **Run nwc-convert.py** (optional, for audio demos)
   - Calls nwc-conv.exe: .nwctxt → .mid → **audio_output_folder**
   - Calls fluidsynth.exe: .mid → .wav → **audio_output_folder**
   - Calls ffmpeg.exe: .wav → .flac → **audio_output_folder**

4. **Create/update lyrics** (Manual)
   - Create or update liedtekst .tex file in git repository
   - Use analysis.txt (from build folder) as reference for measure numbers and structure

5. **Run lt-generate.py**
   - Renders liedtekst PDFs (all variants) → **distribution folder**
   - Renders structuur.pdf → **distribution folder**

6. **Run lt-upload.ps1** (optional)
   - Uploads generated PDFs from dist folder to PDrive (cloud storage)

7. **Create audio recording** (Manual)
   - Import .flac file into Tenacity (from audio_output_folder)
   - Import labeltrack.txt into Tenacity (from audio_output_folder)
   - Make recording with properly labeled sections

### Storage Locations

- **git repository** (`input_folder`): Source files (.tex, .nwctxt, volgorde.jsonc, lt-config.jsonc)
- **build folder** (`build_folder`): Intermediate files (merged .nwctxt, analysis.txt, structuur.tex)
- **distribution folder** (`distributie_folder`): Final PDFs ready for distribution
- **audio_output_folder**: Audio files (.mid, .wav, .flac) and labeltrack.txt for Tenacity
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

```
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

# Generate only specific variant (1=basic, 2=measures, 3=chords, 4=measures+chords, 5=all)
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

# Convert to audio formats
python nwc-convert.py "song.nwctxt"
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

The script also generates "structuur" PDFs from auto-generated .tex files in the build folder. **Note**: structuur.tex files are NOT deleted after successful compilation (changed from previous behavior).

### Transposition System

Songs can specify transpositions in .tex files using `\newcommand{\transpositions}{2, 3}`. The system:
- Always generates transpose=0 version
- Plus additional transpositions specified
- Updates output filename with key and transposition info
- Uses German note names (Cis=C#, Des=Db, etc.)

The `transpose()` function in `lt-generate.py` preserves chord extensions and handles both sharps (is) and flats (es).

### Configuration Matching

`lt_configloader.py` provides layout override system:
- Song-specific `lt-config.jsonc` files define conditions (song ID, display options) and actions (margin/fontsize adjustments)
- Matching uses wildcards: `null` values in conditions match any setting
- **First match wins**: Order matters in config arrays

### NWC File Processing

NWC files have:
- Header section (file metadata)
- Multiple staffs (Bass, Zang, etc.)
- Each staff has properties, notes, bars, tempo, etc.

Key concepts:
- **Begintel** (pickup measure): Detected when `StartingBar:0` and first Rest before first Bar
- **Vooraf** measures: Count before "liedstart" marker (minus begintel if present)
- **Measure counting**: Uses Bar markers and Dur: elements to determine measure boundaries

`nwc_utils.py` provides:
- `NwcFile` class: Parse and access staffs by name or index
- `NwcStaff` class: Represents individual staff with name extraction
- `parse_nwctxt()`: Legacy function for backward compatibility

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
- `constants.py`: Centralized string constants (prefixes, file extensions, staff names)
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
- `{title} ({id})`: Basic song
- `{title} ({id}) in {key} transp({+/-n})`: Transposed version
- `{title} ({id}) met akkoorden`: With chords
- `{title} ({id}) met maatnummers, akkoorden en gitaargrepen`: Full version
- `{title} structuur.tex/.pdf`: Song structure analysis

## Testing Considerations

When testing changes:
- Always test with `--no-cleanup` to inspect auxiliary files
- Check both single-song and multi-song processing
- Verify all 5 variants generate correctly (`--only 1` through `--only 5`)
- Test path resolution with both relative and absolute paths
- Validate generated filenames don't contain invalid characters
