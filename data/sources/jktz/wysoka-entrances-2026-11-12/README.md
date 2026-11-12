# Cztery otwory systemu Wysoka–Za Siedmiu Progami–Pośrednia

Pozycje pochodzą z istniejącej sieci JKTZ, nie z nowych pomiarów terenowych.
Tożsamości otworów przyjęto na podstawach rozliczonych w J01-08–10 migracji
CAVE_ID. Nie wyprowadzano ich ze zbieżności współrzędnych, nazw ani numerów ID.
Nie zmieniono pomiarów, numeracji, połączeń, kotwicy ani historii GPS.

| Nowy obiekt GPS | Jaskinia | Stacja JKTZ | Podstawa identyfikacji |
| --- | --- | --- | --- |
| KSW-0264 | C-0412 | Wysoka7Progow:W7-500 | III.SRV:45–46 jawnie opisuje górny otwór Za7; karta PIG 1667 wymienia górny 04, odrębny od dolnego 03. |
| KSW-0265 | C-0665 | Wysoka7Progow:W-300 | IV.SRV:64–65 i OTWORY.SRV:405–407 jawnie opisują górny otwór Wysokiej; karta PIG 1665 wymienia otwór 02. |
| KSW-0266 | C-0499 | Wysoka7Progow:W7-P500 | PIONY.SRV:535–536 i przyjęta rekonstrukcja PR #146; karta PIG 1668 wymienia środkowy 06. |
| KSW-0267 | C-0499 | Wysoka7Progow:W7-P507 | III.SRV:85–92 i przyjęta rekonstrukcja PR #146; karta PIG 1668 wymienia górny 07. |

Podziemna sieć JKTZ należy do systemu C-1053. Obiekty GPS zachowują
przynależność do jaskiń składowych. Dotychczasowe KSW-0123 (Za7 dolny 03),
KSW-0189 (Wysoka, W7-0) i KSW-0153 (Pośrednia dolny 05) pozostają bez zmian.
ID przydzielono kolejno ponad najwyższe istniejące ID KSW mechanizmem
`IdSequence`; resolver granic dla wszystkich czterech punktów potwierdził KSW.

## Źródła i ich ograniczenia

- [JKTZ, rewizja 77963f9ea8268556197a16e9b391cb0539b5a4ee](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/tree/77963f9ea8268556197a16e9b391cb0539b5a4ee/Poligony/D_Koscieliska/Wys_Grzbiet/Wysoka-7_Progow):
  siedem SRV `I`, `II`, `III`, `IV`, `V`, `7PROGOW`, `PIONY` oraz `KATASTER.wpj`
  i wersjonowane `Poligony/OTWORY.SRV`. Ich sumy są w [coordinates.json](coordinates.json).
  Wszystkie te pliki odpowiadają bajtowo wskazanej rewizji.
- [Przyjęta rekonstrukcja PR #146](https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich/pull/146),
  squash `4b5d15d2882597eb504289818661f630a3b36597`: Pośrednia ma odrębną
  numerację W7-P500…507; dolny otwór W7-PD jest aliasem W7-505/1.
  Oryginalnego protokołu nie odzyskano. Przypisania zachowują status rekonstrukcji,
  nie weryfikacji terenowej. Dokumentuje to `_RAW/01/README.md` obok SRV.
- Archiwalny `doc/jaskinie_polski_pig_dump.jsonl` tej samej rewizji JKTZ:
  dokładne `inventory_number` T.F-09.13, T.F-09.12 i T.F-09.14, pole `other_entrances`.
  Publiczne karty: [Za7 1667](https://jaskiniepolski.pgi.gov.pl/Details/Information/1667),
  [Wysoka 1665](https://jaskiniepolski.pgi.gov.pl/Details/Information/1665),
  [Pośrednia 1668](https://jaskiniepolski.pgi.gov.pl/Details/Information/1668).
  Pole dojścia karty Wysokiej omyłkowo powtarza 07 przy środkowym otworze;
  nie jest podstawą zamiany przyjętych 06/07. Wysokości opisowe PIG nie służyły
  do dobierania ani poprawiania współrzędnych modelu.
- [GPS v2.1.1, KSW-0189/m-003](https://github.com/dlubom/gps-kataster-obiektow-tatr/blob/d34bcb0868f636af2eaa9ddb702bb11a78c193ab/data/objects/KSW/KSW-0189.yml):
  jedyna czynna kotwica systemu, Wysoka7Progow:W7-0, lon 19.88454604,
  lat 49.2336413, H 1486.69 m. Best jest ręczny; źródło
  `unknown:gnss:Wysoka7Progow`, status nieweryfikowany, datum i dokładności nieznane.
  Metadane v2.1.1, ID wydania i SHA obu artefaktów zapisano w coordinates.json;
  katalog odczytano czytnikiem J02. Kompilacja używała wersjonowanego OTWORY,
  bez renderowania go starym szablonem z nowego Best Mnichowej.

## Wyznaczenie pozycji

Survex 1.4.24 skompilował całe JKTZ bez ostrzeżeń. Użyto niezmienionego
`.REF` WGS 1984 / UTM 34N z KATASTER.wpj, dotychczasowego `DECL=0`
oraz pełnej sieci i jej wyrównania. Daty pomiarów i rzeczywista deklinacja
pozostają nieustalone. Nie sumowano samodzielnie wybranej drogi przez sieć.

```sh
cavern --no-auxiliary-files -o /tmp/wysoka-baseline KATASTER.wpj
survexport --csv /tmp/wysoka-baseline.3d /tmp/wysoka-stations.csv
```

Poniżej wynik zapisany w `.3d` i CSV co 0,01 m (E/N w EPSG:32634).
Konwersja EPSG:32634 → 4326 używa `always_xy=True` poprzez helper JKTZ
`.agents/skills/utm34n-wgs84/utm34n_wgs84.py` (pyproj 3.7.2).
Wysokość przeniesiono bez przeliczenia datum. Wyniki lon/lat zapisano
z 10 miejscami po przecinku, aby zachować centymetrowy wynik kompilatora;
liczba cyfr nie jest deklaracją dokładności. Kontrola odwrotnej transformacji
różni się od wejścia o mniej niż 0,001 m.

| Obiekt | E [m] | N [m] | H [m] | lon | lat |
| --- | ---: | ---: | ---: | ---: | ---: |
| KSW-0264 | 418780.53 | 5454053.75 | 1472.29 | 19.8843292794 | 49.2338725272 |
| KSW-0265 | 418795.15 | 5454044.15 | 1498.68 | 19.8845320112 | 49.2337881284 |
| KSW-0266 | 418792.35 | 5454030.84 | 1486.77 | 19.8844962526 | 49.2336680529 |
| KSW-0267 | 418791.31 | 5454042.41 | 1488.18 | 19.8844796261 | 49.2337719703 |

Każdy rekord ma jeden pomiar `m-001`, `source: wlasne`,
`method: siec_pomiarowa`, `elevation_source: other`, status `nieweryfikowany`,
datum `unknown` i obie dokładności `null`. Data 2026-11-12 to data wyznaczenia
wyniku, nie nowa data pomiaru terenowego. Bibliografia formalna pozostaje
`unknown`; konkretne źródła tożsamości i modelu wskazano powyżej oraz w YAML.

## Warunek integracji

Te cztery punkty są zależnymi wynikami istniejącej sieci. Służą do
`OBJECT_REF`; **nie dodawać z nich niezależnych aktywnych fixów JKTZ**.
Zachować obecną kotwicę W7-0 i jej historię. J04 wymaga scalenia oraz osobno
zleconego wydania GPS, potem jednego wspólnego snapshotu GPKG/Best.
Sam draft PR albo podgląd CI nie spełnia tego warunku.

Przy integracji JKTZ nadal obowiązuje zatwierdzona zmiana ID fixa Mnichowej
`MnichStudniaWyz:0` z MLW-0009 na MLW-0054 bez zmiany współrzędnych i bez
drugiego aktywnego fixa dolnego otworu. Górny otwór LODMAL pozostaje bez fixa.
