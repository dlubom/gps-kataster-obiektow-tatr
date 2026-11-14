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

## Mnichowa Studnia Wyżnia — otwory i domiar JKTZ

[Decyzja koordynatora i wyliczenie](jktz/mnichowa-2026-11-12/README.md)
przypisują dotychczasowy punkt TPN górnemu otworowi `MLW-0054` i wyznaczają
dolny `MLW-0009` z domiaru `0–B–11`, zachowując kotwicę modelu JKTZ.
Dokument podaje rewizje źródeł, sposób obliczenia i warunek zmiany ID w
szablonie JKTZ przy przejściu na ten katalog.

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

## Marek Jędrzejczak — pomiary z 2026-11-12

| Oryginał | Zawartość | SHA-256 |
| --- | --- | --- |
| [TATRY_261017-261112.xls](marek-jedrzejczak/2026-11-12/TATRY_261017-261112.xls) | Raport GNSS i domiarów oraz zestawienie z pełną precyzją | `359b315b5d19e676b6da511293081dbc3062d12024af6d7b922673eae3074657` |
| [Tatry.pdf](marek-jedrzejczak/2026-11-12/Tatry.pdf) | Jednostronicowy wydruk zestawienia z wartościami do 0,01 m | `2e8cbbf80792fe87186e6c71bb95f933e859e4908b109bda4dbe9e295f329783` |

Pomiary terenowe wykonali Michał Bochynek i Sławomir Boruta. Marek
Jędrzejczak (Speleoclub Wrocław) obliczył wyniki i zweryfikował je
13 listopada 2026 o 21:00 CET. W arkuszu `Zestawienie`
kolumna D (E) to `input_x`, kolumna C (N) to `input_y` w PL-1992,
a kolumna E to wysokość PL-EVRF2007-NH.

| Wiersz danych w PDF (s. 1) | Wiersz `Zestawienie` | Wiersz `Report` | Obiekt / pomiar |
| --- | --- | --- | --- |
| 13 | 15 | 366 | Dolny otwór Ptasiej Studni — `MTZ-0066/m-004` |
| 14 | 16 | 399 | Jaskinia nad Dachem — `MTW-0004/m-003` (w źródle `MTW-004`) |
| 15 | 17 | 430 | Jaskinia Lodowa Litworowa — `MTW-0023/m-003` |

Wszystkie 15 wierszy PDF jest zgodnych z arkuszem `Zestawienie`
w granicach precyzji wydruku. Wiersze 1–12 PDF odpowiadają dwunastu
pomiarom z 2026-10-17, które już są w katalogu. Dla trzech nowych pozycji
PDF i `Zestawienie` podają 2026-11-12 jako datę odczytu katalogu użytego
do porównania, a `Report` podaje 2026-10-27. Data pomiarów terenowych
to 2026-11-12. Wartość „< 0,10 m” dotyczy kotwicy GNSS. Dokładność
końcowych punktów po domiarze BRIC4 jest nieznana. Wysokość 1446,80 m
użyta w porównaniu dla Ptasiej Studni pochodzi z NMT TPN i opisuje grunt.
