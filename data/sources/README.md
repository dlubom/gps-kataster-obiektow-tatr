# Source Data

Ten katalog przechowuje zewnętrzne dane wejściowe i pomocnicze dumpy używane do
review. Nie są one źródłem prawdy V1. Źródłem prawdy pozostają YAML-e w
`data/objects/` i `data/caves/`.

## PIG / Jaskinie Polski

- `pig/pig_otwory_jaskin_.xlsx`
- `pig/pig_otwory_jaskin_.xlsx.-.Export.csv`
- `pig/jaskinie_polski_pig_dump.jsonl`

`jaskinie_polski_pig_dump.jsonl` pochodzi z lokalnego repozytorium
`Jaskiniowy-Kataster-Tatr-Zachodnich/doc/` i zawiera pełniejsze opisy rekordów
PIG / Jaskinie Polski. Jest przydatny do ręcznego rozstrzygania przypadków, w
których jeden rekord katalogowy ma kilka otworów.

Przykład:

```bash
rg -n "Mroźna" data/sources/pig/jaskinie_polski_pig_dump.jsonl
```

W znalezionym rekordzie sprawdź pola takie jak `other_entrances`,
`entrance_access_description`, `cave_description`, `documentation_history` i
`images`. Jeśli opis potwierdza dodatkowy otwór tej samej jaskini, dodaj nowy
`Obiekt`, dopisz jego ID do istniejącej `Jaskinia.object_ids` i zachowaj
referencje źródłowe.

## TPN

- `tpn/tpn_otwory_jaskin.xlsx`
- `tpn/tpn_otwory_jaskin.xlsx.-.Export.csv`

TPN `GLOBALID` jest identyfikatorem rekordu punktowego i trafia do
`Obiekt.external_refs`. `NR_INWENT` opisuje zwykle jaskinię / pozycję
katalogową i trafia do `Jaskinia.external_refs`.
