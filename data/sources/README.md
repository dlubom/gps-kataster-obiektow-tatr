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

## Marek Jędrzejczak — pomiary z 2026-10-17

Materiały dostarczone przez Marka Jędrzejczaka, dodane 2026-11-02:

- [20261017 Tatry.xls](marek-jedrzejczak/2026-10-17/20261017%20Tatry.xls) —
  raport GNSS i obliczenia domiarów do otworów, arkusze `Report` oraz
  `Zestawienie`; obliczył Marek Jędrzejczak (Speleoclub Wrocław).
- [20261017 Tatry.pdf](marek-jedrzejczak/2026-10-17/20261017%20Tatry.pdf) —
  jednostronicowe zestawienie 12 otworów i porównanie z katalogiem.

Oryginały zachowano bez zmian. Obserwacje GNSS pochodzą z 2026-10-17;
2026-10-19 to data nagłówka raportu, a 2026-10-27 to data odczytu katalogu
do porównania. Źródło podaje układ 1992 i wysokości EVRF2007.

| Plik | Bajty | SHA-256 |
| --- | ---: | --- |
| XLS | 108032 | `7effcf02dd157ddf74b625958683243b602e8346a2272b61978ba6580f376b22` |
| PDF | 24396 | `f760fd017c790c8be295dd0f41d0f63f2f078f3ca62660b733b7d27e9199f95f` |

Pochodzenie, lista otworów, źródłowe przypisania ID i dalsza weryfikacja:
[issue #41](https://github.com/dlubom/gps-kataster-obiektow-tatr/issues/41).
Kozia II nie ma ID w oryginalnym zestawieniu; w katalogu otrzymuje `MTW-0076`
w istniejącej jaskini `C-0135`. Dwanaście wynikowych punktów otworów z XLS
dodano jako pomiary zweryfikowane przez Marka i ręczne Best na polecenie
Dariusza Lubomskiego z 2026-11-02. Data weryfikacji i dokładność końcowych
punktów nie zostały podane. Zachowano pełne wartości XYZ z XLS oraz
wcześniejsze pomiary; WGS84 obliczono z końcowych punktów PL-1992.

Nazwy katalogowe pozostają zgodne z PIG. Dwa obiekty Koziej to otwór I
(zachodni, `MTW-0013`) i II (wschodni, `MTW-0076`) według planu S. Kotarby
1998 w PIG. Raport Marka daje II wyżej o około 2,48 m; opis i przekrój PIG
podają II niżej o 2,8 m. Nie używamy określeń górny/dolny.
Decyzją Dariusza Lubomskiego z 2026-11-02 przyjęto wysokości Marka jako
wiarygodniejsze od historycznego opisu i przekroju; numerację zachowano.

W Grzędzie przyjęto pomyłkę oznaczeń I/II w dokumencie źródłowym i poprawiono
przypisania decyzją Dariusza Lubomskiego z 2026-11-02, po porównaniu z planami
Georeferencera oraz relacjami położenia i wysokości w opisach PIG:

| Wiersz XLS `Zestawienie` | Nazwa i ID w oryginalnym dokumencie | Przyjęty obiekt katalogu |
| --- | --- | --- |
| 10 | Dziura w Grzędzie I, MTW-0050 | Dziura w Grzędzie II, MTW-0016 |
| 11 | Dziura w Grzędzie II, MTW-0016 | Dziura w Grzędzie I, MTW-0050 |

Wartości XYH nie zmieniły się; poprawiono nazwy/ID przypisane do wyników.
Oryginalne nazwy i wiersze źródła zachowano w referencjach i załącznikach.
[Nałożenia i zapis decyzji](../../docs/asdlc/verification/issue-41/README.md).
