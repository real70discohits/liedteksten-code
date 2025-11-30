"""
This module is for generating PDF's based on LaTeX (.tex) sourcefiles
that contain my songtexts with measures, chords and guitartabs.

main() is called, defined at the bottom of this file.

py lt-generate.py - processes all .tex files
py lt-generate.py file1, file2 - processes 2 .tex files
py lt-generate.py file1, file2 --no-cleanup processes 2 .tex files and keeps all
    temporary an auxiliary files - which you want if you have to rerun after
    collecting statistics from the first round (such as total nr of pages).

Some configuration for processing liedteksten is read from liedteksten.config.json.

Dependencies:
- pathconfig module (for path configuration)
"""
import os
import re
import subprocess
import argparse
from pathlib import Path
from lt_configloader import ConfigItem, ConfigLoader, get_config
from pathconfig import load_and_resolve_paths, validate_file_exists


# pylint: disable=trailing-whitespace,missing-docstring,line-too-long


# *** Process a single tex file into multiple output pdf's. ***
#
# Note that currently this method is called multiple times for a
# single .tex file, covering configurations like with-tabs, without-tabs,
# with measurenumbers and without. So the multiple output pdf's on
# a single call to this method only happens if a song has multiple transpositions.
def compile_tex_file(
    songtitle, input_folder, output_folder, cleanup=True, engine='pdflatex',
    show_measures=False, show_chords=False, show_tabs=False, tab_orientation='left'):

    # ***  Verify .tex file exists ***
    tex_file = input_folder / songtitle / f"{songtitle}.tex"
    if not validate_file_exists(tex_file, f"LaTeX file for '{songtitle}'"):
        return False

    # ***  Load song-specific configuration ***
    song_folder = input_folder / songtitle
    lt_config_file = song_folder / "lt-config.jsonc"
    configurations = ConfigLoader.load_from_file_optional(lt_config_file)

    # ***  Read .tex file  ***
    with open(tex_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # ***  Extract metadata  ***
    title_match = re.search(r'\\newcommand{\\liedTitel}{(.*?)}', content)
    id_match = re.search(r'\\newcommand{\\liedId}{(.*?)}', content)
    key_match = re.search(r'\\newcommand{\\sleutel}{(.*?)}', content)
    transpositions_match = re.search(r'\\newcommand{\\transpositions}{(.*?)}', content)

    if not title_match or not id_match:
        print(f"⚠️  Skipping {songtitle}: metadata not found")
        return False

    song_title = title_match.group(1)
    song_id = int(id_match.group(1))

    # ***  Parse transpositions ***
    additional_transpositions = []
    if transpositions_match:
        # Extract numbers from "2, 3" or "2,3" or "-2, 3"
        trans_str = transpositions_match.group(1)
        # Find all integers (including negative)
        additional_transpositions = [int(x) for x in re.findall(r'-?\d+', trans_str) if x != '0']

    # Always compile with transpose=0, plus any extra transpositions
    transpositions = [0] + additional_transpositions

    print(f"\nCompiling {len(transpositions)} transposition(s) for {songtitle}")

    success_count = 0

    for transposition in transpositions:

        # ***  Build outputfile name  ***
        parts = [song_title, f"({song_id})"]    # e.g. vla (55)

        if transposition != 0:
            if key_match:
                chord = transpose(key_match.group(1), transposition)
                parts.append(f"in {chord}")          # e.g. vla (55) in A
            parts.append(f'transp({transposition:+d})')

        output_name = " ".join(parts)
        output_name = re.sub(r'[^\w\-\s()]', '', output_name)
        _measurestext = 'maatnummers' if show_measures else ''
        _chordstext = 'akkoorden' if show_chords else ''
        _gittabtext = 'gitaargrepen' if show_tabs else ''
        output_name = output_name + maak_opsomming([_measurestext, _chordstext, _gittabtext])       # e.g. vla (55) in A met maatnummers, akkoorden en gitaargrepen
        print(f"   Generating: {output_name}.pdf")


        # *** Build the TeX command string ***
        _showmeasures = 'true' if show_measures else 'false'
        _showchords = 'true' if show_chords else 'false'
        _showtabs = 'true' if show_tabs else 'false'

        # lookup configuration for set_margins and set_fontsize
        _set_margins = ""
        _set_fontsize = ""
        lied_config: ConfigItem = get_config(configurations, song_id,
                                            show_measures, show_chords,
                                            show_tabs, tab_orientation)

        if not lied_config:
            print(f"   No configuration found for id {song_id} with these parametersettings.")  # not an error
        else:
            print(f"   Applying configuration: {lied_config.description}.")  # not an error
            if lied_config.action.adjustMargins:
                _set_margins = f"\\def\\setMargins{{{lied_config.action.adjustMargins}}}"
            if lied_config.action.adjustFontsize:
                _set_fontsize = f"\\def\\setFontsize{{{lied_config.action.adjustFontsize}}}"

        # construct pdflatex arguments
        pdflatex_args = (f""
                    f"{_set_margins}"
                    f"{_set_fontsize}"
                    f"\\def\\showMeasures{{{_showmeasures}}}"
                    f"\\def\\showChords{{{_showchords}}}"
                    f"\\def\\showTabs{{{_showtabs}}}"
                    f"\\def\\guitarTabOrientation{{{tab_orientation}}}"
                    f"\\def\\transpose{{{transposition}}}"
                    f"\\input{{{songtitle}}}")

        print(f"   Sending arguments to pdflatex: {pdflatex_args}")  # for debug

        # input_folder contains the song folders with .tex files
        tex_input_dir = os.path.abspath(input_folder)
        env = os.environ.copy()
        env['TEXINPUTS'] = f'{tex_input_dir}//;' + env.get('TEXINPUTS', '')

        # ***  Compile twice ***
        original_cleanup = cleanup
        i = 0
        while i < 2:
            result = subprocess.run(
                [engine,
                    f'-output-directory={output_folder}',
                    f'-jobname={output_name}'
                    , pdflatex_args
                ],
                capture_output=True,
                text=True,
                check=False,
                env=env
            )

            if result.returncode == 0:

                # Cleanup auxiliary files
                if i == 0:
                    cleanup = False
                else:
                    cleanup = original_cleanup

                if i == 1:
                    # print and count only once
                    print(f"✅ Success: {output_name}.pdf")
                    success_count += 1

                if cleanup:
                    for ext in ['.aux', '.log', '.out', '.toc']:
                        aux_file = output_folder / f"{output_name}{ext}"
                        if aux_file.exists():
                            aux_file.unlink()
            else:
                print(f"❌ Failed: {songtitle}")
                print(result.stderr)
            i += 1

    return success_count


def maak_opsomming(items):
    """construeer 'met maatnummers, akkoorden en gitaargrepen' op basis
    van een array zoals ["maatnummers", "akkoorden", "gitaargrepen"]."""
    items = [item for item in items if item]

    if not items:
        return ""
    elif len(items) == 1:
        return f" met {items[0]}"
    else:
        return f" met {', '.join(items[:-1])} en {items[-1]}"


def transpose(note, semitones):
    """
    Transpose a note by a number of semitones, preserving any chord extensions.
    Invalid notes are returned unchanged.

    Args:
        note: str - A note like 'C', 'Cis', 'Ami', 'Desmaj7', 'Fissus4', etc.
        semitones: int - Number of semitones to transpose (-12 to 12)

    Returns:
        str - The transposed note with original extensions preserved,
              or the original input if not a valid note

    Examples:
        transpose('C', 2) -> 'D'
        transpose('Ami', 1) -> 'Aism'
        transpose('Desmaj7', 3) -> 'Emaj7'
        transpose('K', 2) -> 'K' (invalid, returned as-is)
        transpose('something', 5) -> 'something' (invalid, returned as-is)
    """
    # Define the chromatic scale using sharps (is = sharp)
    chromatic_sharp = ['C', 'Cis', 'D', 'Dis', 'E', 'F', 'Fis', 'G', 'Gis', 'A', 'Ais', 'B']

    # Define the chromatic scale using flats (es = flat)
    chromatic_flat = ['C', 'Des', 'D', 'Es', 'E', 'F', 'Ges', 'G', 'As', 'A', 'Bes', 'B']

    # Mapping from note names to position in chromatic scale
    note_map = {
        'C': 0, 'Cis': 1, 'Ces': 11,
        'D': 2, 'Dis': 3, 'Des': 1,
        'E': 4, 'Eis': 5, 'Es': 3,
        'F': 5, 'Fis': 6, 'Fes': 4,
        'G': 7, 'Gis': 8, 'Ges': 6,
        'A': 9, 'Ais': 10, 'As': 8,
        'B': 11, 'Bis': 0, 'Bes': 10
    }

    # Extract the note name (base note + accidental) and extension
    # Try to match note names from longest to shortest to catch 'Cis' before 'C'
    note_base = None
    extension = ""

    for note_name in sorted(note_map.keys(), key=len, reverse=True):
        if note.startswith(note_name):
            note_base = note_name
            extension = note[len(note_name):]
            break

    # If no valid note found, return input as-is
    if note_base is None:
        return note

    # Get the position of the base note
    position = note_map[note_base]

    # Calculate new position
    new_position = (position + semitones) % 12

    # Decide whether to use sharp or flat notation
    # If original note used flat (es), prefer flats in result
    # If original note used sharp (is), prefer sharps in result
    use_flats = note_base.endswith('es')

    # Get the transposed note
    if use_flats:
        transposed_base = chromatic_flat[new_position]
    else:
        transposed_base = chromatic_sharp[new_position]

    # Return the transposed note with original extension
    return transposed_base + extension


def compile_structuur_file(songtitle, input_folder, output_folder, cleanup=True, engine='pdflatex'):
    """
    Compile the structuur.tex file for a song if it exists.

    Args:
        songtitle: Song title
        input_folder: Folder containing song folders with .tex files
        output_folder: Folder containing generated structuur.tex files
        cleanup: Whether to remove auxiliary files after compilation
        engine: TeX engine to use (default: pdflatex)

    Returns:
        bool: True if successful, False otherwise
    """

    # ***  Verify .tex file exists ***
    tex_file = input_folder / songtitle / f"{songtitle}.tex"
    if not validate_file_exists(tex_file, f"LaTeX file for '{songtitle}'"):
        return False

    # Read the main .tex file to get metadata
    try:
        with open(tex_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"⚠️  Could not read {tex_file}: {e}")
        return False

    # Extract song title and ID
    title_match = re.search(r'\\newcommand{\\liedTitel}{(.*?)}', content)
    id_match = re.search(r'\\newcommand{\\liedId}{(.*?)}', content)

    if not title_match or not id_match:
        print(f"ℹ️  No metadata found in {tex_file}, skipping structuur generation")
        return False

    # Construct path to structuur.tex file (in output folder)
    bare_filename = songtitle
    structuur_tex = output_folder / f"{bare_filename} structuur.tex"

    if not structuur_tex.exists():
        print(f"ℹ️  No structuur file found: {structuur_tex}")
        return False

    print(f"\n📄 Compiling structuur file: {structuur_tex}")

    # Output name for the PDF (same as .tex)
    output_name = f"{bare_filename} structuur"

    # Convert path to forward slashes for pdflatex (works cross-platform)
    tex_path_for_latex = str(structuur_tex).replace('\\', '/')

    # input_folder contains the song folders with .tex files
    tex_input_dir = os.path.abspath(output_folder)
    env = os.environ.copy()
    env['TEXINPUTS'] = f'{tex_input_dir}//;' + env.get('TEXINPUTS', '')

    # Compile twice for proper references (tables, etc.)
    for _ in range(2):
        result = subprocess.run(
            [engine,
                f'-output-directory={output_folder}',
                f'-jobname={output_name}'
                , tex_path_for_latex
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env
        )

        if result.returncode != 0:
            print(f"❌ Failed to compile: {structuur_tex}")
            print(result.stderr)
            return False

    # Cleanup auxiliary files
    if cleanup:
        for ext in ['.aux', '.log', '.out', '.toc']:
            aux_file = output_folder / f"{output_name}{ext}"
            if aux_file.exists():
                aux_file.unlink()
        # Remove the structuur.tex file after successful compilation
        if structuur_tex.exists():
            structuur_tex.unlink()

    print(f"✅ Success: {output_name}.pdf")
    return True


def strip_extension(filename: str) -> str:
    """
    Removes the extension from a filename (rightmost dot and everything after it).

    Args:
        filename: A filename without any path components

    Returns:
        The filename without extension, or the original if no dot exists

    Raises:
        ValueError: If the input contains path separators or invalid filename characters
    """
    # Check for path separators
    if '/' in filename or '\\' in filename:
        raise ValueError(f"Input contains path separators: {filename}")

    # Invalid characters for Windows (Linux is more permissive, so we use Windows rules)
    # Windows doesn't allow: < > : " / \ | ? *
    # We also check for null byte
    invalid_chars = '<>:"/\\|?*\0'
    for char in invalid_chars:
        if char in filename:
            raise ValueError(f"Input contains invalid filename character '{char}': {filename}")

    # Find rightmost dot
    dot_index = filename.rfind('.')

    # If no dot found, return as is
    if dot_index == -1:
        return filename

    # Return everything before the rightmost dot
    return filename[:dot_index]


def main():
    """Main entry point for lt-generate script.

    Loads path configuration and generates PDFs from LaTeX song files.
    """
    # Load and resolve path configuration
    paths = load_and_resolve_paths()

    parser = argparse.ArgumentParser(description='Compile .tex files with custom output names')
    parser.add_argument('songtitles', nargs='*', help='Specific songtitles (.tex filenames but without extension) to compile (default: all)')
    parser.add_argument('--no-cleanup', action='store_true', help='Keep auxiliary files')
    parser.add_argument('--engine', default='pdflatex', help='TeX engine (default: pdflatex)')
    parser.add_argument('--tab-orientation',
                        choices=['left', 'right', 'traditional'],
                        default='left',
                        help='Tab orientation (default: left)')
    parser.add_argument('-n', '--only', type=int, default=0,
                        help='Generate only this variant (default: 0 = all)')

    args = parser.parse_args()

    if args.songtitles:
        songtitles = args.songtitles
    else:
        # Find all song folders (folders containing a .tex file with same name as folder)
        songtitles = []
        for folder in paths.input_folder.iterdir():
            if folder.is_dir():
                tex_file = folder / f"{folder.name}.tex"
                if tex_file.exists():
                    songtitles.append(folder.name)

    # Read the 'tab orientation' and 'only' values from the commandline args.

    # Has been defaulted to 'left' if not set from cmdline.
    tab_orientation = args.tab_orientation

    # This '--only <number>' param is there to ease generating a single
    # file instead of always all 5 or more variants. The number is not
    # hard connected to a variant but just refers to the (1-based) n-th call
    # in the list of lines that start with "success = ..." below.
    only = args.only

    success = 0
    structuur_success = 0

    if only < 2:
        # generate liedtekst pdf
        success = sum(compile_tex_file(f, paths.input_folder, paths.output_folder, not args.no_cleanup, args.engine) for f in songtitles)

    if only == 2 or only == 0:
        # generate liedtekst pdf with measurenumbers
        success = success + sum(compile_tex_file(f, paths.input_folder, paths.output_folder, not args.no_cleanup, args.engine, show_measures=True) for f in songtitles)

    if only == 3 or only == 0:
        # generate liedtekst pdf with chords
        success = success + sum(compile_tex_file(f, paths.input_folder, paths.output_folder, not args.no_cleanup, args.engine, show_measures=False, show_chords=True) for f in songtitles)

    if only == 4 or only == 0:
        # generate liedtekst pdf with measurenumbers and chords
        success = success + sum(compile_tex_file(f, paths.input_folder, paths.output_folder, not args.no_cleanup, args.engine, show_measures=True, show_chords=True) for f in songtitles)

    if only == 5 or only == 0:
        # generate liedtekst pdf with measurenumbers, chords and guitartabs
        success = success + sum(compile_tex_file(f, paths.input_folder, paths.output_folder, not args.no_cleanup, args.engine, show_measures=True, show_chords=True, show_tabs=True, tab_orientation=tab_orientation) for f in songtitles)

    # Generate structuur PDF for each liedtekst
    print("\n" + "="*60)
    print("Generating structuur PDFs...")
    print("="*60)
    for f in songtitles:
        if compile_structuur_file(str(f), paths.input_folder, paths.output_folder, not args.no_cleanup, args.engine):
            structuur_success += 1

    print(f"\n{'='*60}")
    print(f"Compiled {success} liedtekst files successfully")
    print(f"Compiled {structuur_success} structuur files successfully")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
