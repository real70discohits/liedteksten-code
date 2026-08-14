"""Derived-values test for nwc-concat.py.

Where the golden test compares the *rendered* artefacts byte-for-byte, this
test pins the *meaning*: the scalar/structured values the system computes
(tempo, time signature, pickup, per-section measure counts and start times,
totals, chords). These live in ``expected output/expected-values.json`` per
testset and are easy to read and edit by hand.

The values are obtained by calling the real component functions directly (not
by parsing the artefacts), so they exercise the computation paths and give
precise per-field failure messages.

Run ``pytest --update-golden`` to regenerate expected-values.json after an
intentional spec change.
"""

import json

import pytest

import nwc_analyze

SCRIPT = "nwc-concat.py"
TESTSET = "testset nwc-concat"
SONG = "Returnability (333)"
KEEP_TEMPI = True  # this song has a slower middenstuk; matches the golden run

VALUES_FILENAME = "expected-values.json"


def _round(value, ndigits=3):
    return round(value, ndigits) if isinstance(value, float) else value


def compute_derived_values(mod, nwc_folder, songtitle, tmp_path, keep_tempi):
    """Compute the derived-values dict for a song via the real functions."""
    volgorde = mod.load_song_structure(songtitle, nwc_folder)
    (
        file_list,
        measurecount_and_starttime,
        chords_per_lieddeel,
        _all_labels,
        tempo,
        timesig,
        pickup_beats,
        nett_song_duration
    ) = mod.process_lieddelen(songtitle, volgorde, nwc_folder)

    merged = tmp_path / f"{songtitle}.nwctxt"
    mod.concatenate_nwctxt_files(file_list, str(merged), keep_tempi=keep_tempi)
    analysis = nwc_analyze.analyze_complete_song(merged, tempo=tempo, timesig=timesig)

    return {
        "tempo": tempo,
        "timesig": timesig,
        "pickup_beats": pickup_beats,
        "has_begintel": analysis["has_begintel"],
        "vooraf": analysis["vooraf"],
        "total_bars": analysis["total_bars"],
        "total_measures": analysis["total_measures"],
        "total_duration_seconds": _round(analysis["total_duration"]),
        "sequence": [
            {"name": name, "measures": measures, "start_time_seconds": _round(start)}
            for (name, measures, start, _) in measurecount_and_starttime
        ],
        "chords_per_section": {
            name: {"chords": chord_string, "count": chord_count}
            for name, (chord_string, chord_count, _valid) in chords_per_lieddeel.items()
        },
    }


@pytest.mark.integration
def test_derived_values(sandbox, load_script, tmp_path, update_golden):
    sb = sandbox(TESTSET, SONG)
    mod = load_script(SCRIPT)
    mod.enable_utf8_console()  # the functions print emoji status lines

    nwc_folder = sb.song_folder / "nwc"
    actual = compute_derived_values(mod, nwc_folder, SONG, tmp_path, KEEP_TEMPI)

    values_path = sb.expected / VALUES_FILENAME

    if update_golden:
        values_path.parent.mkdir(parents=True, exist_ok=True)
        values_path.write_text(
            json.dumps(actual, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        pytest.skip(f"--update-golden: refreshed {VALUES_FILENAME}")

    assert values_path.exists(), (
        f"{VALUES_FILENAME} not found. Generate it once with: pytest --update-golden"
    )
    expected = json.loads(values_path.read_text(encoding="utf-8"))

    # convert some arrays to tuples, because the source is in json which doesn't know tuples and just stores as arrrays.
    if 'tempo' in expected:
        expected['tempo'] = tuple(expected['tempo'])

    assert actual == expected
