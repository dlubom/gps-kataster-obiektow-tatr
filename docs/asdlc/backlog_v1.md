# AS-DLC backlog V1

Stan na: 2026-05-17

## Status realizacji

- PBI-001: wykonane 2026-05-15. Struktura katalogow zostala utworzona, shapefile przeniesione do `data/shapes/`, dodano podstawowy `.gitignore`.
- Pamiec operacyjna: dodano `AGENTS.md` i `docs/asdlc/context.md`, zeby kolejny agent mogl odtworzyc stan projektu bez historii rozmowy.
- PBI-002: wykonane 2026-05-15. Dodano `pyproject.toml`, `uv.lock`, minimalny pakiet pod `src/`, test dymny oraz konfiguracje `ruff` i `pytest`.
- PBI-003: wykonane 2026-05-15. Dodano `config/prefixes.yml` z mapowaniem 18 dolin oraz fallbackami `PL` i `SK`; testy sprawdzaja zgodnosc z `data/shapes/doliny.shp` i format prefixow.
- PBI-004: wykonane 2026-05-15. Dodano JSON Schema dla `Obiekt`, `Jaskinia` i `Relacja`, `schema/CHANGELOG.md`, zaleznosc `jsonschema` oraz testy valid/invalid fixture'ow schematu.
- PBI-005: wykonane 2026-05-15. Dodano minimalne fixture'y domenowe dla obiektow i jaskin oraz testy zgodnosci ze schematem i spojnosci cross-reference.
- PBI-006: wykonane 2026-05-15. Dodano modul konwersji WGS84 <-> EPSG:2180 oparty o PyProj, utrwalono konwencje osi `x_1992 = northing`, `y_1992 = easting` oraz testy round-trip i wykrywania zamiany osi.
- PBI-007: wykonane 2026-05-15. Dodano resolver prefixow czytajacy `config/prefixes.yml` i shapefile z `data/shapes/`; wynik rozroznia trafienie w doline, fallback PL/SK z warningiem oraz punkt poza PL/SK jako error.
- PBI-008: wykonane 2026-05-15. Dodano `scripts/assign_id.py`, ktory przyjmuje `lat lon`, uzywa resolvera prefixow, liczy kolejny numer z `data/objects/{PREFIX}/` i wypisuje propozycje ID razem z ostrzezeniami.
- PBI-009: wykonane 2026-05-15. Dodano loader YAML dla `data/objects/`, `data/caves/` i `data/relations/`, rekordy zachowuja sciezke pliku, a brakujace listy sa normalizowane tylko w pamieci.
- PBI-010: wykonane 2026-05-15. Dodano lokalny walidator danych YAML z kodami regul, poziomami `error` / `warning`, sciezka pliku i opisem; CLI `scripts/validate.py` zwraca kod != 0 tylko przy bledach.
- PBI-011: wykonane 2026-05-15. Wyodrebniono algorytm `best_measurement` do modulu aplikacyjnego, dodano testy priorytetow, dat, dokladnosci, stabilnego remisu, trybu manual oraz ostrzezenia walidatora dla rozjazdu `auto`.
- PBI-012: wykonane 2026-05-16. Dodano profilowanie eksportow CSV PIG i TPN, raport JSON/Markdown w `build/reports/source-profile.*` oraz testy bramek: liczby rekordow, braki, duplikaty i zakresy wspolrzednych; finalne YAML nie sa tworzone.
- PBI-013: wykonane 2026-05-16. Dodano importer staging PIG dla CSV/XLSX, raport JSON/Markdown w `build/staging/pig/`, propozycje `Jaskinia` i wstepnych `Obiekt` z pomiarem PIG oraz testy gwarantujace, ze finalne YAML nie sa zapisywane bez review.
- PBI-014: wykonane 2026-05-16. Dodano importer staging TPN dla CSV/XLSX, dopasowania do finalnych YAML i staging PIG, propozycje pomiarow TPN z `GLOBALID` na obiekcie, `NR_INWENT` na jaskini oraz raport statusow: dopasowane, nowe, nierozstrzygniete i odrzucone.
- PBI-015: wykonane 2026-05-16. Dodano format decyzji operatora, applier staging review i CLI `scripts/importers/apply_review.py`; decyzje `create_cave`, `create_object`, `add_measurement`, `link_cave`, `reject` i `unresolved` materializuja finalne YAML dopiero po poprawnym review.
- PBI-016: wykonane 2026-05-16. Dodano build SQLite `build/katalog.sqlite` z walidowanych YAML, tabelami logicznymi V1, metadanymi licznikow, flagami walidacji i najlepszymi geometriami obiektow w WKT.
- PBI-017: wykonane 2026-05-16. Dodano eksport `best-measurements` z walidowanych YAML do GeoJSON, CSV, GPX i ZIP Shapefile EPSG:2180.
- PBI-018: wykonane 2026-05-16. Eksport release zapisuje `metadata.json` z timestampem, wersjami schematow oraz licznikami obiektow, jaskin, relacji, pomiarow i walidacji.
- PBI-019: wykonane 2026-05-16. Dodano workflow `.github/workflows/validate.yml` uruchamiajacy lokalna bramke `uv sync`, Ruff, pytest i `scripts/validate.py` bez budowania release.
- PBI-020: wykonane 2026-05-16. Dodano lokalny builder artefaktow release, workflow `build.yml` dla `main`, workflow `release.yml` dla tagow `v*` oraz bramke `SOURCE_LICENSE_CONFIRMED=true` przed publikacja release.
- PBI-021: wykonane 2026-05-16. Dodano `docs/operations.md` z procedurami recznego pomiaru, walidacji, miesiecznej paczki danych i statusow weryfikacji oraz test dokumentacji.
- PBI-022: wykonane 2026-05-16. Naprawiono kategorie sztolni z TPN: importer rozpoznaje `GENEZA` / nazwe, a 26 istniejacych obiektow `Sztolnia...` ma `category: sztolnia`.
- PBI-023: wykonane 2026-05-16. Dodano ludzkie `README.md`, przeniesiono surowe PIG/TPN XLSX/CSV do `data/sources/`, dodano opis zrodel i skopiowano pelny dump PIG JSONL do review brakujacych otworow.
- PBI-024: wykonane 2026-05-16. Rozdzielono Mrozna na drugi obiekt otworowy z TPN row 982 oraz dodano slowackie jaskinie `Nova Kresanica` i `Obcasna Vyvieracka`.
- PBI-025: wykonane 2026-05-16. Rozstrzygnieto pozostale wielootworowe przypadki TPN, dodano nowe pomiary GNSS/LIDAR, podlaczono Czarna III do Jaskini Czarnej i nazwano bezimienny rekord TPN jako `BEZ_NAZWY_001`.
- PBI-026: wykonane 2026-05-16. Wprowadzono testy mutacyjne przez `mutmut` dla krytycznych modulow, lokalna konfiguracje w `pyproject.toml`, reczny workflow `mutation.yml`, ignorowanie `mutants/` i dokumentacje uruchamiania.
- PBI-027: wykonane 2026-05-16. Doprecyzowano w README i dokumentacji operacyjnej, ze `verification_status: nieweryfikowany` w release jest oczekiwany dla importow PIG/TPN i nie oznacza automatycznie bledu danych.
- PBI-028: wykonane 2026-05-17. Udokumentowano kolumny i pola artefaktow release oraz dodano `object_notes`, `cave_notes` i `measurement_notes` do plaskich eksportow `best-measurements`.

## Przyjęty poziom AS-DLC

Dla tego projektu wybieramy lekki wariant `spec-anchored`:

- specyfikacja w repo jest zrodlem prawdy dla stanu systemu,
- zadania sa malymi PBI, czyli opisami zmiany do wykonania,
- kazde PBI ma jawny zakres, zaleznosci i sposob weryfikacji,
- nie wprowadzamy ciezkiego procesu ani osobnego systemu zarzadzania zadaniami,
- odkrycia z implementacji wracaja do specyfikacji albo do tego backlogu.

## Przeglad aktualnych plikow

Repo jest na etapie zalazka. Zmiany sa zatwierdzane po kolejnych PBI.

| Plik / katalog | Stan | Uwagi |
|---|---:|---|
| `specyfikacja_gps_kataster_obiektow_tatr_v_2.md` | 42 959 B | Specyfikacja draft v2, opisuje model domeny, ID, import, walidacje, build i etapy. |
| `README.md` | istnieje | Ludzkie wejscie do repo: cel projektu, struktura, model i komendy startowe. |
| `data/sources/pig/pig_otwory_jaskin_.xlsx` | 1 arkusz `Export`, 861 wierszy, 15 kolumn | Zrodlo PIG / Jaskinie Polski. |
| `data/sources/pig/pig_otwory_jaskin_.xlsx.-.Export.csv` | 860 rekordow danych | Eksport CSV PIG; kolumny m.in. `ID`, `Nazwa`, `Nr inw.`, `X 1992`, `Y 1992`, `B`, `L`, `Link`. |
| `data/sources/pig/jaskinie_polski_pig_dump.jsonl` | 5388 rekordow JSONL | Pelniejszy dump PIG do recznego sprawdzania opisow jaskin, liczby otworow i nazw otworow. |
| `data/sources/tpn/tpn_otwory_jaskin.xlsx` | 1 arkusz `Export`, 1006 wierszy, 23 kolumny | Zrodlo TPN. |
| `data/sources/tpn/tpn_otwory_jaskin.xlsx.-.Export.csv` | 1005 rekordow danych | Eksport CSV TPN; kolumny m.in. `NR_INWENT`, `NAZWA`, `GLOBALID`, `X1992`, `Y1992`, `Z`. |
| `data/sources/README.md` | istnieje | Opisuje zrodla, zakres dumpu PIG i workflow grep/review dla brakujacych otworow. |
| `data/objects/` | 1005 finalnych YAML | Obiekty terenowe po imporcie/review, w tym `sztolnia`, `wywierzysko` i fallback `SK`. |
| `data/caves/` | 1004 finalne YAML | Jaskinie / pozycje katalogowe; jedna jaskinia moze wskazywac wiele obiektow. |
| `data/shapes/doliny.*` | 18 feature'ow, EPSG:2180 | Polygony dolin, pole kluczowe `NAME`. |
| `data/shapes/granica_polski.*` | 1 feature, EPSG:2180 | Fallback granicy Polski. |
| `data/shapes/granica_slowacji.*` | 1 feature, EPSG:2180 | Fallback granicy Slowacji. |
| `data/shapes/README.md` | istnieje | Opisuje warstwy i algorytm prefixow. |
| `config/prefixes.yml` | 18 dolin + 2 fallbacki | Zrodlo prawdy dla prefixow ID. |
| `tests/test_prefixes.py` | 2 testy | Sprawdza mapowanie `doliny.shp` i format prefixow. |
| `schema/*.schema.json` | 3 schematy | Kontrakty YAML dla `Obiekt`, `Jaskinia` i `Relacja`. |
| `schema/CHANGELOG.md` | istnieje | Wpis dla `schema_version: 1`. |
| `tests/test_schemas.py` | 7 testow | Sprawdza poprawnosc schematow oraz valid/invalid fixture'y PBI-004. |
| `tests/fixtures/*.yml` | 5 fixture'ow | Minimalny zestaw domenowy PBI-005: obiekt, jaskinia, TPN `GLOBALID`, PIG + `NR_INWENT`, reczny `best_measurement`. |
| `tests/test_domain_fixtures.py` | 9 testow | Sprawdza zgodnosc fixture'ow domenowych ze schematami oraz referencje `cave_id` / `object_ids`. |
| `src/gps_kataster_obiektow_tatr/coordinates.py` | istnieje | Konwersja WGS84 <-> EPSG:2180 przez PyProj, z projektowa konwencja osi `x_1992 = northing`, `y_1992 = easting`. |
| `tests/test_coordinates.py` | 5 testow | Sprawdza round-trip kilku punktow tatrzanskich, zgodnosc z osiami PIG/PL-1992 i wykrywanie zamiany osi. |
| `src/gps_kataster_obiektow_tatr/prefix_resolver.py` | istnieje | Resolver prefixow ID: doliny przez point-in-polygon, fallback PL/SK i jawne statusy `ok` / `warning` / `error`. |
| `tests/test_prefix_resolver.py` | 4 testy | Sprawdza punkt w dolinie, punkt w Polsce poza dolinami, punkt po stronie slowackiej i punkt poza PL/SK. |
| `scripts/assign_id.py` | istnieje | CLI i helpery do proponowania kolejnego ID z `lat lon`, resolvera prefixu i plikow w `data/objects/{PREFIX}/`. |
| `tests/test_assign_id.py` | 6 testow | Sprawdza pusty prefix, istniejace pliki, licznik ponad `9999`, warningi resolvera, blad bez prefixu i uruchomienie CLI. |
| `src/gps_kataster_obiektow_tatr/data_loader.py` | istnieje | Loader zrodlowych YAML: obiekty, jaskinie i relacje z `data/`, sciezki plikow dla raportow oraz pamieciowe domyslne puste listy. |
| `tests/test_data_loader.py` | 3 testy | Sprawdza wczytanie fixture'ow, zachowanie sciezek, normalizacje list bez zapisu do YAML oraz blad skladni YAML z czytelna sciezka. |
| `src/gps_kataster_obiektow_tatr/best_measurement.py` | istnieje | Domyslny algorytm `best_measurement.mode: auto`: priorytet zrodel, data, dokladnosc i stabilny remis po `measurement.id`. |
| `src/gps_kataster_obiektow_tatr/source_table.py` | istnieje | Wspolny czytnik tabel zrodlowych CSV/XLSX dla importerow staging. |
| `src/gps_kataster_obiektow_tatr/source_profile.py` | istnieje | Profilowanie CSV PIG/TPN przed importem staging: braki kluczowych pol, duplikaty i zakresy kolumn liczbowych. |
| `src/gps_kataster_obiektow_tatr/pig_staging.py` | istnieje | Importer staging PIG: czyta CSV/XLSX, tworzy propozycje `Jaskinia` i wstepnych `Obiekt` z niskopriorytetowym pomiarem PIG oraz raport JSON/Markdown. |
| `src/gps_kataster_obiektow_tatr/tpn_staging.py` | istnieje | Importer staging TPN: czyta CSV/XLSX, tworzy propozycje pomiarow TPN, dopasowuje do YAML/staging PIG i raportuje statusy review. |
| `src/gps_kataster_obiektow_tatr/staging_review.py` | istnieje | Applier decyzji operatora: materializuje staging do finalnych YAML, dopisuje pomiary TPN, laczy obiekty z jaskiniami i blokuje zapis przy blednych decyzjach. |
| `src/gps_kataster_obiektow_tatr/build_db.py` | istnieje | Build SQLite: waliduje YAML, tworzy tabele logiczne, zapisuje pomiary, referencje, relacje, `metadata`, `validation_flags` oraz najlepsze geometrie obiektow. |
| `src/gps_kataster_obiektow_tatr/best_measurements_export.py` | istnieje | Eksport najlepszych pomiarow: GeoJSON WGS84, CSV WGS84 + EPSG:2180, GPX WGS84, Shapefile ZIP EPSG:2180, notatki obiektu/jaskini/pomiaru oraz `metadata.json`. |
| `src/gps_kataster_obiektow_tatr/release_artifacts.py` | istnieje | Wspolny builder artefaktow release: SQLite, eksporty best-measurements, metadata i `katalog.sqlite.zip`. |
| `tests/test_best_measurement.py` | 11 testow | Sprawdza wszystkie priorytety wyboru, remis dat/dokladnosci/ID oraz fallback do odrzuconych pomiarow. |
| `src/gps_kataster_obiektow_tatr/validator.py` | istnieje | Walidator lokalny: JSON Schema, unikalnosc ID, referencje cross-file, spojnosci wspolrzednych, reguly przestrzenne i ostrzezenia domenowe. |
| `scripts/validate.py` | istnieje | CLI walidatora; wypisuje `kod`, `poziom`, `plik`, `opis` i konczy kodem 1 tylko dla error. |
| `scripts/profile_sources.py` | istnieje | CLI generujace `build/reports/source-profile.json` i `build/reports/source-profile.md` z eksportow CSV PIG/TPN. |
| `scripts/importers/import_pig.py` | istnieje | CLI generujace `build/staging/pig/pig-staging.json` i `.md` bez zapisu finalnych YAML. |
| `scripts/importers/import_tpn.py` | istnieje | CLI generujace `build/staging/tpn/tpn-staging.json` i `.md` bez zapisu finalnych YAML. |
| `scripts/importers/apply_review.py` | istnieje | CLI stosujace plik decyzji operatora do staging PIG/TPN i zapisujace raport review oraz finalne YAML. |
| `scripts/build_db.py` | istnieje | CLI generujace `build/katalog.sqlite` z `data/` albo wskazanego katalogu testowego. |
| `scripts/export_best_measurements.py` | istnieje | CLI generujace `build/exports/best-measurements.geojson`, `.csv`, `.gpx`, `.shp.zip` i `metadata.json`. |
| `scripts/build_release_artifacts.py` | istnieje | Lokalny dry-run buildu/release generujacy pelny zestaw artefaktow: SQLite, eksporty, metadata i ZIP SQLite. |
| `.github/workflows/validate.yml` | istnieje | Workflow CI dla PR i push do `main`: `uv sync`, Ruff, pytest i `scripts/validate.py`; bez build/release. |
| `.github/workflows/mutation.yml` | istnieje | Reczny workflow `workflow_dispatch` uruchamiajacy baseline pytest, `mutmut run` i eksport statystyk mutacyjnych. |
| `.github/workflows/build.yml` | istnieje | Workflow po push/merge do `main`: waliduje YAML, buduje artefakty release i publikuje je jako GitHub Actions artifact. |
| `.github/workflows/release.yml` | istnieje | Workflow dla tagow `v*`: wymaga `SOURCE_LICENSE_CONFIRMED=true`, buduje artefakty i publikuje GitHub Release. |
| `docs/operations.md` | istnieje | Dokumentacja operacyjna PBI-021: reczny pomiar, walidacja, miesieczna paczka danych, statusy `zweryfikowany` / `odrzucony`. |
| `docs/release_artifacts.md` | istnieje | Przeglad plikow release, kolumn/pol CSV, GeoJSON, Shapefile, GPX, metadata i SQLite oraz decyzja o rozdzieleniu notatek. |
| `docs/asdlc/staging_review_decisions.md` | istnieje | Dokumentuje format pliku decyzji operatora i znaczenie akcji PBI-015. |
| `tests/test_validator.py` | 9 testow | Sprawdza duplikat ID, zly `best_measurement`, brak `manual.reason`, zle wspolrzedne, ostrzezenia PBI-010, warningi `best_measurement` PBI-011 oraz exit code CLI. |
| `tests/test_source_profile.py` | 4 testy | Sprawdza profilowanie brakow, duplikatow, zakresow wspolrzednych, zapis raportow i brak tworzenia finalnych YAML. |
| `tests/test_pig_staging.py` | 5 testow | Sprawdza mapowanie referencji PIG/NR_INWENT na jaskinie, niskopriorytetowe pomiary PIG, czytanie XLSX, raport staging oraz brak finalnych YAML. |
| `tests/test_tpn_staging.py` | 6 testow | Sprawdza dopasowanie TPN do staging PIG, nowe obiekty, nierozstrzygniete duplikaty, XLSX, raporty i CLI bez zapisu finalnych YAML. |
| `tests/test_staging_review.py` | 3 testy | Sprawdza sample staging -> decyzje -> finalne YAML -> `validate.py`, decyzje link/reject/unresolved oraz blokade zapisu przy bledach. |
| `tests/test_build_db.py` | 3 testy | Sprawdza build SQLite na fixture'ach, liczby w `metadata`, najlepsze geometrie, CLI i blokade buildu przy bledach walidacji. |
| `tests/test_best_measurements_export.py` | 4 testy | Sprawdza eksport tylko najlepszych pomiarow do GeoJSON/CSV/GPX/Shapefile ZIP, notatki w plaskich eksportach, snapshot `metadata.json`, CLI oraz blokade przy blednej walidacji YAML. |
| `tests/test_ci_workflow.py` | 5 testow | Sprawdza workflow walidacyjny, build/release triggery, upload artefaktow i bramke licencji przed release. |
| `tests/test_mutation_tooling.py` | 3 testy | Sprawdza zaleznosc i konfiguracje `mutmut`, reczny workflow mutacyjny oraz ignorowanie katalogu `mutants/`. |
| `tests/test_release_artifacts.py` | 2 testy | Sprawdza wspolny lokalny dry-run artefaktow release, w tym `katalog.sqlite.zip` i CLI. |
| `tests/test_operational_docs.py` | 2 testy | Sprawdza, ze dokumentacja operacyjna pokrywa zakres PBI-021 i przypomina, ze `build/` nie jest zrodlem prawdy. |

## Bramka kontekstu

Przed implementacja V1 obowiazuja te stale decyzje:

- `Obiekt` to konkretny punkt terenowy, a `Jaskinia` to encja katalogowa/logiczna.
- TPN `GLOBALID` trafia zasadniczo do `Obiekt.external_refs`.
- PIG `ID`, PIG `Link` i `NR_INWENT` trafiaja zasadniczo do `Jaskinia.external_refs`.
- YAML w `data/` jest zrodlem prawdy; SQLite, GeoJSON, GPX, CSV i Shapefile sa artefaktami.
- Frontend, PWA, stale importy, Geoportal i GitHub API sa poza V1.

## Milestone 0: porzadek repo

### PBI-001: Uporzadkowac strukture katalogow

Zakres:

- utworzyc docelowe katalogi `config/`, `data/shapes/`, `data/objects/`, `data/caves/`, `data/relations/`, `data/attachments/`, `schema/`, `scripts/`, `tests/fixtures/`,
- przeniesc `shapes/*` do `data/shapes/`,
- dodac `.gitignore` dla `build/`, cache'y Pythona i lokalnych artefaktow,
- nie zmieniac jeszcze danych zrodlowych TPN/PIG.

Weryfikacja:

- `rg --files` pokazuje strukture zgodna ze specyfikacja,
- shapefile po przeniesieniu nadal otwieraja sie przez `ogrinfo`.

### PBI-002: Utworzyc minimalny projekt Pythonowy

Status: wykonane 2026-05-15.

Zakres:

- dodac `pyproject.toml`,
- skonfigurowac `uv`, `ruff`, `pytest`,
- dodac minimalny pakiet projektu pod `src/`,
- ustalic jedna komende lokalna dla testow i walidacji.

Weryfikacja:

- `uv sync`,
- `uv run ruff check src tests`,
- `uv run pytest`.

### PBI-003: Dodac konfiguracje prefixow

Status: wykonane 2026-05-15.

Zakres:

- utworzyc `config/prefixes.yml`,
- odwzorowac 18 nazw z `data/shapes/doliny.shp` na prefixy ze specyfikacji,
- dodac fallbacki `PL` i `SK`,
- dodac test wykrywajacy brak mapowania dla polygonu doliny.

Weryfikacja:

- test czy kazdy `NAME` z warstwy dolin ma prefix,
- test czy prefix ma format 2-3 uppercase ASCII.

## Milestone 1: kontrakty danych

### PBI-004: Zdefiniowac JSON Schema dla YAML

Status: wykonane 2026-05-15.

Zakres:

- dodac `schema/object.schema.json`,
- dodac `schema/cave.schema.json`,
- dodac `schema/relation.schema.json`,
- dodac `schema/CHANGELOG.md` z wpisem dla `schema_version: 1`.

Weryfikacja:

- pozytywne fixture'y przechodza walidacje schematu,
- negatywne fixture'y padaja na oczekiwanych polach.

### PBI-005: Dodac minimalne fixture'y domenowe

Status: wykonane 2026-05-15.

Zakres:

- `tests/fixtures/valid-object.yml`,
- `tests/fixtures/valid-cave.yml`,
- `tests/fixtures/object-with-tpn-globalid.yml`,
- `tests/fixtures/cave-with-pig-and-nr-inwent.yml`,
- `tests/fixtures/object-with-manual-best.yml`.

Weryfikacja:

- fixture'y sa zgodne ze schematem,
- cross-reference `cave_id` i `object_ids` da sie sprawdzic walidatorem.

## Milestone 2: geografia i ID

### PBI-006: Wprowadzic konwersje WGS84 <-> EPSG:2180

Status: wykonane 2026-05-15.

Zakres:

- dodac modul konwersji wspolrzednych,
- zachowac konwencje osi ze specyfikacji: `x_1992 = northing`, `y_1992 = easting`,
- dodac tolerancje walidacji spojnosci.

Weryfikacja:

- test round-trip dla kilku punktow z Tatr,
- test wykrywajacy zamiane osi.

### PBI-007: Zaimplementowac resolver prefixu

Status: wykonane 2026-05-15.

Zakres:

- czytac warstwy z `data/shapes/`,
- robic point-in-polygon dla dolin,
- robic fallback PL/SK,
- zwracac warning dla punktu poza dolinami, ale w PL/SK,
- zwracac error dla punktu poza PL/SK.

Weryfikacja:

- test punktu w dolinie,
- test punktu w Polsce poza dolinami,
- test punktu po stronie slowackiej,
- test punktu poza PL/SK.

### PBI-008: Dodac `scripts/assign_id.py`

Status: wykonane 2026-05-15.

Zakres:

- przyjmowac `lat lon`,
- wyliczac prefix,
- znajdowac kolejny numer w `data/objects/{PREFIX}/`,
- wypisywac proponowane ID i ostrzezenia.

Weryfikacja:

- test pustego prefixu daje `PREFIX-0001`,
- test istniejacych plikow daje kolejny numer,
- konflikt ID pozostaje zadaniem walidatora.

## Milestone 3: walidator lokalny

### PBI-009: Loader danych YAML

Status: wykonane 2026-05-15.

Zakres:

- czytac obiekty, jaskinie i relacje z `data/`,
- zachowac informacje o sciezce pliku dla raportow,
- normalizowac brakujace listy do pustych list tylko w kodzie, nie nadpisujac YAML.

Weryfikacja:

- test wczytania fixture'ow,
- test bledu YAML z czytelna sciezka.

### PBI-010: Reguly walidacji error/warning

Status: wykonane 2026-05-15.

Zakres:

- zaimplementowac bledy i ostrzezenia z sekcji 11.1 specyfikacji,
- raportowac kod reguly, poziom, plik i opis,
- zakonczyc proces kodem != 0 tylko dla error.

Weryfikacja:

- testy dla duplikatu ID, zlego `best_measurement`, braku `manual.reason`, zlych wspolrzednych,
- test warningow dla braku `horizontal_accuracy_m`, `category: jaskinia_otwor` bez `cave_id`, zlej lokalizacji referencji PIG/NR_INWENT.

### PBI-011: Algorytm `best_measurement`

Status: wykonane 2026-05-15.

Zakres:

- zaimplementowac priorytet: wlasne zweryfikowane > TPN > wlasne nieweryfikowane > PIG > geoportal/publikacja/inne,
- uwzglednic date, dokladnosc i stabilny tie-breaker po `measurement.id`,
- respektowac `mode: manual`.

Weryfikacja:

- testy wszystkich priorytetow,
- test remisu dat i dokladnosci,
- test warningu gdy `mode: auto` wskazuje inny pomiar niz algorytm.

## Milestone 4: import poczatkowy jako staging

### PBI-012: Profil danych PIG i TPN

Status: wykonane 2026-05-16.

Zakres:

- policzyc puste wartosci w kluczowych kolumnach,
- sprawdzic duplikaty `PIG.ID`, `Nr inw.`, `TPN.GLOBALID`, `NR_INWENT`,
- sprawdzic zakresy wspolrzednych,
- zapisac raport do `build/reports/source-profile.*`.

Weryfikacja:

- raport zawiera liczby rekordow, kolumny, duplikaty i braki,
- zadne finalne YAML nie sa jeszcze tworzone.

### PBI-013: Importer staging PIG

Status: wykonane 2026-05-16.

Zakres:

- czytac CSV/XLSX PIG,
- tworzyc propozycje `Jaskinia`,
- tworzyc wstepny `Obiekt` i pomiar PIG tylko tam, gdzie da sie jednoznacznie przypisac punkt,
- nie zapisywac finalnych plikow bez review.

Weryfikacja:

- staging ma referencje PIG i `NR_INWENT` po stronie jaskini,
- pomiary PIG maja niski priorytet i `verification_status: nieweryfikowany`.

### PBI-014: Importer staging TPN

Status: wykonane 2026-05-16.

Zakres:

- czytac CSV/XLSX TPN,
- tworzyc pomiary TPN z `GLOBALID`,
- dopasowywac po `GLOBALID`, `NR_INWENT`, nazwie i odleglosci,
- raportowac przypadki niejednoznaczne.

Weryfikacja:

- `GLOBALID` trafia do referencji obiektu,
- `NR_INWENT` trafia do referencji jaskini,
- wygenerowany raport pokazuje: dopasowane, nowe, nierozstrzygniete, odrzucone.

### PBI-015: Operator review dla staging

Status: wykonane 2026-05-16.

Zakres:

- przygotowac format raportu decyzji operatora,
- obsluzyc decyzje: nowy obiekt, nowy pomiar obiektu, nowa jaskinia, powiazanie z jaskinia, odrzucenie, nierozstrzygniete,
- wygenerowac finalne YAML dopiero po decyzjach.

Weryfikacja:

- sample staging -> decyzje -> finalne YAML przechodzi `validate.py`;
- bledna decyzja blokuje zapis finalnych YAML.

## Milestone 5: build i eksporty

### PBI-016: Build SQLite

Status: wykonane 2026-05-16.

Zakres:

- czytac zwalidowane YAML,
- budowac `build/katalog.sqlite`,
- tworzyc tabele logiczne ze specyfikacji,
- zapisac najlepsze geometrie obiektow.

Weryfikacja:

- test na fixture'ach tworzy SQLite,
- liczby w `metadata` zgadzaja sie z liczba plikow YAML.

### PBI-017: Eksport `best-measurements`

Status: wykonane 2026-05-16.

Zakres:

- wygenerowac GeoJSON,
- wygenerowac CSV,
- wygenerowac GPX,
- przygotowac Shapefile ZIP, jesli zaleznosci geospatial sa gotowe.

Weryfikacja:

- eksport zawiera tylko najlepsze pomiary,
- CSV ma WGS84 i EPSG:2180,
- GeoJSON ma poprawne `FeatureCollection`.

### PBI-018: Metadata release

Status: wykonane 2026-05-16.

Zakres:

- wygenerowac `metadata.json`,
- zapisac liczby obiektow, jaskin, pomiarow, ostrzezen walidacji, wersje schematu i timestamp buildu.

Weryfikacja:

- test snapshotu `metadata.json` na fixture'ach.

## Milestone 6: CI, release, operacje

### PBI-019: CI walidacyjne

Status: wykonane 2026-05-16.

Zakres:

- dodac `.github/workflows/validate.yml`,
- uruchamiac `uv sync`, `ruff`, `pytest`, `scripts/validate.py`.

Weryfikacja:

- lokalne komendy sa takie same jak w CI,
- workflow nie buduje release'ow.

### PBI-020: Build/release workflow

Status: wykonane 2026-05-16.

Zakres:

- dodac `build.yml` po merge do `main`,
- dodac `release.yml` dla tagow `v*`,
- publikowac artefakty buildu/release.

Weryfikacja:

- dry-run lokalny buildu generuje wszystkie oczekiwane pliki,
- release nie probuje publikowac danych bez potwierdzenia licencji zrodel.

### PBI-021: Dokumentacja operacyjna

Status: wykonane 2026-05-16.

Zakres:

- opisac jak dodac nowy pomiar recznie,
- opisac jak uruchomic walidacje,
- opisac jak przygotowac miesieczna paczke danych,
- opisac zasady weryfikacji `zweryfikowany` / `odrzucony`.

Weryfikacja:

- nowa osoba moze na podstawie dokumentu dodac fixture'owy pomiar i przejsc walidacje.

## Milestone 7: poprawki po pierwszym release

### PBI-022: Poprawic kategorie sztolni z TPN

Status: wykonane 2026-05-16.

Zakres:

- importer staging TPN rozpoznaje `category` z `GENEZA` i nazwy obiektu,
- `sztolnia` w `GENEZA` albo nazwie daje `category: sztolnia`,
- istniejace finalne obiekty `Sztolnia...` zostaly przestawione z
  `jaskinia_otwor` na `sztolnia`.

Weryfikacja:

- test importera dla nowej sztolni z TPN,
- kontrola 26 istniejacych obiektow o nazwie zawierajacej `sztoln`,
- `scripts/validate.py` bez errorow.

### PBI-023: Uporzadkowac zrodla i dokumentacje dla ludzi

Status: wykonane 2026-05-16.

Zakres:

- dodac top-level `README.md` z opisem projektu dla GitHuba,
- przeniesc PIG/TPN XLSX i CSV z root do `data/sources/{pig,tpn}/`,
- dodac `data/sources/README.md`,
- skopiowac `jaskinie_polski_pig_dump.jsonl` do `data/sources/pig/`,
- opisac w `docs/operations.md` workflow grep/review dla brakujacych otworow.

Weryfikacja:

- domyslne sciezki importerow i profilowania wskazuja `data/sources/`,
- `rg -n "Mroźna" data/sources/pig/jaskinie_polski_pig_dump.jsonl` znajduje
  rekord PIG z informacja o drugim otworze,
- lokalna walidacja danych przechodzi bez errorow.

### PBI-024: Dopelnic znane brakujace obiekty

Status: wykonane 2026-05-16.

Zakres:

- rozdzielic Jaskinie Mrozna na dwa obiekty otworowe:
  `KSW-0081` i `KSW-0256`,
- dopisac `KSW-0256` do `C-0267.object_ids`,
- dodac slowacka `Nova Kresanica` jako `SK-0001` / `C-1003`,
- dodac `Obcasna Vyvieracka` jako `SK-0002` / `C-1004` z
  `category: jaskinia_otwor`,
- zapisac przeliczenie `E19:55:47.53 N49:13:35.8` na WGS84 decimal:
  lon `19.92986944`, lat `49.22661111`.

Weryfikacja:

- `scripts/assign_id.py` wskazuje prefix `KSW` dla drugiego otworu Mroznej i
  fallback `SK` dla obu slowackich punktow,
- `scripts/validate.py` bez errorow; znane ostrzezenia pozostaja nieblokujace.

### PBI-025: Rozstrzygnac wielootworowe przypadki i nowe pomiary

Status: wykonane 2026-05-16.

Zakres:

- rozdzielic Jaskinie Bandzioch Kominiarski na gorny obiekt `LEJ-0002` i nowy
  dolny obiekt `KSZ-0112`,
- dodac gorny otwor Jaskini Zimnej / Jaskinie Biala jako `KSW-0257`, bez
  tworzenia osobnej jaskini,
- podlaczyc `KSW-0240` jako Jaskinie Czarna III do `C-0699` i usunac
  duplikatowa jaskinie `C-0876`,
- dopisac pomiary GNSS+LIDAR z 2026-05-09 dla glownego otworu Jaskini Czarnej
  i Jaskini Czarnej III, z opisem odczytu Dariusza Lubomskiego z
  `https://cloud.wrogeo.pl/`,
- oznaczyc `Jaskinie Pawlikowskiego` jako system dla Mylnej, Oblazkowej i
  Raptawickiej, dodac pomiary Pawlikowskiego i materializowac polnocny otwor
  Mylnej jako `KSZ-0113`,
- dodac wschodni / SE otwor Jaskini nad Korytem jako `MLZ-0108`,
- dopisac pomiar `Wysoka7Progow` do istniejacej Jaskini Wysokiej `KSW-0189`,
- nazwac bezimienny TPN row 273 / `STR-0024` jako `BEZ_NAZWY_001`.

Weryfikacja:

- `scripts/validate.py` bez errorow,
- finalny katalog ma 1009 obiektow, 1003 jaskinie i 1875 pomiarow,
- znane ostrzezenia walidatora pozostaja nieblokujace:
  `MISSING_HORIZONTAL_ACCURACY`, `MEASUREMENT_OUTSIDE_VALLEYS`,
  `MEASUREMENT_DISTANCE_OUTLIER` i `OBJECT_PREFIX_MISMATCH`.

### PBI-026: Wprowadzic testy mutacyjne

Status: wykonane 2026-05-16.

Zakres:

- dodac `mutmut` jako zaleznosc developerska utrwalona w `uv.lock`,
- skonfigurowac zakres mutacji w `pyproject.toml` dla krytycznych modulow:
  `best_measurement`, `coordinates`, `prefix_resolver`, `validator`,
  staging PIG/TPN oraz `staging_review`,
- dodac reczny workflow `.github/workflows/mutation.yml` uruchamiany przez
  `workflow_dispatch`, bez obciazania standardowego PR CI,
- ignorowac lokalny katalog wynikow `mutants/`,
- opisac uruchamianie w `README.md` i `docs/operations.md`.

Weryfikacja:

- test konfiguracji `mutmut`,
- test workflow mutacyjnego,
- `uv run mutmut run --max-children 2 'gps_kataster_obiektow_tatr.best_measurement*'`
  przechodzi dla `best_measurement` bez przezytych mutantow,
- pelna lokalna bramka Ruff, pytest i `scripts/validate.py` przechodzi bez
  errorow.

### PBI-027: Wyjasnic `nieweryfikowany` w release

Status: wykonane 2026-05-16.

Zakres:

- dopisac w `README.md`, ze poczatkowe release'y moga miec wiekszosc
  najlepszych pomiarow jako `verification_status: nieweryfikowany`,
- dopisac w `docs/operations.md`, ze status oznacza brak projektowego review,
  a nie automatyczny blad danych albo brak proweniencji,
- utrwalic zasade, ze statusow importow PIG/TPN nie zmieniamy hurtowo na
  `zweryfikowany`.

Weryfikacja:

- test dokumentacji operacyjnej sprawdza obecnosc wyjasnienia dla release.

### PBI-028: Udokumentowac kolumny release i dodac notatki do eksportow

Status: wykonane 2026-05-17.

Zakres:

- przejrzec lokalny zestaw release: SQLite, CSV, GeoJSON, GPX, Shapefile ZIP i
  `metadata.json`,
- dodac dokument `docs/release_artifacts.md` opisujacy, ktory plik zawiera
  jakie kolumny albo pola,
- dodac do plaskich eksportow `best-measurements` rozdzielone notatki:
  `object_notes`, `cave_notes`, `measurement_notes`,
- w Shapefile uzyc skroconych nazw DBF: `obj_notes`, `cave_notes`,
  `meas_notes`,
- dopisac notatki do opisu waypointow GPX.

Weryfikacja:

- test eksportu sprawdza notatki w GeoJSON, CSV, GPX i Shapefile,
- pelna lokalna bramka Ruff, pytest, walidacja YAML i build artefaktow release.

## Proponowana kolejnosc startowa

Najmniejsza sensowna sciezka do pierwszego dzialajacego przeplywu:

1. PBI-001: struktura repo.
2. PBI-002: projekt Pythonowy.
3. PBI-003: `config/prefixes.yml`.
4. PBI-004 + PBI-005: schematy i fixture'y.
5. PBI-006 + PBI-007: wspolrzedne i prefixy.
6. PBI-009 + PBI-010 + PBI-011: walidator.
7. PBI-008: `assign_id.py`.
8. PBI-016 + PBI-017: minimalny build i eksport.

Import PIG/TPN warto zaczac dopiero po dzialajacym walidatorze, bo inaczej szybko powstanie duzo danych bez bramek jakosci.
