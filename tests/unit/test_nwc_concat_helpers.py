"""Unit tests for the pure timesig/duration helpers in nwc-concat.py."""

import pytest
from pathlib import Path
from nwc_utils import TimingSegment

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
# time_at_measure
# Return (elapsed_time, beat_duration, beat_base) at the start of a measure (0-based).
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_time_at_measure_one_beat_per_second(concat):
    segments = [TimingSegment(tempo=60, timesig='4/4', measure_count=1)]
    measure_number = 1
    assert concat.time_at_measure(segments, measure_number) == (4.0, 1.0, 4)  # na 1 maat (measure 0) zijn verstreken: 4 sec

@pytest.mark.unit
def test_time_at_measure_zero_based(concat):
    segments = [TimingSegment(tempo=60, timesig='4/4', measure_count=1)]
    measure_number = 0   # Note: maat 0, method is 0-based, dus expected elapsed time at start of measure is 0.
    assert concat.time_at_measure(segments, measure_number) == (0.0, 1.0, 4)  # dur: 4 sec

@pytest.mark.unit
def test_time_at_measure_double_tempo(concat):
    segments = [TimingSegment(tempo=120, timesig='4/4', measure_count=1)]
    measure_number = 1
    assert concat.time_at_measure(segments, measure_number) == (2.0, 0.5, 4)

@pytest.mark.unit
def test_time_at_measure_double_tempo_walz(concat):
    segments = [TimingSegment(tempo=120, timesig='3/4', measure_count=1)]
    measure_number = 1
    assert concat.time_at_measure(segments, measure_number) == (1.5, 0.5, 4)   # dur 1.5 sec

# @pytest.mark.unit
def test_time_at_measure_double_tempo_long(concat):
    segments = [TimingSegment(tempo=120, timesig='4/4', measure_count=50)]
    measure_number = 48
    assert concat.time_at_measure(segments, measure_number) == (96.0, 0.5, 4)

@pytest.mark.unit
def test_time_at_measure_fast_and_long(concat):
    segments = [TimingSegment(tempo=180, timesig='4/4', measure_count=50)]
    measure_number = 50  # Note: er zijn 50 maten, 0-based, dus 0-49. Maat 50 bestaat dus niet, maar deze method is daar niet van onder de indruk.
    result = concat.time_at_measure(segments, measure_number) 
    assert round(result[0], 4) == 66.6667   # dwz bij start maat 50 zijn 66.6sec verstreken
    assert round(result[1], 4) == 0.3333    # dwz één beat duurt 0.33s

@pytest.mark.unit
def test_time_at_measure_fast_but_at_start(concat):
    segments = [TimingSegment(tempo=180, timesig='4/4', measure_count=50)]
    measure_number = 0
    result = concat.time_at_measure(segments, measure_number) 
    assert round(result[0], 4) == 0.0000    # dwz bij start maat 0 zijn 0 sec verstreken
    assert round(result[1], 4) == 0.3333    # dwz één beat duurt 0.33s


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
# process_lieddelen (ADDED BY STEFAN, NOT REALLY A UNITTEST BUT IT HELPS)
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_provess_lieddelen1(concat):
    title = "Humanity (53)"
    nwc_folder = Path(__file__).parent.parent.parent.parent / "testdata/lieddelen"
    volgorde_lieddelen = ['intro', 'couplet 1', 'refrein', 'overgang refr-couplet', 'couplet', 'refrein', 'middenstuk', 'couplet', 'refrein', 'uittro']
    result = concat.process_lieddelen(title, volgorde_lieddelen, nwc_folder)           # expected duration 3:43 verified (excl maten vooraf, which take 3 additional secs)

    # ============ EXPECTED OUTPUT (examples! For the actual values see code below) =================
    # file_list: ['C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) intro.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) couplet 1.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) refrein.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) overgang refr-couplet.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) couplet.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) refrein.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) middenstuk.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) couplet.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) refrein.nwctxt', 'C:\\Persoonlijk\\liedteksten\\Humanity (53)\\nwc\\Humanity (53) uittro.nwctxt']
    # measurecount_and_starttime_per_lieddeel: [('intro', 10, 0.0), ('couplet 1', 18, 13.043478260869566), ('refrein', 15, 36.52173913043478), ('overgang refr-couplet', 10, 56.086956521739125), ('couplet', 24, 69.13043478260869), ('refrein', 15, 100.43478260869564), ('middenstuk', 32, 119.99999999999999), ('couplet', 24, 163.984655277565), ('refrein', 15, 195.28900310365196), ('uittro', 8, 214.8542204949563)]
    # chords_per_lieddeel: {'intro': ('A7sus2(8)', 8, True), 'couplet 1': ('A7sus2(5), Dmaj7(4), A7sus2(5), Dmaj7(4)', 18, True), 'refrein': ('Bm6(3), Em(4), Edim(add 11)(2), Em (add9+11)(2), Dmaj7(2), B(2)', 15, True), 'overgang refr-couplet': ('E6(2), A (schuif)(4), A7sus2(4)', 10, True), 'couplet': ('A7sus2(4), Dmaj7(4), A7sus2(4), Dmaj7(4), A7sus2(4), Dmaj7(4)', 24, True), 'middenstuk': ('Em7(4), A7(4), Em7(4), A7(4), Em7(4), A7(4), Em7(4), A7(4)', 32, True), 'uittro': ('Em6(2), A(4), D(2)', 8, True)}
    # all_labels: [('intro', 0.0), ('Start zang', 12.391304347826088), ('couplet 1', 13.043478260869566), ('D', 19.56521739130435), ('A', 24.782608695652176), ('D', 31.304347826086957), ('refrein', 36.52173913043478), ('E', 40.43478260869565), ('Edim', 45.65217391304348), ('Em', 48.26086956521739), ('B', 53.47826086956522), ('overgang refr-couplet', 56.086956521739125), ('A', 58.69565217391304), ('couplet', 69.13043478260869), ('D', 74.34782608695652), ('A', 79.56521739130434), ('D', 84.78260869565217), ('A', 90.0), ('D', 95.21739130434781), ('refrein', 100.43478260869564), ('E', 104.34782608695652), ('Edim', 109.56521739130434), ('Em', 112.17391304347825), ('B', 117.39130434782608), ('middenstuk', 119.99999999999999), ('A', 125.51724137931033), ('E', 131.03448275862067), ('A', 136.55172413793102), ('E', 142.06896551724137), ('A', 147.58620689655172), ('E', 153.10344827586206), ('A', 158.62068965517238), ('couplet', 163.984655277565), ('D', 169.2020465819128), ('A', 174.41943788626065), ('D', 179.63682919060847), ('A', 184.8542204949563), ('D', 190.07161179930412), ('refrein', 195.28900310365196), ('E', 199.20204658191284), ('Edim', 204.41943788626065), ('Em', 207.0281335384346), ('B', 212.2455248427824), ('uittro', 214.8542204949563), ('A', 217.46291614713022), ('D', 222.68030745147806)]
    # first_lieddeel_tempo: 184
    # first_lieddeel_timesig: '4/4'
    # pickup_beats:1.0
    # netto_song_duration: 222  (3:42)
    # ================================================================================

    # assert files
    expected_paths = ['C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) intro.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) couplet 1.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) refrein.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) overgang refr-couplet.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) couplet.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) refrein.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) middenstuk.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) couplet.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) refrein.nwctxt', 'C:\\Persoonlijk\\liedteksten\\testdata\\lieddelen\\Humanity (53) uittro.nwctxt']
    expected_paths = ['D:\\persoonlijk\\LT\\testdata\\lieddelen\\Humanity (53) intro.nwctxt', 'D:\\persoonlijk\\LT\\testdata\\lieddelen\\Humanity (53) couplet 1.nwctxt', 'D:\\persoonlijk\\LT\\testdata\\lieddelen\\Humanity (53) refrein.nwctxt', 'D:\\persoonlijk\\LT\\testdata\\lieddelen\\Humanity (53) overgang refr-couplet.nwctxt', 'D:\\persoonlijk\\LT\\testdata\\lieddelen\\Humanity (53) couplet.nwctxt', 'D:\\persoonlijk\\LT\\testdata\\lieddelen\\Humanity (53) refrein.nwctxt', 'D:\\persoonlijk\\LT\\testdata\\lieddelen\\Humanity (53) middenstuk.nwctxt', 'D:\\persoonlijk\\LT\\testdata\\lieddelen\\Humanity (53) couplet.nwctxt', 'D:\\persoonlijk\\LT\\testdata\\lieddelen\\Humanity (53) refrein.nwctxt', 'D:\\persoonlijk\\LT\\testdata\\lieddelen\\Humanity (53) uittro.nwctxt']
    rng = len(expected_paths) 
    for i in range(rng):
        assert result[0][i] == expected_paths[i]

    # assert measurecount_and_starttime_per_lieddeel
    # BUG FIXED BY THIS TEST: maten vooraf werden niet meegeteld, waardoor intro een te korte duur kreeg. Mogelijk hierdoor verschoven alle labels?
    # DESIGN ERROR FOUND BY THIS TEST: pickup beat wordt overgeslagen, maar vooraf_measures niet. Dat is incorrect: Het moet allebei wel meetellen (nl bij exacte weergave van de compos in .nwctxt) of allebei niet (bij bepalen 'netto' duur van song).
    # OLD EXPECTATION, HAS DESIGN ERROR: expected_measurecount_and_starttime_per_lieddeel = [('intro', 8, 0.32608695652173914), ('couplet 1', 18, 13.369565217391305), ('refrein', 15, 36.84782608695652), ('overgang refr-couplet', 10, 56.413043478260875), ('couplet', 24, 69.45652173913044), ('refrein', 15, 100.76086956521739), ('middenstuk', 32, 120.32608695652173), ('couplet', 24, 164.31074223408675), ('refrein', 15, 195.6150900601737), ('uittro', 8, 215.18030745147806)]
    # NEW THOUGHT: m_cnt_and_starttime moet altijd de starttijden bevatten voor de labeltrack, want er is geen ander doel: dit includeert dus de vooraf-sectie.
    # Maar de maat-count heeft 2 doelen: de stats (dan zonder voorafsectie) en berekening starttijden (dan met). Voorstel: splits het intro op basis van het liedstart-label in 'vooraf' en 'intro'. 
    # expected_measurecount_and_starttime_per_lieddeel = [('vooraf', 2, 0.0, 2.9347826086956523), ('intro', 8, 2.9347826086956523), ('couplet 1', 18, 15.978260869565219), ('refrein', 15, 39.45652173913044), ('overgang refr-couplet', 10, 59.02173913043478), ('couplet', 24, 72.06521739130434), ('refrein', 15, 103.3695652173913), ('middenstuk', 32, 122.93478260869564), ('couplet', 24, 166.91943788626065), ('refrein', 15, 198.22378571234762), ('uittro', 8, 217.78900310365196)]
    expected_measurecount_and_starttime_per_lieddeel = [('vooraf', 2, 0.0, 2.9347826086956523), ('intro', 8, 2.9347826086956523, 13.043478260869566), ('couplet 1', 18, 15.978260869565219, 23.47826086956522), ('refrein', 15, 39.45652173913044, 19.565217391304348), ('overgang refr-couplet', 10, 59.02173913043478, 13.043478260869566), ('couplet', 24, 72.06521739130434, 31.304347826086957), ('refrein', 15, 103.3695652173913, 19.565217391304348), ('middenstuk', 32, 122.93478260869564, 43.984655277565004), ('couplet', 24, 166.91943788626065, 31.304347826086957), ('refrein', 15, 198.22378571234762, 19.565217391304348), ('uittro', 8, 217.78900310365196, 10.434782608695652)]
    rng = len(expected_measurecount_and_starttime_per_lieddeel)
    for i in range(rng):
        assert result[1][i] == expected_measurecount_and_starttime_per_lieddeel[i]

    # assert chords_per_lieddeel 
    expected_chords_per_lieddeel = {'intro': ('A7sus2(8)', 8, True), 'couplet 1': ('A7sus2(5), Dmaj7(4), A7sus2(5), Dmaj7(4)', 18, True), 'refrein': ('Bm6(3), Em(4), Edim(add 11)(2), Em (add9+11)(2), Dmaj7(2), B(2)', 15, True), 'overgang refr-couplet': ('E6(2), A (schuif)(4), A7sus2(4)', 10, True), 'couplet': ('A7sus2(4), Dmaj7(4), A7sus2(4), Dmaj7(4), A7sus2(4), Dmaj7(4)', 24, True), 'middenstuk': ('Em7(4), A7(4), Em7(4), A7(4), Em7(4), A7(4), Em7(4), A7(4)', 32, True), 'uittro': ('Em6(2), A(4), D(2)', 8, True)}
    for key in {'intro', 'couplet 1', 'refrein', 'overgang refr-couplet', 'couplet', 'middenstuk', 'uittro'}:
        assert result[2][key][0] == expected_chords_per_lieddeel[key][0]

    # assert all_labels
    expected_all_labels = [('intro', 2.9347826086956523), ('Start zang', 15.32608695652174), ('couplet 1', 15.978260869565219), ('D', 22.5), ('A', 27.717391304347828), ('D', 34.23913043478261), ('refrein', 39.45652173913044), ('E', 43.369565217391305), ('Edim', 48.58695652173913), ('Em', 51.19565217391305), ('B', 56.413043478260875), ('overgang refr-couplet', 59.02173913043478), ('A', 61.630434782608695), ('couplet', 72.06521739130434), ('D', 77.28260869565217), ('A', 82.5), ('D', 87.71739130434783), ('A', 92.93478260869566), ('D', 98.15217391304347), ('refrein', 103.3695652173913), ('E', 107.28260869565217), ('Edim', 112.5), ('Em', 115.1086956521739), ('B', 120.32608695652173), ('middenstuk', 122.93478260869564), ('A', 128.45202398800598), ('E', 133.96926536731632), ('A', 139.48650674662667), ('E', 145.00374812593702), ('A', 150.52098950524737), ('E', 156.03823088455772), ('A', 161.55547226386807), ('couplet', 166.91943788626065), ('D', 172.13682919060847), ('A', 177.3542204949563), ('D', 182.57161179930412), ('A', 187.78900310365196), ('D', 193.00639440799978), ('refrein', 198.22378571234762), ('E', 202.1368291906085), ('Edim', 207.3542204949563), ('Em', 209.96291614713022), ('B', 215.18030745147806), ('uittro', 217.78900310365196), ('A', 220.39769875582587), ('D', 225.6150900601737)]
    rng = len(expected_all_labels)
    for i in  range(rng):
        assert result[3][i] == expected_all_labels[i]

    assert result[4] == 184                 # initial tempo
    assert result[5] == '4/4'               # initial timesig
    assert result[6] == 1.0                 # nr of pickup beats
    assert round(result[7], 0) == 225.0     # netto song duration, 3:45