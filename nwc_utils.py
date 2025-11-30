"""Shared utility functions for NWC (NoteWorthy Composer) scripts.

This module provides classes and functions for working with .nwctxt files,
including parsing, staff management, and common operations.
"""

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

    def __repr__(self):
        return f"NwcFile(path='{self.filepath}', staffs={len(self.staffs)})"


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
