"""Unit tests for the pure timesig/duration helpers in nwc-concat.py."""

import pytest


@pytest.fixture(scope="module")
def concat(load_script):
    return load_script("nwc-concat.py")


# --------------------------------------------------------------------------- #
# _parse_timesig_value
# --------------------------------------------------------------------------- #
@pytest.mark.unit
@pytest.mark.parametrize(
    "line, expected",
    [
        ("|TimeSig|Signature:4/4|...", "4/4"),
        ("|TimeSig|Signature:3/4", "3/4"),
        ("|TimeSig|Signature:6/8|Opts:x", "6/8"),
        ("|TimeSig|", None),                  # no Signature: part
        ("|Clef|Type:Treble", None),          # not a timesig line at all
    ],
)
def test_parse_timesig_value(concat, line, expected):
    assert concat._parse_timesig_value(line) == expected


# --------------------------------------------------------------------------- #
# _measure_duration_qn  (measure length in quarter notes)
# --------------------------------------------------------------------------- #
@pytest.mark.unit
@pytest.mark.parametrize(
    "timesig, expected_qn",
    [
        ("4/4", 4.0),
        ("3/4", 3.0),
        ("2/2", 4.0),
        ("6/8", 3.0),
        ("2/4", 2.0),
    ],
)
def test_measure_duration_qn(concat, timesig, expected_qn):
    assert concat._measure_duration_qn(timesig) == expected_qn


# --------------------------------------------------------------------------- #
# _pre_bar_duration_qn  (anacrusis length before the first bar)
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_pre_bar_duration_qn_sums_until_first_bar(concat):
    lines = [
        "|Rest|Dur:4th",
        "|Note|Dur:8th|Pos:0",
        "|Bar",
        "|Note|Dur:Whole|Pos:0",   # after the bar, must be ignored
    ]
    assert concat._pre_bar_duration_qn(lines) == pytest.approx(1.5)


@pytest.mark.unit
def test_pre_bar_duration_qn_stops_at_styled_bar(concat):
    lines = ["|Rest|Dur:4th", "|Bar|Style:Double", "|Note|Dur:Whole"]
    assert concat._pre_bar_duration_qn(lines) == pytest.approx(1.0)


@pytest.mark.unit
def test_pre_bar_duration_qn_no_notes(concat):
    assert concat._pre_bar_duration_qn(["|Bar", "|Note|Dur:Whole"]) == 0.0


# --------------------------------------------------------------------------- #
# _last_timesig_in_staff
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_last_timesig_in_staff_returns_last(concat):
    staff = [
        "|TimeSig|Signature:4/4",
        "|Note|Dur:4th",
        "|TimeSig|Signature:3/4",
        "|Note|Dur:4th",
    ]
    assert concat._last_timesig_in_staff(staff) == "3/4"


@pytest.mark.unit
def test_last_timesig_in_staff_none_when_absent(concat):
    assert concat._last_timesig_in_staff(["|Note|Dur:4th", "|Bar"]) is None
