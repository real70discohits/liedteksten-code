"""Shared pytest fixtures and helpers for the lt-code test suite.

Two layers of tests are supported:

* **unit** - call pure/component functions directly. Because several scripts
  have hyphens in their filename (``nwc-concat.py``) they cannot be imported
  with a normal ``import`` statement; use the ``load_script`` fixture.
* **integration** - run a real script end-to-end against ``testdata/`` and
  compare the generated artefacts with the checked-in ``expected output/``
  files. The ``sandbox`` fixture copies a testset into a throwaway temp dir,
  writes a temporary ``paths.jsonc`` and points ``LT_PATHS_CONFIG`` at it, so
  the real code runs without ever touching the git working tree.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTDATA_DIR = REPO_ROOT / "testdata"

# Make the repo scripts/modules importable (constants, nwc_utils, ...).
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# --------------------------------------------------------------------------- #
# --update-golden: rewrite expectations instead of asserting them
# --------------------------------------------------------------------------- #
def pytest_addoption(parser):
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help=(
            "Rewrite golden artefacts and expected-values.json from the current "
            "output instead of comparing. Use after intentionally changing specs; "
            "then review the git diff before committing."
        ),
    )


@pytest.fixture
def update_golden(request):
    """True when the suite is run with --update-golden."""
    return request.config.getoption("--update-golden")


# --------------------------------------------------------------------------- #
# Importing hyphenated scripts as modules (for unit tests)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def load_script():
    """Return a function that imports a repo script by filename as a module.

    Works for hyphenated names that ``import`` cannot handle, e.g.::

        nwc_concat = load_script("nwc-concat.py")
        assert nwc_concat._parse_timesig_value("|TimeSig|Signature:3/4") == (3, 4)
    """

    def _load(script_filename):
        path = REPO_ROOT / script_filename
        module_name = "ltcode_" + script_filename.replace("-", "_").removesuffix(".py")
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    return _load


# --------------------------------------------------------------------------- #
# Sandbox: isolated copy of a testset wired up via LT_PATHS_CONFIG
# --------------------------------------------------------------------------- #
@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Factory that builds an isolated sandbox for a testset.

    Usage::

        sb = sandbox("testset nwc-concat", "Returnability (333)")

    It reconstructs the layout the scripts expect
    (``input/<song>/nwc/<files>``), creates build/dist/audio output folders,
    writes a temp ``paths.jsonc`` with absolute paths and sets
    ``LT_PATHS_CONFIG`` so every script under test redirects there.
    Returns a namespace with the relevant paths plus ``expected`` (the
    checked-in golden folder).
    """

    def _build(testset, songtitle):
        src_input = TESTDATA_DIR / testset / "input"
        assert src_input.is_dir(), f"Testset input not found: {src_input}"

        # Reconstruct the input layout the scripts expect.
        nwc_dir = tmp_path / "input" / songtitle / "nwc"
        nwc_dir.mkdir(parents=True)
        for f in src_input.iterdir():
            if f.is_file():
                shutil.copy2(f, nwc_dir / f.name)

        build = tmp_path / "build"
        dist = tmp_path / "dist"
        audio = tmp_path / "audio"
        for d in (build, dist, audio):
            d.mkdir()

        config = tmp_path / "paths.jsonc"
        config.write_text(
            json.dumps(
                {
                    "input_folder": str(tmp_path / "input"),
                    "build_folder": str(build),
                    "distributie_folder": str(dist),
                    "audio_output_folder": str(audio),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("LT_PATHS_CONFIG", str(config))

        return SimpleNamespace(
            root=tmp_path,
            config=config,
            input_folder=tmp_path / "input",
            build=build,
            dist=dist,
            audio=audio,
            # load_and_resolve_paths() appends the songtitle to build/dist.
            song_build=build / songtitle,
            song_audio=audio / songtitle,
            song_folder=tmp_path / "input" / songtitle,
            expected=TESTDATA_DIR / testset / "expected output",
        )

    return _build


# --------------------------------------------------------------------------- #
# Running a script as a real subprocess (end-to-end smoke / golden tests)
# --------------------------------------------------------------------------- #
@pytest.fixture
def run_script(monkeypatch):
    """Return a function that runs a repo script as a subprocess.

    The subprocess inherits ``LT_PATHS_CONFIG`` (set by ``sandbox``), runs with
    cwd = repo root and captures stdout/stderr. Returns the CompletedProcess.
    """

    def _run(script_filename, *args, extra_env=None):
        """Run a script as a subprocess.

        The scripts are expected to make their own stdout UTF-8 safe (see
        console_utf8.enable_utf8_console), so this deliberately does NOT force
        an encoding - it captures whatever the script actually emits. Pass
        ``extra_env`` to override environment variables (e.g. to force a
        legacy cp1252 console for the UTF-8 regression test).
        """
        cmd = [sys.executable, str(REPO_ROOT / script_filename), *args]
        env = {**os.environ}
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )

    return _run


# --------------------------------------------------------------------------- #
# Golden-file comparison
# --------------------------------------------------------------------------- #
@pytest.fixture
def assert_matches_golden():
    """Return an assertion helper comparing a generated file to a golden file.

    Comparison is line-based and line-ending agnostic (CRLF vs LF) so the test
    does not break on git autocrlf differences. On mismatch it reports the
    first differing line for a readable failure.
    """

    def _assert(actual: Path, expected: Path, normalize=None):
        """Compare ``actual`` to ``expected`` line by line.

        ``normalize`` is an optional ``str -> str`` applied to every line of
        both files before comparison, used to mask volatile content such as
        absolute machine-specific paths.
        """
        actual = Path(actual)
        expected = Path(expected)
        assert actual.exists(), f"Generated file is missing: {actual}"
        assert expected.exists(), f"Golden file is missing: {expected}"

        actual_lines = actual.read_text(encoding="utf-8").splitlines()
        expected_lines = expected.read_text(encoding="utf-8").splitlines()
        if normalize is not None:
            actual_lines = [normalize(line) for line in actual_lines]
            expected_lines = [normalize(line) for line in expected_lines]

        for i, (a, e) in enumerate(zip(actual_lines, expected_lines), start=1):
            if a != e:
                raise AssertionError(
                    f"{actual.name}: first difference at line {i}\n"
                    f"  expected: {e!r}\n"
                    f"  actual:   {a!r}"
                )
        if len(actual_lines) != len(expected_lines):
            raise AssertionError(
                f"{actual.name}: line count differs "
                f"(expected {len(expected_lines)}, got {len(actual_lines)}). "
                f"First extra line: "
                f"{(expected_lines + actual_lines)[min(len(actual_lines), len(expected_lines))]!r}"
            )

    return _assert
