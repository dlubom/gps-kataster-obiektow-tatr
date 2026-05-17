# Przeglad artefaktow release

Ten dokument opisuje lokalna paczke generowana przez:

```bash
uv run python scripts/build_release_artifacts.py
```

Zrodlem prawdy pozostaja YAML-e w `data/`. Pliki w `build/` sa artefaktami
pochodnymi i nie sa commitowane.

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

Uwagi w DBF sa limitowane do 254 znakow na pole, zgodnie z praktycznym limitem
pol tekstowych Shapefile.

## `best-measurements.gpx`

GPX nie ma kolumn. Kazdy waypoint zawiera:

- atrybuty `lat` i `lon` w WGS84,
- opcjonalne `ele` oraz `time`,
- `name` ustawione na `object_id`,
- `type` ustawione na `category`,
- `desc` z nazwa/ID, `measurement_id`, zrodlem, data obserwacji oraz notatkami
  obiektu, jaskini i pomiaru, jesli istnieja.

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

Nie dodajemy na razie notatek z `external_refs` do plaskiego eksportu, bo to
potrafiloby dublowac `source_ref`, `pig_url`, `tpn_globalid` i szybko robic
nieczytelny CSV. Pelne notatki referencji zostaja w `katalog.sqlite`.
