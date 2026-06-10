# Tests — handleiding

Regressienet voor de lt-code scripts. Twee soorten tests:

- **golden tests** — draaien een echt script (subprocess) op een testset en
  vergelijken de gegenereerde bestanden (`.nwctxt`, `analysis.txt`,
  `structuur.tex`, labeltrack) byte-voor-byte met `expected output/`.
- **waarden-test** — roept de componentfuncties direct aan en toetst de
  *afgeleide waarden* (tempo, maatsoort, pickup, maten + starttijden per
  sectie, totalen, akkoorden) tegen `expected output/expected-values.json`.
- **unittests** (`tests/unit/`) — snelle, geïsoleerde tests van pure functies
  (`transpose`, `calc_timing`, `parse_duration`, timesig-/lyric-helpers, ...)
  met kleine handgemaakte snippets, zonder bestanden of subprocessen.

Alles draait geïsoleerd: een testset wordt naar een tijdelijke map gekopieerd
en de scripts worden via de `LT_PATHS_CONFIG`-omgevingsvariabele daarheen
omgeleid. De git-werkmap wordt nooit aangeraakt tijdens een testrun.

## Draaien

```bash
pip install -r requirements-dev.txt    # eenmalig
python -m pytest                       # alles
python -m pytest -m integration        # alleen end-to-end golden/waarden-tests
python -m pytest -m unit               # alleen snelle unittests (< 1 s)
python -m pytest tests/integration/test_nwc_concat_values.py   # één bestand
```

## Tests bijwerken na een specwijziging

Heb je bewust het gedrag aangepast (andere lay-out in `structuur.tex`, andere
berekening, extra veld, ...)? Dan kloppen de verwachtingen niet meer. Werk ze
bij in drie stappen:

1. **Regenereer de verwachtingen** uit de huidige output:

   ```bash
   python -m pytest --update-golden
   ```

   Dit herschrijft *zowel* de golden-bestanden in `expected output/` *als* de
   `expected-values.json` van elke testset. De tests worden dan "skipped"
   (ze vergelijken niet, ze schrijven).

2. **Controleer de diff** — dit is de belangrijkste stap. Bekijk of de
   wijzigingen kloppen met wat je bedoelde:

   ```bash
   git diff -- testdata/
   ```

   Klopt de diff niet met je bedoeling, dan zit er een echte fout in de code:
   herstel die en herhaal stap 1. Commit de nieuwe verwachtingen pas als de
   diff exact is wat je verwacht.

3. **Bevestig dat alles weer groen is** (zonder de vlag):

   ```bash
   python -m pytest
   ```

> `--update-golden` is een stomp instrument: het neemt de *huidige* output als
> waarheid aan. Gebruik het alleen ná een bewuste wijziging en lees altijd de
> diff. Voor het allereerste vullen van een nieuwe testset gebruik je dezelfde
> vlag.

### Eén testset bijwerken i.p.v. alles

```bash
python -m pytest "tests/integration/test_nwc_concat_values.py" --update-golden
```

## Een nieuwe testset toevoegen

1. Maak `testdata/testset <naam>/input/` met de bron-`.nwctxt`-bestanden en de
   `volgorde.jsonc` (zelfde namen als de scripts verwachten:
   `<lied> <sectie>.nwctxt`, `<lied> volgorde.jsonc`).
2. Schrijf een testbestand naar voorbeeld van
   [test_nwc_concat_golden.py](integration/test_nwc_concat_golden.py) en
   [test_nwc_concat_values.py](integration/test_nwc_concat_values.py); pas
   `TESTSET`, `SONG` en zo nodig `KEEP_TEMPI` aan.
3. Genereer de verwachtingen: `python -m pytest --update-golden`.
4. Controleer de gegenereerde `expected output/`-bestanden en commit.
5. Voeg een korte `README.md` toe in de testset-folder (welke scenario's,
   bekende bijzonderheden). Zie de bestaande testset als voorbeeld.

## Volatiele waarden (machine-specifiek)

Sommige output bevat regels die per machine/run verschillen — bv. de
`Locatie:`-regel in `analysis.txt` (absoluut buildpad). Die worden in de
vergelijking gemaskeerd via een `normalize`-functie (`_mask_locatie`), en bij
`--update-golden` wordt de gemaskeerde vorm opgeslagen zodat de golden-bestanden
portable blijven. Heeft nieuwe output zo'n volatiele regel, voeg dan een
maskeer-functie toe in het testbestand.

## Hoe de stukken samenhangen

| Bestand | Rol |
|---|---|
| `conftest.py` | fixtures: `sandbox`, `run_script`, `assert_matches_golden`, `load_script`, `--update-golden` |
| `pytest.ini` | testpaden + markers (`unit`, `integration`) |
| `requirements-dev.txt` | testafhankelijkheden (pytest) |
| `testdata/testset */input/` | bron-`.nwctxt` + `volgorde.jsonc` |
| `testdata/testset */expected output/` | golden-artefacten + `expected-values.json` |
