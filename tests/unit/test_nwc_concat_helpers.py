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
        ("2/2", 4.0),  # deze is goed om te begrijpen
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

@pytest.mark.unit
def test_pre_bar_duration_qn_stops_at_styled_bar2(concat):
    lines = ["|Rest|Dur:Whole", "|Bar|Style:Double", "|Note|Dur:Whole"]
    assert concat._pre_bar_duration_qn(lines) == pytest.approx(4.0)

@pytest.mark.unit
def test_pre_bar_duration_qn_stops_at_styled_bar3(concat):
    lines = ["|Note|Dur:Half", "|Rest|Dur:32nd", "|Bar|Style:Double", "|Note|Dur:Whole"]
    assert concat._pre_bar_duration_qn(lines) == pytest.approx(2.125)


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
def test_last_timesig_in_staff_returns_last_2(concat):
    staff = [
        "|TimeSig|Signature:4/4",
        "|Note|Dur:4th",
        "|Bar",
        "|Rest|Dur:8th",
        "|Bar",
        "|Note|Dur:4th",
    ]
    assert concat._last_timesig_in_staff(staff) == "4/4"

@pytest.mark.unit
def test_last_timesig_in_staff_none_when_absent(concat):
    assert concat._last_timesig_in_staff(["|Note|Dur:4th", "|Bar"]) is None

# --------------------------------------------------------------------------- #
# get_measure_count
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_get_measure_count1(concat):
    assert concat.get_measure_count("../../../testdata/complete files/Humanity (53).nwctxt") is 169   # expected count 169 verified

@pytest.mark.unit
def test_get_measure_count2(concat):
    assert concat.get_measure_count("../../../testdata/complete files/Such A Beauty (6).nwctxt") is 86   # expected count 86 verified

@pytest.mark.unit
def test_get_measure_count3(concat):
    assert concat.get_measure_count("../../../testdata/complete files/Wasting No Time (4).nwctxt") is 126  # expected count 126 verified

@pytest.mark.unit
def test_get_measure_count4(concat):
    assert concat.get_measure_count("../../../testdata/complete files/Maybe Love Strikes Again (56).nwctxt") is 156   # expected count 156 verified

@pytest.mark.unit
def test_get_measure_count5(concat):
    assert concat.get_measure_count("../../../testdata/complete files/Live Long Democracy (46).nwctxt") is 160   # expected count 160 verified

