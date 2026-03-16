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
from constants import EXT_NWCTXT, FOLDER_NWC


_SECTIE_LABEL_PLACEHOLDER = 'liedsectienaam'
_SECTIE_LABEL_LINE_PREFIX = '|Text|Text:"'


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
        created += 1

    print()
    print(f"Klaar. {created} bestand(en) aangemaakt, {skipped} overgeslagen.")


if __name__ == "__main__":
    main()
