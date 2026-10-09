#!/usr/bin/env python3
"""
lt-checkdrive.py — Controleer of PDF's verouderd zijn t.o.v. de .tex bronbestanden.

Twee modi:
- Drive-check (default): vergelijkt .tex mtime met PDF's in de lokale
  Proton Drive sync-map (_Liedjes).
- Lokale check (--local-only): vergelijkt .tex mtime met bestaande PDF's in
  de distributie folder (_dist). Alleen bestaande PDF's worden gecontroleerd;
  ontbrekende PDF's of wezen zijn daar niet relevant.

Song mapping: liedtitels in de repo zijn mogelijk gesaneerd t.b.v. automatisering
(bv. "Shes such a beauty"), terwijl de foldernamen op Proton Drive de originele
schrijfwijze gebruiken (bv. "She's such a beauty"). Via 'song_mapping_file' in
paths.jsonc kan een extern bestand (buiten de repo!) met de mapping
lokale titel -> Drive-titel worden opgegeven.

Het script is uitsluitend rapporterend: er wordt niks gewijzigd.

Usage:
    python lt-checkdrive.py
    python lt-checkdrive.py "Melody (9)"
    python lt-checkdrive.py --local-only
    python lt-checkdrive.py --list-wezen
    python lt-checkdrive.py --verbose
"""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from console_utf8 import enable_utf8_console
from pathconfig import load_and_resolve_paths, validate_folder_exists, load_jsonc

# Sync-delay tussen Drive en lokale map, plus klokafwijkingen, opvangen:
# verschillen kleiner dan dit venster gelden als actueel.
SYNC_TOLERANCE_SECONDS = 4*24*60*60         # 24x60x60 is 1 day. Ik zet m op 4 dagen omdat een voorkomende tijdspanne is tussen een push en een pull op een ander device.

_DRIVE_FOLDER_RE = re.compile(r'^(\d{2,})\.\s+(.+)$')


# ---------------------------------------------------------------------------
# Song mapping (lokale titel -> Drive titel)
# ---------------------------------------------------------------------------

def load_song_mapping(mapping_file: Path | None) -> dict[str, str]:
    """Laadt de mapping van lokale liedtitel -> originele Drive-liedtitel.

    Het bestand is optioneel en bevindt zich buiten de repository (via
    'song_mapping_file' in paths.jsonc). Formaat:

        {
            "Shes such a beauty (6)": "She's such a beauty (6)",
            "Girls cant get enough (49)": "Girls can't get enough (49)"
        }

    - Niet geconfigureerd (None)  -> lege mapping, geen melding (het is immers
        optioneel; de meeste liederen hebben geen afwijkende Drive-naam).
    - Wél geconfigureerd maar het bestand ontbreekt of is corrupt -> waarschuwing,
        want zonder mapping rapporteert de Drive-check gemapte liederen als ONTBREEKT.
        De run wordt niet afgebroken.

    Returns:
        dict: mapping (mogelijk leeg).
    """
    if not mapping_file:
        return {}

    if not mapping_file.is_file():
        print(f"⚠️ Waarschuwing: 'song_mapping_file' is geconfigureerd maar niet "
            f"gevonden: {mapping_file}")
        print("   Zonder mapping kunnen liederen met aangepaste titels als "
            "ONTBREEKT gerapporteerd worden.")
        return {}

    try:
        mapping = load_jsonc(mapping_file)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        print(f"⚠️ Waarschuwing: kon song mapping niet laden ({e}): {mapping_file}")
        return {}

    if not isinstance(mapping, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
        print(f"⚠️ Waarschuwing: song mapping moet een JSON-object met "
            f"string->string waarden zijn: {mapping_file}")
        return {}

    return mapping


def parse_songtitle(songtitle: str):
    """Splitst 'Melody (9)' in ('Melody', 9). Return (None, None) bij geen match."""
    m = re.match(r'^(.*?)\s*\((\d+)\)\s*$', songtitle.strip())
    if not m:
        return None, None
    return m.group(1).strip(), int(m.group(2))


def discover_songs(input_folder: Path) -> list[str]:
    """Vind alle liedmappen in de input folder (map met <mapnaam>.tex erin)."""
    songs = []
    for folder in input_folder.iterdir():
        if folder.is_dir() and (folder / f"{folder.name}.tex").exists():
            songs.append(folder.name)
    return sorted(songs)


def expected_drive_folder_name(song_mapping: dict[str, str], songtitle: str):
    """Bouw de verwachte Drive-foldernaam, bv. "06. She's such a beauty".

    Past eerst de song mapping toe (lokale titel -> originele titel).
    Return None als de titel niet te parsen is.
    """
    drive_title = song_mapping.get(songtitle, songtitle)
    name, sid = parse_songtitle(drive_title)
    if name is None:
        return None
    return f"{sid:02d}. {name}"


def drive_song_folder(pdrive_folder: Path, song_mapping: dict[str, str],
                      songtitle: str):
    """Bouw het verwachte Drive-folderpad, met mapping toegepast op de titel."""
    folder_name = expected_drive_folder_name(song_mapping, songtitle)
    if folder_name is None:
        return None
    return pdrive_folder / folder_name


def pdf_matches_song(pdf_stem: str, songtitle: str) -> bool:
    """Prefix-match: exact gelijk, of gevolgd door ' ' (variant) of ' -' (LargePrint).

    Let op: *songtitle* moet hier de titel zijn waaronder de PDF's zijn
    opgeslagen — voor de Drive-check is dat de GEMAPTE (originele) titel,
    voor de lokale _dist-check de lokale titel.
    """
    if pdf_stem == songtitle:
        return True
    return (pdf_stem.startswith(songtitle + ' ')
            or pdf_stem.startswith(songtitle + ' -'))


def is_stale(pdf_path: Path, tex_mtime: float) -> bool:
    return pdf_path.stat().st_mtime < tex_mtime - SYNC_TOLERANCE_SECONDS


def find_pdfs(folder: Path | None, songtitle: str) -> list[Path]:
    """Vind alle bij het lied horende PDF's, recursief (Standard/, Large Print/, ...)."""
    if not folder or not folder.is_dir():
        return []
    return sorted(p for p in folder.rglob('*.pdf')
                  if pdf_matches_song(p.stem, songtitle))


def check_song(pdf_paths: list[Path], tex_mtime: float):
    """Classificeer één lied. Return ('status', [verouderde pdf's])."""
    if not pdf_paths:
        return 'ONTBREEKT', []
    stale = [p for p in pdf_paths if is_stale(p, tex_mtime)]
    if stale:
        return 'VEROUDERD', stale
    return 'ACTUEEL', []


def _fmt_mtime(path: Path) -> str:
    return datetime.datetime.fromtimestamp(
        path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')


def run_drive_check(songs: list[str], paths, song_mapping: dict[str, str],
                    args) -> int:
    if not paths.pdrive_folder:
        print("❌ Error: 'pdrive_folder' is niet geconfigureerd in paths.jsonc.")
        return 2
    pdrive = paths.pdrive_folder
    if not validate_folder_exists(pdrive, "Proton Drive sync-map (pdrive_folder)"):
        print("   Draait de Proton Drive client? Is de juiste map gekozen?")
        return 2

    print(f"Drive-check: {len(songs)} lied(er) — {pdrive}")
    print("=" * 60)

    counts = {'ACTUEEL': 0, 'VEROUDERD': 0, 'ONTBREEKT': 0}

    for song in songs:
        tex = paths.input_folder / song / f"{song}.tex"
        tex_mtime = tex.stat().st_mtime

        # Drive-titel: mapping toegepast (identiek aan de lokale titel zonder mapping)
        drive_title = song_mapping.get(song, song)

        pdfs = find_pdfs(drive_song_folder(pdrive, song_mapping, song), drive_title)
        status, stale = check_song(pdfs, tex_mtime)
        counts[status] += 1

        if status == 'VEROUDERD':
            print(f"❌ VEROUDERD  {song}  — {len(stale)}/{len(pdfs)} PDF's ouder "
                  f"dan .tex ({_fmt_mtime(tex)})")
            for p in stale:
                print(f"      └─ {p.relative_to(pdrive)}  ({_fmt_mtime(p)})")
        elif status == 'ONTBREEKT':
            extra = f"  (Drive-titel: '{drive_title}')" if song in song_mapping else ""
            print(f"⚠️  ONTBREEKT  {song}  — geen PDF's gevonden op Drive{extra}")
        elif args.verbose:
            print(f"✅ ACTUEEL    {song}  — {len(pdfs)}/{len(pdfs)} varianten actueel")

    # Wezen / naamafwijkingen: Drive-folders zonder matchend .tex in de repo
    if args.list_wezen:
        expected = {}
        for s in songs:
            folder_name = expected_drive_folder_name(song_mapping, s)
            if folder_name is not None:
                # Sleutel op id-string zoals in de Drive-mapnaam (zonder voorloop-nul)
                sid = parse_songtitle(folder_name)[1]
                expected[f"{sid:g}"] = folder_name

        print()
        for sub in sorted(pdrive.iterdir()):
            if not sub.is_dir():
                continue
            m = _DRIVE_FOLDER_RE.match(sub.name)
            if not m:
                continue
            if m.group(1) in expected:
                if sub.name != expected[m.group(1)]:
                    print(f"🔍 NAAMAFWIJKING {sub.name}  — verwacht '{expected[m.group(1)]}' "
                          f"(check song mapping of Drive-mapnaam)")
            else:
                print(f"🔍 WEES        {sub.name}  — geen .tex in repo")

    print("=" * 60)
    print(f"Samenvatting: {counts['ACTUEEL']} actueel, "
          f"{counts['VEROUDERD']} verouderd, {counts['ONTBREEKT']} ontbreekt")
    return 1 if (counts['VEROUDERD'] or counts['ONTBREEKT']) else 0


def run_local_check(songs: list[str], paths, args) -> int:
    """Lokale _dist-check: alleen melden wat er IS, en verouderd blijkt.

    De _dist folder wordt regelmatig geleegd, dus ontbrekende PDF's zijn normaal
    en worden niet gemeld. Wezen zijn eveneens niet relevant. PDF's in _dist
    dragen de (gesaneerde) lokale titel, dus hier wordt GEEN mapping toegepast.
    """
    print(f"Lokale check: {len(songs)} lied(er) — {paths.distributie_folder}")
    print("=" * 60)

    stale_total = 0
    for song in songs:
        tex = paths.input_folder / song / f"{song}.tex"
        tex_mtime = tex.stat().st_mtime
        pdfs = find_pdfs(paths.distributie_folder, song)  # bestáánde PDF's, lokale titel
        if not pdfs:
            continue
        stale = [p for p in pdfs if is_stale(p, tex_mtime)]
        if stale:
            stale_total += len(stale)
            print(f"❌ VEROUDERD  {song}  — {len(stale)}/{len(pdfs)} PDF's in _dist "
                  f"ouder dan .tex ({_fmt_mtime(tex)})")
            for p in stale:
                print(f"      └─ {p.name}  ({_fmt_mtime(p)})")
        elif args.verbose:
            print(f"✅ ACTUEEL    {song}  — {len(pdfs)} bestaande PDF's actueel")

    print("=" * 60)
    if stale_total:
        print(f"Samenvatting: {stale_total} verouderde PDF('s) in _dist")
        return 1
    print("Samenvatting: alle bestaande PDF's in _dist zijn actueel")
    return 0


def main():
    enable_utf8_console()
    parser = argparse.ArgumentParser(
        description='Controleer op outdated PDF\'s t.o.v. .tex bronbestanden '
                    '(Proton Drive en/of lokale _dist folder). Mappings worden '
                    'gelezen uit song_mappings.jsonc.')
    parser.add_argument('songtitles', nargs='*',
                        help='Liedtitels om te checken (default: alle; lokale '
                            'titel zoals in de repo)')
    parser.add_argument('--local-only', action='store_true',
                        help='Controleer alleen de lokale _dist folder i.p.v. Drive')
    parser.add_argument('--list-wezen', action='store_true',
                        help='Toon Drive-folders zonder bijbehorend .tex')
    parser.add_argument('--verbose', action='store_true',
                        help='Toon ook actuele liederen')
    args = parser.parse_args()

    songtitle = args.songtitles[0] if len(args.songtitles) == 1 else ""
    paths = load_and_resolve_paths(songtitle)

    # Song mapping laden vóór alle checks (uitbestand buiten de repo,
    # geadresseerd via 'song_mapping_file' in paths.jsonc).
    song_mapping = load_song_mapping(paths.song_mapping_file)

    songs = args.songtitles or discover_songs(paths.input_folder)
    if not songs:
        print("❌ Error: geen liederen gevonden (check input_folder)")
        sys.exit(2)

    if args.local_only:
        # Lokale check: geen mapping nodig, maar wél even melden wat er geladen is.
        if song_mapping:
            print(f"ℹ️ Song mapping genegeerd (lokale check): "
                  f"{len(song_mapping)} titel(s) in {paths.song_mapping_file}\n")
        sys.exit(run_local_check(songs, paths, args))

    # Bij de Drive-check expliciet maken dat er gemapt wordt (voorkomt
    # stille ONTBREEKT-meldingen door een vergeten mapping-bestand).
    if paths.song_mapping_file:
        print(f"ℹ️ Song mapping geladen: {len(song_mapping)} titel(s) — "
              f"{paths.song_mapping_file}\n")
    sys.exit(run_drive_check(songs, paths, song_mapping, args))


if __name__ == '__main__':
    main()