"""Shared utility functions for NWC (NoteWorthy Composer) scripts.

This module provides classes and functions for working with .nwctxt files,
including parsing, staff management, and common operations.
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple
from constants import NWC_PREFIX_ADDSTAFF, NWC_END_MARKER


class NwcStaff:
    """Represents a single staff from a .nwctxt file."""

    def __init__(self, lines: List[str]):
        """Initialize a staff with its content lines.

        Args:
            lines: List of lines from the staff section (including |AddStaff| line)
        """
        self.lines = lines
        self.name = self._extract_name()

    def _extract_name(self) -> Optional[str]:
        """Extract staff name from AddStaff line.

        Returns:
            Staff name if found, None otherwise
        """
        for line in self.lines:
            if 'Name:"' in line:
                try:
                    start = line.find('Name:"') + 6
                    end = line.find('"', start)
                    return line[start:end]
                except IndexError:
                    pass
        return None

    def get_content(self) -> str:
        """Get staff content as a single string.

        Returns:
            All staff lines joined with newlines
        """
        return '\n'.join(self.lines)

    def set_muted_and_volume(self, muted: bool, volume: int = 127):
        """Set Muted property and Volume in the second StaffProperties line.

        Args:
            muted: True to mute the staff, False to unmute
            volume: Volume level (0-127, default: 127)

        The second StaffProperties line (after AddStaff) contains Muted and Volume.
        Example: |StaffProperties|Muted:Y|Volume:127|StereoPan:64|...
        """
        muted_value = 'Y' if muted else 'N'

        # Find the second StaffProperties line (index-wise)
        staff_props_count = 0
        target_index = None

        for i, line in enumerate(self.lines):
            if line.startswith('|StaffProperties|'):
                staff_props_count += 1
                if staff_props_count == 2:
                    target_index = i
                    break

        if target_index is None:
            # No second StaffProperties line found, cannot modify
            return

        # Update Muted and Volume properties using regex
        line = self.lines[target_index]

        # Update Muted property
        line = re.sub(r'Muted:[YN]', f'Muted:{muted_value}', line)

        # Update Volume property
        line = re.sub(r'Volume:\d+', f'Volume:{volume}', line)

        self.lines[target_index] = line

    def __repr__(self):
        return f"NwcStaff(name='{self.name}', lines={len(self.lines)})"


class NwcFile:
    """Represents a parsed .nwctxt file.

    Provides access to the file header and individual staffs.
    """

    def __init__(self, filepath: str | Path):
        """Initialize and parse a .nwctxt file.

        Args:
            filepath: Path to the .nwctxt file
        """
        self.filepath = Path(filepath)
        self.header_lines: List[str] = []
        self.staffs: List[NwcStaff] = []
        self._parse()

    def _parse(self):
        """Parse the .nwctxt file into header and staff sections."""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        current_staff = []
        in_header = True

        for line in lines:
            line = line.rstrip('\n')

            if line.startswith(NWC_PREFIX_ADDSTAFF):
                in_header = False
                if current_staff:
                    self.staffs.append(NwcStaff(current_staff))
                current_staff = [line]
            elif line == NWC_END_MARKER:
                if current_staff:
                    self.staffs.append(NwcStaff(current_staff))
            elif in_header:
                self.header_lines.append(line)
            else:
                current_staff.append(line)

    def get_staff_by_name(self, name: str) -> Optional[NwcStaff]:
        """Get a staff by its name.

        Args:
            name: Name of the staff to find

        Returns:
            NwcStaff if found, None otherwise
        """
        for staff in self.staffs:
            if staff.name == name:
                return staff
        return None

    def get_staff_by_index(self, index: int) -> Optional[NwcStaff]:
        """Get a staff by its index (0-based).

        Args:
            index: Zero-based index of the staff

        Returns:
            NwcStaff if index is valid, None otherwise
        """
        if 0 <= index < len(self.staffs):
            return self.staffs[index]
        return None

    def write_to_file(self, filepath: str | Path):
        """Write the current NwcFile (with any modifications) to a file.

        Args:
            filepath: Path to the output file

        This writes the header, all staffs, and the end marker.
        """
        filepath = Path(filepath)
        with open(filepath, 'w', encoding='utf-8') as f:
            # Write header
            for line in self.header_lines:
                f.write(line + '\n')

            # Write all staffs
            for staff in self.staffs:
                for line in staff.lines:
                    f.write(line + '\n')

            # Write end marker
            f.write(NWC_END_MARKER + '\n')

    def set_all_staffs_muted(self, muted: bool, volume: int = 127):
        """Set all staffs to muted/unmuted with specified volume.

        Args:
            muted: True to mute all staffs, False to unmute
            volume: Volume level (0-127, default: 127)
        """
        for staff in self.staffs:
            staff.set_muted_and_volume(muted, volume)

    def set_staff_muted_by_name(self, staff_name: str, muted: bool, volume: int = 127):
        """Set a specific staff to muted/unmuted by name.

        Args:
            staff_name: Name of the staff to modify
            muted: True to mute the staff, False to unmute
            volume: Volume level (0-127, default: 127)

        Returns:
            True if staff was found and modified, False otherwise
        """
        staff = self.get_staff_by_name(staff_name)
        if staff:
            staff.set_muted_and_volume(muted, volume)
            return True
        return False

    def __repr__(self):
        return f"NwcFile(path='{self.filepath}', staffs={len(self.staffs)})"


def calc_timing(tempo: int, timesig: str):
    """Calculate timing parameters from tempo and time signature.

    NOTE: measure_duration is incorrect for compound meters like 6/8, where the
    tempo (BPM) refers to quarter notes but the beat unit is an eighth note.

    Args:
        tempo: Tempo in BPM (quarter notes per minute)
        timesig: Time signature string, e.g. "4/4" or "3/4"

    Returns:
        tuple: (beat_duration, measure_duration, beats_per_measure, beat_base)
        - beat_duration: seconds per quarter-note beat (60 / tempo)
        - measure_duration: seconds per full measure
        - beats_per_measure: numerator of time signature
        - beat_base: denominator of time signature
    """
    beat_duration = 60.0 / tempo
    s_beats_per_measure, _, s_beat_base = timesig.partition('/')
    beats_per_measure = int(s_beats_per_measure)
    beat_base = int(s_beat_base)
    measure_duration = beats_per_measure * beat_duration
    return beat_duration, measure_duration, beats_per_measure, beat_base


def parse_duration(line: str) -> float:
    """Parse NWC duration from Note or Rest line and convert to quarter notes.

    Args:
        line: Line containing |Dur: specification

    Returns:
        float: Duration in quarter notes, or 0.0 if not parseable
    """
    if '|Dur:' not in line:
        return 0.0

    try:
        dur_start = line.find('|Dur:') + 5
        dur_end = line.find('|', dur_start)
        if dur_end == -1:
            dur_value = line[dur_start:].strip()
        else:
            dur_value = line[dur_start:dur_end].strip()

        duration_map = {
            'Whole': 4.0,
            'Half': 2.0,
            '4th': 1.0,
            '8th': 0.5,
            '16th': 0.25,
            '32nd': 0.125,
        }

        dur_base = dur_value.split(',')[0].strip()
        is_dotted = ',Dotted' in line
        is_dbl_dotted = ',DblDotted' in line

        base_duration = 0.0
        for key, value in duration_map.items():
            if dur_base == key:
                base_duration = value
                break

        if base_duration == 0.0:
            return 0.0

        if is_dbl_dotted:
            return base_duration * 1.75
        elif is_dotted:
            return base_duration * 1.5

        return base_duration

    except (IndexError, ValueError):
        return 0.0


def parse_nwctxt(filepath: str | Path) -> Tuple[List[str], List[List[str]]]:
    """Parse a .nwctxt file into header and staff sections.

    This function provides backward compatibility with existing code.
    New code should use the NwcFile class directly.

    Args:
        filepath: Path to the .nwctxt file

    Returns:
        Tuple of (header_lines, staff_sections) where:
        - header_lines: List of header lines
        - staff_sections: List of lists, each containing lines for one staff
    """
    nwc = NwcFile(filepath)
    staff_sections = [staff.lines for staff in nwc.staffs]
    return nwc.header_lines, staff_sections
