"""Unit tests for the pure parsing helpers in nwc_analyze.py."""

from pathlib import Path

import pytest

import nwc_analyze


# --------------------------------------------------------------------------- #
# parse_song_info / find_song_number
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_parse_song_info_extracts_title():
    assert nwc_analyze.parse_song_info('|SongInfo|Title:"My Song"|Author:"x"') == "My Song"


@pytest.mark.unit
def test_parse_song_info_unknown_when_absent():
    assert nwc_analyze.parse_song_info("|Something|Else:1") == "Unknown"


@pytest.mark.unit
@pytest.mark.parametrize(
    "stem, expected",
    [
        ("Returnability (333)", "333"),
        ("Song 12 take 7", "7"),     # last number wins
        ("no numbers here", None),
    ],
)
def test_find_song_number(stem, expected):
    assert nwc_analyze.find_song_number(Path(f"{stem}.nwctxt")) == expected


# --------------------------------------------------------------------------- #
# parse_lyric_text
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_parse_lyric_text_splits_syllables():
    line = '|Lyric1|Text:"Hal-lo we-reld"'
    assert nwc_analyze.parse_lyric_text(line) == ["Hal", "lo", "we", "reld"]


@pytest.mark.unit
def test_parse_lyric_text_no_match_returns_empty():
    assert nwc_analyze.parse_lyric_text("|Note|Dur:4th") == []


@pytest.mark.unit
def test_parse_lyric_text_preserves_underscore():
    # Underscores are not delimiters - they keep a syllable together.
    assert nwc_analyze.parse_lyric_text('|Lyric1|Text:"a_b cd"') == ["a_b", "cd"]


# --------------------------------------------------------------------------- #
# find_part_of_element
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_find_part_of_element():
    el = "|Note|Dur:8th|Pos:-3^|Opts:Stem=Up,Beam=End"
    assert nwc_analyze.find_section_in_line("Pos", el) == "Pos:-3^"


@pytest.mark.unit
def test_find_part_of_element_case_insensitive():
    el = "|Note|Dur:8th|Pos:0"
    assert nwc_analyze.find_section_in_line("dur", el) == "Dur:8th"


@pytest.mark.unit
def test_find_part_of_element_missing_returns_none():
    assert nwc_analyze.find_section_in_line("Opts", "|Note|Dur:8th") is None


# --------------------------------------------------------------------------- #
# multiple_notes_count_as_one  (slurs / ties)
# --------------------------------------------------------------------------- #
@pytest.mark.unit
@pytest.mark.parametrize(
    "element, expected",
    [
        ("|Note|Dur:8th|Pos:0|Opts:Slur", True),       # slur
        ("|Note|Dur:8th|Pos:-3^|Opts:Stem=Up", True),  # tie marker '^' on Pos
        ("|Note|Dur:4th|Pos:0", False),
    ],
)
def test_multiple_notes_count_as_one(element, expected):
    assert nwc_analyze.multiple_notes_count_as_one(element) is expected


# --------------------------------------------------------------------------- #
# count_bars_in_staff
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_count_bars_in_staff():
    content = "|Note|Dur:4th\n|Bar\n|Note|Dur:4th\n|Bar|Style:Double"
    assert nwc_analyze.blindly_count_barmarkers_in_staff(content) == 2


# --------------------------------------------------------------------------- #
# detect_begintel
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_detect_begintel_true_when_rest_before_first_bar():
    assert nwc_analyze.detect_begintel("|Rest|Dur:4th|Bar|Note|Dur:Whole") is True


@pytest.mark.unit
def test_detect_begintel_false_without_leading_rest():
    assert nwc_analyze.detect_begintel("|Note|Dur:4th|Bar|Note|Dur:Whole") is False


# --------------------------------------------------------------------------- #
# count_vooraf_measures
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_count_vooraf_measures_subtracts_begintel():
    content = "\n".join(
        [
            "|Rest|Dur:4th",            # begintel (pickup)
            "|Bar",
            "|Note|Dur:Whole|Pos:0",      # one count-in measure
            "|Bar",
            '|Text|Text:"liedstart"',   # song really starts here
            "|Note|Dur:4th|Pos:0",
            "|Bar",
        ]
    )
    # 2 bars before liedstart, with above minimum duration, minus 1 for the begintel -> 1 vooraf measure.
    assert nwc_analyze.count_vooraf_measures(content) == 1


@pytest.mark.unit
def test_count_vooraf_measures_zero_without_liedstart():
    content = "|Rest|Dur:4th\n|Bar\n|Note|Dur:4th\n|Bar"
    assert nwc_analyze.count_vooraf_measures(content) == 0


# --------------------------------------------------------------------------- #
# get_single_duration_struct
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_get_single_duration_struct_01():
    content = "|Rest|Dur:4th"
    assert nwc_analyze.get_single_duration_struct(content) == ("4th", 1.0)

@pytest.mark.unit
def test_get_single_duration_struct_02():
    content = "|Note|Dur:8th|Pos:0|Opts:Stem=Down,Beam=First"
    assert nwc_analyze.get_single_duration_struct(content) == ("8th", 1.0)

@pytest.mark.unit
def test_get_single_duration_struct_03():
    content = "|Rest|Dur:4th|Opts:Stem=Down"
    assert nwc_analyze.get_single_duration_struct(content) == ("4th", 1.0)

@pytest.mark.unit
def test_get_single_duration_struct_04():
    content = "|Note|Dur:4th,Staccato|Pos:-4|Opts:Stem=Up"
    assert nwc_analyze.get_single_duration_struct(content) == ("4th", 1.0)

@pytest.mark.unit
def test_get_single_duration_struct_05():
    content = "|Note|Dur:4th,Dotted|Pos:-4|Opts:Stem=Up"
    assert nwc_analyze.get_single_duration_struct(content) == ("4th", 1.5)

@pytest.mark.unit
def test_get_single_duration_struct_06():
    content = "|Note|Dur:8th,Slur|Pos:-4|Opts:Stem=Up"
    assert nwc_analyze.get_single_duration_struct(content) == ("8th", 1.0)

@pytest.mark.unit
def test_get_single_duration_struct_07():
    content = "|Note|Dur:Half,DblDotted|Pos:-4^"
    assert nwc_analyze.get_single_duration_struct(content) == ("Half", 1.75)

@pytest.mark.unit
def test_get_single_duration_struct_08():
    content = "|Note|Dur:8th|Pos:1|Opts:Stem=Down,Beam=First"
    assert nwc_analyze.get_single_duration_struct(content) == ("8th", 1.0)


# --------------------------------------------------------------------------- #
# convert_duration
# --------------------------------------------------------------------------- #

# a-serie: base conversions
@pytest.mark.unit
def test_convert_duration_a01():
    dur = "4th"
    to_base_note = 4
    assert nwc_analyze.convert_duration(dur, to_base_note) == 1.0

@pytest.mark.unit
def test_convert_duration_a02():
    dur = "8th"
    to_base_note = 8
    assert nwc_analyze.convert_duration(dur, to_base_note) == 1.0

@pytest.mark.unit
def test_convert_duration_a03():
    dur = "16th"
    to_base_note = 16
    assert nwc_analyze.convert_duration(dur, to_base_note) == 1.0

@pytest.mark.unit
def test_convert_duration_a04():
    dur = "32nd"
    to_base_note = 32
    assert nwc_analyze.convert_duration(dur, to_base_note) == 1.0

@pytest.mark.unit
def test_convert_duration_a05():
    dur = "Whole"
    to_base_note = 1
    assert nwc_analyze.convert_duration(dur, to_base_note) == 1.0

@pytest.mark.unit
def test_convert_duration_a06():
    dur = "Half"
    to_base_note = 2
    assert nwc_analyze.convert_duration(dur, to_base_note) == 1.0

# b-serie: advanced conversions
@pytest.mark.unit
def test_convert_duration_b01():
    dur = "8th"
    to_base_note = 4
    assert nwc_analyze.convert_duration(dur, to_base_note) == 0.5

@pytest.mark.unit
def test_convert_duration_b02():
    dur = "Half"
    to_base_note = 4
    assert nwc_analyze.convert_duration(dur, to_base_note) == 2.0

@pytest.mark.unit
def test_convert_duration_b03():
    dur = "Half"
    to_base_note = 16
    assert nwc_analyze.convert_duration(dur, to_base_note) == 8.0

@pytest.mark.unit
def test_convert_duration_b04():
    dur = "32nd"
    to_base_note = 8
    assert nwc_analyze.convert_duration(dur, to_base_note) == 0.25

# c-serie: erroneous input
def test_convert_duration_invalid_message_c01():
    dur = "32th"    # wrong value!
    to_base_note = 4
    with pytest.raises(ValueError, match="Unknown duration"):
        nwc_analyze.convert_duration(dur, to_base_note)

def test_convert_duration_invalid_message_c02():
    dur = "32nd"
    to_base_note = 0  # wrong value!
    with pytest.raises(ValueError, match="to_base_note must be positive, got"):
        nwc_analyze.convert_duration(dur, to_base_note)