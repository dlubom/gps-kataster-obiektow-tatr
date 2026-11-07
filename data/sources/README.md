# Source Data

Ten katalog przechowuje zewnętrzne dane wejściowe i pomocnicze dumpy do ręcznej
oceny. Nie są one źródłem prawdy V1: jest nim katalog YAML w `data/`.
Początkowe importy PIG/TPN zakończono; nowe rekordy i pomiary edytuje się
bezpośrednio w YAML i poddaje przeglądowi w PR.

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
`Obiekt` z własnym ID, ustaw jego `cave_id` i `membership_ordinal` oraz
zachowaj referencje źródłowe. Lista `Jaskinia.object_ids` jest wyliczana;
nie edytuj jej w źródłowym YAML.

## TPN

- `tpn/tpn_otwory_jaskin.xlsx`
- `tpn/tpn_otwory_jaskin.xlsx.-.Export.csv`
- [Pełny zrzut warstwy „Jaskinie” z 19.10.2026](tpn/snapshots/pbi-101-live-20261019/)
  obejmuje 1035 rekordów z atrybutami i geometrią. Zachowuje oryginalne
  odpowiedzi API, schemat warstwy i kontrole liczby rekordów oraz identyfikatorów
  przed i po pobraniu. [Manifest](tpn/snapshots/pbi-101-live-20261019/manifest.json)
  podaje adres warstwy, parametry zapytania i sumy SHA-256.

TPN `GLOBALID` jest identyfikatorem rekordu punktowego i trafia do
`Obiekt.external_refs`. `NR_INWENT` opisuje zwykle jaskinię / pozycję
katalogową i trafia do `Jaskinia.external_refs`.

## KKTJ / Jaskinie Tatr

[Tabela zbiorcza z lipca 2026](kktj/2026-07/jaskinie-tatr.md) to opracowanie
11 tabel PDF z publikacji Jakuba Nowaka, przeznaczone do ręcznego porównywania
z katalogiem. Każdy wiersz wskazuje PDF i stronę, a kursywa zachowuje
źródłowe oznaczenie braku dokumentacji kartograficznej.

## Marek Jędrzejczak — pomiary z 2026-10-17

Marek Jędrzejczak (Speleoclub Wrocław) przekazał poprawiony arkusz
2026-11-04. Zawiera raport obserwacji GNSS i domiarów BRIC4 (`Report`)
oraz końcowe współrzędne 12 otworów (`Zestawienie`). Układ PL-1992,
wysokości PL-EVRF2007-NH. Wszystkie pliki zachowano bajtowo.

| Plik | Rola | SHA-256 |
| --- | --- | --- |
| [Poprawiony XLS](marek-jedrzejczak/2026-10-17/corrected-2026-11-04/20261017%20Tatry.xls) | Źródło pomiarów w katalogu | `516c650d0559e08bbcd1422ce92942c84ba962e52c3207057c1fb32c2868e1ae` |
| [Pierwotny XLS](marek-jedrzejczak/2026-10-17/20261017%20Tatry.xls) | Archiwum | `7effcf02dd157ddf74b625958683243b602e8346a2272b61978ba6580f376b22` |
| [Pierwotny PDF](marek-jedrzejczak/2026-10-17/20261017%20Tatry.pdf) | Archiwum | `f760fd017c790c8be295dd0f41d0f63f2f078f3ca62660b733b7d27e9199f95f` |

W poprawionym XLS wiersz 10 arkusza `Zestawienie` wskazuje Dziurę
w Grzędzie II (`MTW-0016`), a wiersz 11 Dziurę w Grzędzie I (`MTW-0050`).
Współrzędne wynikowe są identyczne w obu wersjach. Do katalogu wprowadzono
pełne wartości z poprawionego arkusza. Zakres i porównanie wersji opisuje
[issue #43](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/43).
