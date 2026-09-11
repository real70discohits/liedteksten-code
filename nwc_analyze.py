#!/usr/bin/env python3
"""
Analyzes .nwctxt files and maps lyrics to measure numbers.

Usage:
    python nwc_analyze.py <path-to-nwctxt-file>
"""

import sys
import re
from fractions import Fraction
from pathlib import Path
from console_utf8 import enable_utf8_console
from pathconfig import load_and_resolve_paths
from nwc_utils import NwcFile, calc_timing, extract_tempo_from_rawdata 
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


def blindly_count_barmarkers_in_staff(staff_content):
    """Count the number of |Bar markers in a staff. Doesn't reckon with incomplete measures."""
    return staff_content.count(NWC_PREFIX_BAR)


def detect_begintel(first_staff):
    """Detect if there's a begintel.

    A begintel is typically a single rest before the first bar. 
    It has no musical meaning but is an adaptation to recording software that when playing the first note produces a distorted sound.
    So it's not a pickup measure, pickup beat or anacrusis.
    """
    # Look for a Rest before the first Bar
    before_first_bar = first_staff.split(NWC_PREFIX_BAR)[0]

    # Check if there's a Rest element
    if NWC_PREFIX_REST in before_first_bar:
        return True
    return False


def count_vooraf_measures_by_filepath(filepath):
    nwc = NwcFile(filepath)
    bass_staff = nwc.get_staff_by_name(STAFF_NAME_BASS)
    try:
        content = bass_staff.get_content()
    except(AttributeError):
        print("❌ Error: no staff has name 'Bass'?")
        raise 
    return count_vooraf_measures(content)


def count_vooraf_measures(staff_content):
    """Count (full) measures before the 'liedstart' marker.

    Returns the number of measures before the song actually starts,
    excluding the begintel (first measure with single beat).

    Args:
        staff_content: a full or partial staff from an .nwctxt file.
    """
    # Find the position of "liedstart" marker
    lines = staff_content.split('\n')
    liedstart_index = -1

    for i, line in enumerate(lines):
        # todo: find the timesig: e.g. 3/4, then we have a criterion for min duration to count as a vooraf measure 
        if line.strip().startswith(f'{NWC_PREFIX_TEXT}Text:"{NWC_MARKER_LIEDSTART}"'):
            liedstart_index = i
            break

    if liedstart_index == -1:
        # No liedstart marker found, return 0
        return 0

    # Collect all lines before liedstart
    lines_vooraf = ""
    for i in range(liedstart_index):
        lines_vooraf += '\n'+ lines[i]

    # Count real measures in that vooraf part
    result = count_measures_in_staff(lines_vooraf, 2, 4)    # todo: see previous remark: we should not hardcode but deduce these minimum values.
    return result


def _count_vooraf_measures(staff_content):  # NOTE: ! OBSOLETE !
    """Count (full) measures before the 'liedstart' marker.

    Returns the number of measures before the song actually starts,
    excluding the begintel (first measure with single beat).

    Args:
        staff_content: a full or partial staff from an .nwctxt file.
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


def multiple_notes_count_as_one(nwctxt_line):
    """Boolean function: detects slurs and ties, meaning that multiple notes 
    count as one (so only a single note for singing and lyrics).

    nwctxt_line example: "|Note|Dur:8th|Pos:-4|Opts:Stem=Up,Beam=First".
    """
    pos = find_section_in_line("Pos", nwctxt_line)
    return nwctxt_line.count('Slur') > 0 or (pos is not None and pos.endswith('^'))


def find_section_in_line(startswith, line):
    """Returns the full section from a line when that section is found by name in the given string.
    Example: find_section_in_line("|Note|Dur:8th|Pos:-3^|Opts:Stem=Up,Beam=End", "Pos") returns "Pos:-3^".
    """
    sections = line.split('|')
    result = None
    for section in sections:
        if section.lower().startswith(startswith.lower()):  # Case-insensitive match
            result = section
            break
    return result


def map_lyrics_to_measures(staff_content, syllables, measure_offset = 0):
    """Map lyrics syllables to measure numbers.

    Returns a dict: {measure_number: [syllables]}

    Args:
        staff_content: nwctxt contents of a staff
        syllables: array of all text syllables, extracted from that same nwctxt file
        measure_offset: means for correcting the measure number, e.g. in case the first measures should be ignored. 
            Pass a negative number if you want to subtract.
    """
    measure_map = {}
    current_measure = measure_offset - 1
    syllable_index = 0
    skip_next_note = False

    # Split staff into lines
    lines = staff_content.split('\n')

    # For easy processing per measure, construct an array of measures: each entry contains all lines of a single array.
    measures = to_measure_array(lines)  # any duration > 0 counts in

    for measure in measures:
        if duration_is_above_minimum(measure):
            current_measure += 1
            if current_measure == 0:    # we skip measure 0! So, e.g.: -2, -1, 1, 2, 3, 4 ...
                current_measure = 1
            if current_measure not in measure_map:
                measure_map[current_measure] = []
            for line in measure:    
                line = line.strip()
                if line.startswith(NWC_PREFIX_NOTE) and syllable_index < len(syllables):
                    if skip_next_note:
                        if multiple_notes_count_as_one(line):
                            skip_next_note = True
                        else:
                            skip_next_note = False
                    else:
                        # Assign next syllable to current measure
                        if current_measure not in measure_map:
                            measure_map[current_measure] = []
                        measure_map[current_measure].append(syllables[syllable_index])
                        syllable_index += 1
                        if multiple_notes_count_as_one(line):
                            skip_next_note = True
                elif line.startswith(NWC_PREFIX_REST):
                    # Skip rests - no syllable assignment
                    pass

    return measure_map


def to_measure_array(lines, include_bar_marker=False):
    """Split a list of staff lines into groups per measure.

    Groups everything between two '|Bar ...' lines into one sublist.
    Lines before the first bar (staff header lines such as |AddStaff|,
    plus any pickup notes) end up in a separate leading group, so that
    measure 1 of the result corresponds to the first real measure.

    Args:
        lines: List of raw lines for one staff (e.g. from
                NwcFile(...).get_staff_by_name(STAFF_NAME_BASS).get_content().split('\n')).
        include_bar_marker: If True, each measure group starts with its own
                '|Bar ...' line (useful when the bar's Style/Repeat attributes
                matter). If False (default), the bar marker is used purely as
                a separator.

    Returns:
        List of lists of lines. result[0] contains the pre-first-bar lines
        (header and/or pickup); result[1:] are the measures in order.
        Trailing empty lines are dropped; a trailing bar with no content
        after it yields no extra group.
    """
    BAR_PREFIXES = ('|Bar|', '|Bar')

    measures = []
    current = []

    for line in lines:
        is_bar = line.startswith('|Bar|') or line == '|Bar'
        if is_bar:
            # Start a new measure; keep the previous group if non-empty
            # (skip trailing empties caused by consecutive bars)
            if current:
                measures.append(current)
            current = [line] if include_bar_marker else []
        else:
            current.append(line)

    if current:
        measures.append(current)

    return measures


# Naast (Dbl)Dotted kent NWC nog meer duur-gerelateerde modifiers, o.a. Triplet=First/Mid/End en Grace.
# Die hebben geen simpele factor (triplet = ×2/3 verdeeld over noten, grace is kort zonder vaste duur).
DURATION_MODIFIERS = {'Dotted': 1.5, 'DblDotted': 1.75}     


def get_single_duration_struct(line):
    """Extracts (durationName, factor) from a single line (from an NWC (.nwctxt) file).
    
    * unittested *

    Example inputs/outputs:
        1. |Rest|Dur:4th                                   => ("4th", 1.0)
        2. |Note|Dur:8th|Pos:0|Opts:Stem=Down,Beam=First   => ("8th", 1.0)
        3. |Rest|Dur:4th|Opts:Stem=Down                    => ("4th", 1.0)
        4. |Note|Dur:4th,Staccato|Pos:-4|Opts:Stem=Up      => ("4th", 1.0)
        5. |Note|Dur:4th,Dotted|Pos:-4|Opts:Stem=Up        => ("4th", 1.5)
        6. |Note|Dur:8th,Slur|Pos:-4|Opts:Stem=Up          => ("8th", 1.0)
        7. |Note|Dur:Half,DblDotted|Pos:-4^                => ("Half", 1.75)
        8. |Note|Dur:8th|Pos:1|Opts:Stem=Down,Beam=First   => ("8th", 1.0)

    """
    match = re.search(r'Dur:([^|]*)', line)
    if match:
        dur, *mods = match.group(1).split(',')
        factor = 1.0
        for m in mods:
            factor *= DURATION_MODIFIERS.get(m, 1.0)
        struct = (dur, factor)
        return struct
    else:
        return None


DURATIONS = {
    'Whole':  Fraction(1),
    'Half':   Fraction(1, 2),
    '4th':    Fraction(1, 4),
    '8th':    Fraction(1, 8),
    '16th':   Fraction(1, 16),
    '32nd':   Fraction(1, 32),
}


def convert_duration(dur, to_base_note):
    """Converts a duration like 'Half', 'Whole' '4th' to a duration in terms of the desired base_note.
    So "Give me the duration of 'Half' in quarternotes (4)" should return 2.

    Args:
        dur: 'Whole', 'Half', '4th', '8th', '16th', '32nd'
        to_base_note: (int) 1, 2, 4, 8, 16, 32 where 1 stands for Whole, 2 for Half etc.

    Examples:
            |  input        |   output
        1.  | '4th', 4      |   1.0
        2.  | '8th', 8      |   1.0
        3.  | '16th', 16    |   1.0
        4.  | '32nd', 32    |   1.0
        5.  | 'Half', 2     |   1.0
        6.  | 'Whole', 1    |   1.0
        7.  | '8th', 4      |   0.5
        8.  | 'Half', 4     |   2.0
        9.  | 'Half', 16    |   8.0
        10. | '32nd', 8     |   0.25
    """
    if dur not in DURATIONS:
        raise ValueError(f"Unknown duration: {dur!r}")
    if to_base_note <= 0:
        raise ValueError(f"to_base_note must be positive, got {to_base_note}")

    return float(Fraction(to_base_note) * DURATIONS[dur])


def get_duration_of_lines(lines, base_note):
    """Determine for a set of nwctxt-lines its summed duration, in quarternotes.

    Args:
        lines: any set of lines from an .nwctxt file.
        base_note = the note in which to express the duration (int) e.g. {1, 2, 4, 8, 16, 32, 64} for resp. whole, half, quarter, eighth etc.
    """
    # trick: call minimum-function with extremely high minimum: then the total
    # duration is always calculated in the second result
    return _duration_is_above_minimum(lines, 99999, base_note)[1]


def duration_is_above_minimum(lines, minimum_duration = None, minimum_duration_base = None):
    """Determine for a set of nwctxt-lines that its summed duration is more than a desired minimum.

    As a side effect, the total duration is calculated, but only when it's less than the required minimum.
    
    Args:
        lines: any set of lines, but the commonest case is all lines of a single measure 
        minimum_duration = for a set of lines with less summed duration than the minimum, false is returned.
        minimum_duration_base = unit of the duration (int) e.g. {1, 2, 4, 8, 16, 32, 64} for resp. whole, half, quarter, eighth etc.
    """
    return _duration_is_above_minimum(lines, minimum_duration, minimum_duration_base)[0]


def _duration_is_above_minimum(lines, minimum_duration = None, minimum_duration_base = None):
    """Determine for a set of nwctxt-lines that its summed duration is more than a desired minimum.

    As a side effect, the total duration is calculated, but only when it's less than the required minimum.
    
    Args:
        lines: any set of lines, but the commonest case is all lines of a single measure 
        minimum_duration = for a set of lines with less summed duration than the minimum, false is returned.
        minimum_duration_base = unit of the duration (int) e.g. {1, 2, 4, 8, 16, 32, 64} for resp. whole, half, quarter, eighth etc.
    """
    # Because we check >=, for 'any duration we cannot use 0 because then no-duration would pass as well. Therefor, we set min_duration to a fraction above 0.
    if minimum_duration is None:
        minimum_duration = 0.0001
        minimum_duration_base = 4
        
    total_meas_dur_in_base = 0  # total counted duration, expressed in base
    for line in lines:
        if '|Dur:' in line:
            dur = get_single_duration_struct(line)
            dur_in_base = convert_duration(dur[0], minimum_duration_base)
            total_meas_dur_in_base += dur_in_base
            if total_meas_dur_in_base > minimum_duration:
                return True, 0.0
    return False, total_meas_dur_in_base


def count_measures_in_staff(staff_content, minimum_duration = None, minimum_duration_base = None):
    """Count the number of 'real' measures in a staff: if no value is given in parameter minimum_duration,
    a bar is 'real' if it contains any duration; else the minimum_duration reckoned with.
    
    Args:
            staff_content: can be partial. Obtain by NwcFile(file_path).get_staff_by_name(STAFF_NAME_BASS).get_content() > lines = %..split('\n')
            minimum_duration = measures with less duration than the minimum are not counted.
            minimum_duration_base = unit of the duration (int) e.g. {1, 2, 4, 8, 16, 32, 64} for resp. whole, half, quarter, eighth etc.
    """

    # NOTE: a value for minimum-duration is given by the timesig, but it can 
    # change during the song so it requires a full mapping of measures to timesig
    # ranges so we don't do that here and leave that up to the caller.

    # Because we check >=, for 'any duration we cannot use 0 because then no-duration would pass as well. Therefor, we set min_duration to a fraction above 0.
    if minimum_duration is None:
        minimum_duration = 0.0001
        minimum_duration_base = 4

    # Init
    lines = staff_content.split('\n')
    all_lines_in_measure = []
    total_measures = 0

    # Walk the lines
    for line in lines:
        # Check for Bar marker
        if line.startswith('|Bar|') or line == '|Bar':      # new bar found
            # add current (=old) bar to measure_count, if it has duration
            if duration_is_above_minimum(all_lines_in_measure, minimum_duration, minimum_duration_base):
                total_measures += 1                         
            # Reset lines array, because we enter a new measure
            all_lines_in_measure = []
        else:
            all_lines_in_measure.append(line)

    # Count the last measure if it has duration
    if all_lines_in_measure and duration_is_above_minimum(all_lines_in_measure, minimum_duration, minimum_duration_base):
        total_measures += 1

    return total_measures


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

    if not title:
        print("⚠️ analyze_nwctxt(): title is missing from nwctxt file.")

    file_name = file_path.stem

    # Get Bass staff to count total measures
    bass_staff = nwc.get_staff_by_name(STAFF_NAME_BASS)
    if not bass_staff:
        print(f"⚠️  Warning: No '{STAFF_NAME_BASS}' staff found in {file_path}")
        return None

    bass_content = bass_staff.get_content()

    # count measures that have duration >= minimum_duration (this can include vooraf- and begintel measures!)
    total_meas_with_min_dur = count_measures_in_staff(bass_content) #, minimum_duration=1, minimum_duration_base=4)

    # Determine how many measures at the beginning to discount.
    # The 'at the beginning' is only to clarify some semantics, e.g. when passing the
    # value to the lyrics mapper because measures at the end then don't matter much.
    meas_at_beginning_to_subtract_count = 0

    # Detect begintel
    has_begintel = detect_begintel(bass_content)
    meas_at_beginning_to_subtract_count += 1 if has_begintel else 0

    # Count vooraf measures
    vooraf_meas_count = count_vooraf_measures(bass_content)
    meas_at_beginning_to_subtract_count += vooraf_meas_count

    # Now we can calculate the netto total ('netto' i.d. count requires min duration)
    netto_total_measures = total_meas_with_min_dur - meas_at_beginning_to_subtract_count

    # Find Zang staff
    zang_staff = nwc.get_staff_by_name(STAFF_NAME_ZANG)

    if not zang_staff:
        print(f"⚠️  Warning: No '{STAFF_NAME_ZANG}' staff found in {file_path}:"
                " measure-lyrics mapping not possible.")
        measure_map = None
    else:
        zang_content = zang_staff.get_content()

        # Extract lyrics
        syllables = parse_lyric_text(zang_content)

        # Map lyrics to measures
        measure_map = map_lyrics_to_measures(zang_content, syllables, -meas_at_beginning_to_subtract_count)

    return {
        'title': title,
        'file': file_path.name,
        'folder': file_path.parent,
        'total_measures': netto_total_measures,
        'has_begintel': has_begintel,
        'vooraf': vooraf_meas_count,
        'measure_map': measure_map,
    }


def analyze_complete_song(file_path, tempo: tuple[int, int] | None =None, timesig=None):
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
        - tempo: Tempo as tuple of BPM (int) and beat_base_note (int)
        - timesig: Time signature string (e.g. "4/4" or None)
        - total_bars: Raw bar count from file
        - has_begintel: Boolean - true if pickup measure exists
        - vooraf: Number of count-in measures before "liedstart"
        - total_measures: netto count of non-empty measures (and excluding begintel and vooraf measures)
        - total_duration: Duration in seconds (only approximately, excluding vooraf, or None if tempo/timesig missing)
        - measure_map: Dict mapping measure numbers to lyrics (renumbered: maat 1 = liedstart)    => good to know! The measure with the 'liedstart' label gets '1', so this should become my standard numbering.

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
    # NOTE: because here tempo and timesig are just for general info about the song, we don't have to reckon with tempo/timesig changes.
    if tempo is None or timesig is None:
        nwc = NwcFile(file_path)
        bass_staff = nwc.get_staff_by_name(STAFF_NAME_BASS)
        if bass_staff:
            bass_lines = bass_staff.lines

            if tempo is None:
                for line in bass_lines:
                    if line.startswith('|Tempo|') and 'Tempo:' in line:     #  "|Tempo|Base:Eighth|Tempo:363|Pos:7"
                        tempo = extract_tempo_from_rawdata(line)

            if timesig is None:
                for line in bass_lines:
                    if line.startswith('|TimeSig|Signature:'):
                        try:
                            sig_part = line.split('|TimeSig|Signature:')[1]
                            timesig = sig_part.split('|')[0]
                            break
                        except (IndexError, ValueError):
                            pass

    # Calculate total duration (excluding vooraf measures)
    total_duration = None
    if tempo and timesig:
        try:
            _, measure_duration, _, _ = calc_timing(tempo, timesig)
            total_duration = basic_analysis['total_measures'] * measure_duration    # BUG: currently, timesig/tempo variations are not reckoned with.
        except (ValueError, ZeroDivisionError):
            total_duration = None

    # Build complete analysis result
    return {
        'title': basic_analysis['title'],
        'file': basic_analysis['file'],
        'folder': basic_analysis['folder'],
        'tempo': tempo,
        'timesig': timesig,
        'total_bars': blindly_count_barmarkers_in_staff(NwcFile(file_path).get_staff_by_name(STAFF_NAME_BASS).get_content()),
        'has_begintel': basic_analysis['has_begintel'],
        'vooraf': basic_analysis['vooraf'],
        'total_measures': basic_analysis['total_measures'],
        'total_duration': total_duration,               # BUG: see above
        'measure_map': basic_analysis['measure_map']
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


def write_analysis_to_file(songtitle, nwctxt_file_path,  tempo=None, timesig=None, use_complete_analysis=True):
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
    paths = load_and_resolve_paths(songtitle)
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
    enable_utf8_console()
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
        
        songtitle = ""
        # Add .nwctxt extension if not present
        if not input_arg.endswith('.nwctxt'):
            songtitle = input_arg
            input_arg += '.nwctxt'
        else:
            songtitle = input_arg.replace(".nwctxt", "")

        # It's just a title, look in build_folder
        paths = load_and_resolve_paths(songtitle)

        # Look in build_folder
        file_path = paths.build_folder / input_arg

        if not file_path.exists():
            print(f"❌ Error: File not found in build folder: {file_path}")
            print(f"\nSearched in: {paths.build_folder}")
            print(f"Looking for: {input_arg}")
            sys.exit(1)

    result_file, result_analysis = write_analysis_to_file(songtitle, file_path)

    if not result_file:
        sys.exit(1)


if __name__ == "__main__":
    main()
