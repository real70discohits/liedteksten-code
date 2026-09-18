#!/usr/bin/env python3
"""
lt-checkdrive.py — Controleer of PDF's verouderd zijn t.o.v. de .tex bronbestanden.

Twee modi:
- Drive-check (default): vergelijkt .tex mtime met PDF's in de lokale
  Proton Drive sync-map (_Liedjes).
- Lokale check (--local-only): vergelijkt .tex mtime met bestaande PDF's in
  de distributie folder (_dist). Alleen bestaande PDF's worden gecontroleerd;
  ontbrekende PDF's of wezen zijn daar niet relevant.

Het script is uitsluitend rapporterend: er wordt niks gewijzigd.

Usage:
    python lt-checkdrive.py
    python lt-checkdrive.py "Melody (9)"
    python lt-checkdrive.py --local-only
    python lt-checkdrive.py --list-wezen
    python lt-checkdrive.py --verbose
"""

import argparse
import re
import sys
from pathlib import Path
from console_utf8 import enable_utf8_console
from pathconfig import load_and_resolve_paths, validate_folder_exists

# Sync-delay tussen Drive en lokale map, plus klokafwijkingen, opvangen:
# verschillen kleiner dan dit venster gelden als actueel.
SYNC_TOLERANCE_SECONDS = 4*24*60*60         # 24x60x60 is 1 day. Ik zet m op 4 dagen omdat een voorkomende tijdspanne is tussen een push en een pull op een ander device.

_DRIVE_FOLDER_RE = re.compile(r'^(\d{2,})\.\s+(.+)$')


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


def drive_song_folder(pdrive_folder: Path, songtitle: str):
    """Bouw de verwachte Drive-foldernaam: '09. Melody'."""
    name, sid = parse_songtitle(songtitle)
    if name is None:
        return None
    return pdrive_folder / f"{sid:02d}. {name}"


def pdf_matches_song(pdf_stem: str, songtitle: str) -> bool:
    """Prefix-match: exact gelijk, of gevolgd door ' ' (variant) of ' -' (LargePrint)."""
    if pdf_stem == songtitle:
        return True
    return (pdf_stem.startswith(songtitle + ' ')
            or pdf_stem.startswith(songtitle + ' -'))


def is_stale(pdf_path: Path, tex_mtime: float) -> bool:
    return pdf_path.stat().st_mtime < tex_mtime - SYNC_TOLERANCE_SECONDS


def find_pdfs(folder: Path, songtitle: str) -> list[Path]:
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
    import datetime
    return datetime.datetime.fromtimestamp(
        path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')


def run_drive_check(songs: list[str], paths, args) -> int:
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
        pdfs = find_pdfs(drive_song_folder(pdrive, song), song)
        status, stale = check_song(pdfs, tex_mtime)
        counts[status] += 1

        if status == 'VEROUDERD':
            print(f"❌ VEROUDERD  {song}  — {len(stale)}/{len(pdfs)} PDF's ouder "
                  f"dan .tex ({_fmt_mtime(tex)})")
            for p in stale:
                print(f"      └─ {p.relative_to(pdrive)}  ({_fmt_mtime(p)})")
        elif status == 'ONTBREEKT':
            print(f"⚠️  ONTBREEKT  {song}  — geen PDF's gevonden op Drive")
        elif args.verbose:
            print(f"✅ ACTUEEL    {song}  — {len(pdfs)}/{len(pdfs)} varianten actueel")

    # Wezen: Drive-folders zonder bijbehorend .tex (alleen op verzoek tonen)
    if args.list_wezen:
        repo_ids = {f"{parse_songtitle(s)[1]:02d}" for s in songs
                    if parse_songtitle(s)[1] is not None}
        print()
        for sub in sorted(pdrive.iterdir()):
            if not sub.is_dir():
                continue
            m = _DRIVE_FOLDER_RE.match(sub.name)
            if not m:
                continue
            if m.group(1) not in repo_ids:
                print(f"🔍 WEES        {sub.name}  — geen .tex in repo")

    print("=" * 60)
    print(f"Samenvatting: {counts['ACTUEEL']} actueel, "
          f"{counts['VEROUDERD']} verouderd, {counts['ONTBREEKT']} ontbreekt")
    return 1 if (counts['VEROUDERD'] or counts['ONTBREEKT']) else 0


def run_local_check(songs: list[str], paths, args) -> int:
    """Lokale _dist-check: alleen melden wat er IS, en verouderd blijkt.

    De _dist folder wordt regelmatig geleegd, dus ontbrekende PDF's zijn normaal
    en worden niet gemeld. Wezen zijn eveneens niet relevant.
    """
    print(f"Lokale check: {len(songs)} lied(er) — {paths.distributie_folder}")
    print("=" * 60)

    stale_total = 0
    for song in songs:
        tex = paths.input_folder / song / f"{song}.tex"
        tex_mtime = tex.stat().st_mtime
        pdfs = find_pdfs(paths.distributie_folder, song)  # bestáánde PDF's
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
        description='Controleer PDF-versheid t.o.v. .tex bronbestanden '
                    '(Proton Drive en/of lokale _dist folder)')
    parser.add_argument('songtitles', nargs='*',
                        help='Liedtitels om te checken (default: alle)')
    parser.add_argument('--local-only', action='store_true',
                        help='Controleer alleen de lokale _dist folder i.p.v. Drive')
    parser.add_argument('--list-wezen', action='store_true',
                        help='Toon Drive-folders zonder bijbehorend .tex')
    parser.add_argument('--verbose', action='store_true',
                        help='Toon ook actuele liederen')
    args = parser.parse_args()

    songtitle = args.songtitles[0] if len(args.songtitles) == 1 else ""
    paths = load_and_resolve_paths(songtitle)

    songs = args.songtitles or discover_songs(paths.input_folder)
    if not songs:
        print("❌ Error: geen liederen gevonden (check input_folder)")
        return 2

    if args.local_only:
        sys.exit(run_local_check(songs, paths, args))
    sys.exit(run_drive_check(songs, paths, args))


if __name__ == '__main__':
    main()
    