# Testdata / teststraat — status & TODO

Hervat-document voor de teststraat. Bedoeld zodat het werk later kan worden
opgepakt zonder de hele context uit losse bestanden te reconstrueren.
Volledige werkwijze staat in [tests/README.md](../tests/README.md).

## Status (laatst bijgewerkt: 2026-06-10)

| Fase | Onderwerp | Status |
|---|---|---|
| 1 | Padconfig-seam voor tests (`LT_PATHS_CONFIG`) + sandbox-harness | ✅ klaar |
| 2 | Golden test op bestaande testset (`testset nwc-concat`) | ✅ klaar |
| — | Bevinding: UTF-8-veilige console-output (`console_utf8.py`) | ✅ klaar |
| 3 | `expected-values.json` per testset + `--update-golden` mechanisme | ✅ klaar |
| 4 | Snelle unit-laag op pure functies (`tests/unit/`) | ✅ klaar |
| 5 | Edge-case testsets | ⏳ **open — wacht op testdata** |

Suite draait groen: `python -m pytest` (~87 tests). Snelle laag: `pytest -m unit`.

## Wat er al staat (oriëntatie bij hervatten)

- **Harness**: `tests/conftest.py` — fixtures `sandbox`, `run_script`,
  `assert_matches_golden` (met `normalize`-haak), `load_script`
  (session-scoped; laadt scripts mét koppelteken zoals `nwc-concat.py`),
  en de `--update-golden` optie.
- **Integratietests**: `tests/integration/`
  - `test_nwc_concat_golden.py` — vergelijkt 4 artefacten byte-voor-byte.
  - `test_nwc_concat_values.py` — toetst afgeleide waarden tegen
    `expected output/expected-values.json` (via `process_lieddelen` +
    `analyze_complete_song`).
  - `test_utf8_output.py` — regressietest cp1252-console.
- **Unittests**: `tests/unit/` — `transpose`, `calc_timing`, `parse_duration`,
  timesig-/lyric-helpers, `NwcFile`/`NwcStaff`, enz.
- **Bestaande testset**: `testdata/testset nwc-concat/` (lied "Returnability
  (333)"). Dekt: happy path, pickupbeat, tempowissel halverwege (middenstuk,
  `--keep-tempi`), akkoorden, labeltrack. Zie de README in die map.

## Fase 5 — TODO (open)

**Blokkade**: vereist nieuwe, realistische `.nwctxt`-bronbestanden. De
gebruiker levert deze aan (handwerk in NoteWorthy Composer), óf we leiden
synthetische secties af uit de bestaande Returnability-secties.

Toe te voegen testsets, elk gericht op één scenario dat de huidige set niet dekt:

1. **`testset geen-pickup`** — lied **zonder** anacrusis.
   - Verwacht: `pickup_beats == 0`, `has_begintel == false`,
     eerste sectie `start_time_seconds == 0.0`.
   - Raakt: `get_pickup_beats`, `detect_begintel`, `_pre_bar_duration_qn`.
2. **`testset maatsoortwissel`** — maatsoort verandert halverwege (bv. een
   sectie in 3/4 tussen 4/4-secties).
   - Verwacht: de smart-TimeSig-filter in `concatenate_nwctxt_files` behoudt de
     échte wissel maar dropt redundante headers; starttijden kloppen met de
     gewijzigde maatduur.
   - Raakt: `_parse_timesig_value`, `_last_timesig_in_staff`,
     `extract_timing_segments`, `time_at_measure`.
   - Let op: tempowissel is al gedekt door Returnability (middenstuk); dit gaat
     specifiek om **maatsoort**.
3. **`testset 1-sectie`** — lied met slechts één sectie.
   - Verwacht: triviale volgorde, geen dubbele-maatstreep tussen secties,
     totalen == die ene sectie.

**Werkwijze per nieuwe testset** (zie tests/README.md voor details):
1. `testdata/testset <naam>/input/` vullen met `<lied> <sectie>.nwctxt` +
   `<lied> volgorde.jsonc`.
2. Testbestand schrijven naar voorbeeld van de bestaande
   `test_nwc_concat_golden.py` / `test_nwc_concat_values.py` (pas `TESTSET`,
   `SONG`, evt. `KEEP_TEMPI` aan).
3. `python -m pytest --update-golden` → genereert `expected output/`.
4. Diff controleren (`git diff -- testdata/`), `README.md` in de testset-map
   toevoegen, committen.
