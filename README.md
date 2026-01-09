# Liedteksten Toolkit

Dit is een Python-gebaseerde toolkit voor het beheren en genereren van bestanden gerelateerd aan popliedjes zoals liedteksten, liedteksten met gitaartabs en akkoorden, maar ook hulpbestanden die teksten koppelen aan maten en structuurbestanden die lied-statistieken en -compositie tonen.

## Inhoudsopgave

- [Liedteksten Toolkit](#liedteksten-toolkit)
  - [Inhoudsopgave](#inhoudsopgave)
  - [Overzicht Scripts](#overzicht-scripts)
  - [Workflow](#workflow)
  - [Opslaglocaties](#opslaglocaties)
  - [Gedetailleerde Commando Referentie](#gedetailleerde-commando-referentie)
    - [nwc-concat.py](#nwc-concatpy)
      - [Syntax](#syntax)
      - [Positionele Parameters](#positionele-parameters)
      - [Optionele Parameters](#optionele-parameters)
      - [Voorbeelden](#voorbeelden)
      - [Gegenereerde Bestanden](#gegenereerde-bestanden)
      - [Vereisten](#vereisten)
    - [lt-generate.py](#lt-generatepy)
      - [Syntax](#syntax-1)
      - [Positionele Parameters](#positionele-parameters-1)
      - [Optionele Parameters](#optionele-parameters-1)
      - [Varianten](#varianten)
      - [Voorbeelden](#voorbeelden-1)
      - [Transpositie](#transpositie)
      - [Gegenereerde Bestanden](#gegenereerde-bestanden-1)
      - [Configuratie Systeem](#configuratie-systeem)
      - [Vereisten](#vereisten-1)
    - [nwc-convert.py](#nwc-convertpy)
      - [Syntax](#syntax-2)
      - [Positionele Parameters](#positionele-parameters-2)
      - [Optionele Parameters](#optionele-parameters-2)
      - [Voorbeelden](#voorbeelden-2)
      - [Conversie Pipeline](#conversie-pipeline)
      - [Gegenereerde Bestanden](#gegenereerde-bestanden-2)
      - [Vereisten](#vereisten-2)
      - [Soundfonts](#soundfonts)
    - [nwc\_analyze.py](#nwc_analyzepy)
      - [Syntax](#syntax-3)
      - [Positionele Parameters](#positionele-parameters-3)
      - [Voorbeelden](#voorbeelden-3)
      - [Gegenereerd Bestand](#gegenereerd-bestand)
      - [Maatsoort en Tempo](#maatsoort-en-tempo)
      - [Speciale Concepten](#speciale-concepten)
  - [Veelvoorkomende Workflows](#veelvoorkomende-workflows)
    - [Nieuw Lied Toevoegen](#nieuw-lied-toevoegen)
    - [Tempo Aanpassen](#tempo-aanpassen)
    - [Liedtekst Wijzigen](#liedtekst-wijzigen)
    - [Alleen Geconfigureerde Varianten Genereren](#alleen-geconfigureerde-varianten-genereren)
    - [Debug LaTeX Compilatie Problemen](#debug-latex-compilatie-problemen)
    - [Alleen Structuur PDF Genereren](#alleen-structuur-pdf-genereren)
    - [Transpositie Toevoegen](#transpositie-toevoegen)
  - [Configuratie](#configuratie)
  - [Afhankelijkheden](#afhankelijkheden)
    - [Python Modules](#python-modules)
    - [Externe Tools](#externe-tools)
  - [Projectstructuur](#projectstructuur)



## Overzicht Scripts

| Script | Doel |
|--------|------|
| **nwc-concat.py** | Voegt NoteWorthy Composer (NWC) sectiebestanden samen tot één compleet bestand en genereert structuurinformatie, analyse en label tracks voor Audacity/Tenacity |
| **lt-generate.py** | Genereert PDF's van liedteksten in verschillende varianten (met/zonder akkoorden, maatnummers, tabs) vanuit LaTeX bronbestanden |
| **nwc-convert.py** | Converteert NWC bestanden naar audioformaten (NWCTXT → MIDI → WAV → FLAC) voor demo's |
| **nwc_analyze.py** | Analyseert NWC bestanden en koppelt liedteksten aan maatnummers |

## Workflow

Het complete proces voor het maken/updaten van een lied (zie ook `project/schema.pu` voor visuele weergave):

1. **Muzieknotatie maken** (Handmatig)
   - Gebruik NoteWorthy Composer GUI om .nwctxt bestanden te maken per liedsectie (intro, vers, refrein, etc.)
   - Bewaar in git repository: `<input_folder>/<Liedtitel>/nwc/`
   - Maak `volgorde.jsonc` om de volgorde van secties te definiëren

2. **nwc-concat.py uitvoeren**
   - Maakt samengevoegd .nwctxt bestand → **build folder**
   - Maakt analysis.txt (teksten gekoppeld aan maten) → **build folder**
   - Maakt structuur.tex (liedstructuur/statistieken) → **build folder**
   - Update tempo en maatsoort in liedtekst .tex → **git repository**
   - Maakt labeltrack.txt (voor Tenacity/Audacity) → **audio_output_folder**

3. **nwc-convert.py uitvoeren** (optioneel, voor audio demo's)
   - Roept nwc-conv.exe aan: .nwctxt → .mid → **audio_output_folder**
   - Roept fluidsynth.exe aan: .mid → .wav → **audio_output_folder**
   - Roept ffmpeg.exe aan: .wav → .flac → **audio_output_folder**

4. **Liedtekst maken/updaten** (Handmatig)
   - Maak of update liedtekst .tex bestand in git repository
   - Gebruik analysis.txt (uit build folder) als referentie voor maatnummers en structuur

5. **lt-generate.py uitvoeren**
   - Rendert liedtekst PDF's (alle varianten) → **distributie folder**
   - Rendert structuur.pdf → **distributie folder**

6. **lt-upload.ps1 uitvoeren** (optioneel)
   - Upload gegenereerde PDF's van dist folder naar PDrive (cloud opslag)

7. **Audio-opname maken** (Handmatig)
   - Importeer .flac bestand in Tenacity (van audio_output_folder)
   - Importeer labeltrack.txt in Tenacity (van audio_output_folder)
   - Maak opname met correct gelabelde secties

## Opslaglocaties

- **git repository** (`input_folder`): Bronbestanden (.tex, .nwctxt, volgorde.jsonc, lt-config.jsonc)
- **build folder** (`build_folder`): Tussenbestanden (samengevoegd .nwctxt, analysis.txt, structuur.tex)
- **distributie folder** (`distributie_folder`): Definitieve PDF's klaar voor distributie
- **audio_output_folder**: Audiobestanden (.mid, .wav, .flac) en labeltrack.txt voor Tenacity
- **PDrive**: Cloud backup van gegenereerde PDF's (via lt-upload.ps1)

---

## Gedetailleerde Commando Referentie

### nwc-concat.py

Voegt individuele NoteWorthy Composer sectiebestanden samen tot één compleet liedbestand en genereert aanvullende bestanden zoals structuurinformatie en label tracks.

#### Syntax

```bash
python nwc-concat.py <liedtitel> [opties]
```

#### Positionele Parameters

| Parameter | Beschrijving |
|-----------|--------------|
| `liedtitel` | Titel van het lied (verplicht). Dit moet overeenkomen met de mapnaam in de input folder |

#### Optionele Parameters

| Parameter | Waarden | Standaard | Beschrijving |
|-----------|---------|-----------|--------------|
| `--keep-tempi` | (vlag) | Uit | Behoud tempo-indicaties in alle lieddelen. Standaard worden tempo-markeringen uit lieddelen na het eerste verwijderd, omdat alleen het eerste liedsectie het tempo bepaalt |

#### Voorbeelden

```bash
# Basis gebruik: voeg secties van "Vader Jacob" samen
python nwc-concat.py "Vader Jacob"

# Behoud alle tempo-markeringen in alle secties
python nwc-concat.py "Vader Jacob" --keep-tempi

# Lied met spaties in de naam
python nwc-concat.py "Boer wat zeg je van mijn kippen"
```

#### Gegenereerde Bestanden

Dit script genereert de volgende bestanden:

1. **`<liedtitel>.nwctxt`** → build folder
   - Samengevoegd NWC bestand met alle secties

2. **`<liedtitel> analysis.txt`** → build folder
   - Tekstbestand met liedteksten gekoppeld aan maatnummers
   - Bevat metadata zoals totaal aantal maten, tempo, maatsoort

3. **`<liedtitel> structuur.tex`** → build folder
   - LaTeX bestand met liedstructuur, statistieken en compositie-overzicht

4. **`<liedtitel> labeltrack t_<tempo>.txt`** → audio_output_folder/`<liedtitel>`/
   - Label track voor Audacity/Tenacity met tijdstempels voor secties
   - Bevat zowel liedsectie-labels als LBLTRCK markers uit het NWC bestand

5. **Update van `<liedtitel>.tex`** → git repository (input folder)
   - Update tempo en maatsoort in het hoofdliedtekst .tex bestand

#### Vereisten

- NWC subfolder in liedmap met individuele sectiebestanden
- `volgorde.jsonc` bestand dat de volgorde van secties definieert
- Bass staff (notenbalk) in NWC bestanden (voor tempo, maatsoort, akkoorden)
- Ritme staff in NWC bestanden (voor maataantallen)
- Zang staff in NWC bestanden (voor liedteksten mapping naar maatnummers)
- Volgorde van staffs is vrij, maar moet gelijk zijn in alle sectiebestanden.

---

### lt-generate.py

Genereert PDF's van liedteksten in verschillende varianten vanuit LaTeX (.tex) bronbestanden. Kan verschillende combinaties genereren van tekst, maatnummers, akkoorden en gitaartabs.

#### Syntax

```bash
python lt-generate.py [liedtitels...] [opties]
```

#### Positionele Parameters

| Parameter | Beschrijving |
|-----------|--------------|
| `liedtitels` | Een of meer liedtitels (optioneel). Als niet opgegeven, worden alle liedteksten in de input folder verwerkt |

#### Optionele Parameters

| Parameter | Waarden | Standaard | Beschrijving |
|-----------|---------|-----------|--------------|
| `--no-cleanup` | (vlag) | Uit | Behoud hulpbestanden (.aux, .log, .out, .toc) na compilatie. Handig voor debugging LaTeX fouten |
| `--no-structuur` | (vlag) | Uit | Sla het genereren van structuur PDF's over. Handig tijdens ontwikkeling als je alleen liedtekst PDF's wilt |
| `--debug` | (vlag) | Uit | Toon pdflatex output op het scherm (zet capture_output=False). Handig voor het debuggen van LaTeX compilatiefouten |
| `--engine` | `pdflatex`, `xelatex`, `lualatex` | `pdflatex` | Specificeer welke TeX engine te gebruiken voor compilatie |
| `--tab-orientation` | `left`, `right`, `traditional` | `left` | Oriëntatie van gitaartabs. Bepaalt hoe de snaren worden weergegeven |
| `-n`, `--only` | `-1`, `0`, `1`, `2`, `3`, `4`, `5` | `0` | Genereer alleen specifieke variant(en). Zie variant tabel hieronder |

#### Varianten

Het `--only` parameter bepaalt welke variant(en) worden gegenereerd:

| Waarde | Betekenis | Variant(en) |
|--------|-----------|-------------|
| `0` | Alles (standaard) | Genereer alle 5 varianten |
| `-1` | Alleen geconfigureerde | Genereer alleen varianten waarvoor een configuratie bestaat in lt-config.jsonc |
| `1` | Basis tekst | Alleen liedtekst zonder extra's |
| `2` | Tekst + maatnummers | Liedtekst met maatnummers in de kantlijn |
| `3` | Tekst + akkoorden | Liedtekst met akkoorden boven de tekst |
| `4` | Tekst + maatnummers + akkoorden | Liedtekst met maatnummers en akkoorden |
| `5` | Volledig | Liedtekst met maatnummers, akkoorden én gitaartabs |

#### Voorbeelden

```bash
# Genereer alle varianten voor alle liedjes
python lt-generate.py

# Genereer alle varianten voor één lied
python lt-generate.py "Vader Jacob"

# Genereer alle varianten voor meerdere liedjes
python lt-generate.py "Vader Jacob" "Alle eendjes"

# Genereer alleen variant met akkoorden (variant 3)
python lt-generate.py "Vader Jacob" --only 3

# Genereer alleen geconfigureerde varianten
python lt-generate.py "Vader Jacob" --only -1

# Genereer met rechtse tab-oriëntatie en behoud hulpbestanden
python lt-generate.py "Vader Jacob" --tab-orientation right --no-cleanup

# Genereer zonder structuur PDF en toon debug output
python lt-generate.py "Vader Jacob" --no-structuur --debug

# Genereer alleen liedtekst (variant 1) en maatnummers (variant 2)
python lt-generate.py "Vader Jacob" --only 1
python lt-generate.py "Vader Jacob" --only 2
```

#### Transpositie

Als een .tex bestand een `\transpositions` commando bevat, worden automatisch extra versies gegenereerd:

```latex
\newcommand{\transpositions}{2, 3}  % Genereer ook versies +2 en +3 halve tonen
```

Dit resulteert in:
- `Vader Jacob (1).pdf` (origineel in C)
- `Vader Jacob (1) in D transp(+2).pdf` (2 halve tonen hoger)
- `Vader Jacob (1) in Es transp(+3).pdf` (3 halve tonen hoger)

#### Gegenereerde Bestanden

Voor elk lied worden de volgende PDF's gegenereerd (afhankelijk van `--only` waarde):

**Liedtekst PDF's** → distributie folder
- `<titel> (<id>).pdf` - basis liedtekst
- `<titel> (<id>) met maatnummers.pdf`
- `<titel> (<id>) met akkoorden.pdf`
- `<titel> (<id>) met maatnummers en akkoorden.pdf`
- `<titel> (<id>) met maatnummers, akkoorden en gitaargrepen.pdf`

**Structuur PDF** → distributie folder (tenzij `--no-structuur`)
- `<titel> structuur.pdf` - liedstructuur, statistieken en compositie-overzicht

#### Configuratie Systeem

Per lied kan een `lt-config.jsonc` bestand worden gemaakt met layout-aanpassingen:

```jsonc
{
  "configurations": [
    {
      "condition": {
        "songId": 1,
        "showMeasures": true,
        "showChords": true,
        "showTabs": null  // null = match elke waarde
      },
      "action": {
        "adjustMargins": "1.5cm",
        "adjustFontsize": "10pt"
      },
      "description": "Compacte layout voor Vader Jacob met akkoorden"
    }
  ]
}
```

#### Vereisten

- pdflatex (of andere TeX engine) moet geïnstalleerd zijn en in PATH
- .tex bestanden moeten de volgende commando's bevatten:
  - `\newcommand{\liedTitel}{...}`
  - `\newcommand{\liedId}{...}`
  - `\newcommand{\sleutel}{...}` (voor transpositie)

---

### nwc-convert.py

Converteert NoteWorthy Composer (.nwctxt) bestanden naar FLAC audioformaat via een pipeline van MIDI en WAV. Handig voor het maken van audio demo's.

#### Syntax

```bash
python nwc-convert.py <input> [opties]
```

#### Positionele Parameters

| Parameter | Beschrijving |
|-----------|--------------|
| `input` | Pad naar .nwctxt bestand of bestandsnaam zonder extensie (verplicht). Als geen extensie wordt opgegeven, wordt `.nwctxt` aangenomen |

#### Optionele Parameters

| Parameter | Waarden | Standaard | Beschrijving |
|-----------|---------|-----------|--------------|
| `--out` | `<pad>` | `audio_output_folder` uit paths.jsonc | Output directory waar de gegenereerde bestanden worden opgeslagen. Er wordt automatisch een submap met de liedtitel gemaakt |
| `--soundfont` | `<pad>` | `soundfont_path` uit paths.jsonc of `FluidR3_GM_GS.sf2` | Pad naar FluidSynth soundfont (.sf2) bestand voor MIDI synthese |

#### Voorbeelden

```bash
# Basis gebruik: converteer bestand uit build folder
python nwc-convert.py "Vader Jacob"

# Converteer met volledig pad
python nwc-convert.py "C:\muziek\Vader Jacob.nwctxt"

# Specificeer output directory
python nwc-convert.py "Vader Jacob" --out "D:\audio"

# Gebruik custom soundfont
python nwc-convert.py "Vader Jacob" --soundfont "C:\soundfonts\piano.sf2"

# Combinatie van opties
python nwc-convert.py "Alle eendjes" --out "D:\demos" --soundfont "C:\sf2\orchestral.sf2"
```

#### Conversie Pipeline

Het script voert de volgende stappen uit:

1. **NWCTXT → MIDI** (via nwc-conv.exe)
   - Converteert muzieknotatie naar MIDI formaat

2. **MIDI → WAV** (via fluidsynth)
   - Synthetiseert MIDI naar ongecomprimeerde audio met soundfont

3. **WAV → FLAC** (via ffmpeg)
   - Comprimeert WAV naar lossless FLAC formaat

#### Gegenereerde Bestanden

Alle bestanden worden opgeslagen in: `<output_dir>/<liedtitel>/`

1. **`<liedtitel>.mid`**
   - MIDI bestand van het lied

2. **`<liedtitel>.wav`**
   - Ongecomprimeerd audio bestand (groot)

3. **`<liedtitel>.flac`**
   - Lossless gecomprimeerd audio bestand (definitieve output)

#### Vereisten

Dit script vereist de volgende externe tools (moeten in PATH staan):

- **nwc-conv** - NoteWorthy Composer converter (onderdeel van NWC)
- **fluidsynth** - MIDI naar audio synthesizer
- **ffmpeg** - Audio format converter

Het script verifieert automatisch of deze tools beschikbaar zijn bij het starten.

#### Soundfonts

Een soundfont (.sf2) is nodig voor MIDI synthese. Populaire opties:
- FluidR3_GM_GS.sf2 (standaard, algemene MIDI geluiden)
- Orchestrale soundfonts voor meer realistische instrumenten
- Piano soundfonts voor solo piano stukken

---

### nwc_analyze.py

Analyseert .nwctxt bestanden en maakt een overzicht van liedteksten gekoppeld aan maatnummers. Dit script wordt meestal intern aangeroepen door nwc-concat.py, maar kan ook standalone gebruikt worden.

#### Syntax

```bash
python nwc_analyze.py <liedtitel-of-pad> [opties]
```

#### Positionele Parameters

| Parameter | Beschrijving |
|-----------|--------------|
| `liedtitel-of-pad` | Liedtitel (zoekt in build folder) of volledig pad naar .nwctxt bestand (verplicht) |

#### Voorbeelden

```bash
# Analyseer bestand op basis van titel (zoekt in build folder)
python nwc_analyze.py "Vader Jacob"

# Analyseer bestand met volledig pad
python nwc_analyze.py "C:\muziek\Vader Jacob.nwctxt"

# Voorbeelden met quotes (nodig bij spaties)
python nwc_analyze.py "Boer wat zeg je van mijn kippen"
python nwc_analyze.py "C:\liedjes\Boer wat zeg je van mijn kippen.nwctxt"
```

#### Gegenereerd Bestand

**`<liedtitel> analysis.txt`** → build folder

Bevat:
- Metadata (liedtitel, liednummer, totaal aantal maten)
- Of er een begintel (opmaat) is
- Aantal maten vooraf (voor "liedstart" marker)
- Tabel met maatnummer en bijbehorende liedtekstsyllaben

Voorbeeld output:
```
*** NWC ANALYSE ***

Analyse van: Vader Jacob.nwctxt
Locatie: C:\build

liedtitel: Vader Jacob
liednummer: 1
totaal aantal maten: 16
heeft begintel: nee
aantal maten vooraf: 2

maat	tekst
1	Va-
2	der Ja-
3	cob, Va-
4	der Ja-
...
```

#### Maatsoort en Tempo

Als de analyse compleet moet zijn (met tempo en maatsoort), gebruik dan de Python API:

```python
from nwc_analyze import analyze_complete_song

analysis = analyze_complete_song("pad/naar/bestand.nwctxt", tempo=120, timesig="4/4")
```

Dit retourneert een dictionary met:
- `total_measures`: Totaal aantal maten (gecorrigeerd, excl. maten vooraf)
- `total_duration`: Duur in seconden (of None)
- `measure_map`: Dict van maatnummer → liedtekstsyllaben (hernummerd zodat maat 1 = liedstart)
- `vooraf`: Aantal maten voor "liedstart" marker
- `has_begintel`: Boolean - of er een opmaat is

#### Speciale Concepten

**Begintel (Pickup Measure)**
- Onvolledige eerste maat (opmaat)
- Wordt gedetecteerd via `StartingBar:0` in NWC bestand
- Telt niet mee in totaal aantal maten

**Maten vooraf**
- Intro-maten voor het eigenlijke lied begint
- Worden gemarkeerd met "liedstart" text marker in NWC bestand
- Worden afgetrokken van totaal en uitgesloten van duurberekening
- Measure map wordt hernummerd zodat "liedstart" = maat 1

---

## Veelvoorkomende Workflows

### Nieuw Lied Toevoegen

```bash
# 1. Maak NWC bestanden in NoteWorthy Composer GUI
#    Sla op in: <input_folder>/Vader Jacob/nwc/
#    - Vader Jacob intro.nwctxt
#    - Vader Jacob vers.nwctxt
#    - Vader Jacob refrein.nwctxt
#    Plus: Vader Jacob volgorde.jsonc

# 2. Voeg secties samen en genereer structuur
python nwc-concat.py "Vader Jacob"

# 3. Maak audio demo (optioneel)
python nwc-convert.py "Vader Jacob"

# 4. Maak liedtekst .tex bestand
#    Gebruik Vader Jacob analysis.txt uit build folder als referentie

# 5. Genereer alle PDF varianten
python lt-generate.py "Vader Jacob"
```

### Tempo Aanpassen

```bash
# 1. Pas tempo aan in NWC bestand (alleen in eerste sectie)
#    Open met NoteWorthy Composer GUI

# 2. Voer scripts opnieuw uit (in deze volgorde!)
python nwc-concat.py "Vader Jacob"
python nwc-convert.py "Vader Jacob"
python lt-generate.py "Vader Jacob"

# Dit update automatisch:
# - Tempo in liedtekst .tex
# - Labeltrack met nieuwe timing
# - Audio demo met nieuwe tempo
# - Structuur PDF met nieuwe duurberekening
```

### Liedtekst Wijzigen

```bash
# 1. Update liedtekst in .tex bestand
#    <input_folder>/Vader Jacob/Vader Jacob.tex

# 2. Regenereer PDF's
python lt-generate.py "Vader Jacob"

# Dat is alles! Alle varianten worden automatisch bijgewerkt.
```

### Alleen Geconfigureerde Varianten Genereren

```bash
# Tijdens ontwikkeling, genereer alleen varianten met layout configuratie
python lt-generate.py "Vader Jacob" --only -1

# Dit is sneller dan alle 5+ varianten genereren
# Handig bij iteratief testen van layout aanpassingen
```

### Debug LaTeX Compilatie Problemen

```bash
# Toon pdflatex output en behoud hulpbestanden
python lt-generate.py "Vader Jacob" --debug --no-cleanup

# Bekijk .log bestand voor details:
# <distributie_folder>/Vader Jacob (1).log
```

### Alleen Structuur PDF Genereren

```bash
# 1. Zorg dat structuur.tex bestaat (via nwc-concat.py)
python nwc-concat.py "Vader Jacob"

# 2. Genereer alleen structuur (variant 1 is minimaal vereist voor metadata)
python lt-generate.py "Vader Jacob" --only 1

# Dit genereert beide:
# - Vader Jacob (1).pdf (basis liedtekst)
# - Vader Jacob structuur.pdf (structuur overzicht)
```

### Transpositie Toevoegen

```bash
# 1. Voeg transpositie toe aan .tex bestand
#    \newcommand{\transpositions}{2, -3}

# 2. Regenereer (genereert nu 3 versies: 0, +2, -3 halve tonen)
python lt-generate.py "Vader Jacob"

# Output:
# - Vader Jacob (1).pdf (origineel)
# - Vader Jacob (1) in D transp(+2).pdf
# - Vader Jacob (1) in A transp(-3).pdf
```

---

## Configuratie

Alle paden worden geconfigureerd in `paths.jsonc`:

```jsonc
{
  "input_folder": "C:/liedjes/teksten",
  "build_folder": "./build",
  "distributie_folder": "./dist",
  "audio_output_folder": "D:/audio",
  "soundfont_path": "C:/soundfonts/FluidR3_GM_GS.sf2"
}
```

Paden kunnen relatief (ten opzichte van paths.jsonc) of absoluut zijn.

## Afhankelijkheden

### Python Modules
```bash
pip install -r requirements.txt
```

### Externe Tools
- **pdflatex** (TeX Live of MiKTeX)
- **nwc-conv** (NoteWorthy Composer)
- **fluidsynth** (MIDI synthesizer)
- **ffmpeg** (audio converter)

Alle externe tools moeten in PATH staan.

## Projectstructuur

```
<input_folder>/
  Vader Jacob/
    Vader Jacob.tex              # Liedtekst met LaTeX markup
    lt-config.jsonc             # Optionele layout configuratie
    nwc/
      Vader Jacob intro.nwctxt
      Vader Jacob vers.nwctxt
      Vader Jacob refrein.nwctxt
      Vader Jacob volgorde.jsonc

<build_folder>/
  Vader Jacob.nwctxt             # Samengevoegd bestand
  Vader Jacob analysis.txt       # Analyse
  Vader Jacob structuur.tex      # LaTeX structuur

<distributie_folder>/
  Vader Jacob (1).pdf
  Vader Jacob (1) met akkoorden.pdf
  ... (meer varianten)
  Vader Jacob structuur.pdf

<audio_output_folder>/
  Vader Jacob/
    Vader Jacob labeltrack t_120.txt
    Vader Jacob.mid
    Vader Jacob.wav
    Vader Jacob.flac
```
