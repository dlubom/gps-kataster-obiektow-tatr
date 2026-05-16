# AS-DLC backlog V1

Stan na: 2026-05-16

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
| `pig_otwory_jaskin_.xlsx` | 1 arkusz `Export`, 861 wierszy, 15 kolumn | Zrodlo PIG / Jaskinie Polski. |
| `pig_otwory_jaskin_.xlsx.-.Export.csv` | 860 rekordow danych | Eksport CSV PIG; kolumny m.in. `ID`, `Nazwa`, `Nr inw.`, `X 1992`, `Y 1992`, `B`, `L`, `Link`. |
| `tpn_otwory_jaskin.xlsx` | 1 arkusz `Export`, 1006 wierszy, 23 kolumny | Zrodlo TPN. |
| `tpn_otwory_jaskin.xlsx.-.Export.csv` | 1005 rekordow danych | Eksport CSV TPN; kolumny m.in. `NR_INWENT`, `NAZWA`, `GLOBALID`, `X1992`, `Y1992`, `Z`. |
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
| `src/gps_kataster_obiektow_tatr/source_profile.py` | istnieje | Profilowanie CSV PIG/TPN przed importem staging: braki kluczowych pol, duplikaty i zakresy kolumn liczbowych. |
| `tests/test_best_measurement.py` | 11 testow | Sprawdza wszystkie priorytety wyboru, remis dat/dokladnosci/ID oraz fallback do odrzuconych pomiarow. |
| `src/gps_kataster_obiektow_tatr/validator.py` | istnieje | Walidator lokalny: JSON Schema, unikalnosc ID, referencje cross-file, spojnosci wspolrzednych, reguly przestrzenne i ostrzezenia domenowe. |
| `scripts/validate.py` | istnieje | CLI walidatora; wypisuje `kod`, `poziom`, `plik`, `opis` i konczy kodem 1 tylko dla error. |
| `scripts/profile_sources.py` | istnieje | CLI generujace `build/reports/source-profile.json` i `build/reports/source-profile.md` z eksportow CSV PIG/TPN. |
| `tests/test_validator.py` | 9 testow | Sprawdza duplikat ID, zly `best_measurement`, brak `manual.reason`, zle wspolrzedne, ostrzezenia PBI-010, warningi `best_measurement` PBI-011 oraz exit code CLI. |
| `tests/test_source_profile.py` | 4 testy | Sprawdza profilowanie brakow, duplikatow, zakresow wspolrzednych, zapis raportow i brak tworzenia finalnych YAML. |

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

Zakres:

- czytac CSV/XLSX PIG,
- tworzyc propozycje `Jaskinia`,
- tworzyc wstepny `Obiekt` i pomiar PIG tylko tam, gdzie da sie jednoznacznie przypisac punkt,
- nie zapisywac finalnych plikow bez review.

Weryfikacja:

- staging ma referencje PIG i `NR_INWENT` po stronie jaskini,
- pomiary PIG maja niski priorytet i `verification_status: nieweryfikowany`.

### PBI-014: Importer staging TPN

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

Zakres:

- przygotowac format raportu decyzji operatora,
- obsluzyc decyzje: nowy obiekt, nowy pomiar obiektu, nowa jaskinia, powiazanie z jaskinia, odrzucenie, nierozstrzygniete,
- wygenerowac finalne YAML dopiero po decyzjach.

Weryfikacja:

- sample staging -> decyzje -> finalne YAML przechodzi `validate.py`.

## Milestone 5: build i eksporty

### PBI-016: Build SQLite

Zakres:

- czytac zwalidowane YAML,
- budowac `build/katalog.sqlite`,
- tworzyc tabele logiczne ze specyfikacji,
- zapisac najlepsze geometrie obiektow.

Weryfikacja:

- test na fixture'ach tworzy SQLite,
- liczby w `metadata` zgadzaja sie z liczba plikow YAML.

### PBI-017: Eksport `best-measurements`

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

Zakres:

- wygenerowac `metadata.json`,
- zapisac liczby obiektow, jaskin, pomiarow, ostrzezen walidacji, wersje schematu i timestamp buildu.

Weryfikacja:

- test snapshotu `metadata.json` na fixture'ach.

## Milestone 6: CI, release, operacje

### PBI-019: CI walidacyjne

Zakres:

- dodac `.github/workflows/validate.yml`,
- uruchamiac `uv sync`, `ruff`, `pytest`, `scripts/validate.py`.

Weryfikacja:

- lokalne komendy sa takie same jak w CI,
- workflow nie buduje release'ow.

### PBI-020: Build/release workflow

Zakres:

- dodac `build.yml` po merge do `main`,
- dodac `release.yml` dla tagow `v*`,
- publikowac artefakty buildu/release.

Weryfikacja:

- dry-run lokalny buildu generuje wszystkie oczekiwane pliki,
- release nie probuje publikowac danych bez potwierdzenia licencji zrodel.

### PBI-021: Dokumentacja operacyjna

Zakres:

- opisac jak dodac nowy pomiar recznie,
- opisac jak uruchomic walidacje,
- opisac jak przygotowac miesieczna paczke danych,
- opisac zasady weryfikacji `zweryfikowany` / `odrzucony`.

Weryfikacja:

- nowa osoba moze na podstawie dokumentu dodac fixture'owy pomiar i przejsc walidacje.

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
