#!/usr/bin/env python3
"""
pad-staffs.py - Pad all staffs in each lieddeel with empty measures to match
the Bass staff's measure count and trailing structure.

For each .nwctxt section file of a song (as listed in volgorde.jsonc):
  - Determines the Bass staff's measure count and time signature.
  - For every other staff (except those listed in PAD_STAFFS_IGNORED_STAFFS,
    e.g. the Ritme staff), appends empty rest measures to the end until the
    measure count matches the Bass.
  - The duration of the appended rest matches the Bass staff's last time
    signature (e.g. Whole for 4/4, Half,Dotted for 3/4 or 6/8).
  - For staffs in the "drums" group (detected via |Group:"drums" on the
    |AddStaff| line), each appended measure's rest content is bracketed by
    a |User|DrumStaff_AUDIO.fso|Pos:1|Class:StaffSig|InOut:Y marker line at
    both its start and end, matching the convention used by NWC drum staffs.
  - If the Bass closes with a trailing |Bar (i.e. its last line before the
    next staff is |Bar), the same trailing |Bar is added to each other staff
    so that the final barline aligns visually across staffs.
  - Staffs that exceed the Bass count are skipped with a warning.

A "measure" is each segment delimited by |Bar markers: the pickup before
the first |Bar counts as one measure if it contains any duration, and the
dangling segment after the last |Bar likewise counts as one if it contains
any duration.

Usage:
    python pad-staffs.py "Song Title"
"""

import argparse
import sys
from pathlib import Path

from pathconfig import (load_and_resolve_paths, validate_file_exists,
                        validate_folder_exists, load_jsonc)
from nwc_utils import NwcFile, NwcStaff
from constants import (NWC_PREFIX_ADDSTAFF, NWC_PREFIX_BAR, NWC_PREFIX_TIMESIG,
                        EXT_NWCTXT, EXT_JSONC, FOLDER_NWC,
                        STAFF_NAME_BASS, PAD_STAFFS_IGNORED_STAFFS)


# Maps a time signature to the NWC |Rest|Dur: tokens that together fill
# exactly one measure. Each token becomes a separate |Rest| line.
_TIMESIG_TO_REST_DURATIONS = {
    '4/4':  ['Whole'],
    '3/4':  ['Half,Dotted'],
    '2/4':  ['Half'],
    '6/8':  ['Half,Dotted'],
    '9/8':  ['Half,Dotted', '4th,Dotted'],
    '12/8': ['Whole,Dotted'],
    '2/2':  ['Whole'],
    '6/4':  ['Whole', 'Half'],
}

_DEFAULT_TIMESIG = '4/4'

# Substring used to detect membership of the "drums" group on |AddStaff| lines.
# A drum staff's AddStaff line contains |Group:"drums" (position not guaranteed).
_DRUMS_GROUP_MARKER = '|Group:"drums"'

# When padding a drum-group staff, each new measure's rest content is bracketed
# by this marker line at the start and the end (between the bar separators).
_DRUMS_AUDIO_MARKER = '|User|DrumStaff_AUDIO.fso|Pos:1|Class:StaffSig|InOut:Y'


def _last_timesig(staff: NwcStaff) -> str | None:
    """Return the last TimeSig signature value seen in this staff, or None."""
    last = None
    prefix = f'{NWC_PREFIX_TIMESIG}Signature:'
    for line in staff.lines:
        if line.startswith(prefix):
            try:
                last = line.split('Signature:')[1].split('|')[0]
            except (IndexError, ValueError):
                pass
    return last


def _count_measures(staff: NwcStaff) -> int:
    """Count measure segments in a staff.

    Each |Bar marker closes one measure. The pickup before the first |Bar
    and the dangling segment after the last |Bar each count as one measure
    iff they contain at least one line with a |Dur: token.
    """
    measures = 0
    current_has_dur = False

    for line in staff.lines:
        if line.startswith(NWC_PREFIX_BAR):
            measures += 1
            current_has_dur = False
        elif '|Dur:' in line:
            current_has_dur = True

    if current_has_dur:
        measures += 1

    return measures


def _staff_in_drums_group(staff: NwcStaff) -> bool:
    """Return True if the staff's |AddStaff| line declares Group:"drums".

    Robust against attribute reordering: matches the |Group:"drums" substring
    anywhere on the AddStaff line (it always starts with | so cannot collide
    with a different attribute that happens to contain the word "drums" as a
    value, e.g. Name:"drumkit").
    """
    for line in staff.lines:
        if line.startswith(NWC_PREFIX_ADDSTAFF):
            return _DRUMS_GROUP_MARKER in line
    return False


def _empty_measure_content_lines(timesig: str, in_drums_group: bool) -> tuple[list[str], bool]:
    """Return (content_lines, is_exact_match): the lines that form one empty
    measure's content (everything between the |Bar separators), WITHOUT a
    leading |Bar.

    The caller adds the |Bar separator itself, so it can skip it when the staff
    already ends with a |Bar (otherwise a phantom empty measure would appear).

    For staffs in the "drums" group, the rest content is bracketed by the
    DrumStaff_AUDIO marker line at the start and end of the measure.

    `is_exact_match` is False when the timesig is not in the known map and a
    Whole-rest fallback is used (caller should warn).
    """
    durations = _TIMESIG_TO_REST_DURATIONS.get(timesig)
    if durations is None:
        rest_lines = ['|Rest|Dur:Whole']
        is_exact = False
    else:
        rest_lines = [f'|Rest|Dur:{dur}' for dur in durations]
        is_exact = True

    if in_drums_group:
        return [_DRUMS_AUDIO_MARKER, *rest_lines, _DRUMS_AUDIO_MARKER], is_exact
    return rest_lines, is_exact


def _staff_ends_with_bar(staff: NwcStaff) -> bool:
    """Return True if the staff's last segment is closed by a |Bar.

    Scans from the end: if a |Bar appears before any line containing |Dur:,
    the staff has no dangling open measure and ends with a bar separator.
    """
    for line in reversed(staff.lines):
        if line.startswith(NWC_PREFIX_BAR):
            return True
        if '|Dur:' in line:
            return False
    return False


def _load_unique_section_paths(songtitle: str, nwc_folder: Path) -> list[Path]:
    """Read volgorde.jsonc and return unique section file paths in first-seen order."""
    volgorde_file = nwc_folder / f"{songtitle} volgorde{EXT_JSONC}"
    if not validate_file_exists(volgorde_file, "Song sequence file (volgorde.jsonc)"):
        sys.exit(1)

    try:
        volgorde_data = load_jsonc(volgorde_file)
        all_sections = volgorde_data['songstructure']
    except Exception as e:
        print(f"❌ Error reading volgorde.jsonc: {e}")
        sys.exit(1)

    seen: set[str] = set()
    unique_paths: list[Path] = []
    for section in all_sections:
        filepath = nwc_folder / f"{songtitle} {section}{EXT_NWCTXT}"
        key = str(filepath)
        if key not in seen:
            seen.add(key)
            if not validate_file_exists(filepath, f"Section file '{section}'"):
                sys.exit(1)
            unique_paths.append(filepath)

    return unique_paths


def _process_file(section_path: Path) -> bool:
    """Pad non-Bass/non-Ritme staffs in one file. Returns True if file was written."""
    nwc = NwcFile(section_path)

    bass = nwc.get_staff_by_name(STAFF_NAME_BASS)
    if bass is None:
        print(f"    ⚠️  No '{STAFF_NAME_BASS}' staff found - skipping file")
        return False

    bass_count = _count_measures(bass)
    bass_timesig = _last_timesig(bass)
    if bass_timesig is None:
        bass_timesig = _DEFAULT_TIMESIG
        print(f"    ⚠️  No TimeSig found in '{STAFF_NAME_BASS}' - assuming {bass_timesig}")

    # Probe the timesig once for the warning; per-staff content lines are
    # computed inside the loop because drum staffs get extra marker lines.
    _, exact_fit = _empty_measure_content_lines(bass_timesig, in_drums_group=False)
    if not exact_fit:
        print(f"    ⚠️  Timesig '{bass_timesig}' not in known map - "
              f"using |Rest|Dur:Whole (may not visually fit the measure)")

    bass_ends_with_bar = _staff_ends_with_bar(bass)
    end_desc = "closed (|Bar)" if bass_ends_with_bar else "dangling"
    print(f"    {STAFF_NAME_BASS:<10}: {bass_count} measures ({bass_timesig}, ends {end_desc})")

    any_modified = False
    for staff in nwc.staffs:
        if staff.name == STAFF_NAME_BASS:
            continue
        if staff.name in PAD_STAFFS_IGNORED_STAFFS:
            print(f"    {staff.name:<10}: skipped (ignored staff)")
            continue

        count = _count_measures(staff)
        if count > bass_count:
            print(f"    {staff.name:<10}: ⚠️  {count} measures > Bass ({bass_count}) - not modified")
            continue

        actions: list[str] = []
        staff_modified = False

        # 1) Pad with empty measures if count < bass_count.
        if count < bass_count:
            to_add = bass_count - count
            ends_with_bar = _staff_ends_with_bar(staff)
            in_drums = _staff_in_drums_group(staff)
            content_lines, _ = _empty_measure_content_lines(bass_timesig, in_drums)
            for i in range(to_add):
                if i > 0 or not ends_with_bar:
                    staff.lines.append('|Bar')
                staff.lines.extend(content_lines)
            drums_suffix = " [drums markers]" if in_drums else ""
            actions.append(f"+{to_add} measure(s)  ({count} → {bass_count}){drums_suffix}")
            staff_modified = True

        # 2) Align trailing structure with Bass: if Bass closes with a |Bar,
        #    the other staffs should too (so their final barline aligns
        #    visually with Bass's final barline).
        staff_ends_with_bar = _staff_ends_with_bar(staff)
        if bass_ends_with_bar and not staff_ends_with_bar:
            staff.lines.append('|Bar')
            actions.append("trailing |Bar added to match Bass")
            staff_modified = True
        elif not bass_ends_with_bar and staff_ends_with_bar:
            actions.append("⚠️  ends with |Bar but Bass is dangling (not auto-fixed)")

        if actions:
            print(f"    {staff.name:<10}: {', '.join(actions)}")
        if staff_modified:
            any_modified = True

    if any_modified:
        nwc.write_to_file(section_path)

    return any_modified


def main():
    parser = argparse.ArgumentParser(
        description=(
            'Pad all staffs in each lieddeel of a song with empty measures so '
            'they have the same measure count as the Bass staff of that '
            'lieddeel. Staffs listed in PAD_STAFFS_IGNORED_STAFFS (e.g. Ritme) '
            'are skipped.'
        )
    )
    parser.add_argument(
        'songtitle',
        help='Title of the song (must match the folder name inside the input folder).'
    )
    args = parser.parse_args()
    songtitle = args.songtitle

    paths = load_and_resolve_paths(songtitle)
    if not paths.validate_input_folder():
        sys.exit(1)

    song_folder = paths.input_folder / songtitle
    if not validate_folder_exists(song_folder, f"Song folder '{songtitle}'"):
        sys.exit(1)

    nwc_folder = song_folder / FOLDER_NWC
    if not validate_folder_exists(nwc_folder, f"NWC subfolder for '{songtitle}'"):
        sys.exit(1)

    section_paths = _load_unique_section_paths(songtitle, nwc_folder)
    if not section_paths:
        print("❌ Error: volgorde.jsonc lists no sections.")
        sys.exit(1)

    print(f"Processing song : {songtitle}")
    print(f"Section files   : {len(section_paths)} unique")
    print()

    total_modified = 0
    for section_path in section_paths:
        print(f"  {section_path.name}")
        if _process_file(section_path):
            print(f"    ✅ Written")
            total_modified += 1
        else:
            print(f"    ✓ No changes needed")

    print()
    print(f"Done. {total_modified} file(s) modified.")


if __name__ == "__main__":
    main()
