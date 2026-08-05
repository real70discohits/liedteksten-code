"""Unit tests for nwc_utils: calc_timing, parse_duration, TimingSegment,
NwcStaff and NwcFile parsing/mutation."""

import pytest

import nwc_utils
from nwc_utils import NwcStaff, NwcFile, TimingSegment


# --------------------------------------------------------------------------- #
# calc_timing
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_calc_timing_4_4_at_120():
    beat, measure, beats_per_measure, beat_base = nwc_utils.calc_timing((120, 4), "4/4")
    assert beat == pytest.approx(0.5)
    assert measure == pytest.approx(2.0)
    assert beats_per_measure == 4
    assert beat_base == 4


@pytest.mark.unit
def test_calc_timing_3_4_at_60():
    beat, measure, beats_per_measure, beat_base = nwc_utils.calc_timing((60, 4), "3/4")
    assert beat == pytest.approx(1.0)
    assert measure == pytest.approx(3.0)
    assert beats_per_measure == 3
    assert beat_base == 4


# --------------------------------------------------------------------------- #
# parse_duration
# --------------------------------------------------------------------------- #
@pytest.mark.unit
@pytest.mark.parametrize(
    "line, expected",
    [
        ("|Note|Dur:Whole|Pos:0", 4.0),
        ("|Note|Dur:Half|Pos:0", 2.0),
        ("|Note|Dur:4th|Pos:0", 1.0),
        ("|Rest|Dur:8th", 0.5),
        ("|Note|Dur:16th|Pos:0", 0.25),
        ("|Note|Dur:4th,Dotted|Pos:0", 1.5),
        ("|Note|Dur:Half,DblDotted|Pos:0", 3.5),
        ("|Note|Dur:4th,DblDotted|Pos:0", 1.75),
        ("|Note|Pos:0", 0.0),            # no Dur
        ("|Note|Dur:Sixteenth|Pos:0", 0.0),  # unknown duration name
    ],
)
def test_parse_duration(line, expected):
    assert nwc_utils.parse_duration(line) == pytest.approx(expected)


# --------------------------------------------------------------------------- #
# TimingSegment
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_timing_segment_duration():
    seg = TimingSegment(tempo=120, timesig="4/4", measure_count=4)
    assert seg.duration() == pytest.approx(8.0)   # 4 measures * 2.0 s


# --------------------------------------------------------------------------- #
# NwcStaff
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_nwcstaff_extracts_name():
    staff = NwcStaff(['|AddStaff|Name:"Bass"|Group:"x"', "|Clef|Type:Bass"])
    assert staff.name == "Bass"


@pytest.mark.unit
def test_nwcstaff_name_none_when_absent():
    assert NwcStaff(["|Clef|Type:Bass"]).name is None


@pytest.mark.unit
def test_nwcstaff_set_muted_targets_second_staffproperties():
    lines = [
        '|AddStaff|Name:"Bass"',
        "|StaffProperties|EndingBar:Section|Visible:Y",
        "|StaffProperties|Muted:N|Volume:0|StereoPan:64",
        "|Clef|Type:Bass",
    ]
    staff = NwcStaff(lines)
    staff.set_muted_and_volume(True, 100)
    # First StaffProperties untouched, second updated.
    assert staff.lines[1] == "|StaffProperties|EndingBar:Section|Visible:Y"
    assert "Muted:Y" in staff.lines[2]
    assert "Volume:100" in staff.lines[2]


# --------------------------------------------------------------------------- #
# NwcFile
# --------------------------------------------------------------------------- #
@pytest.fixture
def sample_nwctxt(tmp_path):
    content = "\n".join(
        [
            "!NoteWorthyComposer(2.0)",
            '|SongInfo|Title:"T"',
            '|AddStaff|Name:"Bass"',
            "|Clef|Type:Bass",
            '|AddStaff|Name:"Zang"',
            "|Clef|Type:Treble",
            "!NoteWorthyComposer-End",
        ]
    )
    path = tmp_path / "sample.nwctxt"
    path.write_text(content + "\n", encoding="utf-8")
    return path


@pytest.mark.unit
def test_nwcfile_parses_header_and_staffs(sample_nwctxt):
    nwc = NwcFile(sample_nwctxt)
    assert nwc.header_lines == ["!NoteWorthyComposer(2.0)", '|SongInfo|Title:"T"']
    assert len(nwc.staffs) == 2
    assert nwc.get_staff_by_index(0).name == "Bass"
    assert nwc.get_staff_by_index(1).name == "Zang"


@pytest.mark.unit
def test_nwcfile_lookup_by_name_and_bounds(sample_nwctxt):
    nwc = NwcFile(sample_nwctxt)
    assert nwc.get_staff_by_name("Zang").name == "Zang"
    assert nwc.get_staff_by_name("Drums") is None
    assert nwc.get_staff_by_index(99) is None


@pytest.mark.unit
def test_nwcfile_roundtrip_write(sample_nwctxt, tmp_path):
    nwc = NwcFile(sample_nwctxt)
    out = tmp_path / "out.nwctxt"
    nwc.write_to_file(out)
    reparsed = NwcFile(out)
    assert [s.name for s in reparsed.staffs] == ["Bass", "Zang"]
    assert reparsed.header_lines == nwc.header_lines
