"""Unit tests for the pure helpers in lt-generate.py:
transpose(), strip_extension() and maak_opsomming().
"""

import pytest


@pytest.fixture(scope="module")
def ltgen(load_script):
    return load_script("lt-generate.py")


# --------------------------------------------------------------------------- #
# transpose
# --------------------------------------------------------------------------- #
@pytest.mark.unit
@pytest.mark.parametrize(
    "note, semitones, expected",
    [
        ("C", 0, "C"),
        ("C", 2, "D"),
        ("C", 12, "C"),          # wraps around the octave
        ("D", -2, "C"),
        ("B", 1, "C"),           # sharp side wraps 11 -> 0
        ("Cis", 1, "D"),
        ("C", 1, "Cis"),         # sharp notation by default
        ("Des", 2, "Es"),        # flat note -> stays in flat notation
        ("Des", 0, "Des"),
        ("Cmaj7", 2, "Dmaj7"),   # extension preserved
        ("Ami", 2, "Bmi"),       # minor suffix preserved
        ("K", 2, "K"),           # invalid note returned unchanged
        ("something", 5, "something"),
    ],
)
def test_transpose(ltgen, note, semitones, expected):
    assert ltgen.transpose(note, semitones) == expected


# --------------------------------------------------------------------------- #
# strip_extension
# --------------------------------------------------------------------------- #
@pytest.mark.unit
@pytest.mark.parametrize(
    "filename, expected",
    [
        ("song.tex", "song"),
        ("a.b.c", "a.b"),        # rightmost dot only
        ("noext", "noext"),
        ("Returnability (333).nwctxt", "Returnability (333)"),
    ],
)
def test_strip_extension(ltgen, filename, expected):
    assert ltgen.strip_extension(filename) == expected


@pytest.mark.unit
@pytest.mark.parametrize("bad", ["a/b.tex", "a\\b.tex", 'a:b', "a?b", "a*b"])
def test_strip_extension_rejects_invalid(ltgen, bad):
    with pytest.raises(ValueError):
        ltgen.strip_extension(bad)


# --------------------------------------------------------------------------- #
# maak_opsomming
# --------------------------------------------------------------------------- #
@pytest.mark.unit
@pytest.mark.parametrize(
    "items, expected",
    [
        ([], ""),
        (["maatnummers"], " met maatnummers"),
        (["maatnummers", "akkoorden"], " met maatnummers en akkoorden"),
        (["a", "b", "c"], " met a, b en c"),
        ([None, "akkoorden"], " met akkoorden"),   # falsy items filtered out
        ([None, "", False], ""),
    ],
)
def test_maak_opsomming(ltgen, items, expected):
    assert ltgen.maak_opsomming(items) == expected
