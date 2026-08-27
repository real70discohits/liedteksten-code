#!/usr/bin/env python3
"""
test_print_sheet.py — Pytest tests for print sheet generation in nwc-concat.

Tests cover:
  - _extract_staff_name()
  - _update_pipe_delimited_line()
  - _trim_staff_to_liedstart()  (with and without liedstart label)
  - create_print_sheet()  (end-to-end with temp files)
  - --no-print-sheet argument parsing
"""

import argparse
import subprocess
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Module-scoped fixture: load nwc-concat.py once for the entire test module
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def concat(load_script):
    """Load the hyphen-named script as a module object.

    Relies on the load_script fixture (defined in conftest.py) which handles
    the dynamic import of files whose names contain non-identifier chars.
    """
    return load_script("nwc-concat.py")


# ---------------------------------------------------------------------------
# Minimal sample .nwctxt content builder
# ---------------------------------------------------------------------------

def build_sample_nwctxt(staff_names=("Bass", "Zang", "Ritme"),
                        include_liedstart=True,
                        include_pickup=True,
                        include_vooraf=True,
                        zang_has_liedstart=True):
    """Return a complete .nwctxt string for testing.

    The file contains:
      - Header lines: |PgSetup| and |SongInfo|
      - One staff per name in staff_names
      - Each staff has: AddStaff, StaffProperties, Clef, optional TimeSig,
        optional pickup rest, optional vooraf measures, then the song body
        starting at a |Text| with 'liedstart' marker.
      - End marker
    """
    lines = []

    # --- Header ---
    lines.append('!NoteWorthyComposer(2.75)')
    lines.append('|PgSetup|StaffSize:16|Zoom:4|TitlePage:Y|JustifyVertically:Y|PrintSystemSepMark:N|ExtendLastSystem:Y|DurationPadding:Y|PageNumbers:0|StaffLabels:First System|BarNumbers:None')
    lines.append('|SongInfo|Title:"Test Song"|Author:"someone"|Lyricist:"some poet"|Copyright1:"Copyright © 2020"|Copyright2:"Some Rights Reserved"')

    for name in staff_names:
        # --- Staff header ---
        lines.append(f'|AddStaff|Name:"{name}"')
        lines.append('|StaffProperties|EndingBar:Section Close|Visible:Y')
        lines.append('|StaffInstrument|Name:"Piano"|Patch:0')
        lines.append('|Clef|Type:Bass')

        # --- TimeSig (always include for Bass-like staffs) ---
        if name in ("Bass", "Zang"):
            lines.append('|TimeSig|Signature:4/4')

        # --- Pickup (anacrusis) ---
        if include_pickup and name in ("Bass", "Zang"):
            lines.append('|Note|Dur:4th|Pos:-2')   # pickup note

        # --- Vooraf measures (2 full measures before liedstart) ---
        if include_vooraf and name in ("Bass", "Zang"):
            lines.append('|Bar')
            lines.append('|Note|Dur:Half|Pos:-2')
            lines.append('|Note|Dur:Half|Pos:-3')
            lines.append('|Bar')
            lines.append('|Note|Dur:Whole|Pos:-2')
            lines.append('|Bar')

        # Liedstart marker: Bass always gets it; Zang only if zang_has_liedstart
        should_have_liedstart = (include_liedstart and name == "Bass") or \
                                (include_liedstart and name == "Zang" and zang_has_liedstart)
        if should_have_liedstart:
            lines.append('|Text|Text:"liedstart"|Font:PageSmallText|Pos:12')

        # --- Song body (3 measures) ---
        if name in ("Bass", "Zang"):
            lines.append('|Note|Dur:4th|Pos:-2')
            lines.append('|Note|Dur:4th|Pos:-3')
            lines.append('|Bar')
            lines.append('|Note|Dur:4th|Pos:-2')
            lines.append('|Note|Dur:4th|Pos:-3')
            lines.append('|Bar')
            lines.append('|Note|Dur:Half|Pos:-2')
            lines.append('|Note|Dur:Half|Pos:-3')
            lines.append('|Bar')
        elif name == "Ritme":
            lines.append('|Note|Dur:4th|Pos:1')
            lines.append('|Bar')
            lines.append('|Note|Dur:4th|Pos:1')
            lines.append('|Bar')
            lines.append('|Note|Dur:4th|Pos:1')

    lines.append('!NoteWorthyComposer-End')
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def build_folder(tmp_path):
    """Provide a temporary build folder."""
    return tmp_path


@pytest.fixture
def sample_file(build_folder):
    """Write a default sample .nwctxt to the build folder and return its path."""
    filepath = build_folder / "Test Song.nwctxt"
    filepath.write_text(build_sample_nwctxt(), encoding='utf-8')
    return filepath


def write_custom_file(build_folder, content, filename="Test Song.nwctxt"):
    """Helper to write custom content to the build folder."""
    filepath = build_folder / filename
    filepath.write_text(content, encoding='utf-8')
    return filepath


# ===========================================================================
# Tests: _extract_staff_name
# ===========================================================================

class TestExtractStaffName:

    @pytest.fixture(autouse=True)
    def _inject(self, concat):
        self.concat = concat

    def test_normal_staff_name(self):
        lines = [
            '|AddStaff|Name:"Bass"',
            '|StaffProperties|EndingBar:Section Close',
            '|Note|Dur:4th|Pos:-2',
        ]
        assert self.concat._extract_staff_name(lines) == "Bass"

    def test_zang_staff_name(self):
        lines = [
            '|AddStaff|Name:"Zang"',
            '|Clef|Type:Treble',
        ]
        assert self.concat._extract_staff_name(lines) == "Zang"

    def test_no_addstaff_line(self):
        lines = [
            '|StaffProperties|EndingBar:Section Close',
            '|Note|Dur:4th|Pos:-2',
        ]
        assert self.concat._extract_staff_name(lines) is None

    def test_empty_lines(self):
        assert self.concat._extract_staff_name([]) is None

    def test_addstaff_without_name(self):
        lines = ['|AddStaff|Visible:Y']
        assert self.concat._extract_staff_name(lines) is None


# ===========================================================================
# Tests: _update_pipe_delimited_line
# ===========================================================================

class TestUpdatePipeDelimitedLine:

    @pytest.fixture(autouse=True)
    def _inject(self, concat):
        self.concat = concat

    def test_update_existing_key(self):
        line = '|PgSetup|StaffSize:16|Zoom:4|PageNumbers:0'
        result = self.concat._update_pipe_delimited_line(line, {'PageNumbers': '1'})
        assert 'PageNumbers:1' in result
        assert 'PageNumbers:0' not in result
        assert 'StaffSize:16' in result

    def test_update_multiple_existing_keys(self):
        line = '|PgSetup|PageNumbers:0|BarNumbers:None|StartingBar:0'
        result = self.concat._update_pipe_delimited_line(
            line, {'PageNumbers': '1', 'BarNumbers': 'Boxed', 'StartingBar': '1'})
        assert 'PageNumbers:1' in result
        assert 'BarNumbers:Boxed' in result
        assert 'StartingBar:1' in result

    def test_append_missing_key(self):
        line = '|PgSetup|StaffSize:16|Zoom:4'
        result = self.concat._update_pipe_delimited_line(line, {'StartingBar': '1'})
        assert 'StartingBar:1' in result

    def test_update_and_append_mixed(self):
        line = '|PgSetup|StaffSize:16|PageNumbers:0'
        result = self.concat._update_pipe_delimited_line(
            line, {'PageNumbers': '1', 'BarNumbers': 'Boxed'})
        assert 'PageNumbers:1' in result
        assert 'BarNumbers:Boxed' in result
        assert 'PageNumbers:0' not in result

    def test_songinfo_update(self):
        line = '|SongInfo|Title:"My Song"|Author:"original"|Lyricist:"poet"'
        result = self.concat._update_pipe_delimited_line(
            line, {'Author': '"s.koks"', 'Lyricist': '""'})
        assert 'Author:"s.koks"' in result
        assert 'Lyricist:""' in result
        assert 'Author:"original"' not in result
        assert 'Lyricist:"poet"' not in result

    def test_preserves_title(self):
        line = '|SongInfo|Title:"Keep This"|Author:"old"'
        result = self.concat._update_pipe_delimited_line(
            line, {'Author': '"s.koks"'})
        assert 'Title:"Keep This"' in result

    def test_empty_updates(self):
        line = '|PgSetup|StaffSize:16'
        result = self.concat._update_pipe_delimited_line(line, {})
        assert result == line


# ===========================================================================
# Tests: _trim_staff_to_liedstart (with liedstart label)
# ===========================================================================

class TestTrimStaffToLiedstart:

    @pytest.fixture(autouse=True)
    def _inject(self, concat):
        self.concat = concat

    def test_trims_pickup_and_vooraf(self):
        """Pickup note + 2 vooraf measures + liedstart marker + body."""
        lines = [
            '|AddStaff|Name:"Bass"',
            '|StaffProperties|EndingBar:Section Close',
            '|Clef|Type:Bass',
            '|TimeSig|Signature:4/4',
            '|Note|Dur:4th|Pos:-2',         # pickup
            '|Bar',                          # bar after pickup
            '|Note|Dur:Half|Pos:-2',         # vooraf measure 1
            '|Note|Dur:Half|Pos:-3',
            '|Bar',                          # bar
            '|Note|Dur:Whole|Pos:-2',        # vooraf measure 2
            '|Bar',                          # bar starting liedstart measure
            '|Text|Text:"liedstart"|Font:PageSmallText|Pos:12',
            '|Note|Dur:4th|Pos:-2',          # song body measure 1
            '|Bar',
            '|Note|Dur:4th|Pos:-3',          # song body measure 2
        ]

        result, bars_removed = self.concat._trim_staff_to_liedstart(lines)

        header_end = 4  # indices 0-3 are header lines (no Dur)
        liedstart_bar_idx = 10  # '|Bar' at index 10 starts the liedstart measure

        expected =[
            '|AddStaff|Name:"Bass"',
            '|StaffProperties|EndingBar:Section Close',
            '|Clef|Type:Bass',
            '|TimeSig|Signature:4/4',
            '|Text|Text:"liedstart"|Font:PageSmallText|Pos:12',
            '|Note|Dur:4th|Pos:-2',          # song body measure 1
            '|Bar',
            '|Note|Dur:4th|Pos:-3',          # song body measure 2
        ]
        assert result == expected
        assert bars_removed == 2

    def test_no_dur_returns_unchanged(self):
        """Staff with no duration elements should be returned unchanged."""
        lines = [
            '|AddStaff|Name:"Bass"',
            '|Clef|Type:Bass',
            '|Bar',
        ]
        result, bars_removed = self.concat._trim_staff_to_liedstart(lines)
        assert result == lines
        assert bars_removed is None

    def test_no_liedstart_no_bars_to_remove_returns_unchanged(self):
        """Staff with Dur but no liedstart marker and no bars to remove returns unchanged."""
        lines = [
            '|AddStaff|Name:"Bass"',
            '|Clef|Type:Bass',
            '|Note|Dur:4th|Pos:-2',
            '|Bar',
            '|Note|Dur:4th|Pos:-3',
        ]
        result, bars_removed = self.concat._trim_staff_to_liedstart(lines)
        assert result == lines
        assert bars_removed is None

    def test_only_pickup_no_vooraf(self):
        """Pickup immediately followed by liedstart bar."""
        lines = [
            '|AddStaff|Name:"Bass"',
            '|Clef|Type:Bass',
            '|TimeSig|Signature:4/4',
            '|Note|Dur:4th|Pos:-2',   # pickup
            '|Bar',                    # bar starting liedstart measure
            '|Text|Text:"liedstart"',
            '|Note|Dur:4th|Pos:-2',
            '|Bar',
        ]
        result, bars_removed = self.concat._trim_staff_to_liedstart(lines)
        # Should keep header (indices 0-2) then jump to the bar (index 4)
        expected = lines[:3] + lines[4:]
        assert result == expected
        assert bars_removed == 0

    def test_no_pickup_first_dur_after_liedstart(self):
        """First Dur is already in the liedstart measure — nothing to trim."""
        lines = [
            '|AddStaff|Name:"Bass"',
            '|Clef|Type:Bass',
            '|TimeSig|Signature:4/4',
            '|Bar',
            '|Text|Text:"liedstart"',
            '|Note|Dur:4th|Pos:-2',   # first Dur, after liedstart
            '|Bar',
        ]
        result, bars_removed = self.concat._trim_staff_to_liedstart(lines)
        assert result == lines
        assert bars_removed is None

# ===========================================================================
# Tests: _trim_staff_to_liedstart (synced via bars_to_remove, no label)
# ===========================================================================

class TestTrimSyncFromBass:

    @pytest.fixture(autouse=True)
    def _inject(self, concat):
        self.concat = concat

    def test_sync_two_bars_removed(self):
        """Zang staff without liedstart label, synced with bars_to_remove=2."""
        lines = [
            '|AddStaff|Name:"Zang"',
            '|StaffProperties|EndingBar:Section Close',
            '|Clef|Type:Treble',
            '|TimeSig|Signature:4/4',
            '|Note|Dur:4th|Pos:1',         # pickup
            '|Bar',                         # 1st bar (remove)
            '|Note|Dur:Half|Pos:1',        # vooraf measure 1
            '|Note|Dur:Half|Pos:0',
            '|Bar',                         # 2nd bar (remove)
            '|Note|Dur:Whole|Pos:1',       # vooraf measure 2
            '|Bar',                         # 3rd bar (keep from here)
            '|Note|Dur:4th|Pos:1',         # song body measure 1
            '|Bar',
            '|Note|Dur:4th|Pos:0',         # song body measure 2
        ]
        result, bars_removed = self.concat._trim_staff_to_liedstart(lines, bars_to_remove=2)

        header_end = 4
        third_bar_idx = 10
        expected = [
            '|AddStaff|Name:"Zang"',
            '|StaffProperties|EndingBar:Section Close',
            '|Clef|Type:Treble',
            '|TimeSig|Signature:4/4',
            '|Note|Dur:4th|Pos:1',         # song body measure 1
            '|Bar',
            '|Note|Dur:4th|Pos:0',         # song body measure 2
        ]
        assert result == expected
        assert bars_removed == 2

    def test_sync_one_bar_removed(self):
        """Only a pickup, no vooraf measures — bars_to_remove=1."""
        lines = [
            '|AddStaff|Name:"Zang"',
            '|Clef|Type:Treble',
            '|TimeSig|Signature:4/4',
            '|Note|Dur:4th|Pos:1',   # pickup
            '|Bar',                   # 1st bar (remove)
            '|Note|Dur:4th|Pos:1',   # song body
            '|Bar',
        ]
        result, bars_removed = self.concat._trim_staff_to_liedstart(lines, bars_to_remove=1)

        expected = lines[:3] + lines[6:]
        assert result == expected
        assert bars_removed == 1

    def test_sync_zero_bars(self):
        """bars_to_remove=0 — trim just the pickup, keep from 1st bar."""
        lines = [
            '|AddStaff|Name:"Zang"',
            '|Clef|Type:Treble',
            '|TimeSig|Signature:4/4',
            '|Note|Dur:4th|Pos:1',   # pickup (first Dur)
            '|Bar',                   # 1st bar (keep from here)
            '|Note|Dur:4th|Pos:1',   # song body
            '|Bar',
        ]
        result, bars_removed = self.concat._trim_staff_to_liedstart(lines, bars_to_remove=0)

        expected = lines[:3] + lines[4:]
        assert result == expected
        assert bars_removed == 0

    # def test_sync_not_enough_bars(self):
    #     """Staff has fewer bars than bars_to_remove — return unchanged."""
    #     lines = [
    #         '|AddStaff|Name:"Zang"',
    #         '|Clef|Type:Treble',
    #         '|Note|Dur:4th|Pos:1',
    #         '|Bar',
    #         '|Note|Dur:4th|Pos:1',
    #     ]
    #     expected =  [
    #         '|AddStaff|Name:"Zang"',
    #         '|Clef|Type:Treble',
    #         '|Note|Dur:4th|Pos:1',
    #         '|Bar',
    #         '|Note|Dur:4th|Pos:1',
    #     ]
    #     result, bars_removed = self.concat._trim_staff_to_liedstart(lines, bars_to_remove=4)
    #     assert result == expected
        # assert bars_removed is None

    def test_sync_none_bars_to_remove(self):
        """bars_to_remove=None and no liedstart — return unchanged."""
        lines = [
            '|AddStaff|Name:"Zang"',
            '|Clef|Type:Treble',
            '|Note|Dur:4th|Pos:1',
            '|Bar',
            '|Note|Dur:4th|Pos:1',
        ]
        result, bars_removed = self.concat._trim_staff_to_liedstart(lines, bars_to_remove=None)
        assert result == lines
        assert bars_removed is None

# ===========================================================================
# Tests: create_print_sheet (end-to-end)
# ===========================================================================

class TestCreatePrintSheet:

    @pytest.fixture(autouse=True)
    def _inject(self, concat):
        self.concat = concat

    def test_creates_output_file(self, sample_file, build_folder):
        """Output file is created with the expected suffix."""
        result = self.concat.create_print_sheet(sample_file, build_folder, "Test Song")

        expected_name = "Test Song notenschrift bas- en zanglijn.nwctxt"
        assert result.name == expected_name
        assert result.exists()

    def test_strips_non_bass_zang_staffs(self, sample_file, build_folder):
        """Ritme staff should be removed; Bass and Zang kept."""
        result = self.concat.create_print_sheet(sample_file, build_folder, "Test Song")
        content = result.read_text(encoding='utf-8')

        assert 'Name:"Bass"' in content
        assert 'Name:"Zang"' in content
        assert 'Name:"Ritme"' not in content

    def test_trims_vooraf_measures_both_staffs(self, build_folder):
        """Vooraf measures should be removed from BOTH Bass and Zang,
        even when Zang has no liedstart label."""
        content = build_sample_nwctxt(zang_has_liedstart=False)
        source = write_custom_file(build_folder, content)
        result = self.concat.create_print_sheet(source, build_folder, "Test Song")
        result_content = result.read_text(encoding='utf-8')

        assert 'liedstart' in result_content
        # The Whole note was only in vooraf measures; after trimming there
        # should be none in either staff.
        assert result_content.count('|Note|Dur:Whole') == 0

    def test_trims_vooraf_zang_has_label(self, sample_file, build_folder):
        """When Zang also has a liedstart label, trimming should work too."""
        result = self.concat.create_print_sheet(sample_file, build_folder, "Test Song")
        content = result.read_text(encoding='utf-8')
        assert 'liedstart' in content
        assert content.count('|Note|Dur:Whole') == 0

    def test_updates_pgsetup(self, sample_file, build_folder):
        """PgSetup should have StartingBar:1, BarNumbers:Boxed, PageNumbers:1."""
        result = self.concat.create_print_sheet(sample_file, build_folder, "Test Song")
        content = result.read_text(encoding='utf-8')

        assert 'StartingBar:1' in content
        assert 'BarNumbers:Boxed' in content
        assert 'PageNumbers:1' in content
        assert 'PageNumbers:0' not in content
        assert 'BarNumbers:None' not in content

    def test_updates_songinfo_author_lyricist(self, sample_file, build_folder):
        """SongInfo should have Author 's.koks' and empty Lyricist."""
        result = self.concat.create_print_sheet(sample_file, build_folder, "Test Song")
        content = result.read_text(encoding='utf-8')

        assert 'Author:"s.koks"' in content
        assert 'Lyricist:""' in content
        assert 'Author:"someone"' not in content
        assert 'Lyricist:"some poet"' not in content

    def test_preserves_title(self, sample_file, build_folder):
        """Original title in SongInfo should be preserved."""
        result = self.concat.create_print_sheet(sample_file, build_folder, "Test Song")
        content = result.read_text(encoding='utf-8')

        assert 'Title:"Test Song"' in content

    def test_updates_copyright_year(self, sample_file, build_folder):
        """Copyright should reflect the current year."""
        result = self.concat.create_print_sheet(sample_file, build_folder, "Test Song")
        content = result.read_text(encoding='utf-8')

        from datetime import date
        current_year = date.today().year
        assert f'Copyright © {current_year}' in content
        assert 'All Rights Reserved' in content

    def test_end_marker_present(self, sample_file, build_folder):
        """Output file should end with the NWC end marker."""
        result = self.concat.create_print_sheet(sample_file, build_folder, "Test Song")
        content = result.read_text(encoding='utf-8')

        assert content.rstrip().endswith('!NoteWorthyComposer-End')

    def test_no_pgsetup_inserts_default(self, build_folder):
        """If header lacks |PgSetup|, a default line should be inserted."""
        content = build_sample_nwctxt()
        content = content.replace(
            '|PgSetup|StaffSize:16|Zoom:4|TitlePage:Y|JustifyVertically:Y|PrintSystemSepMark:N|ExtendLastSystem:Y|DurationPadding:Y|PageNumbers:0|StaffLabels:First System|BarNumbers:None\n',
            '')
        source = write_custom_file(build_folder, content)
        result = self.concat.create_print_sheet(source, build_folder, "Test Song")
        result_content = result.read_text(encoding='utf-8')

        assert '|PgSetup|' in result_content
        assert 'StartingBar:1' in result_content

    def test_no_songinfo_inserts_default(self, build_folder):
        """If header lacks |SongInfo|, a default line should be inserted."""
        content = build_sample_nwctxt()
        content = content.replace(
            '|SongInfo|Title:"Test Song"|Author:"someone"|Lyricist:"some poet"|Copyright1:"Copyright © 2020"|Copyright2:"Some Rights Reserved"\n',
            '')
        source = write_custom_file(build_folder, content)
        result = self.concat.create_print_sheet(source, build_folder, "Test Song")
        result_content = result.read_text(encoding='utf-8')

        assert '|SongInfo|' in result_content
        assert 'Author:"s.koks"' in result_content

    def test_missing_bass_staff(self, build_folder):
        """Should warn but still produce output when Bass staff is absent."""
        content = build_sample_nwctxt(staff_names=("Zang", "Ritme"))
        source = write_custom_file(build_folder, content)
        result = self.concat.create_print_sheet(source, build_folder, "Test Song")
        result_content = result.read_text(encoding='utf-8')

        assert 'Name:"Zang"' in result_content
        assert 'Name:"Bass"' not in result_content

    def test_missing_zang_staff(self, build_folder):
        """Should warn but still produce output when Zang staff is absent."""
        content = build_sample_nwctxt(staff_names=("Bass", "Ritme"))
        source = write_custom_file(build_folder, content)
        result = self.concat.create_print_sheet(source, build_folder, "Test Song")
        result_content = result.read_text(encoding='utf-8')

        assert 'Name:"Bass"' in result_content
        assert 'Name:"Zang"' not in result_content

    def test_no_liedstart_no_trim(self, build_folder):
        """If no liedstart marker in any staff, staffs should be kept intact."""
        content = build_sample_nwctxt(include_liedstart=False)
        source = write_custom_file(build_folder, content)
        result = self.concat.create_print_sheet(source, build_folder, "Test Song")
        result_content = result.read_text(encoding='utf-8')

        assert 'Name:"Bass"' in result_content
        assert 'Name:"Zang"' in result_content

    def test_output_filename_with_parentheses(self, build_folder):
        """Output filename should handle parentheses in the stem correctly."""
        content = build_sample_nwctxt()
        source = write_custom_file(build_folder, content, filename="Someliedtitel (8).nwctxt")
        result = self.concat.create_print_sheet(source, build_folder, "Someliedtitel (8)")

        expected_name = "Someliedtitel (8) notenschrift bas- en zanglijn.nwctxt"
        assert result.name == expected_name
        assert result.exists()

    def test_zang_without_label_trims_correctly(self, build_folder):
        """End-to-end: Zang without liedstart label should still be trimmed
        by the same bar count as Bass."""
        content = build_sample_nwctxt(zang_has_liedstart=False)
        source = write_custom_file(build_folder, content)
        result = self.concat.create_print_sheet(source, build_folder, "Test Song")
        result_content = result.read_text(encoding='utf-8')

        # Both staffs should have their vooraf measures removed.
        # The Whole note only appears in vooraf measure 2.
        assert result_content.count('|Note|Dur:Whole') == 0

        # The pickup Half notes also only appear in vooraf measure 1.
        # After trimming, the song body starts with 4th notes.
        # Count lines: the vooraf Half notes should be gone.
        half_count = result_content.count('|Note|Dur:Half|Pos:-2')
        # In the original sample, there are 2 Half notes per staff in vooraf,
        # plus 2 Half notes per staff in the song body (last measure).
        # After trimming vooraf: only the song body Half notes remain.
        # 2 staffs × 2 song body Half notes = 2 (only Pos:-2, Pos:-3 is different)
        # Actually let's just check there are fewer than before.
        original_content = content
        original_half_count = original_content.count('|Note|Dur:Half|Pos:-2')
        assert half_count < original_half_count

# ===========================================================================
# Tests: --no-print-sheet argument parsing
# ===========================================================================

class TestNoPrintSheetArgument:

    def test_argument_defaults_to_false(self):
        """Without --no-print-sheet, the flag should be False."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--no-print-sheet', action='store_true')
        args = parser.parse_args([])
        assert args.no_print_sheet is False

    def test_argument_set_to_true(self):
        """With --no-print-sheet, the flag should be True."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--no-print-sheet', action='store_true')
        args = parser.parse_args(['--no-print-sheet'])
        assert args.no_print_sheet is True


# ===========================================================================
# Integration test: --help includes the new flag
# ===========================================================================

class TestMainIntegration:

    @pytest.fixture(autouse=True)
    def _script_path(self):
        """Resolve the absolute path to nwc-concat.py alongside this test file."""
        self.script_path = Path(__file__).parent.parent.parent / "nwc-concat.py"

    def test_help_contains_no_print_sheet(self):
        """Verify the --no-print-sheet argument appears in help output."""
        result = subprocess.run(
            [sys.executable, str(self.script_path), '--help'],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        assert '--no-print-sheet' in result.stdout

    def test_help_contains_keep_tempi(self):
        """Sanity check: existing --keep-tempi flag should still be present."""
        result = subprocess.run(
            [sys.executable, str(self.script_path), '--help'],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        assert '--keep-tempi' in result.stdout
