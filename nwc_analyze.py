#!/usr/bin/env python3
"""
Analyzes .nwctxt files and maps lyrics to measure numbers.

Usage:
    python nwc_analyze.py <path-to-nwctxt-file>
"""

import sys
import re
from pathlib import Path
from pathconfig import load_and_resolve_paths
from nwc_utils import NwcFile
from constants import (STAFF_NAME_BASS, STAFF_NAME_ZANG, NWC_PREFIX_BAR,
                       NWC_PREFIX_NOTE, NWC_PREFIX_REST, NWC_PREFIX_TEXT,
                       NWC_MARKER_LIEDSTART)


def parse_song_info(content):
    """Extract title and number from SongInfo line."""
    match = re.search(r'\|SongInfo\|Title:"([^"]*)"', content)
    title = match.group(1).replace(r"\'", "'") if match else "Unknown"

    # Extract number from filename or content if available
    # For now, we'll need to get it from metadata or filename
    return title


def find_song_number(nwctxt_path):
    """Determine the song number
    """
    # Get the base filename without extension
    base_name = nwctxt_path.stem

    # extract any numbers and return the last one or None.
    numbers = re.findall(r'\d+', base_name)
    last_number_index = len(numbers) - 1

    return numbers[last_number_index] if last_number_index >= 0 else None




def parse_lyric_text(lyric_line):
    """Parse Lyric1 text and split into syllables.

    Rules:
    - Remove leading/trailing quotes
    - Replace \' with '
    - Remove \n
    - Split on spaces and hyphens to get syllables
    """
    # Extract text from |Lyric1|Text:"..."
    match = re.search(r'\|Lyric1\|Text:"(.*?)"', lyric_line, re.DOTALL)
    if not match:
        return []

    text = match.group(1)

    # Unescape characters
    text = text.replace(r"\'", "'")
    text = text.replace(r'\n', ' ')

    # Split on spaces and hyphens to get syllables
    # But preserve underscores (they join syllables)
    syllables = []
    current = ""

    i = 0
    while i < len(text):
        char = text[i]

        if char in (' ', '-'):
            if current.strip():
                syllables.append(current.strip())
                current = ""
        else:
            current += char

        i += 1

    # Add last syllable
    if current.strip():
        syllables.append(current.strip())

    return syllables


def count_bars_in_staff(staff_content):
    """Count the number of |Bar markers in a staff."""
    return staff_content.count(NWC_PREFIX_BAR)    # to do: if song starts with just a single note, don't count the first measure.


def detect_begintel(first_staff):
    """Detect if there's a begintel (pickup measure).

    A begintel is typically a single note before the first bar.
    """
    # Look for a Note before the first Bar
    before_first_bar = first_staff.split(NWC_PREFIX_BAR)[0]

    # Check if there's a Note element
    if NWC_PREFIX_REST in before_first_bar:
        return True
    return False


def count_vooraf_measures(staff_content):
    """Count measures before the 'liedstart' marker.

    Returns the number of measures before the song actually starts,
    excluding the begintel (first measure with single beat).
    """
    # Find the position of "liedstart" marker
    lines = staff_content.split('\n')
    liedstart_index = -1

    for i, line in enumerate(lines):
        if line.strip().startswith(f'{NWC_PREFIX_TEXT}Text:"{NWC_MARKER_LIEDSTART}"'):
            liedstart_index = i
            break

    if liedstart_index == -1:
        # No liedstart marker found, return 0
        return 0

    # Count bars before liedstart
    bars_before = 0
    for i in range(liedstart_index):
        if lines[i].strip().startswith(NWC_PREFIX_BAR):
            bars_before += 1

    # Subtract 1 for the begintel (first measure with one beat doesn't count)
    if bars_before > 0 and detect_begintel(staff_content):
        bars_before = bars_before - 1

    return bars_before


def map_lyrics_to_measures(staff_content, syllables):
    """Map lyrics syllables to measure numbers.

    Returns a dict: {measure_number: [syllables]}
    """
    measure_map = {}
    current_measure = 0
    syllable_index = 0
    skip_next_note = False

    # Split staff into elements
    elements = staff_content.split('\n')

    for element in elements:
        element = element.strip()

        if element.startswith(NWC_PREFIX_BAR):
            current_measure += 1
            if current_measure not in measure_map:
                measure_map[current_measure] = []
        elif element.startswith(NWC_PREFIX_NOTE) and syllable_index < len(syllables):
            if skip_next_note:
                if element.count('Slur') > 0 or element.endswith('^'):
                    skip_next_note = True
                else:
                    skip_next_note = False
            else:
                # Assign next syllable to current measure
                if current_measure not in measure_map:
                    measure_map[current_measure] = []
                measure_map[current_measure].append(syllables[syllable_index])
                syllable_index += 1
                if element.count('Slur') > 0 or element.endswith('^'):
                    skip_next_note = True
        elif element.startswith(NWC_PREFIX_REST):
            # Skip rests - no syllable assignment
            pass

    return measure_map


def analyze_nwctxt(file_path):
    """Analyze a .nwctxt file and return lyrics mapping.

    Note: This is a legacy function that returns raw data without corrections.
    For complete song analysis with corrected totals, use analyze_complete_song().
    """
    # Parse the NWC file
    nwc = NwcFile(file_path)

    # Extract metadata from header
    header_content = '\n'.join(nwc.header_lines)
    title = parse_song_info(header_content)

    file_name = file_path.stem

    # Get Bass staff to count total measures
    bass_staff = nwc.get_staff_by_name(STAFF_NAME_BASS)
    if not bass_staff:
        print(f"⚠️  Warning: No '{STAFF_NAME_BASS}' staff found in {file_path}")
        return None

    bass_content = bass_staff.get_content()
    total_bars = count_bars_in_staff(bass_content)

    # Detect begintel
    has_begintel = detect_begintel(bass_content)

    # Adjust total if begintel exists
    total_measures = total_bars if has_begintel else total_bars + 1

    # Count vooraf measures
    vooraf = count_vooraf_measures(bass_content)

    # Find Zang staff
    zang_staff = nwc.get_staff_by_name(STAFF_NAME_ZANG)

    if not zang_staff:
        print(f"⚠️  Warning: No '{STAFF_NAME_ZANG}' staff found in {file_path}")
        return None

    zang_content = zang_staff.get_content()

    # Extract lyrics
    syllables = parse_lyric_text(zang_content)

    # Map lyrics to measures
    measure_map = map_lyrics_to_measures(zang_content, syllables)

    return {
        'title': title,
        'file': file_path.name,
        'folder': file_path.parent,
        'total_measures': total_measures,
        'has_begintel': has_begintel,
        'vooraf': vooraf,
        'measure_map': measure_map,
    }


def analyze_complete_song(file_path, tempo=None, timesig=None):
    """Complete analysis of a merged .nwctxt file with corrected totals.

    This function provides a single source of truth for all song metadata,
    with proper handling of 'maten vooraf' (count-in measures) and 'begintel' (pickup).

    Args:
        file_path: Path to the .nwctxt file (string or Path object)
        tempo: Optional tempo (BPM) - if None, will be extracted from file
        timesig: Optional time signature (e.g. "4/4") - if None, will be extracted from file

    Returns:
        dict with all song metadata:
        - title: Song title
        - file: Filename
        - folder: Parent folder path
        - tempo: Tempo in BPM (int or None)
        - timesig: Time signature string (e.g. "4/4" or None)
        - total_bars: Raw bar count from file
        - has_begintel: Boolean - true if pickup measure exists
        - vooraf: Number of count-in measures before "liedstart"
        - total_measures: Corrected total (excluding begintel and vooraf)
        - total_duration: Duration in seconds (excluding vooraf, or None if tempo/timesig missing)
        - measure_map: Dict mapping measure numbers to lyrics (renumbered: maat 1 = liedstart)

        Returns None if analysis fails.
    """
    from nwc_utils import NwcFile
    from constants import STAFF_NAME_BASS

    file_path = Path(file_path)

    # Get basic analysis
    basic_analysis = analyze_nwctxt(file_path)
    if not basic_analysis:
        return None

    # Extract tempo and timesig if not provided
    if tempo is None or timesig is None:
        nwc = NwcFile(file_path)
        bass_staff = nwc.get_staff_by_name(STAFF_NAME_BASS)
        if bass_staff:
            bass_lines = bass_staff.lines

            if tempo is None:
                for line in bass_lines:
                    if line.startswith('|Tempo|') and 'Tempo:' in line:
                        try:
                            tempo_part = line.split('Tempo:')[1]
                            tempo_str = tempo_part.split('|')[0]
                            tempo = int(tempo_str)
                            break
                        except (IndexError, ValueError):
                            pass

            if timesig is None:
                for line in bass_lines:
                    if line.startswith('|TimeSig|Signature:'):
                        try:
                            sig_part = line.split('|TimeSig|Signature:')[1]
                            timesig = sig_part.split('|')[0]
                            break
                        except (IndexError, ValueError):
                            pass

    # Calculate corrected total measures (excluding begintel and vooraf)
    total_measures_corrected = basic_analysis['total_measures'] - basic_analysis['vooraf']

    # Calculate total duration (excluding vooraf measures)
    total_duration = None
    if tempo and timesig:
        try:
            beats_per_second = tempo / 60
            beat_duration = 1 / beats_per_second
            s_beats_per_measure, _, s_beat_base = timesig.partition('/')
            beats_per_measure = int(s_beats_per_measure)
            measure_duration = beats_per_measure * beat_duration

            # Duration = only the 'real' measures (excluding vooraf)
            total_duration = total_measures_corrected * measure_duration
        except (ValueError, ZeroDivisionError):
            total_duration = None

    # Renumber measure_map so that the measure containing "liedstart" becomes maat 1
    # Subtract vooraf from all measure numbers
    measure_map_renumbered = {}
    vooraf = basic_analysis['vooraf']
    for original_maat_num, syllables in basic_analysis['measure_map'].items():
        # New measure number = original - vooraf
        # This makes the measure containing "liedstart" become maat 1
        new_maat_num = original_maat_num - vooraf
        measure_map_renumbered[new_maat_num] = syllables

    # Build complete analysis result
    return {
        'title': basic_analysis['title'],
        'file': basic_analysis['file'],
        'folder': basic_analysis['folder'],
        'tempo': tempo,
        'timesig': timesig,
        'total_bars': count_bars_in_staff(NwcFile(file_path).get_staff_by_name(STAFF_NAME_BASS).get_content()),
        'has_begintel': basic_analysis['has_begintel'],
        'vooraf': vooraf,
        'total_measures': total_measures_corrected,
        'total_duration': total_duration,
        'measure_map': measure_map_renumbered,
    }


def format_output(analysis, song_number=None):
    """Format analysis results as text output."""
    if not analysis:
        return "No analysis available"

    lines = []
    lines.append('*** NWC ANALYSE ***')
    lines.append('')
    lines.append(f"Analyse van: {analysis['file']}")
    lines.append(f"Locatie: {analysis['folder']}")
    lines.append('')
    lines.append(f"liedtitel: {analysis['title']}")
    if song_number:
        lines.append(f"liednummer: {song_number}")
    lines.append(f"totaal aantal maten: {analysis['total_measures']}")
    lines.append(f"heeft begintel: {'ja' if analysis['has_begintel'] else 'nee'}")
    lines.append(f"aantal maten vooraf: {analysis['vooraf']}")
    lines.append("")
    lines.append("maat\ttekst")

    # Output lyrics by measure
    measure_map = analysis['measure_map']
    for measure_num in sorted(measure_map.keys()):
        if measure_num == 0:
            continue  # Skip measure 0 (before first bar)

        syllables = measure_map[measure_num]
        text = " ".join(syllables)
        lines.append(f"{measure_num}\t{text}")

    # Fill in empty measures
    # for i in range(1, analysis['total_measures'] + 1):
    #     if i not in measure_map:
    #         lines.append(f"{i}\t")

    return "\n".join(lines)


def write_analysis_to_file(nwctxt_file_path, tempo=None, timesig=None, use_complete_analysis=True):
    """Analyze a .nwctxt file and write results to output folder.

    Args:
        nwctxt_file_path: Path to the .nwctxt file (string or Path object)
        tempo: Optional tempo (BPM) for complete analysis
        timesig: Optional time signature (e.g. "4/4") for complete analysis
        use_complete_analysis: If True (default), use analyze_complete_song() with corrected totals.
                              If False, use legacy analyze_nwctxt() with raw data.

    Returns:
        tuple: (Path to created analysis file or None, analysis dict or None)
    """
    file_path = Path(nwctxt_file_path)

    if not file_path.exists():
        print(f"❌ Error: File not found: {file_path}")
        return None, None

    # Load and resolve path configuration
    paths = load_and_resolve_paths()
    build_folder = paths.build_folder

    # Analyze the file
    if use_complete_analysis:
        analysis = analyze_complete_song(file_path, tempo=tempo, timesig=timesig)
    else:
        analysis = analyze_nwctxt(file_path)

    if not analysis:
        return None, None

    # Try to find song number
    song_number = find_song_number(file_path)

    # Format output
    output = format_output(analysis, song_number)

    # Create output filename
    output_filename = f"{file_path.stem} analysis.txt"

    # Write to file
    output_file = build_folder / output_filename

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"✅ Analysis written to: {output_file}")
        return output_file, analysis
    except Exception as e:
        print(f"❌ Error writing output file: {e}")
        return None, None


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python nwc_analyze.py <song-title-or-path>")
        print("  Examples:")
        print("    python nwc_analyze.py \"She's so beautiful (22)\"")
        print("    python nwc_analyze.py \"path/to/file.nwctxt\"")
        sys.exit(1)

    input_arg = sys.argv[1]

    # Check if input is a path (contains path separators) or just a title
    if '/' in input_arg or '\\' in input_arg or Path(input_arg).exists():
        # It's a path, use as-is
        file_path = Path(input_arg)
    else:
        # It's just a title, look in build_folder
        paths = load_and_resolve_paths()

        # Add .nwctxt extension if not present
        if not input_arg.endswith('.nwctxt'):
            input_arg += '.nwctxt'

        # Look in build_folder
        file_path = paths.build_folder / input_arg

        if not file_path.exists():
            print(f"❌ Error: File not found in build folder: {file_path}")
            print(f"\nSearched in: {paths.build_folder}")
            print(f"Looking for: {input_arg}")
            sys.exit(1)

    result_file, result_analysis = write_analysis_to_file(file_path)

    if not result_file:
        sys.exit(1)


if __name__ == "__main__":
    main()
