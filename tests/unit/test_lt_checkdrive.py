"""Tests voor lt-checkdrive.py (pure functies + integratie met tmp_path-fixture)."""
import os
import time
from pathlib import Path
import pytest


# ---------------------------------------------------------------------------
# Module-scoped fixture: load nwc-concat.py once for the entire test module
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def checkdrive(load_script):
    """Load the hyphen-named script as a module object.

    Relies on the load_script fixture (defined in conftest.py) which handles
    the dynamic import of files whose names contain non-identifier chars.
    """
    return load_script("lt-checkdrive.py")


class TestParseSongtitle:

    @pytest.fixture(autouse=True)
    def _inject(self, checkdrive):
        self.checkdrive = checkdrive

    def test_regular(self):
        assert self.checkdrive.parse_songtitle("Melody (9)") == ("Melody", 9)

    def test_multi_word(self):
        assert self.checkdrive.parse_songtitle("Girls Cant Get Enough (49)") == \
            ("Girls Cant Get Enough", 49)

    def test_suffix_disambiguation(self):
        # Dupes worden opgelost via naam-achtervoegsel, niet nummer
        assert self.checkdrive.parse_songtitle("Shes Got To Hurt II (38)") == \
            ("Shes Got To Hurt II", 38)

    def test_no_id_returns_none(self):
        assert self.checkdrive.parse_songtitle("Get Together") == (None, None)

    def test_leading_trailing_spaces(self):
        assert self.checkdrive.parse_songtitle("  Melody (9) ") == ("Melody", 9)


class TestDriveSongFolder:

    @pytest.fixture(autouse=True)
    def _inject(self, checkdrive):
        self.checkdrive = checkdrive

    def test_single_digit_padded(self):
        assert self.checkdrive.drive_song_folder(Path("_Liedjes"), "Melody (9)").name == "09. Melody"

    def test_two_digits_unchanged(self):
        assert self.checkdrive.drive_song_folder(Path("_Liedjes"), "Night Man (55)").name == "55. Night Man"


class TestPdfMatchesSong:

    @pytest.fixture(autouse=True)
    def _inject(self, checkdrive):
        self.checkdrive = checkdrive

    def test_exact(self):
        assert self.checkdrive.pdf_matches_song("Melody (9)", "Melody (9)")

    def test_variant(self):
        assert self.checkdrive.pdf_matches_song("Melody (9) met maatnummers", "Melody (9)")

    def test_transposition(self):
        assert self.checkdrive.pdf_matches_song("Melody (9) in D transp(+2)", "Melody (9)")

    def test_largeprint(self):
        assert self.checkdrive.pdf_matches_song("Melody (9) - LargePrint", "Melody (9)")

    def test_largeprint_variant(self):
        assert self.checkdrive.pdf_matches_song("Melody (9) met akkoorden - LargePrint", "Melody (9)")

    def test_other_song_same_basename_does_not_match(self):
        assert not self.checkdrive.pdf_matches_song("Shes Got To Hurt II (38)", "Shes Got To Hurt (24)")

    def test_id_boundary_not_matched(self):
        assert not self.checkdrive.pdf_matches_song("Melody (10) met akkoorden", "Melody (1)")

class TestIsStale:

    @pytest.fixture(autouse=True)
    def _inject(self, checkdrive):
        self.checkdrive = checkdrive

    def _mk(self, tmp_path, name, age):
        p = tmp_path / name
        p.write_text("x")
        os.utime(p, (time.time() - age, time.time() - age))
        return p

    def test_within_tolerance_is_fresh(self, tmp_path):
        pdf = self._mk(tmp_path, "a.pdf", self.checkdrive.SYNC_TOLERANCE_SECONDS - 20)
        assert not self.checkdrive.is_stale(pdf, time.time())

    def test_beyond_tolerance_is_stale(self, tmp_path):
        pdf = self._mk(tmp_path, "a.pdf", self.checkdrive.SYNC_TOLERANCE_SECONDS + 500)
        assert self.checkdrive.is_stale(pdf, time.time())


class TestCheckSong:

    @pytest.fixture(autouse=True)
    def _inject(self, checkdrive):
        self.checkdrive = checkdrive


    def test_empty_is_missing(self):
        assert self.checkdrive.check_song([], 0.0) == ('ONTBREEKT', [])

    def test_mix_is_stale(self, tmp_path):
        fresh = tmp_path / "fresh.pdf"; fresh.write_text("x")
        old = tmp_path / "old.pdf"; old.write_text("x")
        past = time.time() - (5*24*60*60)  # 5 days ago
        os.utime(old, (past, past))
        status, stale = self.checkdrive.check_song([fresh, old], time.time())
        assert status == 'VEROUDERD'
        assert stale == [old]


class TestIntegrationFindPdfs:

    @pytest.fixture(autouse=True)
    def _inject(self, checkdrive):
        self.checkdrive = checkdrive


    def test_recursive_subfolders(self, tmp_path):
        song = "Melody (9)"
        for sub in ["Standard", "Large Print"]:
            d = tmp_path / "09. Melody" / sub
            d.mkdir(parents=True)
            (d / f"{song}.pdf").write_text("x")
        (tmp_path / "09. Melody" / "andere.pdf").write_text("x")  # geen match
        found = self.checkdrive.find_pdfs(tmp_path / "09. Melody", song)
        assert len(found) == 2
