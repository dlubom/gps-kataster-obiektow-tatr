# Przeglad artefaktow release

## Paczka testowa w komentarzu PR

Każda nowa i ponownie otwarta PR oraz każdy jej push (także draft)
uruchamia `PR export preview`. Po udanym buildzie komentarz bota
**Paczka testowa eksportów** zawiera link **Pobierz ZIP eksportów**.
Pobierz po zalogowaniu do GitHub i rozpakuj paczkę, aby obejrzeć np.
Excel Best/Full, GPX w GPS lub GeoJSON/Shapefile w QGIS.
ZIP obejmuje wszystkie dziewięć plików wydania wymienionych poniżej,
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
| `build/exports/metadata.json` | Metadane paczki i liczniki walidacji. | JSON bez geometrii. |
| `build/exports/statistics.md` | Tabele PL/EN/SK dodawane do opisu wydania. | Markdown, rozwijane sekcje językowe. |
| `build/exports/statistics.json` | Te same statystyki do dalszego przetwarzania. | JSON, `statistics_schema_version: 1`. |
| `build/exports/katalog.xlsx` | Czytelny Excel: wybrane punkty oraz pełne dane z historią. | XLSX, arkusze Best i Full. |

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
