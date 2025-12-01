#!/usr/bin/env python3
"""
nwc-concat.py - Concatenate NoteWorthy Composer sections based on sequence file.

Creates:
- Concatenated .nwctxt file with all sections
- LaTeX structure file with song metadata, parts overview, and composition

Usage:
    python nwc-concat.py "Song Title"
    python nwc-concat.py "Song Title" --keep-tempi

Dependencies:
- pathconfig module (for path configuration)

"""

import argparse
import commentjson
import sys
from pathlib import Path
import re
from pathconfig import load_and_resolve_paths, validate_file_exists, validate_folder_exists, load_jsonc
from nwc_analyze import write_analysis_to_file
from nwc_utils import parse_nwctxt, NwcFile
from constants import (NWC_PREFIX_ADDSTAFF, NWC_PREFIX_STAFF_PROPERTIES,
                       NWC_PREFIX_STAFF_INSTRUMENT, NWC_PREFIX_CLEF,
                       NWC_PREFIX_TIMESIG, NWC_PREFIX_TEMPO, NWC_PREFIX_BAR,
                       NWC_END_MARKER, FOLDER_NWC, EXT_NWCTXT, EXT_JSONC, EXT_TEX, EXT_TXT)


def concatenate_nwctxt_files(file_list, output_file, keep_tempi=False):
    """Concatenate multiple .nwctxt files
    
    Args:
        file_list: List of .nwctxt files to concatenate
        output_file: Output file path
        keep_tempi: If False (default), remove tempo indicators from files after the first.
                If True, keep all tempo indicators.
    """
    
    # Parse the first file to get header and initial staff structure
    header, first_staffs = parse_nwctxt(file_list[0])
    
    # Initialize concatenated staffs with first file's data
    concatenated_staffs = []
    for staff_lines in first_staffs:
        concatenated_staffs.append(staff_lines)
    
    # Process remaining files
    for filepath in file_list[1:]:
        _, staffs = parse_nwctxt(filepath)
        
        # Ensure we have the same number of staffs
        if len(staffs) != len(concatenated_staffs):
            print(f"⚠️ Warning: {filepath} has {len(staffs)} staffs, expected {len(concatenated_staffs)}")
            # Continue with minimum number of staffs
            min_staffs = min(len(staffs), len(concatenated_staffs))
        else:
            min_staffs = len(staffs)
        
        # Concatenate each staff
        for i in range(min_staffs):
            # Skip staff header lines (already have them from first file)
            staff_data = []
            skip_prefixes = [NWC_PREFIX_ADDSTAFF, NWC_PREFIX_STAFF_PROPERTIES,
                            NWC_PREFIX_STAFF_INSTRUMENT, NWC_PREFIX_CLEF, NWC_PREFIX_TIMESIG]

            # Only skip tempo lines if keep_tempi is False (default behavior)
            if not keep_tempi:
                skip_prefixes.append(NWC_PREFIX_TEMPO)
            
            for line in staffs[i]:
                if not any(line.startswith(prefix) for prefix in skip_prefixes):
                    staff_data.append(line)
            
            # Add a double bar between sections for clarity
            if staff_data and not staff_data[0].startswith(NWC_PREFIX_BAR):
                concatenated_staffs[i].append(f'{NWC_PREFIX_BAR}|Style:Double')
            
            concatenated_staffs[i].extend(staff_data)
    
    # Write output file
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write header
        for line in header:
            f.write(line + '\n')
        
        # Write concatenated staffs
        for staff_lines in concatenated_staffs:
            for line in staff_lines:
                f.write(line + '\n')

        f.write(f'{NWC_END_MARKER}\n')


def get_measure_count(filepath):
    """Extract measure count from second staff in .nwctxt file
    
    Looks for a line like |Bar|Style:LocalRepeatClose|Repeat:4 in the second staff
    and extracts the number after Repeat:, then adds any additional measures with
    duration after the repeat-close marker.
    
    If no repeat count is found, counts all measures that contain duration.
    """
    _, staff_sections = parse_nwctxt(filepath)
    
    if len(staff_sections) < 2:
        return None
    
    # Look at second staff for the repeat marker
    second_staff = staff_sections[1]
    
    repeat_count = None
    measures_after_repeat = 0
    total_measures = 0
    after_repeat = False
    current_measure_has_dur = False
    
    for line in second_staff:
        if 'Style:LocalRepeatClose' in line and 'Repeat:' in line:
            # Extract the number after Repeat:
            try:
                repeat_part = line.split('Repeat:')[1]
                repeat_count = int(repeat_part.split('|')[0])
                after_repeat = True
                current_measure_has_dur = False
            except (IndexError, ValueError):
                pass
        else:
            # Check for Bar marker
            if line.startswith('|Bar|') or line == '|Bar':
                if current_measure_has_dur:
                    if after_repeat:
                        measures_after_repeat += 1
                    else:
                        total_measures += 1
                current_measure_has_dur = False
            elif '|Dur:' in line:
                current_measure_has_dur = True
    
    # Count the last measure if it has duration
    if current_measure_has_dur:
        if after_repeat:
            measures_after_repeat += 1
        else:
            total_measures += 1
    
    # Determine final count
    if repeat_count is not None:
        # Use repeat count plus any measures after it
        final_count = repeat_count + measures_after_repeat
    else:
        # No repeat found, use total measures counted
        final_count = total_measures
    
    return final_count if final_count > 0 else None


def extract_chords_from_first_staff(filepath):
    """Extract chord progression from first staff of .nwctxt file
    
    Returns:
        tuple: (chord_string, total_measures, is_valid)
        - chord_string: formatted string like "B, F#, E(2), B(5)" or "-" if no chords
        - total_measures: total count of measures
        - is_valid: True if count matches expected
    """
    _, staff_sections = parse_nwctxt(filepath)
    
    if len(staff_sections) < 1:
        return "-", 0, True
    
    first_staff = staff_sections[0]
    
    chords = []
    current_chord = None
    current_measures = 0
    current_measure_has_dur = False
    
    for line in first_staff:
        # Check for chord indication in Text entries
        if line.startswith('|Text|') and 'Text:"' in line:
            # Extract the text content
            try:
                text_start = line.find('Text:"') + 6
                text_end = line.find('"', text_start)
                if text_end > text_start:
                    text_content = line[text_start:text_end]
                    # Check if it starts with "akk:" (ignoring whitespace)
                    text_stripped = text_content.strip()
                    if text_stripped.startswith('akk:'):
                        # Save previous chord if any
                        if current_chord is not None:
                            if current_measures > 1:
                                chords.append(f"{current_chord}({current_measures})")
                            else:
                                chords.append(current_chord)
                        
                        # Extract new chord (everything after "akk:")
                        new_chord = text_stripped[4:].strip()
                        current_chord = new_chord
                        current_measures = 0
                        current_measure_has_dur = False
            except (IndexError, ValueError):
                continue
        
        # Check for Bar marker
        if line.startswith('|Bar|') or line == '|Bar':
            if current_chord is not None and current_measure_has_dur:
                current_measures += 1
            current_measure_has_dur = False
        
        # Check for duration (note or rest)
        if '|Dur:' in line:
            current_measure_has_dur = True
    
    # Handle the last chord and last measure
    if current_chord is not None:
        # Count last measure if it has duration
        if current_measure_has_dur:
            current_measures += 1
        
        if current_measures > 1:
            chords.append(f"{current_chord}({current_measures})")
        elif current_measures == 1:
            chords.append(current_chord)
    
    # Calculate total measures from chords
    total_from_chords = 0
    for chord in chords:
        if '(' in chord:
            # Extract number from parentheses
            try:
                count = int(chord.split('(')[1].rstrip(')'))
                total_from_chords += count
            except (IndexError, ValueError):
                total_from_chords += 1
        else:
            total_from_chords += 1
    
    if not chords:
        return "-", 0, True
    
    chord_string = ", ".join(chords)
    return chord_string, total_from_chords, True


def extract_tempo_and_timesig(filepath):
    """Extract tempo and time signature from first staff of .nwctxt file

    Returns:
        tuple: (tempo, timesig)
        - tempo: integer tempo value or None if not found
        - timesig: string like "4/4" or None if not found
    """
    nwc = NwcFile(filepath)

    if len(nwc.staffs) < 1:
        return None, None

    first_staff = nwc.get_staff_by_index(0)
    staff_lines = first_staff.lines

    tempo = None
    timesig = None

    for line in staff_lines:
        # Look for tempo (only first occurrence)
        if tempo is None and line.startswith(NWC_PREFIX_TEMPO) and 'Tempo:' in line:
            try:
                # Extract tempo value after "Tempo:"
                tempo_part = line.split('Tempo:')[1]
                # Get the number before the next pipe or end of string
                tempo_str = tempo_part.split('|')[0]
                tempo = int(tempo_str)
            except (IndexError, ValueError):
                pass

        # Look for time signature (only first occurrence)
        if timesig is None and line.startswith(f'{NWC_PREFIX_TIMESIG}Signature:'):
            try:
                # Extract signature after "Signature:"
                sig_part = line.split(f'{NWC_PREFIX_TIMESIG}Signature:')[1]
                # Get the signature before the next pipe or end of string
                timesig = sig_part.split('|')[0]
            except (IndexError, ValueError):
                pass

        # Stop searching once both are found
        if tempo is not None and timesig is not None:
            break

    return tempo, timesig


def write_latex_file(tex_file, songtitle, tempo, timesig, measurecount_and_starttime_per_lieddeel, chords_per_lieddeel, pickup_beats):
    """Write complete LaTeX file with song meta info

    Args:
        tex_file: Path to .tex file
        songtitle: Title of the song
        tempo: Tempo value (integer) or None
        timesig: Time signature string (e.g. "4/4") or None
        measurecount_and_starttime_per_lieddeel: List of tuples (section_name, measure_count, start_time) in structure order
        chords_per_lieddeel: Dict mapping section_name to (chord_string, chord_count, is_valid)
        pickup_beats: Number of pickup beats at the start of the song
    """
    
    # Get unique sections in order of first appearance
    unique_lieddelen = []
    seen = set()
    for lieddeel_name, _, _ in measurecount_and_starttime_per_lieddeel:
        if lieddeel_name not in seen:
            unique_lieddelen.append(lieddeel_name)
            seen.add(lieddeel_name)
    
    # Escape LaTeX special characters in strings
    def escape_latex(text):
        """Escape special LaTeX characters"""
        if text is None:
            return "?"
        text = str(text)
        replacements = {
            '\\': r'\textbackslash{}',
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\textasciicircum{}',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
    
    # Write the complete file
    with open(tex_file, 'w', encoding='utf-8') as f:
        # Document header
        f.write(r'\documentclass[a4paper,11pt]{article}' + '\n')
        f.write(r'\usepackage[utf8]{inputenc}' + '\n')
        f.write(r'\usepackage[dutch]{babel}' + '\n')
        f.write(r'\usepackage{array}' + '\n')
        f.write(r'\usepackage[margin=2cm]{geometry}' + '\n')
        f.write(r'\pagestyle{empty}' + '\n')
        f.write('\n')
        
        f.write(r'\usepackage{fancyhdr}  % for footer, header' + '\n')
        f.write(r'\pagestyle{fancy}' + '\n')
        f.write(r'\fancyhf{} % clear all header and footer fields' + '\n')
        f.write(r'\renewcommand{\headrulewidth}{0pt}  % clear hrule in header' + '\n')
        f.write(r'\cfoot{\fontsize{6pt}{7.2pt}\selectfont autogenerated by nwc-concat \hspace{0.5cm} \today }' + '\n')
        f.write(r'\chead{\fontsize{8pt}{9.6pt}\selectfont ' + tex_file.name.replace('.tex', '.pdf') + '}\n')
        f.write('\n')

        f.write(r'\begin{document}' + '\n')
        f.write('\n')

        # Title
        f.write(r'\section*{Lied structuur}' + '\n')
        f.write('\n')

        # Calculate total measures
        totalmeasures = 0
        for _, measures, _ in measurecount_and_starttime_per_lieddeel:
            if measures is not None:
                totalmeasures += measures

        # Calculate total duration
        total_duration_seconds = get_duration(measurecount_and_starttime_per_lieddeel, tempo, timesig, pickup_beats)
        if total_duration_seconds is not None:
            # Round to nearest second
            total_duration_seconds = round(total_duration_seconds)
            # Format as "m:ss"
            minutes = total_duration_seconds // 60
            seconds = total_duration_seconds % 60
            duration_formatted = f"{minutes}:{seconds:02d}"
        else:
            duration_formatted = "?"

        # Basis table with title, time signature, tempo, measures and duration
        f.write(r'\begin{tabular}{ll}' + '\n')
        f.write(r'\hline' + '\n')
        f.write(r'\textbf{Basis} & \\' + '\n')
        f.write(r'\hline' + '\n')
        f.write(f'Titel & {escape_latex(songtitle)} \\\\\n')
        f.write(f'Maatsoort & {escape_latex(timesig) if timesig else "?"} \\\\\n')
        f.write(f'Tempo & {tempo if tempo else "?"} \\\\\n')
        f.write(f'\\#Maten & {totalmeasures} \\\\\n')
        f.write(f'Duur & {duration_formatted} \\\\\n')
        f.write(r'\hline' + '\n')
        f.write(r'\end{tabular}' + '\n')
        f.write('\n')
        f.write(r'\vspace{0.5cm}' + '\n')
        f.write('\n')
        
        # Lied delen section
        f.write(r'\subsection*{Lied delen}' + '\n')
        f.write('\n')
        f.write(r'\begin{tabular}{l|c|p{8cm}}' + '\n')
        f.write(r'\hline' + '\n')
        f.write(r'\textbf{Naam} & \textbf{\#Maten} & \textbf{Akkoorden (\#mt)} \\' + '\n')
        f.write(r'\hline' + '\n')
        
        for lieddeel_name in unique_lieddelen:
            # Get measure count (from first occurrence)
            measures = None
            for s, m, _ in measurecount_and_starttime_per_lieddeel:
                if s == lieddeel_name:
                    measures = m
                    break
            
            # Get chord info
            chord_string, chord_count, is_valid = chords_per_lieddeel.get(
                lieddeel_name, ("-", 0, True)
            )
            
            measure_str = str(measures) if measures is not None else "?"
            
            # Check if chord count matches measure count
            if chord_string != "-" and measures is not None and chord_count != measures:
                chord_string += " [INVALID COUNT]"
            
            f.write(f'{escape_latex(lieddeel_name)} & {measure_str} & {escape_latex(chord_string)} \\\\\n')
        
        f.write(r'\hline' + '\n')
        f.write(r'\end{tabular}' + '\n')
        f.write('\n')
        
        # Compositie section
        f.write(r'\subsection*{Compositie}' + '\n')
        f.write('\n')
        f.write(r'Compositie van het lied, met tussen haakjes het aantal maten:' + '\n')
        f.write('\n')
        f.write(r'\vspace{0.3cm}' + '\n')
        f.write('\n')
        
        # Write table
        f.write(r'\renewcommand{\arraystretch}{1.3}  % some space between rows' + '\n')
        f.write('\n')
        f.write(r'\begin{tabular}{l|l|c|p{8cm}}' + '\n')
        f.write(r'\hline' + '\n')
        f.write(r'\textbf{Volgnr} & \textbf{Deel} & \textbf{\#Maten} & \textbf{Akkoorden(\#mt)} \\' + '\n')
        f.write(r'\hline' + '\n')

        totalmeasures = 0
        for i, (section, measures, _) in enumerate(measurecount_and_starttime_per_lieddeel, 1):
            if measures is not None:
                totalmeasures += measures

            # Get chord info for this section
            chord_string, _, _ = chords_per_lieddeel.get(section, ("-", 0, True))

            measure_str = str(measures) if measures is not None else "?"
            f.write(f'{i} & {escape_latex(section)} & {measure_str} & {escape_latex(chord_string)} \\\\\n')

        f.write(r'\hline' + '\n')
        f.write(r'\end{tabular}' + '\n')
        f.write('\n')

        # Document footer
        f.write(r'\end{document}' + '\n')


def write_labeltrack_file(labeltrack_file, measurecount_and_starttime_per_lieddeel):
    """Write complete label track for song
    
    Args:
        labeltrack_file: Path to .txt file
        measures_per_lieddeel: List of tuples (lieddeel, measure_count, start_in_seconds) in structure order
    """
    if labeltrack_file is None or measurecount_and_starttime_per_lieddeel is None:
        print("⚠️ No labeltrack file created because of empty parameter value(s).")
        return

    # Write the complete file
    with open(labeltrack_file, 'w', encoding='utf-8') as f:
        for triple in measurecount_and_starttime_per_lieddeel:
            lieddeel, _, time = triple
            formattedsixdecimals = f"{time:.6f}"     # use result = f"{x:.6f} om altijd 6 decimals te hebben als string
            start = formattedsixdecimals
            f.write(f'{start}\t{start}\t{lieddeel}' + '\n')


def update_liedtekst_tex_file(liedtitel, tempo, maatsoort, song_folder=None):
    """Update tempo and maatsoort in .tex file

    Args:
        liedtitel: Song title (string)
        tempo: Tempo value (int)
        maatsoort: Time signature in format "int/int" (string)
        song_folder: Path to song folder (Path object). If None, uses parent directory.

    Returns:
        bool: True if successful, False otherwise
    """
    # Validatie tempo
    if not isinstance(tempo, int) or tempo < 10:
        print(f"❌ Error: Tempo must be an integer >= 10, got: {tempo}")
        return False

    # Validatie maatsoort
    if not maatsoort or not isinstance(maatsoort, str):
        print("❌ Error: Maatsoort is empty or not a string")
        return False

    # Check maatsoort format (int/int)
    if not re.match(r'^\d+/\d+$', maatsoort):
        print(f"❌ Error: Maatsoort must be in format 'int/int', got: {maatsoort}")
        return False

    # Determine tex file location (in song folder)
    if song_folder is None:
        tex_file = Path(f"../{liedtitel}/{liedtitel}.tex")
    else:
        tex_file = Path(song_folder) / f"{liedtitel}.tex"

    # Check if .tex file exists
    if not validate_file_exists(tex_file, f"Liedtekst .tex file for '{liedtitel}'"):
        return False

    # Read file
    try:
        with open(tex_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

    # Replace maatsoort
    new_content = re.sub(
        r'(\\newcommand\{\\maatsoort\}\{)[^}]*(\})',
        rf'\g<1>{maatsoort}\g<2>',
        content
    )
    
    # Replace tempo
    new_content = re.sub(
        r'(\\newcommand\{\\tempo\}\{)[^}]*(\})',
        rf'\g<1>{tempo}\g<2>',
        new_content
    )
    
    # Write file
    try:
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
    except Exception as e:
        print(f"❌ Error writing file: {e}")
        return False
    
    print(f"✅ Successfully updated {tex_file}: tempo={tempo}, maatsoort={maatsoort}")
    return True


def get_duration(measurecount_and_starttime_per_lieddeel, tempo, timesig, beats_up_front):
    """Calculate total duration of the array of lieddelen with their measure count
    given tempo (bpm) and timesignature (3/4, 4/4 etc.).
    
    Returns None when data is unknown.
    """
    
    beats_before = 0
    if beats_up_front is not None and isinstance(beats_up_front, (int, float)):
        beats_before = beats_up_front

    if measurecount_and_starttime_per_lieddeel is None or tempo is None or tempo == 0 or timesig is None:
        return None
    
    # determine the duration of a single measure
    beats_per_second = tempo / 60
    beat_duration = 1 / beats_per_second
    s_beats_per_measure, _, s_beat_base = timesig.partition('/')  # beat base is not needed? Dit gaat mis bij 6/8 vermoed ik, nog checken.
    beats_per_measure = int(s_beats_per_measure)
    beat_base = int(s_beat_base)
    measure_duration = beats_per_measure * beat_duration

    # calculate duration of all given lieddelen
    totalduration = 0
    for entry in measurecount_and_starttime_per_lieddeel:
        measure_count = entry[1]
        lieddeel_duration = (measure_count * measure_duration)
        totalduration += lieddeel_duration
    
    return totalduration  + (beats_before * beat_duration)  


def get_pickup_beats(nwctxt_filepath):
    """
    Detect and calculate pickup beats (anacrusis) in a NoteWorthy file.
    
    A pickup exists when:
    1. PgSetup contains StartingBar:0
    2. First Rest comes before first Bar
    
    Args:
        nwctxt_filepath: Path to .nwctxt file
    
    Returns:
        float: Number of pickup beats, or 0.0 if no pickup
    """
    with open(nwctxt_filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Check condition 1: StartingBar:0
    has_starting_bar_zero = False
    for line in lines:
        if line.startswith('|PgSetup|'):
            if '|StartingBar:0' in line:
                has_starting_bar_zero = True
            break
    
    if not has_starting_bar_zero:
        return 0.0
    
    # Find time signature to determine beat unit
    timesig_denominator = 4  # default
    for line in lines:
        if line.startswith('|TimeSig|Signature:'):
            try:
                sig = line.split('Signature:')[1].split('|')[0]
                timesig_denominator = int(sig.split('/')[1])
                break
            except (IndexError, ValueError):
                pass
    
    # Check condition 2: First Rest before first Bar
    first_rest_dur = None
    found_bar_first = False
    
    for line in lines:
        if line.startswith('|Bar'):
            found_bar_first = True
            break
        elif line.startswith('|Rest|Dur:'):
            # Extract duration
            try:
                dur_part = line.split('|Dur:')[1].split('|')[0]
                first_rest_dur = dur_part
                break
            except IndexError:
                pass
    
    if found_bar_first or first_rest_dur is None:
        return 0.0
    
    # Calculate beats from duration
    # Map duration names to whole note fractions
    duration_map = {
        'Whole': 1.0,
        'Half': 0.5,
        '4th': 0.25,
        '8th': 0.125,
        '16th': 0.0625,
        '32nd': 0.03125,
        '64th': 0.015625
    }
    
    # Parse duration (might include modifiers like ,Dotted)
    dur_base = first_rest_dur.split(',')[0]
    dur_base = dur_base.replace("\n","", -1)  # remove any lineendings
    note_value = duration_map.get(dur_base, 0.0)
    
    # Handle dotted notes
    if ',Dotted' in first_rest_dur or ',Dot' in first_rest_dur:
        note_value *= 1.5
    elif ',DblDotted' in first_rest_dur:
        note_value *= 1.75
    
    # Handle triplets
    if ',Triplet' in first_rest_dur:
        note_value *= (2.0 / 3.0)
    
    # Calculate beats based on time signature
    beat_unit_value = 1.0 / timesig_denominator
    beats = note_value / beat_unit_value
    
    return beats


def validate_and_setup_folders(songtitle, paths):
    """Validate input/output folders and song structure.

    Args:
        songtitle: Name of the song
        paths: ResolvedPaths object with folder paths

    Returns:
        tuple: (song_folder, nwc_folder)

    Raises:
        SystemExit: If validation fails
    """
    # Validate folders
    if not paths.validate_input_folder():
        sys.exit(1)
    if not paths.ensure_output_folders():
        sys.exit(1)

    # Open song folder
    song_folder = paths.input_folder / songtitle
    if not validate_folder_exists(song_folder, f"Song folder '{songtitle}'"):
        sys.exit(1)

    # Open nwc subfolder within song folder
    nwc_folder = song_folder / FOLDER_NWC
    if not validate_folder_exists(nwc_folder, f"NWC subfolder for '{songtitle}'"):
        sys.exit(1)

    return song_folder, nwc_folder


def load_song_structure(songtitle, nwc_folder):
    """Load song structure from volgorde.jsonc file.

    Args:
        songtitle: Name of the song
        nwc_folder: Path to NWC folder

    Returns:
        list: List of lieddeel names in order

    Raises:
        SystemExit: If file cannot be loaded or parsed
    """
    volgorde_file = nwc_folder / f"{songtitle} volgorde{EXT_JSONC}"
    if not validate_file_exists(volgorde_file, "Song sequence file (volgorde)"):
        sys.exit(1)

    try:
        volgorde_data = load_jsonc(volgorde_file)
        return volgorde_data['songstructure']
    except (commentjson.JSONLibraryException, ValueError, KeyError) as e:
        print(f"❌ Error reading volgorde: {e}")
        sys.exit(1)


def process_lieddelen(songtitle, volgorde_lieddelen, nwc_folder):
    """Process all lieddelen and extract metadata.

    Args:
        songtitle: Name of the song
        volgorde_lieddelen: List of lieddeel names
        nwc_folder: Path to NWC folder

    Returns:
        tuple: (file_list, measurecount_and_starttime_per_lieddeel, chords_per_lieddeel, tempo, timesig, pickup_beats)
    """
    file_list = []
    measurecount_and_starttime_per_lieddeel = []
    chords_per_lieddeel = {}
    tempo = None
    timesig = None
    pickup_beats = 0

    for lieddeel in volgorde_lieddelen:
        lieddeel_nwctxt = nwc_folder / f"{songtitle} {lieddeel}{EXT_NWCTXT}"

        if not validate_file_exists(lieddeel_nwctxt, f"Lieddeel file '{lieddeel}'"):
            sys.exit(1)

        # Extract tempo and timesig from first section, only once per deel
        if tempo is None and timesig is None:
            tempo, timesig = extract_tempo_and_timesig(str(lieddeel_nwctxt))
            pickup_beats = get_pickup_beats(lieddeel_nwctxt)
            print(f"⚠️ NOTE: Detected {pickup_beats} beats up front.")

        file_list.append(str(lieddeel_nwctxt))
        measure_count = get_measure_count(str(lieddeel_nwctxt))
        lieddeel_starttime = get_duration(measurecount_and_starttime_per_lieddeel, tempo, timesig, pickup_beats)
        measurecount_and_starttime_per_lieddeel.append((lieddeel, measure_count, lieddeel_starttime))

        # Extract chord info only once per unique section
        if lieddeel not in chords_per_lieddeel:
            chord_string, chord_count, is_valid = extract_chords_from_first_staff(str(lieddeel_nwctxt))
            chords_per_lieddeel[lieddeel] = (chord_string, chord_count, is_valid)

        measure_str = f" ({measure_count} measures)" if measure_count else ""
        print(f"Adding lieddeel: {lieddeel}{measure_str}")

    return file_list, measurecount_and_starttime_per_lieddeel, chords_per_lieddeel, tempo, timesig, pickup_beats


def main():
    """Main entry point for nwc-concat script.

    Loads path configuration, validates folders, and concatenates
    NoteWorthy Composer files based on song structure.
    """
    parser = argparse.ArgumentParser(description='Concatenate NoteWorthy Composer files')
    parser.add_argument('songtitle', help='Title of the song')
    parser.add_argument('--keep-tempi', action='store_true',
                        help='Keep tempo indicators from all lieddelen (default: remove from lieddelen after first)')
    args = parser.parse_args()

    songtitle = args.songtitle
    keep_tempi = args.keep_tempi

    # Load and resolve path configuration
    paths = load_and_resolve_paths()

    # Validate and setup folders
    song_folder, nwc_folder = validate_and_setup_folders(songtitle, paths)

    # Load song structure
    volgorde_lieddelen = load_song_structure(songtitle, nwc_folder)

    print(f"Processing song: {songtitle}")
    print(f"Sequence: {' - '.join(volgorde_lieddelen)}")
    print(f"Tempo handling: {'Keep all tempi' if keep_tempi else 'Remove tempi from lieddelen 2+'}")

    # Process all lieddelen
    (file_list, measurecount_and_starttime_per_lieddeel, chords_per_lieddeel,
     tempo, timesig, pickup_beats) = process_lieddelen(songtitle, volgorde_lieddelen, nwc_folder)

    # Concatenate files
    output_nwctxt = paths.output_folder / f"{songtitle}.nwctxt"
    print(f"\nConcatenating {len(file_list)} lieddelen...")
    concatenate_nwctxt_files(file_list, str(output_nwctxt), keep_tempi=keep_tempi)
    print(f"✅ Success! Concatenated .nwctxt files to {output_nwctxt}")

    # Write analysis of concatenated .nwctxt file
    write_analysis_to_file(output_nwctxt)

    # Generate complete LaTeX structure file
    tex_file = paths.output_folder / f"{songtitle} structuur.tex"
    print(f"Generating: {tex_file}")
    write_latex_file(tex_file, songtitle, tempo, timesig, measurecount_and_starttime_per_lieddeel, chords_per_lieddeel, pickup_beats)
    print(f"✅ Success! Created: {tex_file}")

    # Generate label track file for Tenacity
    labeltrack_file = paths.audio_output_folder / f"{songtitle} labeltrack t_{tempo}.txt"
    print(f"Generating: {labeltrack_file}")
    write_labeltrack_file(labeltrack_file, measurecount_and_starttime_per_lieddeel)
    print(f"✅ Success! Created: {labeltrack_file}")

    update_liedtekst_tex_file(songtitle, tempo, timesig, song_folder)
    print(f"✅ Success! Updated liedtekst tempo and timesig for {songtitle}")


if __name__ == "__main__":
    main()