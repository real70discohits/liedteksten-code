# DRIVE-CHECK — Check for outdated PDF's on Proton Drive

## Doel

Na het wijzigen van een .tex bronbestand kan onduidelijk zijn of de PDF's die
op Proton Drive staan nog actueel zijn. `lt-checkdrive.py` vergelijkt per lied
de laatste wijzigingsdatum van de .tex met die van de PDF's op Drive en
rapporteert wat verouderd of ontbreekt. Het script wijzigt niets.

## Prerequisites

- **Proton Drive desktop client** geïnstalleerd, aangemeld én draaiend.
- De `_Liedjes`-folder is gesynchroniseerd als lokale map (zichtbaar in de
  Explorer/Finder).
- Aanbevolen: markeer `_Liedjes` als **"Always available on this device"**
  in de Drive-app (PDF's zijn klein; dit voorkomt afhankelijkheid van
  placeholder-metadata). Zonder deze instelling werkt de check óók: online-only
  bestanden verschijnen als placeholders waarvan de metadata (naam, mtime)
  lokaal beschikbaar is; de check downloadt geen bestandsinhoud.
- `pdrive_folder` geconfigureerd in `paths.jsonc` (verwijst naar de
  `_Liedjes`-folder).
- Internetverbinding is niet nodig voor de check zelf.

## Gebruik

python lt-checkdrive.py                     # alle liederen, Drive-check
python lt-checkdrive.py "Melody (9)"        # één lied
python lt-checkdrive.py --local-only        # alleen lokale _dist folder
python lt-checkdrive.py --list-wezen        # Drive-folders zonder .tex
python lt-checkdrive.py --verbose           # ook actuele liederen tonen

## Matching en naamconventies

- Lokaal bronbestand: `<input_folder>/<titel> (<id>)/<titel> (<id>).tex`
- Drive-map per lied: `_Liedjes/<id met voorloop-nul t/m 2 cijfers>. <naam>/`,
  met daarin submappen als `Standard/` en `Large Print/` (recursief gescand).
- Een PDF hoort bij een lied als de bestandsnaam exact gelijk is aan de
  liedtitel, of begint met de liedtitel + spatie (varianten: "met maatnummers",
  "met akkoorden", transposities als "in D transp(+2)") of + " -" (LargePrint).
- Verschillen kleiner dan 2 minuten (SYNC_TOLERANCE_SECONDS) gelden als actueel.

## Song mapping (afwijkende Drive-titels)

Liedtitels in de repo zijn mogelijk gesaneerd t.b.v. automatisering
(apostroffen e.d. verwijderd, bv. "Shes such a beauty"), terwijl de
foldernamen op Proton Drive de originele schrijfwijze gebruiken
("She's such a beauty"). Voor zulke liederen werkt de Drive-check met
een mapping-bestand.

- Locatie: root van de liedjesrepo (naast paths.jsonc), pad geconfigureerd
  via `"song_mapping_file"` in paths.jsonc.
- Formaat: JSON-object `{"<lokale titel (id)>": "<Drive-titel (id)>"}` —
  zie het voorbeeldbestand song_mapping.jsonc.
- Werking: de mapping wordt vóór het parsen op de volledige liedtitel
  (inclusief id) toegepast, zowel voor de Drive-mapnaam als voor het
  matchen van PDF-bestandsnamen. Liederen zonder entry gebruiken de
  lokale titel ongewijzigd.
- Alleen de Drive-check gebruikt de mapping; bij `--local-only` worden
  PDF's altijd gematcht op de lokale (gesaneerde) titel.
- Bij het starten print de Drive-check hoeveel titels er gemapt zijn,
  zodat een ontbrekend of corrupt mapping-bestand direct opvalt
  (gemapte liederen zouden anders als ONTBREEKT gerapporteerd worden).
- Zie ook --list-wezen: een Drive-map met een bekende id maar een
  afwijkende naam wordt gemeld als NAAMAFWIJKING (controleer de mapping
  of een handmatige hernoeming op Drive).

## Statussen

- **ACTUEEL** — alle gevonden Drive-PDF's zijn niet ouder dan de .tex.
- **VEROUDERD** — minstens één PDF is ouder dan de .tex. Oplossing:
  `python lt-generate.py "<lied>"` en de nieuwe PDF's uploaden.
- **ONTBREEKT** — geen PDF's voor dit lied op Drive. Oplossing: genereren
  en uploaden (of slepen naar de browser/drive-map).
- **WEES** (alleen met --list-wezen) — Drive-folder zonder bijbehorend .tex.

## Exit codes (voor eventuele automatisering)

0 = alles actueel · 1 = verouderd/ontbreekt · 2 = configuratie-/mapfout

## Lokale check (--local-only)

De _dist folder wordt regelmatig geleegd: ontbrekende PDF's zijn normaal en
worden niet gemeld. De check meldt uitsluitend PDF's die bestaan én verouderd
zijn ten opzichte van de .tex.

## Bekende beperkingen

- Online-only placeholders: mtime-check werkt, maar een bestand dat vanaf een
  ander apparaat is gewijzigd is pas zichtbaar zodra de client gesynchroniseerd
  heeft. Draai de check dus bij voorkeur als de client 'Synced' toont.
- De Drive-mapnaam wordt afgeleid van lied-id + naam zoals in de repo; hernoem
  je een map handmatig op Drive, dan wordt het lied 'ONTBREEKT'/'WEES'.
- Handmatig hernoemde Drive-folders: controleer eerst of de song mapping
  (song_mapping.jsonc) de juiste titel bevat; is dat in orde, dan is de
  map wellicht handmatig op Drive hernoemd en meldt --list-wezen dit als
  NAAMAFWIJKING.
