# Testdata TODO

## 1. Testrunner toevoegen

Maak een pytest-bestand (bijv. `tests/test_nwc_concat.py`) dat:

- `nwc-concat.py` aanroept op de testdata
- de gegenereerde output vergelijkt met de bestanden in `expected output/`

Hierdoor kan de AI tests automatisch uitvoeren en resultaten verifiëren.

## 2. Paths-configuratie voor tests

`nwc-concat.py` laadt paden via `paths.jsonc`. Definieer voor elke testset waar
de output terecht moet komen, zodat de testrunner de output kan ophalen en vergelijken.

## 3. Meer testcases (edge cases)

Huidige testset dekt de happy path. Voeg toe:

- Een lied **zonder** pickupbeat (anacrusis)
- Een lied met **tempo- of maatsoortwijziging** halverwege
- Een lied met slechts **1 sectie**

## 4. Beschrijving per testset

Voeg een `README.md` toe per testset-folder met:

- Welke scenario's de test dekt
- Bekende bijzonderheden van de testdata (bijv. "bevat pickupbeat", "tempo wijzigt na intro")
