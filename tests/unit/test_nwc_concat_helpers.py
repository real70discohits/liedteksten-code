"""Unit tests for the pure timesig/duration helpers in nwc-concat.py."""

import pytest
from pathlib import Path


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

# --------------------------------------------------------------------------- #
# process_lieddelen
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_provess_lieddelen1(concat):
    title = "Humanity (53)"
    nwc_folder = Path(__file__).parent.parent.parent.parent / "testdata/lieddelen"
    volgorde_lieddelen = ['intro', 'couplet 1', 'refrein', 'overgang refr-couplet', 'couplet', 'refrein', 'middenstuk', 'couplet', 'refrein', 'uittro']
    result = concat.process_lieddelen(title, volgorde_lieddelen, nwc_folder)           # expected duration 3:43 verified (excl maten vooraf, which take 3 additional secs)

    # ============ OUTPUT (✔️ = handmatig geverifiëerd) =================
    # ✔️ file_list: ['C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) intro.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) couplet 1.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) refrein.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) overgang refr-couplet.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) couplet.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) refrein.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) middenstuk.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) couplet.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) refrein.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) uittro.nwctxt']
    # ✔️ measurecount_and_starttime_per_lieddeel: [('intro', 10, 0.0), ('couplet 1', 18, 13.043478260869566), ('refrein', 15, 36.52173913043478), ('overgang refr-couplet', 10, 56.086956521739125), ('couplet', 24, 69.13043478260869), ('refrein', 15, 100.43478260869564), ('middenstuk', 32, 119.99999999999999), ('couplet', 24, 163.984655277565), ('refrein', 15, 195.28900310365196), ('uittro', 8, 214.8542204949563)]
    # ✔️ chords_per_lieddeel: {'intro': ('A7sus2(8)', 8, True), 'couplet 1': ('A7sus2(5), Dmaj7(4), A7sus2(5), Dmaj7(4)', 18, True), 'refrein': ('Bm6(3), Em(4), Edim(add 11)(2), Em (add9+11)(2), Dmaj7(2), B(2)', 15, True), 'overgang refr-couplet': ('E6(2), A (schuif)(4), A7sus2(4)', 10, True), 'couplet': ('A7sus2(4), Dmaj7(4), A7sus2(4), Dmaj7(4), A7sus2(4), Dmaj7(4)', 24, True), 'middenstuk': ('Em7(4), A7(4), Em7(4), A7(4), Em7(4), A7(4), Em7(4), A7(4)', 32, True), 'uittro': ('Em6(2), A(4), D(2)', 8, True)}
    # ✔️ all_labels: [('intro', 0.0), ('Start zang', 12.391304347826088), ('couplet 1', 13.043478260869566), ('D', 19.56521739130435), ('A', 24.782608695652176), ('D', 31.304347826086957), ('refrein', 36.52173913043478), ('E', 40.43478260869565), ('Edim', 45.65217391304348), ('Em', 48.26086956521739), ('B', 53.47826086956522), ('overgang refr-couplet', 56.086956521739125), ('A', 58.69565217391304), ('couplet', 69.13043478260869), ('D', 74.34782608695652), ('A', 79.56521739130434), ('D', 84.78260869565217), ('A', 90.0), ('D', 95.21739130434781), ('refrein', 100.43478260869564), ('E', 104.34782608695652), ('Edim', 109.56521739130434), ('Em', 112.17391304347825), ('B', 117.39130434782608), ('middenstuk', 119.99999999999999), ('A', 125.51724137931033), ('E', 131.03448275862067), ('A', 136.55172413793102), ('E', 142.06896551724137), ('A', 147.58620689655172), ('E', 153.10344827586206), ('A', 158.62068965517238), ('couplet', 163.984655277565), ('D', 169.2020465819128), ('A', 174.41943788626065), ('D', 179.63682919060847), ('A', 184.8542204949563), ('D', 190.07161179930412), ('refrein', 195.28900310365196), ('E', 199.20204658191284), ('Edim', 204.41943788626065), ('Em', 207.0281335384346), ('B', 212.2455248427824), ('uittro', 214.8542204949563), ('A', 217.46291614713022), ('D', 222.68030745147806)]
    # ✔️ first_lieddeel_tempo: 184
    # ✔️ first_lieddeel_timesig: '4/4'
    # ✔️ pickup_beats:1.0
    # =====================

    # assert files
    expected_paths = ['C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) intro.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) couplet 1.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) refrein.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) overgang refr-couplet.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) couplet.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) refrein.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) middenstuk.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) couplet.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) refrein.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) uittro.nwctxt']
    rng = len(expected_paths) 
    for i in range(rng):
        assert result[0][i] == expected_paths[i]

    # assert measurecount_and_starttime_per_lieddeel
    # BUG FIXED BY THIS TEST: maten vooraf werden niet meegeteld, waardoor intro een te korte duur kreeg. Mogelijk hierdoor verschoven alle labels?
    # DESIGN ERROR FOUND BY THIS TEST: pickup beat wordt overgeslagen, maar vooraf_measures niet. Dat is incorrect: Het moet allebei wel meetellen (nl bij exacte weergave van de compos in .nwctxt) of allebei niet (bij bepalen 'netto' duur van song).
    # OLD EXPECTATION, HAS DESIGN ERROR: expected_measurecount_and_starttime_per_lieddeel = [('intro', 8, 0.32608695652173914), ('couplet 1', 18, 13.369565217391305), ('refrein', 15, 36.84782608695652), ('overgang refr-couplet', 10, 56.413043478260875), ('couplet', 24, 69.45652173913044), ('refrein', 15, 100.76086956521739), ('middenstuk', 32, 120.32608695652173), ('couplet', 24, 164.31074223408675), ('refrein', 15, 195.6150900601737), ('uittro', 8, 215.18030745147806)]
    expected_measurecount_and_starttime_per_lieddeel = [('intro', 10, 0.0), ('couplet 1', 18, 13.043478260869566), ('refrein', 15, 36.52173913043478), ('overgang refr-couplet', 10, 56.086956521739125), ('couplet', 24, 69.13043478260869), ('refrein', 15, 100.43478260869564), ('middenstuk', 32, 119.99999999999999), ('couplet', 24, 163.984655277565), ('refrein', 15, 195.28900310365196), ('uittro', 8, 214.8542204949563)]
    rng = len(expected_measurecount_and_starttime_per_lieddeel)
    for i in range(rng):
        assert result[1][i] == expected_measurecount_and_starttime_per_lieddeel[i]

    # assert chords_per_lieddeel 
    expected_chords_per_lieddeel = {'intro': ('A7sus2(8)', 8, True), 'couplet 1': ('A7sus2(5), Dmaj7(4), A7sus2(5), Dmaj7(4)', 18, True), 'refrein': ('Bm6(3), Em(4), Edim(add 11)(2), Em (add9+11)(2), Dmaj7(2), B(2)', 15, True), 'overgang refr-couplet': ('E6(2), A (schuif)(4), A7sus2(4)', 10, True), 'couplet': ('A7sus2(4), Dmaj7(4), A7sus2(4), Dmaj7(4), A7sus2(4), Dmaj7(4)', 24, True), 'middenstuk': ('Em7(4), A7(4), Em7(4), A7(4), Em7(4), A7(4), Em7(4), A7(4)', 32, True), 'uittro': ('Em6(2), A(4), D(2)', 8, True)}
    for key in {'intro', 'couplet 1', 'refrein', 'overgang refr-couplet', 'couplet', 'middenstuk', 'uittro'}:
        assert result[2][key][0] == expected_chords_per_lieddeel[key][0]

    # assert all_labels
    expected_all_labels = [('intro', 0.0), ('Start zang', 12.391304347826088), ('couplet 1', 13.043478260869566), ('D', 19.56521739130435), ('A', 24.782608695652176), ('D', 31.304347826086957), ('refrein', 36.52173913043478), ('E', 40.43478260869565), ('Edim', 45.65217391304348), ('Em', 48.26086956521739), ('B', 53.47826086956522), ('overgang refr-couplet', 56.086956521739125), ('A', 58.69565217391304), ('couplet', 69.13043478260869), ('D', 74.34782608695652), ('A', 79.56521739130434), ('D', 84.78260869565217), ('A', 90.0), ('D', 95.21739130434781), ('refrein', 100.43478260869564), ('E', 104.34782608695652), ('Edim', 109.56521739130434), ('Em', 112.17391304347825), ('B', 117.39130434782608), ('middenstuk', 119.99999999999999), ('A', 125.51724137931033), ('E', 131.03448275862067), ('A', 136.55172413793102), ('E', 142.06896551724137), ('A', 147.58620689655172), ('E', 153.10344827586206), ('A', 158.62068965517238), ('couplet', 163.984655277565), ('D', 169.2020465819128), ('A', 174.41943788626065), ('D', 179.63682919060847), ('A', 184.8542204949563), ('D', 190.07161179930412), ('refrein', 195.28900310365196), ('E', 199.20204658191284), ('Edim', 204.41943788626065), ('Em', 207.0281335384346), ('B', 212.2455248427824), ('uittro', 214.8542204949563), ('A', 217.46291614713022), ('D', 222.68030745147806)]
    rng = len(expected_all_labels)
    for i in  range(rng):
        assert result[3][i] == expected_all_labels[i]

    assert result[4] == 184                 # initial tempo
    assert result[5] == '4/4'               # initial timesig
    assert result[6] == 1.0                 # nr of pickup beats
    assert round(result[7], 0) == 222.0     # netto song duration, 3:42