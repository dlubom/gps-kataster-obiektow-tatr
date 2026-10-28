# Przeglad artefaktow release

## Paczka testowa w komentarzu PR

Każda nowa i ponownie otwarta PR oraz każdy jej push (także draft)
uruchamia `PR export preview`. Po udanym buildzie komentarz bota
**Paczka testowa eksportów** zawiera link **Pobierz ZIP eksportów**.
Pobierz po zalogowaniu do GitHub i rozpakuj paczkę, aby obejrzeć np.
Excel Best/Full, GPX w GPS lub GeoJSON/Shapefile w QGIS.
ZIP obejmuje wszystkie trzynaście plików wydania wymienionych poniżej,
`preview.json` i `SHA256SUMS` (`sha256sum -c SHA256SUMS` po rozpakowaniu).
SQLite i Shapefile zachowują własne wewnętrzne ZIP-y jak w wydaniu.

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
uv run --frozen python scripts/fetch_jktz_release.py --output-dir build/inputs/jktz
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
uv run python scripts/fetch_jktz_release.py --output-dir build/inputs/jktz
uv run python scripts/build_release_artifacts.py
```

Zrodlem prawdy pozostaja YAML-e w `data/`. Pliki w `build/` sa artefaktami
pochodnymi i nie sa commitowane.

## Wersjonowanie

Oficjalne wydania sa wersjonowane semver tagami `vX.Y.Z`. Release jest
publikowany recznie przez annotated tag, a notatki GitHub Release pochodza z
sekcji `CHANGELOG.md` o tym samym numerze wersji.

## Zestaw plikow

| Plik | Rola | Geometria / format |
|---|---|---|
| `build/katalog.sqlite` | Pelny wygenerowany snapshot katalogu. | SQLite, tabele relacyjne. |
| `build/exports/katalog.sqlite.zip` | Spakowany `katalog.sqlite` do release. | ZIP zawierajacy `katalog.sqlite`. |
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
| `build/exports/katalog.xlsx` | Czytelny Excel: wybrane punkty oraz pełne dane z historią. | XLSX, arkusze Best i Full. |
| `build/exports/katalog-qgis.zip` | Przenośny projekt QGIS, historia GPS, podkłady i modele JKTZ. | QGS, GeoJSON WGS84 i oryginalne Shapefile XYZ EPSG:32634. |

Statystyki pokazują osobno źródło i sposób wyznaczenia pozycji, dla punktów
Best oraz pełnej historii. `selected_points.by_position_method` i
`measurement_history.by_position_method` zawierają zapisane metody oraz
dwie klasy wynikające z udokumentowanych tagów: `lidar_gnss` (`ustalenie`
z `lidar` i `gnss_anchor`) oraz `survey_anchor` (`source_record` z
`survey_anchor`). Jawna metoda ma pierwszeństwo; dowiązanie do GNSS nie
jest bezpośrednim pomiarem GNSS. Rozbicie nie deklaruje dokładności ani
geodezyjnego rodzaju GNSS. Źródłowe `wlasne` ma etykietę „Opracowania własne”.

## `katalog-qgis.zip`

Rozpakuj **cały ZIP** i otwórz `kataster.qgs` w QGIS 3.44 LTR lub 4.0.1.
Nie przenoś samego projektu bez katalogów `points/` i `jktz/`. Projekt ma
ścieżki względne i widok 2D w EPSG:2180, bez pluginów, makr i akcji.

| Warstwa | Domyślnie | Zawartość |
|---|---|---|
| ★ Best | włączona | Zapisany wybór każdego obiektu, bez ponownego rankingu. |
| ○ Pozostałe | wyłączona | Pozostałe pomiary poza odrzuconymi. |
| × Odrzucone | wyłączona | Odrzucone pomiary poza Best. |
| Linie do Best | wyłączona | Dodatnia różnica XY w metrach PL-1992 do wybranego punktu. |
| Full | wyłączona | Pełna historia do tabeli atrybutów, także pomiary odrzucone. |
| JKTZ / osobny model | wyłączona | Opublikowane ciągi pomiarowe, zachowane XYZ i EPSG:32634. |

Odrzucony Best pozostaje w Best. Koincydentne pomiary pozostają w tabeli,
bez linii o zerowej długości. Wybierz warstwę, otwórz tabelę atrybutów lub
użyj Identify Features. Show Map Tips pokazuje nazwę, ID, źródło, status,
różnicę XY, dokładność i uwagi. Etykiety pojawiają się po przybliżeniu.
Zakładki regionalne są grupowane według prefiksów ID.

Podkłady **online**: TPN RGB 2020 (wybrany), RGB 2018, NMT, NMPT oraz OSM.
W grupie TPN wybiera się jeden podkład. Przy skali 1:25000 i większym
oddaleniu TPN jest ukryte, a OSM służy do przeglądu całego zbioru.
Kafelki TPN mają poziomy 15–20. NMT/NMPT to obrazy JPG, **nie numeryczne
rastry wysokości**; nie określono ich daty, datum pionowego ani dokładności.
Usługi mogą być niedostępne; punkty i JKTZ pozostają lokalne.
Źródła: [TPN](https://tpn.obliview.com/),
[OpenStreetMap i autorzy](https://www.openstreetmap.org/copyright).

Osobny krok pobrania ustala **najnowsze stabilne wydanie JKTZ raz na build**.
Builder i odbiór nie łączą się z serwerami map ani GitHub. `manifest.json`
zapisuje GPS version/commit/czas i hashe SQLite/Best oraz tag JKTZ, URL wydania
i assetu, SHA-256 archiwum, warstwy, liczniki i hashe plików. Licencja GPS
to CC BY 4.0. JKTZ zachowuje CC BY-SA 4.0 i oryginalne pliki atrybucji
w `jktz/`. Podkłady są odwołaniami do usług, bez kopiowania ich kafelków.

Nazwy modeli JKTZ są prefiksami eksportów, nie automatycznym powiązaniem
z obiektami GPS. Linie są ciągami pomiarowymi, nie obrysem ścian jaskiń.
Nie przesuwamy ich do GPS Best. GPS i JKTZ są osobnymi migawkami;
zachowanie Z nie potwierdza jego datum ani dokładności.

Te same lokalne wejścia, czas i pochodzenie dają identyczny bajtowo ZIP.
Kolejny build może pobrać nowsze JKTZ. Do odtworzenia zachowaj `JKTZ.zip`
i `source.json` z katalogu wejściowego; sam ZIP QGIS zawiera wybrane modele
i ich pochodzenie, a nie całe źródłowe archiwum wydania JKTZ.

Release i preview blokuje niezależny odbiór przeniesionej paczki w natywnych
QGIS **3.44.15 i 4.0.1**, w kontenerach bez sieci: porównanie z SQLite/JKTZ,
CRS, dostawcy warstw, domyślna widoczność, skale, etykiety, map tips i render
lokalnych wektorów. Nie jest to test dostępności usług online.
[Lokalne odtwarzanie i odbiór](operations.md#paczka-qgis-i-wejście-jktz).

## `katalog.xlsx`

Generowany przy każdym buildzie wydania, bez osobnego ręcznego kroku.
**Best** ma jeden wiersz na obiekt: podstawowe pola wybranego punktu z CSV,
w tym współrzędne WGS84, wysokość, źródło, weryfikację i dokładność.
**Full** ma jeden wiersz na zachowany pomiar z SQLite, także starszy lub
odrzucony, z pełnymi danymi pomiaru i towarzyszącymi danymi obiektu.
Kolumna „Wybrany do eksportu” porównuje ID pomiaru w obrębie tego samego
obiektu. Powtarzające się ID obiektu w Full są historią, nie duplikatami.

Full zachowuje uwagi, dane wyboru, nadania ID i autorstwa; listy referencji,
załączników i relacji są tekstem JSON w osobnych kolumnach. Metadane jaskini
obejmują ID, nazwę, system, uwagi i referencje. SQLite pozostaje pełnym
relacyjnym snapshotem. Załączniki są opisane, nie osadzone w Excelu.

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

Powstają przy każdym `build_release_artifacts.py`, z wygenerowanego CSV
(wybrane punkty) oraz SQLite (pozycje katalogowe i cała historia).
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
CSV, GeoJSON, GPX i SQLite zachowują pełny tekst. Plik `.cpg` wskazuje UTF-8.

## `best-measurements.gpx`

GPX nie ma kolumn. Kazdy waypoint zawiera:

- atrybuty `lat` i `lon` w WGS84,
- opcjonalne `ele` oraz `time`,
- `name` ustawione na `name_local` obiektu (nazwę konkretnego otworu);
  przy braku, `null`, pustej nazwie lub samych białych znakach używane jest `object_id`,
- `type` ustawione na `category`,
- `desc` z nazwą, jawnym `object <object_id>`, `measurement_id`, źródłem,
  datą obserwacji oraz notatkami obiektu, jaskini i pomiaru, jeśli istnieją.

Nazwy w etykietach GPX pojawią się w wydaniach po v1.0.4. Powtarzające się
nazwy są dozwolone; trwałe ID w opisie pozwala wskazać konkretny punkt w CSV/Excelu.

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

Przypisanie wynika ze współrzędnych wskazanego Best oraz istniejących
polygonów i `config/prefixes.yml`, nie z historycznego prefiksu trwałego ID.
Wschód/zachód danej doliny pozostają w jednej grupie. Kolejność punktów
pozostaje zgodna z pełnym GPX, według ID. Powstają też puste pliki grup.

Każdy dodatkowy plik ma najwyżej 500 punktów. Przekroczenie limitu albo
nierozpoznany region przerywa eksport czytelnym błędem przed zapisem jego
plików, bez nadpisania wcześniejszych eksportów. Builder mógł już wcześniej
zbudować SQLite; nie oznacza to gotowej paczki do publikacji. Nie obcinamy
punktów ani nie rozcinamy dolin automatycznie. Wzrost liczby punktów wymaga
ponownego uzgodnienia grup. `metadata.json` zachowuje dotychczasowy kontrakt.
Pliki są w lokalnym buildzie, podglądzie PR i wydaniach po v1.2.1.

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

## `katalog.sqlite`

SQLite trzyma pelniejszy model niz plaskie eksporty. Glowne tabele i kolumny:

| Tabela | Kolumny |
|---|---|
| `objects` | `id`, `schema_version`, `category`, `name_local`, `cave_id`, `id_assignment_method`, `assigned_from_measurement_id`, `assigned_prefix`, `prefix_override_reason`, `best_measurement_id`, `computed_best_measurement_id`, `best_lat`, `best_lon`, `best_x_1992`, `best_y_1992`, `best_geom_wgs84`, `best_geom_1992`, `notes`, `created_at`, `created_by`, `updated_at`, `updated_by` |
| `caves` | `id`, `schema_version`, `name`, `system_name`, `object_ids_json`, `notes`, `created_at`, `created_by`, `updated_at`, `updated_by` |
| `measurements` | `object_id`, `id`, `lat`, `lon`, `x_1992`, `y_1992`, `geom_wgs84`, `geom_1992`, `elevation_m`, `elevation_datum`, `elevation_source`, `horizontal_accuracy_m`, `vertical_accuracy_m`, `source`, `source_ref`, `observed_at`, `observed_date`, `source_date`, `method`, `device`, `tags_json`, `verification_status`, `verified_by`, `verified_at`, `notes`, `created_at`, `created_by` |
| `best_measurements` | `object_id`, `mode`, `measurement_id`, `computed_best_measurement_id`, `reason`, `updated_at`, `updated_by` |
| `object_external_refs` | `object_id`, `system`, `ref_type`, `external_id`, `url`, `scope`, `notes` |
| `cave_external_refs` | `cave_id`, `system`, `ref_type`, `external_id`, `url`, `scope`, `notes` |
| `attachments` | `object_id`, `path`, `type`, `description`, `created_at`, `created_by` |
| `relations` | `id`, `schema_version`, `from_object_id`, `to_object_id`, `relation_type`, `notes` |
| `validation_flags` | `code`, `severity`, `path`, `description` |
| `metadata` | `key`, `value` |

## Decyzja o notatkach

W plaskich plikach release warto miec notatki, ale nie jako jedno pole
`notes`. Rozdzial na `object_notes`, `cave_notes` i `measurement_notes`
pozwala zachowac sens domenowy:

- `object_notes` opisuje konkretny punkt terenowy,
- `cave_notes` opisuje pozycje katalogowa / jaskinie,
- `measurement_notes` opisuje proweniencje albo zastrzezenia wybranego pomiaru.

Kontekst lokalizacji TPN (`TPN WER_LOK:` i `TPN UWAGI:`) jest zapisany przy
pomiarze. Jeśli jest on wybranym best, trafia do `measurement_notes` w CSV
i GeoJSON oraz części `measurement notes` opisu GPX. SQLite przechowuje
notes wszystkich pomiarów. Tekst TPN nie zmienia statusu weryfikacji;
długi kontekst może być skrócony w `meas_notes` DBF zgodnie z limitem wyżej.

Nie dodajemy na razie notatek z `external_refs` do plaskiego eksportu, bo to
potrafiloby dublowac `source_ref`, `pig_url`, `tpn_globalid` i szybko robic
nieczytelny CSV. Pelne notatki referencji zostaja w `katalog.sqlite`.
