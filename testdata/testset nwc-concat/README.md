# Testset: nwc-concat

Golden testset voor `nwc-concat.py`. Gebruikt door
`tests/integration/test_nwc_concat_golden.py`.

## Lied

**Returnability (333)** — 10 secties in `volgorde.jsonc`.

## Scenario's die deze testset dekt

- Happy path: volledige concatenatie van meerdere secties tot één `.nwctxt`.
- **Pickupbeat (anacrusis)** aan het begin van het lied.
- **Tempowissel halverwege**: het `middenstuk` is langzamer, daarom moet
  gecompileerd worden met `--keep-tempi` (zie de comment in `volgorde.jsonc`).
  De test draait daarom met die vlag.
- Akkoordextractie per sectie en maattelling per sectie.
- Labeltrack-generatie (tempo 184 → bestandsnaam `... labeltrack t_184.txt`).

## Verwachte output (`expected output/`)

| Bestand | Vergelijking |
|---|---|
| `Returnability (333).nwctxt` | exact |
| `Returnability (333) analysis.txt` | exact, behalve de `Locatie:`-regel (zie hieronder) |
| `Returnability (333) structuur.tex` | exact |
| `Returnability (333) labeltrack t_184.txt` | exact |

## Bekende bijzonderheden

- **`Locatie:`-regel in `analysis.txt`** bevat een absoluut, machine-specifiek
  buildpad. De test maskeert deze regel (`_mask_locatie`) omdat hij per
  machine/run verschilt. Kandidaat voor latere refactor: schrijf hier een
  relatief pad of alleen de songtitel.
- **`structuur.tex` is op 2026-06-09 ververst** naar de toen-actuele output.
  De vorige golden was verouderd: de kop heette nog `Lied delen` i.p.v.
  `Compositie`/`Lied onderdelen` en de tabelvolgorde was gewijzigd. De
  berekende data (maataantallen, akkoorden) was identiek; alleen de lay-out
  in de code was sindsdien aangepast.
