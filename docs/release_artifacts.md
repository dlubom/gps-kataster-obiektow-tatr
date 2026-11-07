# Przeglad artefaktow release

## Paczka testowa w komentarzu PR

Każda nowa i ponownie otwarta PR oraz każdy jej push (także draft)
uruchamia `PR export preview`. Po udanym buildzie komentarz bota
**Paczka testowa eksportów** zawiera link **Pobierz ZIP eksportów**.
Pobierz po zalogowaniu do GitHub i rozpakuj paczkę, aby obejrzeć np.
Excel Best/Full, GPX w GPS lub GeoJSON/Shapefile w QGIS.
ZIP obejmuje wszystkie trzynaście plików wydania wymienionych poniżej,
`preview.json` i `SHA256SUMS` (`sha256sum -c SHA256SUMS` po rozpakowaniu).
Shapefile zachowuje wewnętrzny ZIP; dump i GeoPackage są osobnymi plikami.

Retencja wynosi **14 dni** od uploadu; komentarz pokazuje datę wygaśnięcia.
Po wygaśnięciu uruchom ponownie build albo wypchnij kolejny commit.
Jedna aktualizowana wiadomość pokazuje budowanie, błąd albo najnowszy
link; opis PR i komentarze ludzi pozostają tekstem autora.
Podgląd nie jest oficjalnym wydaniem. Wersja w statystykach pozostaje
pusta, a commit i czas opisują konkretny build podglądu.

Build sprawdza dokładny syntetyczny merge, head i bazę, zapisane w manifeście
i nazwie artefaktu. Opóźnione wyniki, starsze próby oraz paczki dla innej
bazy/merge nie dostają aktualnego linku. Sama zmiana `main` nie uruchamia
nowego buildu; odśwież PR przez push albo ponowne otwarcie. Przy konflikcie
GitHub nie uruchamia `pull_request`: najpierw rozwiąż konflikt.
Komentarz oznacza datowaną migawkę wskazanych SHA, a nie śledzenie bazy na żywo.

Budowa działa bez zapisu do repozytorium i bez sekretów. Komentarz publikuje
osobny `workflow_run`, używający kodu z domyślnej gałęzi i metadanych API.
Nie pobiera ani nie wykonuje paczki ani kodu PR. Fork może wymagać
standardowego zatwierdzenia uruchomienia Actions przez maintainerów.
Zasady: [GitHub workflow_run](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run).

**Pierwsza PR instalacyjna:** automatyczny komentarz ruszy po przyjęciu
publishera na `main` (wymóg GitHub `workflow_run`). W samej instalacyjnej
PR operator dodaje link po sprawdzeniu runu, SHA, 14-dniowej retencji
i pobraniu ZIP-a. Odbiór tego wyjątku jest opisany w PR.

Lokalny odpowiednik buildu (wyjściowy katalog musi jeszcze nie istnieć):

```bash
uv run --frozen python scripts/build_pr_preview.py \
  --output-dir build/local-pr-preview --repository dlubom/gps-kataster-obiektow-tatr \
  --pr-number 1 --head-sha HEAD_SHA --base-sha BASE_SHA --merge-sha MERGE_SHA \
  --run-id 1 --run-attempt 1
```

Lokalne wartości pochodzenia są deklaracją operatora; CI weryfikuje SHA
wobec checkoutu i rodziców commitu. Paczki nie zmieniają tagowego procesu wydania.

## Oficjalna paczka wydania

Ten dokument opisuje lokalna paczke generowana przez:

```bash
uv run --frozen python scripts/build_release_artifacts.py --base-ref origin/main
```

Źródłem prawdy są rekordy YAML w `data/`; `schema/catalog.sql` definiuje
model tymczasowego PostgreSQL/PostGIS.
Pliki w `build/` są artefaktami
pochodnymi i nie sa commitowane.

Builder, CLI, preview i workflow wydania korzystają z jednej kolejności
`ReleaseArtifactsResult.artifact_paths`: 8 plików Best i 5 pozostałych plików
wydania. Przed atomową podmianą builder sprawdza dokładny komplet, bez
braków, dodatkowych plików, powtórzeń, dowiązań ani ścieżek poza katalogiem
wynikowym. Błąd serializera lub odczytu zachowuje poprzedni komplet.

Do paczkowania służy opcjonalne `--artifact-list`. Po udanym buildzie stdout
zawiera wyłącznie 13 ścieżek w dotychczasowej kolejności, każdą zakończoną
bajtem NUL (także ostatnią). Ścieżki zachowują postać `--output-dir`;
spacje i znaki nowej linii nie są separatorami. Bez tej flagi pozostają
komunikaty `wrote:` i podsumowanie. Błędy zachowują dotychczasowe kanały i kody;
listę wolno konsumować wyłącznie po exit 0.

```bash
mkdir -p build
uv run --frozen python scripts/build_release_artifacts.py \
  --base-ref origin/main --artifact-list > build/release-artifacts.list
```

Workflow wydania czyta tę listę jako tablicę argumentów `gh`, bez wildcardu,
ponownego spisu nazw ani wykonywania zawartości listy. Plik listy leży poza
`build/exports/` i nie jest publicznym artefaktem. Paczka wydania nadal ma
13 plików, a preview dodaje tylko `preview.json` i `SHA256SUMS`. Zaufany
publisher komentarza nadal korzysta wyłącznie z metadanych GitHub.

Samodzielny eksport Best publikuje 8 plików z `BestMeasurementsExportResult`.
Po walidacji wejścia i historii nadal odmawia nadpisania katalogu zawierającego
choć jeden z pięciu pozostałych plików pełnego wydania. Do przebudowy pełnej
paczki użyj buildera wydania albo osobnego `--output-dir`.

## Wersjonowanie

Oficjalne wydania sa wersjonowane semver tagami `vX.Y.Z`. Release jest
publikowany recznie przez annotated tag, a notatki GitHub Release pochodza z
sekcji `CHANGELOG.md` o tym samym numerze wersji.

## Zestaw plikow

| Plik | Rola | Geometria / format |
|---|---|---|
| `build/exports/katalog.dump` | Pełny snapshot katalogu z bibliografią i historią. | PostgreSQL custom dump; odtworzenie sprawdzane podczas buildu. |
| `build/exports/katalog.gpkg` | Warstwy Best oraz wszystkich pomiarów. | GeoPackage; geometria Point, jawny CRS, wysokość osobno. |
| `build/exports/best-measurements.csv` | Plaski eksport najlepszego pomiaru dla kazdego obiektu. | CSV, WGS84 + EPSG:2180. |
| `build/exports/best-measurements.geojson` | Ten sam plaski eksport jako warstwa punktowa. | GeoJSON `FeatureCollection`, geometria WGS84 lon/lat. |
| `build/exports/best-measurements.shp.zip` | Warstwa punktowa do QGIS/desktop GIS. | ZIP Shapefile, geometria EPSG:2180. |
| `build/exports/best-measurements.gpx` | Lekki eksport terenowy/nawigacyjny. | GPX waypointy WGS84. |
| `build/exports/chocholowska-lejowa-koscieliska.gpx` | Dodatkowy GPX: Chochołowska, Lejowa i Kościeliska. | Do 500 waypointów WGS84. |
| `build/exports/mietusia-sucha-woda.gpx` | Dodatkowy GPX: od Miętusiej po Suchą Wodę. | Do 500 waypointów WGS84. |
| `build/exports/pozostale-pl-sk.gpx` | Dodatkowy GPX: PL/SK poza regionami dolin. | Do 500 waypointów WGS84. |
| `build/exports/metadata.json` | Metadane paczki i liczniki walidacji. | JSON bez geometrii. |
| `build/exports/statistics.md` | Tabele PL/EN/SK dodawane do opisu wydania. | Markdown, rozwijane sekcje językowe. |
| `build/exports/statistics.json` | Te same statystyki do dalszego przetwarzania. | JSON, `statistics_schema_version: 1`. |
| `build/exports/katalog.xlsx` | Czytelny Excel: wybrane punkty oraz pełne dane z historią. | XLSX, arkusze Best, Full i Jaskinie. |

Statystyki pokazują osobno źródło i sposób wyznaczenia pozycji, dla punktów
Best oraz pełnej historii. `selected_points.by_position_method` i
`measurement_history.by_position_method` zawierają zapisane metody oraz
dwie klasy wynikające z udokumentowanych tagów: `lidar_gnss` (`ustalenie`
z `lidar` i `gnss_anchor`) oraz `survey_anchor` (`source_record` z
`survey_anchor`). Jawna metoda ma pierwszeństwo; dowiązanie do GNSS nie
jest bezpośrednim pomiarem GNSS. Rozbicie nie deklaruje dokładności ani
geodezyjnego rodzaju GNSS. Źródłowe `wlasne` ma etykietę „Opracowania własne”.

## Morfometria

CSV, GeoJSON oraz warstwy `best` i `measurements` GeoPackage podają
`cave_length_m`, `cave_depth_m` i `cave_denivelation_m` w metrach oraz
`cave_denivelation_qualifier` i `cave_morphometry_source_ref`. Shapefile
używa pól `cave_len_m`, `cave_dep_m`, `cave_den_m` (trzy miejsca po
przecinku), `cave_den_q` i `cave_m_ref`. Puste wartości liczbowe są
nieznane. GPX pokazuje znane wymiary i odniesienie do źródła w opisie
punktu oraz oznacza przybliżoną deniwelację przez `~`.

Przy potwierdzonej części CSV, GeoJSON i GeoPackage podają `system_cave_id`,
`cave_system_name`, `system_length_m`, `system_depth_m`,
`system_denivelation_m`, `system_denivelation_qualifier` i
`system_morphometry_source_ref`. Shapefile używa odpowiednio `sys_cav_id`,
`sys_name`, `sys_len_m`, `sys_dep_m`, `sys_den_m`, `sys_den_q` i
`sys_m_ref`. GPX podpisuje dostępne wymiary systemu w opisie otworu.
We wszystkich trzech arkuszach Excel wartości części i systemu mają osobne
kolumny. Rekord zbiorczy bez własnych otworów jest widoczny w arkuszu
Jaskinie i w dumpie.

## `katalog.xlsx`

Generowany przy każdym buildzie wydania, bez osobnego ręcznego kroku.
**Best** ma jeden wiersz na obiekt: te same podstawowe pola wybranego punktu co CSV,
w tym współrzędne WGS84, wysokość, źródło, weryfikację i dokładność.
**Full** ma jeden wiersz na zachowany pomiar z PostgreSQL, także starszy lub
odrzucony, z pełnymi danymi pomiaru i towarzyszącymi danymi obiektu.
Kolumna „Wybrany do eksportu” porównuje ID pomiaru w obrębie tego samego
obiektu. Powtarzające się ID obiektu w Full są historią, nie duplikatami.

**Jaskinie** ma jeden wiersz na pozycję katalogową, także bez przypisanego
otworu. Best i Full pokazują wymiary jaskini obok punktu i pozwalają
powiązać wiersz z arkuszem Jaskinie przez ID jaskini.

Full zachowuje uwagi, dane wyboru, nadania ID i autorstwa; listy referencji,
załączników i relacji są tekstem JSON w osobnych kolumnach. Metadane jaskini
obejmują ID, nazwę, system, uwagi i referencje. Dump PostgreSQL jest pełnym
relacyjnym snapshotem, w tym z bibliografią. Załączniki są opisane, nie osadzone w Excelu.

Oba arkusze mają polskie nagłówki, filtry, pasy wierszy i zamrożone pierwsze
dwie kolumny oraz nagłówki. Liczby i daty dzienne od 1900-01-01 są typowane;
wcześniejsze daty są tekstem ISO `YYYY-MM-DD`, aby zachować je bez zmian.
Znaczniki czasu zachowują oryginalny tekst ISO 8601. Puste komórki nie są zerami.
Nazwy i uwagi są tekstem, nigdy formułami. Długie uwagi/listy można odczytać w pasku formuły
lub po poszerzeniu kolumny. Przekroczenie limitu tekstu komórki Excel powoduje
błąd zamiast cichego obcięcia; zapis XLSX jest atomowy. Właściwości pliku
zawierają wersję wydania, commit i czas generowania. XLSX pojawi się w wydaniach
po v1.0.4, nie zmienia starszych paczek.

## Statystyki wydania

Powstają przy każdym `build_release_artifacts.py` ze wspólnego `ExportData`:
tych samych wybranych punktów co CSV, pozycji katalogowych i pełnej historii
z jednego zwalidowanego stanu PostgreSQL. Dane są przygotowywane raz na build;
statystyki nie odczytują plików ani nie odbudowują historii i indeksu pomiarów.
Oddzielają obiekty od jaskiń i pomiarów; zawierają rodzaje obiektów, źródła,
statusy weryfikacji i liczbę punktów ze znaną/nieznaną dokładnością poziomą.
Historia obejmuje również odrzucone pomiary. Brak dokładności nie jest zerem;
status weryfikacji nie oznacza zawsze sprawdzenia w terenie.

Workflow wydania przekazuje `--release-version "$GITHUB_REF_NAME"`
i `--source-commit "$GITHUB_SHA"`; raport zachowuje też `generated_at`
eksportu. Lokalnie pominięte wartości są `null`, a raport ma oznaczenie
podglądu lokalnego. W JSON: `counts`, `selected_points`, `measurement_history`;
liczniki źródeł/kategorii/statusów zawierają tylko występujące wartości.
Tabele Markdown pokazują także zera. Nie ma ręcznych liczników w README.
Statystyki są dodatkiem dla wydań po v1.0.4; nie aktualizują starszych wydań.

## `best-measurements.csv`

Kazdy wiersz oznacza jeden obiekt i jego autorytatywny
`best_measurement.measurement_id`.

Kolumny:

- identyfikacja obiektu: `object_id`, `category`, `name_local`, `cave_id`,
- wybor najlepszego pomiaru: `measurement_id`, `best_mode`,
  `computed_best_measurement_id`, `best_reason`,
- wspolrzedne: `lat`, `lon`, `x_1992`, `y_1992`, `elevation_m`,
- proweniencja pomiaru: `source`, `source_ref`, `observed_at`,
  `observed_date`, `method`, `verification_status`,
- dokladnosc: `horizontal_accuracy_m`, `vertical_accuracy_m`,
- referencje katalogowe: `nr_inwent`, `pig_id`, `pig_url`, `tpn_globalid`,
- notatki: `object_notes`, `cave_notes`, `measurement_notes`.

## `best-measurements.geojson`

Geometria jest punktem WGS84 w kolejnosci GeoJSON `[lon, lat]`. Wlasciwosci
feature'a sa tym samym zestawem pol co w `best-measurements.csv`.

## `best-measurements.shp.zip`

Shapefile zapisuje geometrie w EPSG:2180. DBF ma krotszy, GIS-przyjazny zestaw
pol:

`object_id`, `name_local`, `category`, `cave_id`, `meas_id`, `lat`, `lon`,
`x_1992`, `y_1992`, `elev_m`, `source`, `nr_inwent`, `pig_id`, `pig_url`,
`tpn_gid`, `obs_date`, `status`, `obj_notes`, `cave_notes`, `meas_notes`.

Uwagi w DBF są limitowane do **254 bajtów UTF-8** na pole; tekst jest
ucinany przed niepełnym znakiem. Dotyczy to `obj_notes`, `cave_notes`
i `meas_notes`. Shapefile nie gwarantuje pełnej treści długich uwag;
CSV, GeoJSON, GPX i dump PostgreSQL zachowują pełny tekst. Plik `.cpg` wskazuje UTF-8.

## `best-measurements.gpx`

GPX nie ma kolumn. Kazdy waypoint zawiera:

- atrybuty `lat` i `lon` w WGS84,
- opcjonalne `ele` oraz `time`,
- `name` ustawione na `name_local` obiektu (nazwę konkretnego otworu);
  przy braku, `null`, pustej nazwie lub samych białych znakach używane jest `object_id`,
- `type` ustawione na `category`,
- `desc` z nazwą, jawnym `object <object_id>`, `measurement_id`, źródłem,
  datą obserwacji oraz notatkami obiektu, jaskini i pomiaru, jeśli istnieją.

Powtarzające się nazwy są dozwolone; trwałe ID w opisie pozwala wskazać konkretny punkt w CSV/Excelu.

### Dodatkowe GPX według grup dolin

`best-measurements.gpx` pozostaje pełnym eksportem, bez limitu 500 punktów.
Trzy dodatkowe pliki mają identyczne waypointy jak pełny GPX, z tym samym
Best, ID, nazwą, współrzędnymi, wysokością, datą i opisem. Zmienia się nazwa
zbioru w metadanych GPX. Każdy punkt trafia do dokładnie jednej grupy:

| Plik | Regiony |
|---|---|
| `chocholowska-lejowa-koscieliska.gpx` | CHZ, CHW, LEJ, KSZ, KSW |
| `mietusia-sucha-woda.gpx` | MTZ, MTW, STN, MLZ, MLW, BRA, STR, DZI, BIA, BYZ, BYW, OLC, SUW |
| `pozostale-pl-sk.gpx` | PL, SK poza polygonami dolin |

Przypisanie pochodzi z `v_measurement_regions` na tym samym połączeniu
PostgreSQL co katalog. `ST_Covers` obejmuje granice poligonów, także granice
ich otworów; przy nakładaniu wygrywa niższy `boundaries.ordinal`.
Eksporter odczytuje region faktycznie wybranego pomiaru (również manual),
nie trwałego ID ani propozycji auto. `ExportData` przechowuje go wewnętrznie;
nie ma ponownego resolvera Pythona ani nowych publicznych kolumn.
Wschód/zachód danej doliny pozostają w jednej grupie. Kolejność punktów
pozostaje zgodna z pełnym GPX, według ID. Powstają też puste pliki grup.

Każdy dodatkowy plik ma najwyżej 500 punktów. Przekroczenie limitu albo
nierozpoznany region przerywa eksport czytelnym błędem przed zapisem jego
plików, bez nadpisania wcześniejszych eksportów. Builder mógł już wcześniej
odtworzyć bazę; nie oznacza to gotowej paczki do publikacji. Nie obcinamy
punktów ani nie rozcinamy dolin automatycznie. Wzrost liczby punktów wymaga
ponownego uzgodnienia grup. `metadata.json` zachowuje dotychczasowy kontrakt.
Pliki są w lokalnym buildzie, podglądzie PR i wydaniach.

## `metadata.json`

Pola:

- `metadata_schema_version`,
- `data_schema_version`,
- `generated_at`,
- `counts.objects`,
- `counts.caves`,
- `counts.relations`,
- `counts.measurements`,
- `counts.validation_warnings`,
- `counts.validation_errors`.

## `katalog.dump`

Custom dump PostgreSQL zawiera pełny model relacyjny, a nie tylko wybrane
punkty. [Schemat SQL](../schema/catalog.sql) jest dokładną definicją tabel,
typów i widoków; [diagramy](architecture/schema.md) pokazują ich powiązania.

| Tabele / widoki | Zawartość |
|---|---|
| `objects`, `caves` | Obiekty terenowe i pozycje katalogowe, źródła, audyt i stan bibliografii. Przynależność otworu wyznacza `objects.cave_id`, a części systemu `caves.system_cave_id`. |
| `measurements`, `measurement_tags` | Pełna uporządkowana historia z natywną geometrią EPSG:4326/2180, wysokością, datum i pochodzeniem. Klucz pomiaru to `(object_id, id)`. |
| `best_policy` | Tryb auto/manual, ręczne wskazanie i uzasadnienie. |
| `v_measurements`, `v_auto_best`, `v_best` | Wyliczone współrzędne, niezależny wynik auto oraz ostatecznie wybrany Best. |
| `object_external_refs`, `cave_external_refs` | Referencje TPN/PIG i pozostałych źródeł, z zachowanymi notatkami. |
| `publications` i trzy tabele `*_citations` | Pełne opisy bibliograficzne oraz przywołania dla jaskiń, obiektów i pomiarów. |
| `attachments`, `relations` | Opisy załączników i powiązania obiektów. Same pliki załączników nie są osadzane w dumpie. |

Do odtworzenia potrzebny jest zgodny PostgreSQL z PostGIS, a do pliku custom
narzędzie `pg_restore`. Nie otwiera się go programem SQLite. Przykład dla
nowej, osobnej bazy na przypiętym PostgreSQL 18/PostGIS 3.6
([runtime](operations.md#runtime-lokalny-i-ci)); standardowe zmienne `PGHOST`,
`PGPORT`, `PGUSER` opisują połączenie:

```bash
createdb kataster_review
pg_restore --exit-on-error --no-owner --no-privileges \
  --dbname kataster_review build/exports/katalog.dump
psql --dbname kataster_review -c 'SELECT count(*) FROM catalog.v_best;'
dropdb kataster_review
```

Build sam odtwarza dump w osobnej bazie, porównuje komplet tabel oraz wynik
Best i usuwa własne zasoby. Brak narzędzia, błąd restore lub różnica danych
blokuje podmianę zestawu wynikowego.

## `katalog.gpkg`

GeoPackage jest plikiem do GIS, np. QGIS, z warstwami `best` i `measurements`.
Pierwsza zawiera jeden wybrany pomiar na obiekt, druga pełną historię,
także pomiary starsze i odrzucone. Tożsamość wiersza określa para
`object_id` i `measurement_id`. Wysokość i datum są atrybutami niezależnymi
od poziomego CRS; nie deklarujemy przez to znanego układu pionowego.

Podczas buildu GeoPackage jest ponownie odczytywany. Sprawdzane są deklaracje
typów wszystkich pól (także pustych warstw i kolumn null), EPSG:2180, Point, ID,
liczność, wszystkie wyeksportowane atrybuty i geometria; samo istnienie pliku
nie jest wynikiem pozytywnym. Pełna bibliografia i model relacyjny są w dumpie.
Starsze wydania sprzed migracji zawierają `katalog.sqlite.zip` zamiast dwóch
nowych formatów; ich pliki pozostają niezmienione.

## Decyzja o notatkach

W plaskich plikach release warto miec notatki, ale nie jako jedno pole
`notes`. Rozdzial na `object_notes`, `cave_notes` i `measurement_notes`
pozwala zachowac sens domenowy:

- `object_notes` opisuje konkretny punkt terenowy,
- `cave_notes` opisuje pozycje katalogowa / jaskinie,
- `measurement_notes` opisuje proweniencje albo zastrzezenia wybranego pomiaru.

Kontekst lokalizacji TPN (`TPN WER_LOK:` i `TPN UWAGI:`) jest zapisany przy
pomiarze. Jeśli jest on wybranym best, trafia do `measurement_notes` w CSV
i GeoJSON oraz części `measurement notes` opisu GPX. PostgreSQL przechowuje
notes wszystkich pomiarów. Tekst TPN nie zmienia statusu weryfikacji;
długi kontekst może być skrócony w `meas_notes` DBF zgodnie z limitem wyżej.

Nie dodajemy na razie notatek z `external_refs` do plaskiego eksportu, bo to
potrafiloby dublowac `source_ref`, `pig_url`, `tpn_globalid` i szybko robic
nieczytelny CSV. Pełne notatki referencji pozostają w `katalog.dump` i arkuszu Full.
