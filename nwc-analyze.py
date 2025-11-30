#!/usr/bin/env python3
"""
Analyzes .nwctxt files and maps lyrics to measure numbers.

Usage:
    python nwc-analyze.py <path-to-nwctxt-file>
"""

import sys
import re
from pathlib import Path


def parse_song_info(content):
    """Extract title and number from SongInfo line."""
    match = re.search(r'\|SongInfo\|Title:"([^"]*)"', content)
    title = match.group(1).replace(r"\'", "'") if match else "Unknown"

    # Extract number from filename or content if available
    # For now, we'll need to get it from metadata or filename
    return title


def split_into_staffs(content):
    """Split content into individual staffs."""
    # Split on |AddStaff| to get each staff section
    staff_sections = content.split('|AddStaff|')  # todo: remove first entry, which is not a staff.
    return staff_sections


def get_staff_by_name(staff_sections, name):
    """Find a staff section by its name."""
    for section in staff_sections:
        if f'Name:"{name}"' in section:
            return section
    return None


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
    return staff_content.count('|Bar')    # to do: if song starts with just a single note, don't count the first measure.


def detect_begintel(first_staff):
    """Detect if there's a begintel (pickup measure).

    A begintel is typically a single note before the first bar.
    """
    # Look for a Note before the first Bar
    before_first_bar = first_staff.split('|Bar')[0]

    # Check if there's a Note element
    if '|Rest|' in before_first_bar:
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
        if line.strip().startswith('|Text|Text:"liedstart"'):
            liedstart_index = i
            break

    if liedstart_index == -1:
        # No liedstart marker found, return 0
        return 0

    # Count bars before liedstart
    bars_before = 0
    for i in range(liedstart_index):
        if lines[i].strip().startswith('|Bar'):
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

        if element.startswith('|Bar'):
            current_measure += 1
            if current_measure not in measure_map:
                measure_map[current_measure] = []
        elif element.startswith('|Note|') and syllable_index < len(syllables):
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
        elif element.startswith('|Rest|'):
            # Skip rests - no syllable assignment
            pass

    return measure_map


def analyze_nwctxt(file_path):
    """Analyze a .nwctxt file and return lyrics mapping."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract metadata
    title = parse_song_info(content)

    # Split into staffs
    staff_sections = split_into_staffs(content)

    # Use first staff to count total measures
    first_staff =  get_staff_by_name(staff_sections, "Bass")
    total_bars = count_bars_in_staff(first_staff)

    # Detect begintel
    has_begintel = detect_begintel(first_staff)

    # Adjust total if begintel exists
    total_measures = total_bars if has_begintel else total_bars + 1

    # Count vooraf measures
    vooraf = count_vooraf_measures(first_staff)

    # Find Zang staff
    zang_staff = get_staff_by_name(staff_sections, "Zang")

    if not zang_staff:
        print(f"⚠️  Warning: No 'Zang' staff found in {file_path}")
        return None

    # Extract lyrics
    syllables = parse_lyric_text(zang_staff)

    # Map lyrics to measures
    measure_map = map_lyrics_to_measures(zang_staff, syllables)

    return {
        'title': title,
        'total_measures': total_measures,
        'has_begintel': has_begintel,
        'vooraf': vooraf,
        'measure_map': measure_map
    }


def format_output(analysis, song_number=None):
    """Format analysis results as text output."""
    if not analysis:
        return "No analysis available"

    lines = []
    lines.append(f"titel: {analysis['title']}")
    if song_number:
        lines.append(f"nummer: {song_number}")
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


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python nwc-analyze.py <path-to-nwctxt-file>")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)

    # Analyze the file
    analysis = analyze_nwctxt(file_path)

    if analysis:
        # Print formatted output
        output = format_output(analysis)
        print(output)


if __name__ == "__main__":
    main()
