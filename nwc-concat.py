#!/usr/bin/env python3
"""
nwc-concat.py - Concatenate NoteWorthy Composer sections based on sequence file.

Creates:
- Concatenated .nwctxt file with all sections
- LaTeX structure file with song metadata, parts overview, and composition

Staff Conventions:
This script extracts specific information from named staffs:
- Bass staff: Contains tempo, time signature, and chord annotations (akk: markers)
- Ritme staff: Contains measure count information via repeat markers

The order of staffs in .nwctxt files is flexible, but must be consistent across
all section files for the same song.

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
from nwc_analyze import write_analysis_to_file, count_vooraf_measures
from nwc_utils import parse_nwctxt, NwcFile, parse_duration
from constants import (NWC_PREFIX_ADDSTAFF, NWC_PREFIX_STAFF_PROPERTIES,
                        NWC_PREFIX_STAFF_INSTRUMENT, NWC_PREFIX_CLEF,
                        NWC_PREFIX_TIMESIG, NWC_PREFIX_TEMPO, NWC_PREFIX_BAR,
                        NWC_PREFIX_TEXT, NWC_END_MARKER, FOLDER_NWC, EXT_NWCTXT,
                        EXT_JSONC, STAFF_NAME_BASS, STAFF_NAME_RITME
                        )

def get_duration_per_tempo_and_timesig_progression_from_bass_staff(filepath, start_tempo, start_timesig, ignore_first_measure=False):
    """
    Returns a list of tempo and timesig changes, with their calculated measure_count and duration.
    Returns the duration of any pickup_beats as well, so the caller can decide what to do with it.

    For exact calculation of duration, we must know both the tempo, the number of measures and
    the timesig (3/4, 4/4): without the timesig we don't know how many beats are in a measure.
    """

    tempo_and_timesig_progression = extract_progression_of_multiple_targets_with_measurecount_from_bass_staff(
        filepath, (find_tempo, start_tempo), (find_timesig, start_timesig))

    # Nu we tempo, timesig en measure_count hebben kunnen we duration gaan berekenen.
    
    # BUG: NIET VOOR INTRO, WANT DAN MOET JE WETEN OF DE EERSTE MAAT EEN PICKUP MAAT IS
    # 
    # FUNCTIE VAN PICKUPBEATS
    # de functie van de pickupbeat(s) is het issue te voorkomen dat in Tenacity geluid op de 
    # allereerste tel krakerig afspeelt of zelfs laat wegvallen, met als gevolg dat je tijdens het inspelen
    # verkeerd gaat tellen: daarom de eerste tel altijd overslaan. Qua definitie hoeft het niet één tel te zijn
    # maar spreken we van pickupbeats zodra er minder tellen in de eerste maat zitten dan de timesig aangeeft.
    #
    # FUNCTIE VAN VOORAFMATEN
    # De functie van voorafmaten is om tijdens recording tijd te hebben tussen het _starten_ van de opname,
    # waarvoor je één hand nodig hebt en ik dus mijn plectrum met neerleggen, en 
    # het begin van het muziekstuk, omdat ik altijd loop te hannesen met het omhangen van mijn gitaar en 
    # positioneren van mijn plectrum, het op de juiste plek voor de mic gaan staan etc. 
    #
    # DOELEN
    # - duur van het liedje berekenen (ergo: pickupbeats en voorafmaten _niet_ meenemen)
    # - labeltrack maken met exacte tijdsposities (ergo: pickupbeats en voorafmaten _wel_ meenemen)
    
    # COMPLICATIE:
    # - Duration berekenen we vaak op basis van het aantal maten, maar voor een maat met pickupbeats
    #   is dat incorrect omdat daar minder tellen inzitten dan de timesig aangeeft.
    # 
    # Dus code-structuur:
    # tempo/timesig analyse: is onafhankelijk van pickupbeats en voorafmaten, want telt gewoon het aantal maten en niet duration.
    # calculate_pickupbeats: param tempo/timesig analyse: telt aantal beats in eerste maat als dat minder is dan timesig-teller; 
    #       needs timesig/tempo om duration ervan te bepalen. 
    #       Returns beats_count, beats_duration. 
    # calculate_voorafmaten: param pickupbeats, tempo/timesig: telt aantal HELE maten before liedstart, zonder pickupbeats. 
    #       needs pickupbeats om wel/niet eerste maat te negeren en timesig/tempo om duration te bepalen. 
    #       Returns measures_count, measures_duration.
    
    tempo_and_timesig_progression = [
        [tempo, timesig, measure_count, calculate_duration_by_measure_count(tempo, timesig, measure_count)]
        for tempo, timesig, measure_count in tempo_and_timesig_progression
    ] 

    return tempo_and_timesig_progression


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


def extract_progression_of_multiple_targets_with_measurecount_from_bass_staff(filepath, *finders_with_initial_value):
    """
    Extracts the progression of target combinations, such as the combination of tempo and timesig.

    An example of what is meant by 'progression of targets', with tempo and timesig as targets:
    progress    tempo   timesig     duration
    1           180     4/4         34          song starts with 34 measures t=180, 'mars' candans
    2           172     3/4         12          then 12 measures slow 'walz' (hoem-pa-pa)
    3           180     4/4         42          then back to original tempo and cadans for 42 measures.

    - *finders_with_initial_value is an unlimited list of tuples of find_methods with 
        their start_value (required!)), unlimited at least in theory: I never tested more than 2.
    - start_values should be passed when they are not set at the start of the given file.**

    ** Example when start_values are required: suppose you pass a filepath to a lieddeel to this
    method, then it may inherit its initial tempo from its preceding lieddeel. It may then
    have a tempo along the way or even no tempo indicator at all. Since the preceding
    lieddeel is unknown to the current method, it can't resolve these startvalues by itself.
    But note that this method always first tries to find the indicators itself, because the
    caller does not yet know for sure about the available indicators in the current lieddeel.
    """
    nwc = NwcFile(filepath)

    bass_staff = nwc.get_staff_by_name(STAFF_NAME_BASS)
    if not bass_staff:
        return "-", 0, True

    bass_staff_lines = bass_staff.lines

    # Hint of what this method tries to solve: suppose you want to make a list of all subsequent
    # changes of a certain parameter in a song, say 'tempo'. That's easy: loop through all
    # lines and detect each tempo change. 
    # But then you realize that for each tempo (bpm) you need to know what timesig it has, because
    # if the value is counted as eight-note beats, it is half as slow as when it counts as
    # quarternotes! So now you want to list changes to a combination of parameters and
    # each change must contain a record of both parameters.
    # So, hopefully, the code hopefully makes more sense: for each parameter that you want to
    # monitor there's a corresponding find_method (and optional start_value). A
    # parameter that you want to monitor is called a _target_ (search target).


    # -- INITIALIZATION start --

    results = []   # list of lists: the inner list is in the order of the find_methods
    nr_of_values_per_result_record = 3  # tempo, timesig, duration
    first_result = [None] * nr_of_values_per_result_record

    # Problem: for the first record, targets may have been set at the beginning of the song but
    # maybe they're not: we don't know yet so should we use the inherited values or not?
    # Solution: we always use the startvalues, and in case indeed the targets are found
    # at the beginning of the song, the measures_count is still 0 and the first record,
    # with our start_values, is deleted automatically. So nothing complex here!

    # Initialize first_result with startvalues. Note: for intro, this will result in default values 120 and '4/4'.
    i_fm = 0   # indexer for the list of find_methods, 0-based
    for find_method, startvalue in finders_with_initial_value:
        first_result[i_fm] = startvalue
        i_fm += 1

    results.append(first_result)
    # -- INITIALIZATION end --    
    # Status: all targets have a value in first_result (but no measure_count yet).

    # nu regel voor regel het hele bestand doorlopen op zoek naar changed targets
    result = [None] * nr_of_values_per_result_record  # [None, None, None, ...]
    last_result = results[-1]  # [-1] returns the last element of a list. We need this to detect changes.
    last_target = None
    measures_count = 0
    current_measure_has_duration = False
    i_line = 0
    for line in bass_staff_lines:   # we'll find the same targets initially, but they will be ignored.
        i_line += 1
        i_fm = 0
        for find_method, _ in finders_with_initial_value:
            found_target = find_method(line)  # returns the target value, defined elsewhere
            if found_target is not None:
                # check wether it has changed
                last_target = last_result[i_fm]
                if found_target != last_target:
                    # Check wether the previous settings had any duration:
                    # Als nog geen measures gevonden zijn, dus voor de vorige tempo/timesig settings, en
                    # we vinden alweer de volgende tempo of timesig indicator, dan zitten we kennelijk
                    # nog in dezelfde maat: één van de vorige waardes wordt dus overruled: in dat geval
                    # moeten we dus niet een nieuw record toevoegen maar de bestaande wijzigen.
                    if measures_count == 0:
                        # update existing record instead of add new one
                        result = last_result        # let result point to the existing record (result and last_result now point to the same record)
                        result[i_fm] = found_target # update value
                        # 'update the records'
                        last_target = found_target
                    else:
                        # store measurecount of previous change in last position of result list.
                        last_result[-1] = measures_count
                        # 'update the records' (administratie bijwerken)
                        result = last_result.copy() # copy previous result
                        result[i_fm] = found_target # update with the found target
                        results.append(result)
                        last_result = result 
                        measures_count = 0      # reset counter
                break  # done for this line, goto next
            i_fm += 1
    
        # Check for Bar marker
        if line.startswith('|Bar|') or line == '|Bar':
            if current_measure_has_duration:        # last_target is not None and ... weggehaald
                measures_count += 1
            current_measure_has_duration = False

        # Check for duration (note or rest)
        if '|Dur:' in line:
            current_measure_has_duration = True

    # Fill in measures_count for the last result because loop 
    #   exited before count had been completed and stored
    if last_result is not None:
        # Count last measure, since it hasn't been counted in yet
        if current_measure_has_duration:
            measures_count += 1

        # store count (or delete record if count is empty)
        if measures_count != 0:  # stefan: weetniet waarom 1 en niet 0
            last_result[-1] = measures_count
        else:
            results.pop()   # remove last entry (points to last_result btw) if it has no duration
    
    # hier niet de duur of iets anders berekenen: dit is immers een 'generieke' methode.

    return results


def calculate_duration_by_measure_count(tempo, timesig, measure_count):
    """Straight mathematics: returns the number of seconds.
    
    Given bpm (beats per minutes = tempo), the value of a single beat (the y 
    in timesig x/y), the number of beats per measure (the x in timesig x/y) and
    the number of measures (measure_count) we can simply calculate its 
    duration as a number of seconds.

    formule (van claude): duur maat (seconden) = (teller / noemer) * 4 * (60 / bpm)
    Dus dat keer aantal maten is de totale te retourneren duur
    """
    teller, noemer = map(int, timesig.split('/'))  # numerator, denominator
    duration = measure_count * (teller / noemer) * 4 * (60 / tempo)
    return duration


def calculate_duration_by_beat_count(tempo, beat_count):
    """Straight mathematics: returns the number of seconds.
    
    Given bpm (beats per minutes = tempo) and the number of beats (beat_count)
    we can simply calculate its duration as a number of seconds.
    """

    if tempo <= 0 or beat_count <= 0:
        return 0.0
    else:
        # 160 beats/min => 160/60 beats/sec => 60/160 sec per beat => 60/tempo sec per beat
        duration = beat_count * (60 / tempo)
        return duration


def extract_targets_with_measurecount_from_bass_staff(filepath, find_method):
    """Extracts the progression of targets from the Bass staff of a .nwctxt file.
    For each target, the number of measures is counted (equal targets are not aggregated).

    The 'find_method' parameter is a ref to a function: for example find_chord, find_tempo etc.
    
    Returns:
        tuple: (target, total_measures, is_valid)
        - target: the type of thing you're looking for. E.g. chord, as a formatted string like "B, F#, E(2), B(5)" or "-" if no chords
        - total_measures: total count of measures for that target
        - is_valid: True if count matches expected
    """
    nwc = NwcFile(filepath)

    bass_staff = nwc.get_staff_by_name(STAFF_NAME_BASS)
    if not bass_staff:
        return "-", 0, True

    bass_staff_lines = bass_staff.lines

    targets: list[tuple[int, int]] = []
    current_target = None
    current_measures = 0
    current_measure_has_duration = False

    for line in bass_staff_lines:
        # Check for target indication line
        found_target = find_method(line)  # returns the target value, defined elsewhere
        if found_target is not None:
            if found_target == current_target:
                continue  # redundant repetition apparently; nothing really changes
            # Save previous target if any
            if current_target is not None:
                if current_measures > 1:
                    targets.append((current_target, current_measures))
                else:
                    targets.append((current_target, 0))
            current_target = found_target
            current_measures = 0
            current_measure_has_duration = False

        # Check for Bar marker
        if line.startswith('|Bar|') or line == '|Bar':
            if current_target is not None and current_measure_has_duration:
                current_measures += 1
            current_measure_has_duration = False

        # Check for duration (note or rest)
        if '|Dur:' in line:
            current_measure_has_duration = True

    # Handle the last target and last measure
    if current_target is not None:
        # Count last measure if it has duration
        if current_measure_has_duration:
            current_measures += 1

        if current_measures > 1:
            targets.append((current_target, current_measures))
        elif current_measures == 1:
            targets.append((current_target, 0))

    return targets


def find_bar(line):
    """
    Returns 1 if line contains a bar; returns None otherwise.
    Assumes as input a line from an nwctxt file.
    """
    if line.startswith(NWC_PREFIX_BAR) or line == '|Bar':
        return 1
    else:
        return None


def find_tempo(line):
    """
    Returns a tempo > 0 if line contains a tempo; returns None otherwise.
    Assumes as input a line from an nwctxt file.
    """
    # Look for tempo
    if line.startswith(NWC_PREFIX_TEMPO) and 'Tempo:' in line:
        try:
            # Extract tempo value after "Tempo:"
            tempo_part = line.split('Tempo:')[1]
            # Get the number before the next pipe or end of string
            tempo_str = tempo_part.split('|')[0]
            tempo = int(tempo_str)
            return tempo
        except (IndexError, ValueError):
            pass
    return None


def find_timesig(line):
    """
    Returns a timesig (e.g. 4/4) if line contains a timesig; returns None otherwise.
    Assumes as input a line from an nwctxt file.
    """
    # Look for timesig
    if line.startswith(f'{NWC_PREFIX_TIMESIG}Signature:'):
        try:
            # Extract signature after "Signature:"
            sig_part = line.split(f'{NWC_PREFIX_TIMESIG}Signature:')[1]
            # Get the signature before the next pipe or end of string
            timesig = sig_part.split('|')[0]
            return timesig
        except (IndexError, ValueError):
            pass
    return None


def find_chord(line):
    """
    Returns a chord if line contains an 'akk:'-text; returns None otherwise.
    Assumes as input a line from an nwctxt file.
    """
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
                    # Extract new chord (everything after "akk:")
                    new_chord = text_stripped[4:].strip()
                    return new_chord
        except (IndexError, ValueError):
            pass
    return None


def find_liedstart(line):
    NWC_MARKER_LIEDSTART = "liedstart"
    return line.strip().startswith(f'{NWC_PREFIX_TEXT}Text:"{NWC_MARKER_LIEDSTART}"')


def extract_tempi_from_bass_staff(filepath):
    """Extracts the tempo progression from the Bass staff of a .nwctxt file.
    For each tempo, the number of measures is counted (equal tempi are not aggregated).

    Returns:
        tuple: (tempo, total_measures, is_valid)
        - chord_string: 120, etc.
        - total_measures: total count of measures
        - is_valid: True if count matches expected
    """
    return extract_targets_with_measurecount_from_bass_staff(filepath, find_tempo)


def extract_timesigs_from_bass_staff(filepath):
    """Extracts the timesignature (3/4, 4/4) progression from the Bass staff of a .nwctxt file.
    For each timesig, the number of measures is counted (equal tempi are not aggregated).

    Returns:
        tuple: (timesig, total_measures, is_valid)
        - timesig: 3/4, 4/4 etc.
        - total_measures: total count of measures
        - is_valid: True if count matches expected
    """
    return extract_targets_with_measurecount_from_bass_staff(filepath, find_timesig)


def extract_chords_from_bass_staff(filepath):
    """Extract chord progression from Bass staff of .nwctxt file

    Returns:
        tuple: (chord_string, total_measures, is_valid)
        - chord_string: formatted string like "B, F#, E(2), B(5)" or "-" if no chords
        - total_measures: total count of measures
        - is_valid: True if count matches expected
    """
    targets = extract_targets_with_measurecount_from_bass_staff(filepath, find_chord)

    # Calculate total measures from chords
    total_from_chords = 0
    for _, count in targets:
        total_from_chords += count

    if not targets:
        return "-", 0, True

    chord_string = ", ".join(f"{chord} ({measure_count})" for chord, measure_count in targets)
    return chord_string, total_from_chords, True


def extract_first_tempo_and_timesig_from_bass_staff(filepath):
    """Extract _first_ tempo and time signature from Bass staff of .nwctxt file (lieddeel)

    IMPORTANT: the _first_ doesn't mean that it's at the beginning of the staff. So this
    method is as reliable as its input: don't use this method on anything else than the
    first part of a song, or the whole of it: not any other subpart.

    Returns:
        tuple: (tempo, timesig)
        - tempo: integer tempo value or None if not found
        - timesig: string like "4/4" or None if not found
    """
    nwc = NwcFile(filepath)

    bass_staff = nwc.get_staff_by_name(STAFF_NAME_BASS)
    if not bass_staff:
        return None, None

    staff_lines = bass_staff.lines

    tempo = None
    timesig = None

    for line in staff_lines:
        # Look for tempo (only first occurrence)
        if tempo is None:
            tempo = find_tempo(line)

        # Look for time signature (only first occurrence)
        if timesig is None:
            timesig = find_timesig(line)

        # Stop searching once both are found
        if tempo is not None and timesig is not None:
            break

    if tempo is None or timesig is None:
        raise ImportError("Het input bestand is ongeldig want er ontbreekt een tempo- timesignature indicator.")

    return tempo, timesig


def extract_lbltrck_markers_from_bass_staff(filepath):
    """Extract LBLTRCK markers with precise beat positions from Bass staff (of a lieddeel).

    Scans the Bass staff for Text elements with format 'LBLTRCK: label_text'
    and determines their exact position within measures.

    Args:
        filepath: Path to .nwctxt file

    Returns:
        List of tuples: (label_text, measure_number, beat_position_in_quarters)
        - measure_number is 0-based (0 = first measure)
        - beat_position_in_quarters is position within measure in quarter notes
        Empty list if no markers found or Bass staff not found
    """
    nwc = NwcFile(filepath)

    bass_staff = nwc.get_staff_by_name(STAFF_NAME_BASS)
    if not bass_staff:
        return []

    staff_lines = bass_staff.lines
    markers = []
    current_measure = 0
    current_beat_pos = 0.0  # Position within current measure in quarter notes
    current_measure_has_dur = False

    for line in staff_lines:
        # Check for LBLTRCK marker in Text entries
        if line.startswith(NWC_PREFIX_TEXT) and 'Text:"' in line:
            try:
                # Extract the text content
                text_start = line.find('Text:"') + 6
                text_end = line.find('"', text_start)
                if text_end > text_start:
                    text_content = line[text_start:text_end]
                    # Check if it starts with "LBLTRCK:"
                    text_stripped = text_content.strip()
                    if text_stripped.startswith('LBLTRCK:'):
                        # Extract label text (everything after "LBLTRCK:")
                        label_text = text_stripped[8:].strip()
                        if label_text:  # Only add non-empty labels
                            markers.append((label_text, current_measure, current_beat_pos))
            except (IndexError, ValueError):
                continue

        # Track measure boundaries
        if line.startswith(NWC_PREFIX_BAR) or line == '|Bar':
            if current_measure_has_dur:
                current_measure += 1
                current_beat_pos = 0.0
            current_measure_has_dur = False

        # Track durations for precise beat position
        if '|Dur:' in line:
            current_measure_has_dur = True
            duration = parse_duration(line)
            current_beat_pos += duration

    return markers


def write_latex_file(tex_file, songtitle, tempo, timesig, data_per_lieddeel, chords_per_lieddeel, pickup_beats_first_lieddeel, complete_analysis=None):
    """Write complete LaTeX file with song meta info

    Args:
        tex_file: Path to .tex file
        songtitle: Title of the song
        tempo: Tempo value (integer) or None
        timesig: Time signature string (e.g. "4/4") or None
        data_per_lieddeel: List of tuples (lieddeel, lieddeel_measure_count, 
            lieddeel_starttime_with_pickupbeats, lieddeel_duration_with_pickupbeats, duration_of_pickup_beats)
        chords_per_lieddeel: Dict mapping section_name to (chord_string, chord_count, is_valid)
        pickup_beats: Number of pickup beats at the start of the song
        complete_analysis: Optional dict from analyze_complete_song() with corrected totals.
                If provided, uses total_measures and total_duration from this.
                If None, falls back to legacy calculation.
    """

    # Get unique sections in order of first appearance
    unique_lieddelen = []
    seen = set()
    for lieddeel_name, _, _, _, _ in data_per_lieddeel:
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

        # Use complete_analysis if provided, otherwise fall back to legacy calculation
        if complete_analysis:
            totalmeasures = complete_analysis['total_measures']
            total_duration_seconds = complete_analysis['total_duration']
        else:
            # Legacy calculation (for backwards compatibility)
            # totalmeasures = 0
            # for _, measures, _ in measurecount_and_starttime_per_lieddeel:
            #     if measures is not None:
            #         totalmeasures += measures
            # total_duration_seconds = get_duration(measurecount_and_starttime_per_lieddeel, tempo, timesig, pickup_beats)        # legacy indeed: only correct when song has just one tempo.
            raise AssertionError  # complete_analysis must be true (legacy no longer supported)

        # Format duration
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
            for s, m, _, _, _ in data_per_lieddeel:
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
        for i, (section, measures, _, _, _) in enumerate(data_per_lieddeel, 1):
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


def write_labeltrack_file(labeltrack_file, all_labels):
    """Write complete label track for song

    Args:
        labeltrack_file: Path to .txt file
        all_labels: List of tuples (label_text, time_in_seconds) containing both
                lieddeel markers and LBLTRCK markers
    """
    if labeltrack_file is None or all_labels is None:
        print("⚠️ No labeltrack file created because of empty parameter value(s).")
        return

    # Sort labels by time
    sorted_labels = sorted(all_labels, key=lambda x: x[1])

    # Write the complete file in Audacity label track format
    with open(labeltrack_file, 'w', encoding='utf-8') as f:
        for label_text, time in sorted_labels:
            formattedsixdecimals = f"{time:.6f}"
            f.write(f'{formattedsixdecimals}\t{formattedsixdecimals}\t{label_text}\n')


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


def get_beats_before_target_from_first_staff(nwctxt_filepath, tempo, timesig, finder):
    """
    Return the number and duration of beats dat voorafgaat aan een opgegeven markering ('finder') (tellen vooraf, anacrusis) in a NoteWorthy file (lieddeel).

    Note: only the first part of a song can have 'vooraf' beats (we can't check that here, but caller arrange for this)
    
    Args:
        nwctxt_filepath: Path to .nwctxt file
    
    Returns:
        float: number and total duration of the vooraf beats.
    """
    with open(nwctxt_filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the position (regelnr) of target
    found_on_line_in_file = -1
    for i, line in enumerate(lines):
        if finder(line) is not None:
            found_on_line_in_file = i
            break

    if found_on_line_in_file == -1:
        # No target found, return 0
        return 0

    # Count beats before liedstart
    beats_count = 0
    for i in range(found_on_line_in_file):
        contents = lines[i].strip()
        if "|Dur:" in contents:
            dur_with_modifier = contents.split("|Dur:")[1].split("|")[0]    # e.g. "4th,Dotted", or "Whole"
            beats_count += get_beats_for_notelength_name(dur_with_modifier, timesig)

    beats_duration = calculate_duration_by_beat_count(tempo, beats_count)

    return beats_count, beats_duration


def get_beats_for_notelength_name(noteworthy_note, timesig):
    """ Calculate beat count from strings like "Whole", "4th,Dotted" etc. """

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
    dur_base = noteworthy_note.split(',')[0]
    dur_base = dur_base.replace("\n","", -1)  # remove any lineendings
    note_value = duration_map.get(dur_base, 0.0)

    # Handle dotted notes
    if ',Dotted' in noteworthy_note or ',Dot' in dur_with_modifier:
        note_value *= 1.5
    elif ',DblDotted' in noteworthy_note:
        note_value *= 1.75

    # Handle triplets
    if ',Triplet' in noteworthy_note:
        note_value *= (2.0 / 3.0)

    # Calculate beats based on time signature
    beat_unit_value = 1.0 / timesig
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


# to do: vooraf_measures zijn nog included in het resultaat: die moeten echter opgeteld worden 
# bij de pickupbeats en als geheel moet de duur ervan berekend worden zodat die optioneel van
# de totale duur kan worden afgetrokken.
def process_lieddelen(songtitle, volgorde_lieddelen, nwc_folder):
    """Process all lieddelen and extract metadata.

    Args:
        songtitle: Name of the song
        volgorde_lieddelen: List of lieddeel names
        nwc_folder: Path to NWC folder

    Returns:
        tuple: (file_list, measurecount_and_starttime_per_lieddeel, chords_per_lieddeel, all_labels, tempo, timesig, pickup_beats)
        all_labels is a list of tuples: (label_text, time_in_seconds)
    """

    #   A note about this code: it calculates the starttime van een 
    # lieddeel door de duur van de VOORGAANDE lieddelen te berekenen.
    # Daarom moet je goed opletten wat current en wat previous is.

    file_list = []
    data_per_lieddeel = []
    chords_per_lieddeel = {}
    all_labels = []
    tempo = None
    timesig = None
    vooraf_beats_in_first_lieddeel = 0   # includes 'maten_vooraf' as well
    vooraf_beats = 0
    inherited_tempo = 120   # these are the defaults that you will see when you don't set them in the intro lieddeel
    inherited_timesig = '4/4'
    tempo_and_timesig_progression_in_lieddeel = None

    i_lieddeel = 0
    for lieddeel in volgorde_lieddelen:
        lieddeel_nwctxt = nwc_folder / f"{songtitle} {lieddeel}{EXT_NWCTXT}"

        if not validate_file_exists(lieddeel_nwctxt, f"Lieddeel file '{lieddeel}'"):
            sys.exit(1)

        # data_per_lieddeel only contains all preceding lieddelen, until the current one.
        # Datastructuur = list of 
        #   0-lieddeel, 
        #   1-lieddeel_measure_count, 
        #   2-lieddeel_starttime, 
        #   3-lieddeel_duration, 
        #   4-duration_of_pickup_beats

        # tempo_and_timesig_progression_in_lieddeel contains progress over an entire lieddeel.
        # Datastructuur = list of 
        #   0-tempo, 
        #   1-timesig, 
        #   2-measure_count,
        #   3-duration

        # Extract pickup beats for first section only
        if i_lieddeel == 0:
            
            beats_before_first_bar = get_beats_before_target_from_first_staff(lieddeel_nwctxt, find_bar)

            # to do: als beats before first bar gelijk is aan de teller van de timesig is er niks aan de hand: dan pickup_beat op 0 zetten.
            # Is het kleiner, dan count als 'pickup_beats' instellen.

            pickup_beats_in_first_lieddeel, duration_of_pickup_beats = beats_before_first_bar
            vooraf_beats_in_first_lieddeel, duration_of_vooraf_beats = get_beats_before_target_from_first_staff(lieddeel_nwctxt, find_liedstart)
            
            # for further processing:
            pickup_beats = pickup_beat_in_first_lieddeel
            vooraf_beats = vooraf_beats_in_first_lieddeel  
            print(f"ℹ️ NOTE: Detected {pickup_beat_in_first_lieddeel} beats up front.")
        else:
            vooraf_beats = 0   # alleen in eerste lieddeel houden we rekening met pickup_beats. In andere lieddelen zijn pickup beats simpelweg een fout die je daar maar moet herstellen.
            # get tempo/timesig from preceding lieddeel
            inherited_tempo = tempo_and_timesig_progression_in_lieddeel[-1][0]      # from last record get first value
            inherited_timesig = tempo_and_timesig_progression_in_lieddeel[-1][1]    # from last record get second value

        file_list.append(str(lieddeel_nwctxt))

        # Extract tempo and timesig progression from current lieddeel
        tempo_and_timesig_progression_in_lieddeel = \
            get_duration_per_tempo_and_timesig_progression_from_bass_staff(
                lieddeel_nwctxt, inherited_tempo, inherited_timesig
            )
        
        # Store first tempo and timesig, for return value. 
        if i_lieddeel == 0:
            tempo = tempo_and_timesig_progression_in_lieddeel[0][0]
            timesig = tempo_and_timesig_progression_in_lieddeel[0][1]

        # Count measures for current entire lieddeel
        lieddeel_measure_count = sum(measure_count for  _, _, measure_count, _ in tempo_and_timesig_progression_in_lieddeel)
        
        # Sum durations of all preceding lieddelen: this gives us the starttime of the current one.
        lieddeel_starttime_with_pickupbeats = 0   # default, works for intro only
        if i_lieddeel != 0:
            lieddeel_starttime_with_pickupbeats = sum(duration for  _, _, _, duration, _ in data_per_lieddeel)

        # Calculate durations (and other values) of current lieddeel
        # Note: in practice, only the first lieddeel can have pickupbeats, but we do it for all.
        lieddeel_duration_with_pickupbeats = sum(duration for  _, _, _, duration in tempo_and_timesig_progression_in_lieddeel)
        lieddeel_duration_without_pickupbeats = lieddeel_duration_with_pickupbeats - duration_of_vooraf_beats
        
        # Store results
        data_per_lieddeel.append((lieddeel, lieddeel_measure_count, lieddeel_starttime_with_pickupbeats, 
                                    lieddeel_duration_with_pickupbeats, duration_of_vooraf_beats))
        
        # Add lieddeel label to all_labels list
        all_labels.append((lieddeel, lieddeel_starttime_with_pickupbeats))   
        # note: duration of pickup_beats has not been subtracted from 
        # starttime: that is exactly so required for the labeltrack!

        # Extract LBLTRCK markers and calculate their absolute times
        lbltrck_markers = extract_lbltrck_markers_from_bass_staff(str(lieddeel_nwctxt))     # to do: this is not an exact calculation: to be improved.
        if lbltrck_markers:
            # Calculate timing parameters
            beats_per_second = tempo / 60
            beat_duration = 1 / beats_per_second
            s_beats_per_measure, _, s_beat_base = timesig.partition('/')
            beats_per_measure = int(s_beats_per_measure)
            beat_base = int(s_beat_base)
            measure_duration = beats_per_measure * beat_duration

            # Add each marker with its precise absolute time
            for label_text, measure_number, beat_pos_in_quarters in lbltrck_markers:
                # Convert quarter note position to beats in current time signature
                # Example: in 4/4, quarter = 1 beat; in 6/8, quarter = 0.5 beats
                beats_within_measure = beat_pos_in_quarters * (4.0 / beat_base)
                time_within_measure = beats_within_measure * beat_duration

                marker_time = lieddeel_starttime_with_pickupbeats + (measure_number * measure_duration) + time_within_measure
                all_labels.append((label_text, marker_time))

        # Extract chord info only once per unique section
        if lieddeel not in chords_per_lieddeel:
            chord_string, chord_count, is_valid = extract_chords_from_bass_staff(str(lieddeel_nwctxt))
            chords_per_lieddeel[lieddeel] = (chord_string, chord_count, is_valid)

        measure_str = f" ({lieddeel_measure_count} measures)" if lieddeel_measure_count else ""
        print(f"Adding lieddeel: {lieddeel}{measure_str}")
        i_lieddeel += 1

    return file_list, data_per_lieddeel, chords_per_lieddeel, all_labels, tempo, timesig, vooraf_beats_in_first_lieddeel


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
    paths = load_and_resolve_paths(songtitle)

    # Validate and setup folders
    song_folder, nwc_folder = validate_and_setup_folders(songtitle, paths)

    # Load song structure
    volgorde_lieddelen = load_song_structure(songtitle, nwc_folder)

    print(f"Processing song: {songtitle}")
    print(f"Sequence: {' - '.join(volgorde_lieddelen)}")
    print(f"Tempo handling: {'Keep all tempi' if keep_tempi else 'Remove tempi from lieddelen 2+'}")

    # Process all lieddelen
    (file_list, data_per_lieddeel, chords_per_lieddeel, all_labels,
    main_tempo, main_timesig, pickup_beats_in_first_lieddeel) = process_lieddelen(songtitle, volgorde_lieddelen, nwc_folder)

    # file_list, data_per_lieddeel, chords_per_lieddeel, all_labels, tempo, timesig, pickup_beats_in_first_lieddeel
    # data_per_lieddeel: lieddeel, lieddeel_measure_count, lieddeel_starttime_with_pickupbeats, lieddeel_duration_with_pickupbeats, duration_of_pickup_beats))

    # Concatenate files
    output_nwctxt = paths.build_folder / f"{songtitle}.nwctxt"
    print(f"\nConcatenating {len(file_list)} lieddelen...")
    concatenate_nwctxt_files(file_list, str(output_nwctxt), keep_tempi=keep_tempi)
    print(f"✅ Success! Concatenated .nwctxt files to {output_nwctxt}")

    # Analyze concatenated .nwctxt file (get complete song metadata)
    _ , complete_analysis = write_analysis_to_file(songtitle, output_nwctxt)

    if not complete_analysis:
        print("⚠️ Warning: Analysis failed, continuing with limited data")
        complete_analysis = {
            'total_measures': 0,
            'total_duration': None,
            'vooraf': 0,
        }

    # Generate complete LaTeX structure file using analysis data
    tex_file = paths.build_folder / f"{songtitle} structuur.tex"
    print(f"Generating: {tex_file}")
    write_latex_file(tex_file, songtitle, main_tempo, main_timesig, data_per_lieddeel,
                    chords_per_lieddeel, pickup_beats_in_first_lieddeel, complete_analysis)
    print(f"✅ Success! Created: {tex_file}")

    # Generate label track file for Tenacity in song-specific subfolder
    song_audio_folder = paths.audio_output_folder / songtitle
    song_audio_folder.mkdir(parents=True, exist_ok=True)
    labeltrack_file = song_audio_folder / f"{songtitle} labeltrack t_{main_tempo}.txt"
    print(f"Generating: {labeltrack_file}")
    write_labeltrack_file(labeltrack_file, all_labels)
    print(f"✅ Success! Created: {labeltrack_file}")

    update_liedtekst_tex_file(songtitle, main_tempo, main_timesig, song_folder)
    print(f"✅ Success! Updated liedtekst tempo and timesig in {songtitle}.tex")


if __name__ == "__main__":
    main()
