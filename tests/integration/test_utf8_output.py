"""Regression test for UTF-8 safe console output.

The scripts print status with emoji (✅, ❌, ...). On Windows, whenever stdout
is not an interactive console (redirected to a file, or captured by a test
runner / parent process) the default encoding is cp1252 and printing an emoji
raised UnicodeEncodeError, crashing the script.

console_utf8.enable_utf8_console() (called at the start of every main()) fixes
this. This test reproduces the failing condition by forcing a legacy cp1252
stdio in the child process and asserts the script still completes and emits its
emoji output.
"""

import pytest

SCRIPT = "nwc-concat.py"
TESTSET = "testset nwc-concat"
SONG = "Returnability (333)"

# Force the pre-fix failure condition regardless of host platform/locale:
# disable Python UTF-8 mode and pin stdio to cp1252.
LEGACY_CP1252 = {"PYTHONUTF8": "0", "PYTHONIOENCODING": "cp1252"}


@pytest.mark.integration
def test_emoji_output_survives_legacy_cp1252(sandbox, run_script):
    sandbox(TESTSET, SONG)
    result = run_script(SCRIPT, SONG, "--keep-tempi", extra_env=LEGACY_CP1252)

    assert result.returncode == 0, (
        "Script crashed under cp1252 stdio (UTF-8 fix not effective)\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    # The success messages contain emoji; their presence proves the emoji were
    # encoded and flushed rather than triggering UnicodeEncodeError.
    assert "✅" in result.stdout
    assert "UnicodeEncodeError" not in result.stderr
