# Mnichowa Studnia Wyżnia — przypisanie otworów i domiar

Decyzja koordynatora Dariusza Lubomskiego z 2026-11-12:

> Przyjmijmy jako decyzję koordynatora, że punkt TPN dotyczy górnego otworu 0.
> Dolny 11 z MLW-0009 wylicz z domiaru, zachowując obecną geometrię.
> Przygotuj zmiany w GPS.

To świadome przypisanie tożsamości otworów. Publiczny rekord TPN nie
identyfikuje wejścia. Analiza NMT z LiDAR TPN i inspekcja obrazów nie
rozstrzygnęły tożsamości ani dokładności terenowej. Nie zastępują tej decyzji.

| Obiekt | Stacja JKTZ | Best |
| --- | --- | --- |
| `MLW-0054`, otwór górny | `MnichStudniaWyz:0` | `m-001`: dokładny dotychczasowy punkt TPN |
| `MLW-0009`, otwór dolny | `MnichStudniaWyz:11` | `m-003`: domiar od górnego otworu |

Oba obiekty należą do `C-0288`. Wcześniejsze decyzje koordynatora
identyfikują `11` jako dolny otwór i `0–B–11` jako domiar powierzchniowy.
Nie zmieniono daty, odczytów ani klasyfikacji źródłowego pliku JKTZ.

## Źródła

- [GPS v2.1.0, MLW-0009/m-002](https://github.com/dlubom/gps-kataster-obiektow-tatr/blob/9cc09122a5403808cdcc662cfc98636c2aaff3ad/data/objects/MLW/MLW-0009.yml):
  TPN `{29508047-79F7-4739-BAD5-FC2D7E4CAD8B}`;
  lon `19.92963606546537`, lat `49.24323886500313`, H `1699.893361 m`.
  Zachowano pełne wartości YAML, daty rekordu `2022-05-25`, datum `unknown`
  i nieznane dokładności. Źródło wysokości nie zostało ustalone.
- [JKTZ MSW1.SRV](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/blob/77963f9ea8268556197a16e9b391cb0539b5a4ee/Poligony/D_Malej_Laki/Prawe_zb/Mnich_Studnia_Wyz/MSW1.SRV),
  SHA-256 `163ace1805299047d74a3827a10d78c646d15b7a8b7162b165517dd58b7213fa`.
  Jest to transkrypcja JKTZ; oryginały i ich pochodzenie pozostają w
  pakietach `_RAW/01`, `_RAW/02`, `_RAW/03` w tym samym katalogu.
  Zachowano skuteczny `#DATE 2002-02-03`, `meters order=DAV`, `A=D V=D`
  oraz `.REF` z `KATASTER.wpj` tej samej rewizji.
  Wyjaśnienie datowania to osobna sprawa
  [JKTZ #151](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/issues/151).

| Od | Do | D [m] | A [°] | V [°] |
| --- | --- | ---: | ---: | ---: |
| 0 | B | 16,38 | 27 | −52 |
| B | 11 | 13,32 | 272 | −30 |

## Wyliczenie

Kotwicę WGS84 przeliczono do UTM 34N (EPSG:32634, kolejność E/N), otrzymując
`E=422093.4866131534`, `N=5455047.318252991 m`. Orientację domiaru zachowano
z kompilacji Survex 1.4.24 w dotychczasowym kontekście JKTZ, wraz z
deklinacją wynikającą z daty i zbieżnością południków. Nie dodawano surowego
wektora azymutalnego bezpośrednio do współrzędnych mapowych.

Format `.3d` zapisuje centymetry. Aby nie wyznaczać domiaru przez odejmowanie
zaokrąglonych stacji, w izolowanych próbach skompilowano wyłącznie dwie nogi
z długościami pomnożonymi przez 10 000, 100 000 i 1 000 000, zachowując
pozostałe dyrektywy, `.REF` i fix. Różnice współrzędnych podzielono przez
odpowiednią skalę. Wyniki są zbieżne do `0,00000055 m`; jest to kontrola
numeryczna, nie oszacowanie dokładności pomiaru. Oryginalnych danych nie
skalowano ani nie zmieniano. Wektor poziomy z ostatniej próby:

`dE=-6.24870609 m`, `dN=9.86874755 m`.

Wysokość wyliczono bezpośrednio z odczytów:

`dH = 16.38 × sin(-52°) + 13.32 × sin(-30°) = -19.567616144078105 m`.

Po dodaniu wektora do dokładnej kotwicy i transformacji EPSG:32634 → 4326
otrzymano lon `19.929548310996175`, lat `49.24332682581145`,
H `1680.3257448559218 m`. W `m-003` zapisano lon `19.9295483110`,
lat `49.2433268258` i H `1680.325745 m`. Liczba cyfr służy reprodukcji;
nie oznacza dokładności terenowej. Datum pozostaje `unknown`, dokładności
`null`, status `nieweryfikowany`. Data `2026-11-12` to data wyznaczenia
wyniku sieci, a nie nowego pomiaru w terenie.

## Historia i przejście JKTZ na nowy katalog

Dolny obiekt zachowuje `m-001` PIG i `m-002` TPN w pierwotnej kolejności,
z niezmienionymi źródłowymi współrzędnymi, wysokością i datami. `m-002`
jest odrzucony tylko jako pomiar dolnego otworu. Jedyna bieżąca referencja
obiektowa GLOBALID TPN należy do górnego `MLW-0054`. Historyczny `source_ref`
pozostaje przy dolnym `m-002`; dlatego zbiorcze pole eksportowe `tpn_globalid`
może nadal występować przy obu obiektach. Aktualną relację określa
`object_external_refs`.

Przejście JKTZ na wydanie z tymi danymi wymaga równoczesnej zmiany wywołania
`gps_fix('MnichStudniaWyz:0', 'MLW-0009')` na
`gps_fix('MnichStudniaWyz:0', 'MLW-0054')`. Współrzędne istniejącego fixa
pozostają identyczne. **Nie dodawać niezależnego aktywnego fixa stacji `11`**
na podstawie wyniku tej samej sieci. Samo pobranie nowego Best przy starym
szablonie przesunęłoby model; wymaga to skoordynowanej aktualizacji JKTZ.

Próbne przełączenie ID zachowało bajty całego renderu `OTWORY.SRV`.
Izolowana kompilacja Mnichowej przed i po daje identyczne `.3d` przy
`SOURCE_DATE_EPOCH=0`; wszystkie 15 stacji zgadzają się z dotychczasowym
modelem całego JKTZ z dokładnością zapisu 0,01 m. Jest to dowód zachowania
dotychczasowej geometrii Survex, nie potwierdzenie współrzędnych terenowych.
Pełne porównanie projektu i natywne Walls należą do późniejszej integracji
JKTZ. Ten zapis GPS sam nie zmienia źródeł JKTZ ani nie publikuje wydania.
