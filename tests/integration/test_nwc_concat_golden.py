"""End-to-end golden test for nwc-concat.py.

Runs the real script against ``testdata/testset nwc-concat`` inside an isolated
sandbox (see the ``sandbox`` fixture) and compares every generated artefact to
the checked-in ``expected output/`` files.

This is the regression net to run before/after refactoring nwc-concat.py.
"""

import shutil

import pytest


def _mask_locatie(line):
    """Mask the machine-specific absolute build path in analysis.txt.

    The 'Locatie:' line embeds the absolute output folder, which differs per
    machine/run and is irrelevant to the analysis content under test.
    """
    if line.startswith("Locatie:"):
        return "Locatie: <build folder>"
    return line


SCRIPT = "nwc-concat.py"
TESTSET = "testset nwc-concat"
SONG = "Returnability (333)"

# The volgorde.jsonc for this song notes it must be compiled with --keep-tempi
# (the middenstuk is slower), which is how the expected output was generated.
CLI_ARGS = (SONG, "--keep-tempi")


@pytest.fixture
def concat_run(sandbox, run_script):
    """Build the sandbox, run nwc-concat, and return (sandbox, result)."""
    sb = sandbox(TESTSET, SONG)
    result = run_script(SCRIPT, *CLI_ARGS)
    return sb, result


@pytest.mark.integration
def test_script_succeeds(concat_run):
    sb, result = concat_run
    assert result.returncode == 0, (
        f"nwc-concat exited with {result.returncode}\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "filename, location, normalize",
    [
        (f"{SONG}.nwctxt", "song_build", None),
        (f"{SONG} analysis.txt", "song_build", _mask_locatie),
        (f"{SONG} structuur.tex", "song_build", None),
        (f"{SONG} labeltrack t_(184, 4).txt", "song_audio", None),
    ],
)
def test_artifact_matches_golden(
    concat_run, assert_matches_golden, update_golden, filename, location, normalize
):
    sb, result = concat_run
    assert result.returncode == 0, (
        f"nwc-concat failed before artefact comparison\n{result.stdout}\n{result.stderr}"
    )
    actual = getattr(sb, location) / filename
    expected = sb.expected / filename

    if update_golden:
        assert actual.exists(), f"Cannot update golden, output missing: {actual}"
        expected.parent.mkdir(parents=True, exist_ok=True)
        if normalize is None:
            shutil.copyfile(actual, expected)
        else:
            # Store the normalized form so the committed golden is portable
            # (e.g. without machine-specific absolute paths).
            lines = actual.read_text(encoding="utf-8").splitlines()
            expected.write_text(
                "\n".join(normalize(line) for line in lines) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        pytest.skip(f"--update-golden: refreshed {expected.name}")

    assert_matches_golden(actual, expected, normalize=normalize)
