#!/usr/bin/env python3
"""
init-liedsecties.py — Initialize song section .nwctxt files from a template.

For each specified section name, creates a '<songtitle> <sectie>.nwctxt' file
in the song's nwc subfolder by copying the template file.
Existing files are never overwritten.

If no template is specified, '<songtitle> intro.nwctxt' in the nwc subfolder
is used as the default template.

Usage:
    python init-liedsecties.py "Song Title" --sectie-namen vers refrein
    python init-liedsecties.py "Song Title" --sectie-namen vers refrein "overgang couplet refrein"
    python init-liedsecties.py "Song Title" --sectie-namen intro vers refrein --template "My Template"
"""

import argparse
import sys
from pathlib import Path

from pathconfig import (load_and_resolve_paths, validate_file_exists,
                        validate_folder_exists, ensure_folder_writable)
from constants import (EXT_NWCTXT, FOLDER_NWC,
                       NWC_PREFIX_ADDSTAFF, NWC_PREFIX_BAR)
from nwc_utils import NwcFile, NwcStaff


_SECTIE_LABEL_PLACEHOLDER = 'liedsectienaam'
_SECTIE_LABEL_LINE_PREFIX = '|Text|Text:"'

# Sectienaam waarvoor een kwartrust + maatstreep vooraan elke staff wordt
# ingevoegd. Recording software laat aan het begin van een bestand vaak ruis
# horen waardoor de eerste tel verloren gaat; deze extra kwartrust vangt die
# ruisfase op zodat de feitelijke muziek schoon begint.
_INTRO_SECTIE_NAME = 'intro'

# Detectie van drum-groep op de |AddStaff| regel. Gelijk aan pad-staffs.py.
_DRUMS_GROUP_MARKER = '|Group:"drums"'

# Markerregel die rond rust- en bar-regels in drum-staffs wordt gezet, conform
# de NWC drum-staff conventie (zelfde als pad-staffs.py).
_DRUMS_AUDIO_MARKER = '|User|DrumStaff_AUDIO.fso|Pos:1|Class:StaffSig|InOut:Y'

# Regels die voor het eerste |Dur: per staff worden ingevoegd in intro's.
_KWARTRUST_LINE = '|Rest|Dur:4th'
_BAR_LINE = '|Bar'


def _is_intro_sectie(sectie_naam: str) -> bool:
    """Return True if the given section name designates an intro (case-insensitive)."""
    return sectie_naam.lower() == _INTRO_SECTIE_NAME


def _staff_in_drums_group(staff: NwcStaff) -> bool:
    """Return True if the staff's |AddStaff| line declares Group:"drums"."""
    for line in staff.lines:
        if line.startswith(NWC_PREFIX_ADDSTAFF):
            return _DRUMS_GROUP_MARKER in line
    return False


def _find_first_duration_index(lines: list[str]) -> int | None:
    """Return the index of the first line containing |Dur:, or None if none."""
    for i, line in enumerate(lines):
        if '|Dur:' in line:
            return i
    return None


def _has_leading_kwartrust_bar(lines: list[str], first_dur_idx: int) -> bool:
    """Return True if the staff already starts its music with |Rest|Dur:4th + |Bar.

    Intervening |User|... lines (drum audio markers) between the rest and the
    bar are tolerated; any other content in between is treated as 'different
    pattern' so the prepend should still happen.
    """
    if lines[first_dur_idx] != _KWARTRUST_LINE:
        return False
    for i in range(first_dur_idx + 1, len(lines)):
        line = lines[i]
        if line.startswith('|User|'):
            continue
        return line.startswith(NWC_PREFIX_BAR)
    return False


def _prepend_intro_kwartrust(nwc_path: Path) -> bool:
    """Prepend |Rest|Dur:4th + |Bar to each staff in the intro file.

    For drum-group staffs the rest and bar are bracketed by the
    |User|DrumStaff_AUDIO.fso|... marker line (same convention as pad-staffs.py).
    Staffs that already start with the |Rest|Dur:4th + |Bar pattern are left
    untouched, so calling this on an already-prepended intro is a no-op.

    Returns True iff at least one staff was modified and the file was rewritten.
    """
    nwc = NwcFile(nwc_path)
    any_modified = False

    for staff in nwc.staffs:
        first_dur_idx = _find_first_duration_index(staff.lines)
        if first_dur_idx is None:
            continue

        if _has_leading_kwartrust_bar(staff.lines, first_dur_idx):
            continue

        in_drums = _staff_in_drums_group(staff)

        # For drum staffs the line just before the first |Dur: is typically an
        # audio marker. Shift the insertion one line up so the new rest+bar
        # gets its own pair of markers without leaving the existing marker
        # dangling above the new content.
        insert_idx = first_dur_idx
        if (in_drums and insert_idx > 0
                and staff.lines[insert_idx - 1] == _DRUMS_AUDIO_MARKER):
            insert_idx -= 1

        if in_drums:
            prepend = [_DRUMS_AUDIO_MARKER, _KWARTRUST_LINE,
                       _DRUMS_AUDIO_MARKER, _BAR_LINE]
        else:
            prepend = [_KWARTRUST_LINE, _BAR_LINE]

        staff.lines[insert_idx:insert_idx] = prepend
        any_modified = True

    if any_modified:
        nwc.write_to_file(nwc_path)

    return any_modified


def _apply_edits(content: str, sectie_naam: str) -> tuple[str, bool]:
    """Apply section-specific edits to template content before writing.

    Replaces the placeholder section name in the label line of the top staff:
        |Text|Text:"liedsectienaam"|Font:PageSmallText|Pos:12
    becomes (for e.g. sectie_naam="refrein"):
        |Text|Text:"refrein"|Font:PageSmallText|Pos:12

    Args:
        content:     Raw text content copied from the template file.
        sectie_naam: Name of the section being created.

    Returns:
        Tuple of (edited content, placeholder_found).
        placeholder_found is False when the template contained no placeholder
        to replace (content is returned unchanged in that case).
    """
    old = f'{_SECTIE_LABEL_LINE_PREFIX}{_SECTIE_LABEL_PLACEHOLDER}"'
    new = f'{_SECTIE_LABEL_LINE_PREFIX}{sectie_naam}"'
    if old not in content:
        return content, False
    return content.replace(old, new), True


def main():
    parser = argparse.ArgumentParser(
        description=(
            'Initialiseert .nwctxt sectiebestanden voor een lied door ze te kopiëren '
            'vanuit een template. Bestaande bestanden worden niet overschreven.'
        )
    )
    parser.add_argument(
        'songtitle',
        help='Titel van het lied (moet overeenkomen met de mapnaam in de input folder).'
    )
    parser.add_argument(
        '--sectie-namen',
        required=True,
        nargs='+',
        metavar='SECTIE',
        dest='sectie_namen',
        help=(
            'Eén of meer sectienamen om aan te maken (bv. intro vers refrein). '
            'Meerdere woorden per sectienaam zijn mogelijk met aanhalingstekens: '
            '"overgang couplet refrein". Ten minste één naam is verplicht.'
        )
    )
    parser.add_argument(
        '--template',
        default=None,
        metavar='BESTANDSNAAM',
        help=(
            'Bestandsnaam van het template .nwctxt bestand (zonder extensie). '
            'Het bestand moet in de input folder staan (de map die alle liedmappen bevat). '
            'Als niet opgegeven, wordt "<liedtitel> intro.nwctxt" in de nwc-submap gebruikt.'
        )
    )
    args = parser.parse_args()

    songtitle = args.songtitle
    sectie_namen = args.sectie_namen  # list, due to nargs='+'

    # --- Validation 1: contradiction check (pure argument logic, no filesystem) ---
    if args.template is None:
        if any(n.lower() == 'intro' for n in sectie_namen):
            print(
                "❌ Fout: 'intro' staat in --sectie-namen, maar er is geen --template opgegeven.\n"
                "   Zonder --template gebruikt het script '<liedtitel> intro.nwctxt' als template.\n"
                "   Dit bestand kan niet tegelijk als template én als nieuw bestand fungeren.\n"
                "\n"
                "   Mogelijke oplossingen:\n"
                "   1. Geef een expliciet template op:  --template \"<bestandsnaam>\"\n"
                "   2. Verwijder 'intro' uit --sectie-namen (als het intro-bestand al bestaat)"
            )
            sys.exit(1)

    # --- Validation 2: load paths, validate song folder ---
    paths = load_and_resolve_paths(songtitle)

    if not paths.validate_input_folder():
        sys.exit(1)

    song_folder = paths.input_folder / songtitle
    if not validate_folder_exists(song_folder, f"Liedmap '{songtitle}'"):
        sys.exit(1)

    nwc_folder = song_folder / FOLDER_NWC

    # --- Validation 3: resolve and validate template ---
    if args.template is not None:
        template_name = args.template
        if not template_name.endswith(EXT_NWCTXT):
            template_name += EXT_NWCTXT
        template_path = paths.input_folder / template_name
        if not validate_file_exists(template_path, f"Template bestand '{args.template}'"):
            sys.exit(1)
        print(f"Lied            : {songtitle}")
        print(f"Template        : {template_path.name}  (expliciet opgegeven)")
    else:
        # Implicit: use <songtitle> intro.nwctxt from the nwc subfolder.
        if not nwc_folder.exists():
            print(
                f"❌ Fout: Geen --template opgegeven en de nwc-submap bestaat nog niet:\n"
                f"   {nwc_folder}\n"
                f"   Het standaard template '{songtitle} intro{EXT_NWCTXT}' is daardoor "
                f"niet te vinden.\n"
                f"   Gebruik --template om een template op te geven."
            )
            sys.exit(1)
        template_path = nwc_folder / f"{songtitle} intro{EXT_NWCTXT}"
        if not validate_file_exists(
                template_path,
                f"Standaard template '{songtitle} intro{EXT_NWCTXT}'"):
            sys.exit(1)
        print(f"Lied            : {songtitle}")
        print(f"Template        : {template_path.name}  (standaard intro)")

    print(f"Sectienamen     : {', '.join(sectie_namen)}")
    print()

    # --- All validation done: now touch the filesystem ---

    # Create nwc folder if it doesn't exist yet (song folder is confirmed to exist).
    if not ensure_folder_writable(nwc_folder, f"NWC-submap voor '{songtitle}'"):
        sys.exit(1)

    # Read template content once before the loop.
    template_content = template_path.read_text(encoding='utf-8')

    # Create a file per section name.
    created = 0
    skipped = 0

    for sectie_naam in sectie_namen:
        target_filename = f"{songtitle} {sectie_naam}{EXT_NWCTXT}"
        target_path = nwc_folder / target_filename

        if target_path.exists():
            print(f"  ⚠️  Overgeslagen  : {target_filename}  (bestaat al)")
            skipped += 1
            continue

        content, placeholder_found = _apply_edits(template_content, sectie_naam)
        if not placeholder_found:
            print(f"  ⚠️  Label niet vervangen: placeholder '{_SECTIE_LABEL_PLACEHOLDER}' "
                  f"niet gevonden in template")
        target_path.write_text(content, encoding='utf-8')
        print(f"  ✅ Aangemaakt    : {target_filename}")

        # Voor intro-secties: voeg vooraan in elke staff een kwartrust +
        # maatstreep toe (na de voortekens, vóór het eerste |Dur:). Vangt
        # de ruisfase op aan het begin van een audio-opname.
        if _is_intro_sectie(sectie_naam):
            if _prepend_intro_kwartrust(target_path):
                print(f"     ➕ Kwartrust + maatstreep toegevoegd aan intro")

        created += 1

    print()
    print(f"Klaar. {created} bestand(en) aangemaakt, {skipped} overgeslagen.")


if __name__ == "__main__":
    main()
