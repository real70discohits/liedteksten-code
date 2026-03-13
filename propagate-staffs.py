#!/usr/bin/env python3
"""
propagate-staffs.py - Propagate staffs from a template to all song section files.

For each .nwctxt section file of a song (as listed in volgorde.jsonc):
  - Adds any missing staffs (copied from template with first 2 real measures)
  - Reorders all staffs to match the template order

A "real" measure has total note/rest duration > 1 quarter note.
Empty measures and single-beat measures (such as pickup measures) are skipped
when determining which measures to copy.

The template determines which staffs must exist and in which order.
If no template is specified, the first section from volgorde.jsonc is used.

Template location: the input_folder (parent of the git repository root),
i.e. the same directory that contains all song folders.

Usage:
    python propagate-staffs.py "Song Title"
    python propagate-staffs.py "Song Title" "template-filename"
    python propagate-staffs.py "Song Title" "template-filename.nwctxt"

Notes:
- Staffs are never removed from target files.
- Staffs present in a target file but absent from the template are moved to the end.
- Files in a git repository: changes can always be undone via git.
"""

import argparse
import sys
from pathlib import Path

from pathconfig import (load_and_resolve_paths, validate_file_exists,
                        validate_folder_exists, load_jsonc)
from nwc_utils import NwcFile, NwcStaff, parse_duration
from constants import (NWC_PREFIX_ADDSTAFF, NWC_PREFIX_STAFF_PROPERTIES,
                        NWC_PREFIX_STAFF_INSTRUMENT, NWC_PREFIX_CLEF,
                        NWC_PREFIX_TIMESIG, NWC_PREFIX_TEMPO, NWC_PREFIX_BAR,
                        EXT_NWCTXT, EXT_JSONC, FOLDER_NWC, STAFF_NAME_BASS)


# Prefixes that identify "header" lines at the top of each staff section.
# These are copied unchanged when a missing staff is inserted into a target file.
_STAFF_HEADER_PREFIXES = (
    NWC_PREFIX_ADDSTAFF,
    NWC_PREFIX_STAFF_PROPERTIES,
    NWC_PREFIX_STAFF_INSTRUMENT,
    NWC_PREFIX_CLEF,
    NWC_PREFIX_TIMESIG,
    NWC_PREFIX_TEMPO,
    '|Dynamic|',
    '|PgSetup|',
)

# A measure must contain more than this many quarter notes to be considered "real".
_MIN_REAL_MEASURE_DURATION = 1.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _split_staff_header_content(staff: NwcStaff):
    """Split a staff's lines into (header_lines, content_lines).

    Header lines are those that appear at the start of the staff section and
    match known header prefixes (AddStaff, StaffProperties, Clef, TimeSig,
    Tempo, Dynamic, …).  Everything else is musical content.
    """
    header_lines = []
    content_lines = []
    in_header = True

    for line in staff.lines:
        if in_header and any(line.startswith(p) for p in _STAFF_HEADER_PREFIXES):
            header_lines.append(line)
        else:
            in_header = False
            content_lines.append(line)

    return header_lines, content_lines


def _extract_first_real_measures(staff: NwcStaff, n_measures: int = 2) -> NwcStaff:
    """Return a new NwcStaff containing the staff header plus all content
    from the start up to and including the first *n_measures* real measures.

    A real measure has a total note/rest duration > 1 quarter note.
    Everything from the beginning up to and including the n_measures-th real
    measure is collected.  Leading empty measures and pickup measures (≤ 1
    quarter note) are included as-is; they do not count towards *n_measures*.
    Content after the n_measures-th real measure is discarded.

    Args:
        staff:     Source NwcStaff (from the template).
        n_measures: How many real measures to copy (default: 2).

    Returns:
        NwcStaff with header lines + content up to and including the
        n_measures-th real measure.
    """
    header_lines, content_lines = _split_staff_header_content(staff)

    collected: list[str] = []
    current_measure_lines: list[str] = []
    current_duration: float = 0.0
    real_count: int = 0

    for line in content_lines:
        if line.startswith(NWC_PREFIX_BAR):
            # Close current segment: include the bar marker, then decide whether
            # this was a real measure and whether to stop.
            current_measure_lines.append(line)
            if current_duration > _MIN_REAL_MEASURE_DURATION:
                real_count += 1
            collected.extend(current_measure_lines)
            current_measure_lines = []
            current_duration = 0.0
            if real_count >= n_measures:
                break
        else:
            current_measure_lines.append(line)
            current_duration += parse_duration(line)

    # If the loop ended without a trailing |Bar| and we still need content,
    # include the remaining lines (last open segment).
    if real_count < n_measures and current_measure_lines:
        collected.extend(current_measure_lines)

    return NwcStaff(header_lines + collected)


# ---------------------------------------------------------------------------
# File-level processing
# ---------------------------------------------------------------------------

def _load_unique_section_paths(songtitle: str, nwc_folder: Path):
    """Read volgorde.jsonc and return unique section file paths.

    Returns:
        tuple: (unique_paths, all_sections)
        - unique_paths:  List[Path] – deduplicated, preserving first-appearance order.
        - all_sections:  List[str] – all section names from volgorde.jsonc (may repeat).
    """
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

    return unique_paths, all_sections


def _process_file(target_path: Path, template_staff_names: list[str],
                template_nwc: NwcFile):
    """Add missing staffs and reorder staffs in one target file.

    Args:
        target_path:          Path to the .nwctxt file to update.
        template_staff_names: Ordered staff names from the template.
        template_nwc:         Parsed template NwcFile (for extracting content).

    Returns:
        tuple: (modified, added_names, was_reordered, final_order)
        - modified:      bool – True if the file was written.
        - added_names:   List[str] – names of staffs that were added.
        - was_reordered: bool – True if the staff order changed.
        - final_order:   List[str] – staff names after all changes.
    """
    nwc = NwcFile(target_path)

    # Use lowercase keys for all name lookups so matching is case-insensitive.
    # (A song will never have both "BaseDrum" and "Basedrum" as distinct staffs.)
    def _lower(name):
        return name.lower() if name is not None else None

    existing_lower = {_lower(s.name) for s in nwc.staffs}

    # 1. Add missing staffs (case-insensitive check).
    added_names: list[str] = []
    for name in template_staff_names:
        if _lower(name) not in existing_lower:
            template_staff = template_nwc.get_staff_by_name(name)
            new_staff = _extract_first_real_measures(template_staff)
            nwc.staffs.append(new_staff)
            added_names.append(name)
            existing_lower.add(_lower(name))  # keep set in sync

    # 2. Reorder: template staffs first (in template order), then any extras.
    # Build a case-insensitive lookup for sort keys.
    template_order = {_lower(name): i for i, name in enumerate(template_staff_names)}

    # Staffs present in this file but absent from the template get sorted to the
    # end with an undefined relative order.  Collect them so we can warn later.
    extra_names = [s.name for s in nwc.staffs if _lower(s.name) not in template_order]

    original_order = [s.name for s in nwc.staffs]
    nwc.staffs.sort(key=lambda s: template_order.get(_lower(s.name), len(template_staff_names)))
    final_order = [s.name for s in nwc.staffs]
    was_reordered = original_order != final_order

    # 3. Write back only if something changed.
    modified = bool(added_names) or was_reordered
    if modified:
        nwc.write_to_file(target_path)

    return modified, added_names, was_reordered, final_order, extra_names


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            'Propagate staffs from a template to all .nwctxt section files of a song. '
            'Missing staffs are added (first 2 real measures copied from template) '
            'and all staffs are reordered to match the template.'
        )
    )
    parser.add_argument(
        'songtitle',
        help='Title of the song (must match the folder name inside the input folder).'
    )
    # add --template as named argument (note: prefix with --template is required in the call)
    parser.add_argument(
        '--template',
        nargs='?',
        default=None,
        help=(
            'Filename of the template .nwctxt file (without extension, case-sensitive). '
            'The file must be located in the input folder (parent of the git repository). '
            'If omitted, the first section from volgorde.jsonc is used as the template.'
        )
    )
    args = parser.parse_args()

    songtitle = args.songtitle
    template_arg = args.template

    # Load and validate paths.
    paths = load_and_resolve_paths(songtitle)

    if not paths.validate_input_folder():
        sys.exit(1)

    song_folder = paths.input_folder / songtitle
    if not validate_folder_exists(song_folder, f"Song folder '{songtitle}'"):
        sys.exit(1)

    nwc_folder = song_folder / FOLDER_NWC
    if not validate_folder_exists(nwc_folder, f"NWC subfolder for '{songtitle}'"):
        sys.exit(1)

    # Load section files from volgorde.jsonc.
    unique_section_paths, all_sections = _load_unique_section_paths(songtitle, nwc_folder)

    if not unique_section_paths:
        print("❌ Error: volgorde.jsonc lists no sections.")
        sys.exit(1)

    print(f"Processing song : {songtitle}")
    print(f"Section files   : {len(unique_section_paths)} unique "
            f"({len(all_sections)} total in volgorde)")

    # Determine template.
    if template_arg is not None:
        template_name = template_arg
        if not template_name.endswith(EXT_NWCTXT):
            template_name += EXT_NWCTXT
        template_path = paths.input_folder / template_name
        if not validate_file_exists(template_path, f"Template file '{template_arg}'"):
            sys.exit(1)
        template_nwc = NwcFile(template_path)
        print(f"Template        : {template_path.name}  (explicit)")
    else:
        template_path = unique_section_paths[0]
        template_nwc = NwcFile(template_path)
        print(f"Template        : {template_path.name}  (first section)")

    template_staff_names = [s.name for s in template_nwc.staffs]
    print(f"Template staffs : {', '.join(template_staff_names)}")

    # Warn if Bass is not the first staff in the template.
    if template_staff_names and template_staff_names[0] != STAFF_NAME_BASS:
        print(f"⚠️  Warning: first staff in template is '{template_staff_names[0]}', "
                f"expected '{STAFF_NAME_BASS}'")

    print()

    # Process each unique section file.
    total_modified = 0
    total_added = 0

    for section_path in unique_section_paths:
        print(f"  {section_path.name}")

        modified, added_names, was_reordered, final_order, extra_names = _process_file(
            section_path, template_staff_names, template_nwc
        )

        if added_names:
            print(f"    + Added    : {', '.join(added_names)}")
            total_added += len(added_names)

        if was_reordered:
            print(f"    ~ Reordered: {', '.join(final_order)}")

        if extra_names:
            print(f"    ⚠️  Staffs not in template, placed at end: "
                  f"{', '.join(str(n) for n in extra_names)}")
            if template_arg is None:
                print(f"       Tip: run with --template to define the canonical staff order.")

        if not modified:
            print(f"    ✓ No changes needed")
        else:
            print(f"    ✅ Written  : {section_path.name}")
            total_modified += 1

        # Per-file Bass check (after sorting).
        if final_order and final_order[0] != STAFF_NAME_BASS:
            print(f"    ⚠️  Warning: first staff is '{final_order[0]}', "
                    f"expected '{STAFF_NAME_BASS}'")

    print()
    print(f"Done. {total_modified} file(s) modified, {total_added} staff(s) added.")


if __name__ == "__main__":
    main()
