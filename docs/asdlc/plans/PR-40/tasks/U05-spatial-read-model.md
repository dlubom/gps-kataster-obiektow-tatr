# U05 — region GPX z modelu odczytu SQL

Przeczytaj [indeks](../README.md), [spec](../spec.md), [design](../design.md)
i [development](../development.md). Zależności: U01/U02. Realizuje S03/S04.

## Spec

`schema/catalog.sql::v_measurement_regions` już przypisuje region każdego
pomiaru przez `ST_Covers`, z kolejnością `boundaries.ordinal`.
`best_measurements_export._group_gpx_rows` ponownie wywołuje Pythonowy
`resolve_prefix` dla każdego wybranego pomiaru. Usuń to drugie obliczenie
z eksportu zwalidowanego katalogu.

Grupowanie ma dotyczyć faktycznie wybranego pomiaru, również manual Best,
a nie prefiksu trwałego ID obiektu ani wyniku automatycznego Best.
Nazwy trzech plików grupowych i ich zawartość/kolejność pozostają zgodne.
Obowiązuje dotychczasowy limit 500 punktów na grupę; przekroczenie nadal
blokuje przed publikacją, bez automatycznego podziału doliny.

## Design

- Pobierz region wybranego pomiaru z istniejącego połączenia katalogu;
  nie otwieraj dodatkowej bazy, nie ładuj geometrii i nie wykonuj zapytania
  osobno dla każdego wiersza.
- Przekaż go wewnętrzną niezmienną strukturą `ExportData` albo jego danych
  wejściowych. Nie rozszerzaj `BEST_FIELDS` ani publicznych kolumn Full.
- Zachowaj regułę błędu `GpxGroupingError` przed publikacją, gdy wybrany
  pomiar nie ma grupy. Nie stosuj cichego fallbacku na prefiks ID.
- `prefix_resolver` nadal obsługuje kandydatów przed SQL. Nie usuwaj go
  globalnie; porównaj obie semantyki brzegowe przed uznaniem wyników za równoważne.

## Development

1. Dodaj niezależne przypadki punktu wewnątrz/na granicy/poza poligonem,
   otworu w poligonie, nakładania regionów i priorytetu ordinal, PL/SK
   oraz braku regionu. Sprawdź grupę 500 i 501 punktów. Oczekiwane grupy
   określ w danych testu, nie resolverem.
2. Prześledź `Catalog.dataset`, `prepare_export_data`, pełny build i standalone
   Best. Wybierz najkrótszą ścieżkę udostępnienia istniejącego wyniku SQL.
3. Przełącz `_group_gpx_rows`; usuń zbędny import/wywołania resolvera w eksporterze.
   Dodaj test, że eksport z gotowego stanu nie wykonuje Pythonowej geometrii.
4. Porównaj eksporty dla całego katalogu; osobno przypadek manual Best
   w innym regionie niż auto Best i trwały prefiks ID.
5. Uaktualnij opis grup GPX, jeśli wymaga wskazania nowego właściciela obliczeń;
   zachowaj dane `config/` i `data/shapes/` bez zmian.

```bash
uv run --frozen pytest -q tests/test_export_data.py tests/test_best_measurements_export.py tests/test_grouped_gpx.py tests/test_postgres_exports.py tests/test_prefix_resolver.py tests/test_postgres_catalog.py
```

## Odbiór

- [x] Dla eksportu geografia liczona jest raz w SQL, bez ponownego resolvera
  i bez dodatkowego katalogu; obie ścieżki eksportu używają tej samej danej.
- [x] Testy granic/otworów/nakładania i manual Best wskazują oczekiwane grupy;
  brak regionu i 501 punktów blokują bez zmiany poprzednich plików;
  grupa 500 punktów pozostaje legalna.
- [x] Każdy punkt występuje dokładnie raz w sumie grup; kolejność i precyzja
  czterech GPX oraz pozostałych dziewięciu artefaktów pozostają zgodne.
- [x] Pola sterujące grupowaniem nie wyciekły do publicznych formatów;
  pełna bramka, porównanie i exact-SHA CI spełniają procedurę.

### Wynik wdrożenia i odbioru

Baza refaktoru: `519a008c53a9d63f8f6ef67d2f8aff31690725d3`.
Zaakceptowana baza historii: `ad5fa191a36d5a5f45f0b2de523bd39125827573`,
potwierdzona jako bieżący base PR i `origin/main`, osobno od bazy refaktoru.

`Catalog.dataset()` dołącza `v_measurement_regions` do dotychczasowego
zbiorczego odczytu pomiarów. Niemutowalne krotki `measurement_regions` są obok
rekordów, a `ExportData.gpx_regions` zawiera region wybranego pomiaru.
Publiczne pola i źródłowy model zmian pozostają bez dodatkowego pola regionu.
Usunięto import/wywołanie `resolve_prefix` w eksporterze; importer go zachowuje.
Obie ścieżki używają tego samego przygotowania i grupowania.

Nowe testy są pisane bez konwersji/walidacji fixture przed produkcyjnym API.
Dziesięć nowych przypadków najpierw zawiodło na braku metadanych SQL lub
wywołaniu geometrii Pythona, następnie przeszło. Literalne oczekiwania
obejmują wnętrze, krawędź i wierzchołek, wnętrze i krawędź otworu,
nakładanie i odwrócenie ordinal, PL/SK oraz brak regionu. Manual PIG Best
leży w innym regionie niż auto TPN i trwały prefiks KSW. Obie ścieżki
blokują brak/null/nieznany region bez nadpisania poprzednich plików.

**Różnica brzegowa:** kontrastowy test dokładnych współrzędnych 2180
potwierdza, że dotychczasowy resolver even/odd wyklucza krawędź otworu,
a `ST_Covers` ją obejmuje. Eksport stosuje jawny kontrakt SQL zgodnie z S03;
nie deklarujemy pełnej równoważności obu algorytmów. Resolver kandydatów
nie jest w tym zadaniu zmieniany.

- Zestaw sześciu plików karty po poprawce kopiowania: **129 PASS**
  (118 wcześniejszych + 11 nowych przypadków); model źródłowy osobno: **24 PASS**.
  Ruff format/lint, `git diff --check` i 86 lokalnych odsyłaczy: PASS.
  Niezależny przegląd pierwotnego diffu uruchomił 10 nowych regresji bez uwag.
  Pełna bramka ujawniła niekompatybilność `mappingproxy` z `deepcopy` wspólnego
  modelu; osobna regresja odtworzyła błąd. Poprawka używa krotek metadanych,
  zachowuje kopiowanie historii/modelu zmian i przeszła regresje (56 PASS).
- **13/13 formatów zgodnych przed/po**, przy `--generated-at 2026-11-05T20:00:00Z`,
  wersji `u05-parity` i identycznym źródłowym SHA. Dziewięć tekstów jest zgodnych
  bajtowo; XLSX: wszystkie komórki/typy/formaty i XML; SHP: wszystkie składowe,
  rekordy, geometria i CRS; GPKG: wszystkie deklaracje/tabele/wartości/typy/null,
  geometria i CRS oraz integrity/FK check; oba dumpy odtworzono natywnie,
  porównano wszystkie tabele, oba widoki Best i schemat.
  Normalizacja dotyczy wyłącznie technicznych nagłówków ZIP/dump, daty nagłówka
  DBF, `gpkg_contents.last_change`, `gpkg_metadata_reference.timestamp` i losowego
  tokena `restrict` klienta PG. Nie normalizowano wartości źródłowych.
- **4185/4185 diagnostyk identycznych** (kod/severity/ścieżka/kolejność/treść),
  0 błędów. Zachowano 1029 obiektów / 1019 jaskiń / 1946 pomiarów i 27 manual
  Best. Cztery GPX są zgodne bajtowo: pełny 1029, grupy **491/481/57** punktów.
- Python produkcyjny **+23/−8, netto +15**, identycznie po pominięciu białych
  znaków; SQL/schematy 0; testy +263/−0. U05 zmniejsza wykonaną pracę, nie
  wielkość kodu: 1029 → 0 wywołań resolvera Pythona na rzeczywisty eksport.
  Testy obu API potwierdzają jeden katalog i brak geometrii Pythona; pomiar
  projekcji przed/po potwierdził **16 → 16** zbiorczych odczytów dla 1029 obiektów,
  bez zapytania na punkt. Brak zmian `data/`, `config/`, SQL, schematów i CI.

Pełna lokalna bramka: **1309 PASS / 1 SKIP**, Ruff format/lint, walidacja
katalogu i rzeczywistej historii, pełny build, natywny restore dumpa i odczyt
GeoPackage oraz `git diff --check`: PASS. PG 18.6/PostGIS 3.6.4, GDAL 3.13.3.
Lokalny skip dotyczy zarządzanego Dockera; jego osobny wymagany smoke w CI:
**1 PASS**. Natywne klienty PostgreSQL odebrano lokalnie. CI ma **1308 PASS /
2 SKIP** (restore poza kontenerem i zarządzany Docker w zwykłym zestawie); drugi
przebieg uruchamia zarządzany Docker z wymaganym przełącznikiem.

Kod U05: `4bc02341e4b31664dc623db56432e841ab462782`. Terminalne SUCCESS:
[Validate code and data](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42101960936)
i [PR export preview](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42101960536).
[Paczka 13449088515](https://github.com/dlubom/gps-kataster-obiektow-tatr/actions/runs/42101960536/artifacts/13449088515)
ma SHA-256 `34cedd0d66f8810ce64ef804ff3799410c29dfd781ab5b85d5efa93f02972897`
zgodny z GitHub: 15 plików, **14/14 sum**, zgodne head/base/run/próba oraz merge
`633dddfbfefc351ef1bc759d21db639932582d9c`; obu rodziców sprawdzono w Git.
Odczytano i porównano pełne **13/13 formatów** z niezależnym buildem sprzed
U05 przy metadanych tej paczki. Wartości źródłowe, typy, null, kolejność,
ręczne Best i CRS są zgodne. Dla 21982 pochodnych współrzędnych EPSG:2180
maksimum różnicy wynosi `1.9208528101444244e-9 m`, przy tolerancji `1e-8 m`.

Odbiór CI używa GDAL 3.12 z QGIS i rejestru PROJ zgodnego z CI; WKT nie
uznano automatycznie za równoważne innej deklaracji macowego GDAL 3.13.3.
Poza wyżej wymienionymi czasami/tokenami normalizowano techniczne warianty
indeksów RTree i triggerów GDAL dopiero po odtworzeniu indeksów z geometrii,
`rtreecheck` oraz sprawdzeniu zmiany geometrii/fid, null, insert/delete na
kopiach. Wartości XML XLSX porównano po odczycie każdej komórki wraz z typem
oraz formatem; pozostałe deklaracje XML zachowano ściśle.

Dokumentacja: +121/−13; bilans łącznie z odbiorem względem bazy refaktoru.

Zakończ po U05. Następna karta: [U06](U06-write-result.md), po U04.
