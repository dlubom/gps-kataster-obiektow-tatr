# AS-DLC project context

Last updated: 2026-05-16

## Current mode

The project uses a lightweight AS-DLC flow:

- `spec-anchored`: the specification stays in the repository and remains the
  source of architectural intent.
- PBI-sized work: each step has bounded scope and verification.
- Commit after each completed step.
- Capture durable context in markdown files, not only in chat.

## Files that define project memory

- `AGENTS.md`: instructions for future agents.
- `specyfikacja_gps_kataster_obiektow_tatr_v_2.md`: current specification.
- `docs/asdlc/backlog_v1.md`: task breakdown and PBI status.
- `docs/asdlc/context.md`: compact operational memory.

## Current repository status

PBI-001 is complete:

- target directories exist,
- shapefiles were moved from `shapes/` to `data/shapes/`,
- `.gitignore` exists,
- placeholder `.gitkeep` files keep empty target directories visible.

PBI-002 is complete:

- `pyproject.toml` exists,
- `uv.lock` exists,
- `ruff` and `pytest` are configured,
- a minimal package exists under `src/gps_kataster_obiektow_tatr/`,
- a smoke test exists in `tests/test_package.py`.

PBI-003 is complete:

- `config/prefixes.yml` exists,
- the 18 `NAME` values from `data/shapes/doliny.shp` are mapped to prefixes,
- fallback prefixes `PL` and `SK` are configured,
- tests detect missing or stale valley-prefix mappings and invalid prefix format.

PBI-004 is complete:

- `schema/object.schema.json`, `schema/cave.schema.json` and
  `schema/relation.schema.json` exist,
- `schema/CHANGELOG.md` documents `schema_version: 1`,
- `jsonschema` is available as a dev dependency,
- schema tests cover valid fixtures plus expected failures for a missing object
  ID, bad cave object ID, bad relation type and missing manual-best reason.

PBI-005 is complete:

- `tests/fixtures/valid-object.yml` and `tests/fixtures/valid-cave.yml` provide
  a minimal linked object/cave pair,
- `tests/fixtures/object-with-tpn-globalid.yml` keeps TPN `GLOBALID` on
  `Obiekt.external_refs`,
- `tests/fixtures/cave-with-pig-and-nr-inwent.yml` keeps PIG and inventory
  references on `Jaskinia.external_refs`,
- `tests/fixtures/object-with-manual-best.yml` exercises manual
  `best_measurement` with a reason,
- `tests/test_domain_fixtures.py` validates those fixtures against the schemas
  and checks object/cave cross-references.

PBI-006 is complete:

- `src/gps_kataster_obiektow_tatr/coordinates.py` adds deterministic WGS84
  <-> EPSG:2180 conversion through PyProj,
- the module preserves the spec's axis convention: `x_1992 = northing`,
  `y_1992 = easting`,
- `coordinates_are_consistent(...)` uses a default 0.5 m tolerance for cached
  YAML coordinate checks,
- `tests/test_coordinates.py` covers round-trip conversion for Tatra points,
  PIG-style axis values and axis-swap detection.

PBI-007 is complete:

- `src/gps_kataster_obiektow_tatr/prefix_resolver.py` reads
  `config/prefixes.yml` plus `data/shapes/doliny.shp`,
  `data/shapes/granica_polski.shp` and
  `data/shapes/granica_slowacji.shp`,
- it converts WGS84 to PL-1992 using the project axis convention, then tests
  shapefile geometry as GIS easting/northing,
- valley matches return `status=ok` and the valley prefix,
- points in PL/SK but outside configured valley polygons return fallback
  prefix `PL` or `SK` with `status=warning`,
- points outside PL/SK return `status=error` and no prefix.

PBI-008 is complete:

- `scripts/assign_id.py` accepts `lat lon`,
- it calls the prefix resolver, proposes the next object ID from existing
  `{PREFIX}-{NNNN}.yml` files under `data/objects/{PREFIX}/`,
- fallback `PL` / `SK` resolutions still print a proposed ID plus the resolver
  warning,
- points outside Poland and Slovakia exit nonzero without an ID proposal,
- conflict detection remains assigned to the future validator.

PBI-009 is complete:

- `src/gps_kataster_obiektow_tatr/data_loader.py` loads object, cave and
  relation YAML from `data/objects/`, `data/caves/` and `data/relations/`,
- every loaded record carries its `Path` for future validation reports,
- missing list fields are normalized on the loaded copy only; source YAML and
  `raw_data` are left unchanged,
- bad YAML raises `YamlDataLoadError` with the source path in the message.

PBI-010 is complete:

- `src/gps_kataster_obiektow_tatr/validator.py` validates loaded YAML records
  and reports rule code, severity, file path and description,
- `scripts/validate.py` is the local CLI entrypoint for the same validation
  intended for CI,
- validator errors cover YAML/schema problems, duplicate object IDs,
  file-vs-ID mismatches, broken cross-references, attachment references,
  coordinate mismatch, points outside PL/SK and duplicate TPN `GLOBALID`,
- validator warnings cover points outside configured valley polygons,
  object prefix mismatch against the current best measurement, missing
  `horizontal_accuracy_m`, missing `source_ref`, far-apart measurements,
  `jaskinia_otwor` without `cave_id`, and object-level PIG/NR_INWENT catalog
  references,
- the CLI exits nonzero only when at least one `error` issue is present.

PBI-011 is complete:

- `src/gps_kataster_obiektow_tatr/best_measurement.py` holds the reusable V1
  default selection algorithm for `best_measurement.mode: auto`,
- selection priority is `wlasne` verified, TPN, `wlasne` unverified, PIG,
  other non-rejected sources, then rejected fallback,
- within one priority the algorithm chooses latest observation, then lower
  `horizontal_accuracy_m`, then stable `measurement.id`,
- the validator warns when `mode: auto` points somewhere else, keeps
  `mode: manual` authoritative, and warns when the default can only select an
  `odrzucony` measurement.

PBI-012 is complete:

- `src/gps_kataster_obiektow_tatr/source_profile.py` profiles CSV exports for
  key missing values, duplicate identifiers and coordinate/elevation ranges,
- `scripts/profile_sources.py` writes `build/reports/source-profile.json` and
  `build/reports/source-profile.md`,
- the generated reports are build artifacts, so they are ignored by git through
  the existing `build/` rule,
- PBI-012 intentionally does not create final YAML under `data/objects/` or
  `data/caves/`.

PBI-013 is complete:

- `src/gps_kataster_obiektow_tatr/pig_staging.py` builds reviewable staging
  proposals from the PIG export without writing final YAML,
- `scripts/importers/import_pig.py` reads PIG CSV or XLSX and writes
  `build/staging/pig/pig-staging.json` plus `pig-staging.md`,
- each PIG row becomes a staging `Jaskinia` proposal with PIG `ID`, PIG `Link`
  and `Nr inw.` on `Jaskinia.external_refs`,
- an initial `Obiekt` proposal is created only when coordinate parsing,
  WGS84/PL-1992 consistency and prefix resolution produce a usable point,
- proposed PIG measurements use `source: PIG`, `method: source_record`,
  `verification_status: nieweryfikowany`, no horizontal accuracy, and
  `best_measurement.mode: auto` only inside the staging proposal,
- tests cover CSV import, XLSX import, coordinate-mismatch cave-only fallback,
  report writing and the guarantee that no final YAML is written under `data/`.

PBI-014 is complete:

- `src/gps_kataster_obiektow_tatr/source_table.py` is the shared CSV/XLSX table
  reader used by staging importers,
- `src/gps_kataster_obiektow_tatr/tpn_staging.py` builds reviewable TPN
  measurement proposals without writing final YAML,
- `scripts/importers/import_tpn.py` reads TPN CSV or XLSX and writes
  `build/staging/tpn/tpn-staging.json` plus `tpn-staging.md`,
- TPN `GLOBALID` is proposed on `Obiekt.external_refs`; `NR_INWENT` is
  proposed on `Jaskinia.external_refs`,
- matching checks final YAML records and, when present, the PIG staging JSON;
  order is `GLOBALID`, then `NR_INWENT`, then normalized name plus distance,
- rows are classified for operator review as `matched`, `new`, `unresolved`
  or `rejected`; ambiguous duplicate inventory rows stay unresolved,
- new TPN objects receive a TPN source-record measurement with
  `verification_status: nieweryfikowany`, no horizontal accuracy and
  `best_measurement.mode: auto` only inside the staging proposal,
- tests cover matched measurement updates, new object/cave proposals,
  unresolved duplicate inventory rows, XLSX reading, report writing, CLI
  execution and the guarantee that no final YAML is written under `data/`.

PBI-015 is complete:

- `docs/asdlc/staging_review_decisions.md` documents the operator decision YAML
  format and the V1 review actions,
- `src/gps_kataster_obiektow_tatr/staging_review.py` applies decisions against
  PIG/TPN staging reports and final YAML loaded from `data/`,
- `scripts/importers/apply_review.py` requires a decision file before writing
  any final YAML and emits `build/staging/review/staging-review.json` plus
  `staging-review.md`,
- supported review actions are `create_cave`, `create_object`,
  `add_measurement`, `link_cave`, `reject` and `unresolved`,
- `add_measurement` materializes matched TPN measurement updates, adds TPN
  object refs and cave refs, and refreshes `best_measurement.mode: auto`,
- invalid decisions block all final YAML writes, so review application is
  all-or-nothing for the given decision file,
- TPN matched measurement updates now include `record_number` in the staging
  JSON to make decisions point to source rows directly.

PBI-016 is complete:

- `src/gps_kataster_obiektow_tatr/build_db.py` builds a generated SQLite
  snapshot from validated YAML loaded through the existing data loader,
- `scripts/build_db.py` writes `build/katalog.sqlite` by default and supports
  `--data-dir`, `--output` and deterministic `--generated-at` for tests,
- validation errors block the SQLite build; validation warnings are preserved
  in the `validation_flags` table,
- the SQLite schema includes the V1 logical tables: `objects`, `caves`,
  `measurements`, `object_external_refs`, `cave_external_refs`, `attachments`,
  `relations`, `best_measurements`, `validation_flags` and `metadata`,
- `metadata` stores `generated_at`, schema version and object/cave/relation/
  measurement plus validation issue counts as key-value rows,
- object best geometries are derived from the authoritative YAML
  `best_measurement.measurement_id`; the default computed best measurement is
  stored separately as `computed_best_measurement_id`,
- PBI-016 uses WKT text for `geom_wgs84`, `geom_1992`, `best_geom_wgs84` and
  `best_geom_1992`; SpatiaLite initialization remains a later enhancement if
  export/QGIS needs require it.

PBI-017 is complete:

- `src/gps_kataster_obiektow_tatr/best_measurements_export.py` exports one
  authoritative `best_measurement.measurement_id` row per object after YAML
  validation,
- `scripts/export_best_measurements.py` writes `build/exports/` by default and
  supports `--data-dir`, `--output-dir` and deterministic `--generated-at` for
  tests,
- the export artifacts are `best-measurements.geojson`, `best-measurements.csv`,
  `best-measurements.gpx` and `best-measurements.shp.zip`,
- GeoJSON and GPX use WGS84 point coordinates; CSV includes both WGS84 and
  EPSG:2180; Shapefile geometry is written in EPSG:2180 using GIS order
  easting/northing from project fields `y_1992`/`x_1992`,
- validation errors block all export files.

PBI-018 is complete:

- the same release export now also writes `build/exports/metadata.json`,
- `metadata.json` records `generated_at`, release metadata schema version,
  data schema version and counts for objects, caves, relations, measurements,
  validation warnings and validation errors,
- the CLI prints the metadata path together with the GeoJSON, CSV, GPX and
  Shapefile ZIP artifacts,
- the metadata snapshot test uses a temporary fixture with one validator
  warning to verify the warning count.

## Current data inventory

- PIG workbook: `pig_otwory_jaskin_.xlsx`, sheet `Export`, 861 rows including
  header, 15 columns.
- PIG CSV: `pig_otwory_jaskin_.xlsx.-.Export.csv`, 860 data records.
- TPN workbook: `tpn_otwory_jaskin.xlsx`, sheet `Export`, 1006 rows including
  header, 23 columns.
- TPN CSV: `tpn_otwory_jaskin.xlsx.-.Export.csv`, 1005 data records.
- `data/shapes/doliny.shp`: 18 features, EPSG:2180, key field `NAME`.
- `data/shapes/granica_polski.shp`: 1 feature, EPSG:2180.
- `data/shapes/granica_slowacji.shp`: 1 feature, EPSG:2180.

## Key domain decisions

- `Obiekt` is the main durable ID unit and represents a concrete field point.
- `Jaskinia` is a logical/catalog entity and can group multiple `Obiekt`
  records.
- A cave inventory number is not treated as the durable object ID.
- TPN `GLOBALID` maps to object-level external references.
- PIG catalog identifiers, PIG links and inventory numbers map to cave-level
  external references.
- PIG can seed catalog skeletons and low-priority measurements.
- TPN can later improve object-level point measurements.
- Imports should go through staging/review before final YAML is written.

## Verification facts already checked

After PBI-001:

- `ogrinfo -al -so data/shapes/doliny.shp` opens successfully and reports
  18 features.
- `ogrinfo -al -so data/shapes/granica_polski.shp` opens successfully and
  reports 1 feature.
- `ogrinfo -al -so data/shapes/granica_slowacji.shp` opens successfully and
  reports 1 feature.

After PBI-002:

- `uv sync` completed successfully with CPython 3.14.4.
- `uv run ruff check src tests` passed.
- `uv run ruff format --check src tests` passed.
- `uv run pytest` passed with 1 test.

After PBI-003:

- `config/prefixes.yml` contains 18 valley prefix mappings and two country
  fallback prefixes.
- `tests/test_prefixes.py` checks all `doliny.shp` `NAME` values are mapped.
- `uv sync` completed successfully after adding `pyshp` and `PyYAML` dev
  dependencies.
- `uv run ruff format src tests` passed with no changes.
- `uv run ruff check src tests` passed.
- `uv run pytest` passed with 3 tests.

After PBI-004:

- `schema/object.schema.json` validates the V1 `Obiekt` shape including
  measurements, best measurement, external refs, attachments and audit fields.
- `schema/cave.schema.json` validates the V1 `Jaskinia` shape including
  cave-level external refs and object ID format.
- `schema/relation.schema.json` validates V1 object-object relation records.
- `tests/fixtures/schema/` contains focused valid and invalid schema fixtures.
- `uv sync` completed successfully after adding `jsonschema`.
- `uv run ruff format src tests` passed with no changes.
- `uv run ruff check src tests` passed after removing one unused import.
- `uv run pytest` passed with 10 tests.

After PBI-005:

- `tests/fixtures/` contains the five minimal domain fixtures named in the
  backlog.
- `tests/test_domain_fixtures.py` checks schema validity, `cave_id` /
  `object_ids` symmetry, local measurement references, TPN object references
  and cave-level PIG / `NR_INWENT` references.
- `uv run ruff format src tests` reformatted the new test file.
- `uv run ruff check src tests` passed.
- `uv run pytest` passed with 19 tests.

After PBI-006:

- `pyproj>=3.7.0` is a runtime dependency because the specification requires
  deterministic conversion through PyProj.
- `wgs84_to_1992(...)` returns project YAML fields where `x_1992` is northing
  and `y_1992` is easting.
- `pl1992_to_wgs84(...)` accepts the same project YAML field convention.
- `coordinates_are_consistent(...)` and `coordinate_consistency_error_m(...)`
  provide the reusable tolerance check expected by the future validator.
- `uv run ruff format src tests` passed with no changes.
- `uv run ruff check src tests` passed.
- `uv run pytest` passed with 24 tests.

After PBI-007:

- `pyshp>=2.3.1` and `PyYAML>=6.0.2` are runtime dependencies because prefix
  resolution now reads shapefiles and `config/prefixes.yml` from application
  code.
- `tests/test_prefix_resolver.py` covers four PBI cases:
  `KSW` for a point in `Dolina Kościeliska - Wschód`, `PL` warning for Warsaw,
  `SK` warning for Stary Smokovec and an error for Prague.
- `uv run ruff format src tests` passed with no changes.
- `uv run ruff check src tests` passed.
- `uv run pytest` passed with 28 tests.

After PBI-008:

- `scripts/assign_id.py` is the first V1 developer CLI.
- `next_object_id(...)` returns `{PREFIX}-0001` when
  `data/objects/{PREFIX}/` is empty or missing.
- Existing `{PREFIX}-{NNNN}.yml` files drive the next number by `max + 1`; the
  formatter naturally extends beyond four digits, e.g. `{PREFIX}-10000`.
- Resolver warnings are printed alongside the proposal, while resolver errors
  exit nonzero.
- `uv run ruff format src tests scripts` passed with no changes.
- `uv run ruff check src tests scripts` passed.
- `uv run pytest` passed with 34 tests.

After PBI-009:

- `load_dataset(...)` returns `LoadedDataset(objects, caves, relations)`.
- `LoadedYamlRecord` stores `kind`, `path`, normalized `data` and untouched
  `raw_data`.
- Object list defaults currently cover `external_refs`, `measurements`,
  `attachments` and nested measurement `tags`; cave defaults cover
  `external_refs` and `object_ids`.
- `tests/test_data_loader.py` covers fixture loading, path retention,
  in-memory-only normalization and bad YAML path reporting.
- `uv run ruff format src tests` reformatted the new test file.
- `uv run ruff format --check src tests` passed.
- `uv run ruff check src tests` passed.
- `uv run pytest` passed with 37 tests.

After PBI-010:

- `validate_data_dir(...)` catches YAML loader errors as `YAML_INVALID` issues
  and otherwise validates all object, cave and relation records.
- JSON Schema validation is reported as `SCHEMA_VALIDATION`; `schema_version`
  drift is additionally reported as `SCHEMA_VERSION_INVALID`.
- Cross-record checks cover object-to-cave, cave-to-object, relation-to-object,
  best-measurement and attachment-measurement references.
- Coordinate checks use the existing PyProj helpers and the default 0.5 m
  tolerance; spatial checks reuse the prefix resolver and PL/SK fallback
  boundaries.
- `scripts/validate.py` on the current repository prints `OK: no validation
  issues`.
- `uv run ruff format src tests scripts` passed.
- `uv run ruff check src tests scripts` passed.
- `uv run pytest` passed with 43 tests.

After PBI-011:

- `select_default_best_measurement_id(...)` is reusable outside the validator
  for future build/export logic.
- `tests/test_best_measurement.py` covers all default priorities, the grouped
  `geoportal` / `publikacja` / `inne` priority, latest observation date/time,
  lower horizontal accuracy, stable ID tie-breaks and rejected-only fallback.
- `tests/test_validator.py` covers the warning for `auto` mismatch, confirms
  `manual` best measurement is not checked against the auto algorithm, and
  covers rejected-only fallback warning.
- `uv run ruff format src tests` reformatted the new/changed Python files.
- `uv run ruff format --check src tests scripts` passed.
- `uv run ruff check src tests scripts` passed.
- `uv run pytest` passed with 57 tests.
- `uv run python scripts/validate.py` printed `OK: no validation issues`.

After PBI-012:

- `uv run python scripts/profile_sources.py` generated
  `build/reports/source-profile.json` and `build/reports/source-profile.md`.
- PIG profile: 860 records, 15 columns, no missing expected columns, no missing
  key values for `ID`, `Nazwa`, `Nr inw.`, `X 1992`, `Y 1992`, `B`, `L` or
  `Link`, and no duplicates in `ID` or `Nr inw.`.
- PIG coordinate ranges: `X 1992` 146571.18..157933.10, `Y 1992`
  558156.83..579383.12, `B` 49.18160173..49.28416666, `L`
  19.79967485..20.09027783, `H (wg PIG)` 915.0..2250.0 with 8 missing.
- TPN profile: 1005 records, 23 columns, no missing expected columns,
  `GLOBALID` complete and unique, `NR_INWENT` missing in 143 records, `NAZWA`
  missing in 1 record.
- TPN duplicates: `NR_INWENT` has 4 duplicate groups / 8 records:
  `T.D-08.07`, `T.D-08.08`, `T.D-12.10`, `T.E-08.04`.
- TPN coordinate ranges: `X1992` 146571.18..157933.10, `Y1992`
  557539.51..579383.12, `Z` 909.7399765..2144.220728.
- `find data -type f` confirmed no final YAML object/cave records were created
  by PBI-012; only existing `.gitkeep` files and shapefiles are present.
- `uv run ruff format --check src tests scripts` passed.
- `uv run ruff check src tests scripts` passed.
- `uv run pytest` passed with 61 tests.
- `uv run python scripts/validate.py` printed `OK: no validation issues`.

After PBI-013:

- `uv run python scripts/importers/import_pig.py --generated-at
  2026-05-16T08:00:00Z` generated `build/staging/pig/pig-staging.json` and
  `build/staging/pig/pig-staging.md` from the CSV export.
- `uv run python scripts/importers/import_pig.py --pig-source
  pig_otwory_jaskin_.xlsx --output-dir build/staging/pig-xlsx --generated-at
  2026-05-16T08:00:00Z` verified the XLSX path on the real workbook.
- Both CSV and XLSX staging runs produced 860 records, 860 cave proposals and
  860 object proposals.
- The only staging issues were 46 `POINT_OUTSIDE_VALLEYS` warnings, i.e.
  fallback-prefix cases that require operator review.
- `find data/objects data/caves data/relations -maxdepth 2 -type f -print`
  still listed only the existing `.gitkeep` files; the importer did not create
  final YAML.
- `uv run ruff format --check src tests scripts` passed.
- `uv run ruff check src tests scripts` passed.
- `uv run pytest` passed with 66 tests.
- `uv run python scripts/validate.py` printed `OK: no validation issues`.

After PBI-014:

- `uv run python scripts/importers/import_tpn.py --generated-at
  2026-05-16T09:00:00Z` generated `build/staging/tpn/tpn-staging.json` and
  `build/staging/tpn/tpn-staging.md` from the CSV export using the PIG staging
  JSON as a matching baseline.
- `uv run python scripts/importers/import_tpn.py --tpn-source
  tpn_otwory_jaskin.xlsx --output-dir build/staging/tpn-xlsx --generated-at
  2026-05-16T09:00:00Z` verified the XLSX path on the real workbook.
- Both CSV and XLSX staging runs produced 1005 records: 858 matched, 142 new,
  5 unresolved and 0 rejected.
- The generated TPN reports currently contain 263 review issues, mostly
  distance-review warnings for `NR_INWENT` matches plus unresolved duplicate
  inventory cases.
- `find data/objects data/caves data/relations -maxdepth 2 -type f -print`
  still listed only the existing `.gitkeep` files; the importer did not create
  final YAML.

After PBI-015:

- `uv run pytest tests/test_staging_review.py` passed with 3 tests.
- The review sample test runs `scripts/importers/apply_review.py`, writes
  `C-0001.yml` and `KSW-0001.yml` in a temporary `data/` tree, then verifies
  that `scripts/validate.py --data-dir ...` exits 0.
- The review tests also cover `link_cave`, `reject`, `unresolved` and the
  guarantee that one invalid decision blocks all final YAML writes.
- `uv run ruff format --check src tests scripts` passed.
- `uv run ruff check src tests scripts` passed.
- `uv run pytest` passed with 75 tests.
- `uv run python scripts/validate.py` printed `OK: no validation issues`.

After PBI-016:

- `uv run pytest tests/test_build_db.py` passed with 3 tests.
- The build tests create a temporary valid YAML dataset, run
  `build_sqlite_database(...)` and `scripts/build_db.py`, then verify SQLite
  tables, `metadata` counts, best-measurement geometries and external-ref
  inserts.
- The build tests also verify that validation errors block SQLite creation.
- `uv run ruff format src tests scripts` reformatted the new Python files.
- `uv run ruff format --check src tests scripts` passed.
- `uv run ruff check src tests scripts` passed.
- `uv run pytest` passed with 78 tests.
- `uv run python scripts/validate.py` printed `OK: no validation issues`.
- `uv run python scripts/build_db.py --generated-at 2026-05-16T12:00:00Z`
  generated `build/katalog.sqlite` from current `data/`; current final YAML
  inventory is still empty, so the SQLite summary was 0 objects, 0 caves and
  0 measurements.

After PBI-017:

- `uv run pytest tests/test_best_measurements_export.py` passed with 3 tests.
- The export tests create a temporary valid YAML dataset and verify that only
  the authoritative best measurement is written to GeoJSON, CSV, GPX and a
  readable Shapefile ZIP.
- The export tests also verify the CLI and that validation errors block export
  file creation.
- `uv run ruff format --check src tests scripts` passed.
- `uv run ruff check src tests scripts` passed.
- `uv run pytest` passed with 81 tests.
- `uv run python scripts/validate.py` printed `OK: no validation issues`.
- `uv run python scripts/export_best_measurements.py --generated-at
  2026-05-16T12:00:00Z` generated all four `build/exports/`
  best-measurements artifacts from current `data/`; current final YAML
  inventory is still empty, so the export summary was 0 features.

After PBI-018:

- `uv run pytest tests/test_best_measurements_export.py` passed with 4 tests.
- The metadata snapshot test verifies `metadata_schema_version`,
  `data_schema_version`, `generated_at`, object/cave/relation/measurement
  counts and validation warning/error counts.
- `uv run ruff format --check src tests scripts` passed.
- `uv run ruff check src tests scripts` passed.
- `uv run pytest` passed with 82 tests.
- `uv run python scripts/validate.py` printed `OK: no validation issues`.
- `uv run python scripts/export_best_measurements.py --generated-at
  2026-05-16T12:00:00Z` generated GeoJSON, CSV, GPX, Shapefile ZIP and
  `metadata.json`; current final YAML inventory is still empty, so the metadata
  counts are 0 objects, 0 caves, 0 relations, 0 measurements and 0 validation
  issues.

PBI-019 is complete:

- `.github/workflows/validate.yml` runs on pull requests and pushes to `main`.
- The CI job installs Python 3.12 and `uv`, then runs the same local validation
  gate used for PBI work: `uv sync`, `uv run ruff format --check src tests
  scripts`, `uv run ruff check src tests scripts`, `uv run pytest` and
  `uv run python scripts/validate.py`.
- The validate workflow intentionally does not build SQLite, export release
  artifacts or upload release artifacts; build/release automation remains
  PBI-020.

After PBI-019:

- `uv sync` completed successfully.
- `uv run pytest tests/test_ci_workflow.py` passed with 2 tests.
- `uv run ruff format src tests scripts` reformatted the new workflow test.
- `uv run ruff format --check src tests scripts` passed.
- `uv run ruff check src tests scripts` passed.
- `uv run pytest` passed with 84 tests.
- `uv run python scripts/validate.py` printed `OK: no validation issues`.

After conservative PIG/TPN review import on 2026-05-16:

- Real local PIG/TPN staging was generated from
  `pig_otwory_jaskin_.xlsx.-.Export.csv` and
  `tpn_otwory_jaskin.xlsx.-.Export.csv`.
- The operator-approved conservative policy was: import PIG rows without
  staging issues and TPN matched rows without staging issues only when their
  target object came from a clean PIG row.
- `build/staging/review/decisions-clean.yml` materialized 814 PIG caves,
  814 PIG objects and 567 TPN measurement additions.
- The import wrote 814 final cave YAML files and 814 final object YAML files;
  `data/relations/` still has no relation YAML.
- `uv run python scripts/validate.py` exits 0 on the imported data and reports
  1381 warnings, all `MISSING_HORIZONTAL_ACCURACY`, because source-record PIG
  and TPN measurements do not declare `horizontal_accuracy_m`.
- `uv run python scripts/build_db.py` generated `build/katalog.sqlite` with
  814 objects, 814 caves, 1381 measurements, 0 relations, 0 validation errors
  and 1381 validation warnings.
- `uv run python scripts/export_best_measurements.py` generated GeoJSON, CSV,
  GPX, Shapefile ZIP and `metadata.json`; the best-measurements export contains
  814 features.
- Initially excluded from this conservative import: PIG
  `POINT_OUTSIDE_VALLEYS` rows, TPN distance-review matches, TPN ambiguous
  `NR_INWENT` rows, new TPN-only rows and duplicate clean TPN match row 476 for
  `KSW-0065` / Smocza Jama.

PBI-020 is complete:

- `src/gps_kataster_obiektow_tatr/release_artifacts.py` builds the shared
  release artifact set from YAML: `build/katalog.sqlite`,
  `best-measurements.geojson`, `best-measurements.csv`,
  `best-measurements.gpx`, `best-measurements.shp.zip`, `metadata.json` and
  `katalog.sqlite.zip`.
- `scripts/build_release_artifacts.py` is the local dry-run entrypoint used by
  both GitHub Actions workflows.
- `.github/workflows/build.yml` runs on push to `main` and `workflow_dispatch`,
  validates YAML, builds the release artifact set and uploads it as a GitHub
  Actions artifact.
- `.github/workflows/release.yml` runs only on tags `v*`. The `release` job
  depends on `license_guard`, which requires repository variable
  `SOURCE_LICENSE_CONFIRMED=true` before any GitHub Release publish command can
  run.
- The release job publishes only the generated release files through
  `gh release create`; imported external source data still requires legal/source
  license confirmation before public release.

PBI-021 is complete:

- `docs/operations.md` documents the V1 operational workflow for manual
  measurements, local validation, monthly data-package builds and verification
  statuses.
- The manual-measurement path describes editing object YAML, assigning the next
  local `m-NNN` measurement ID, keeping both WGS84 and project EPSG:2180 fields,
  and updating `best_measurement`.
- The documentation keeps `build/` as generated output, points monthly package
  generation to `scripts/build_release_artifacts.py`, and repeats the release
  license guard.
- `tests/test_operational_docs.py` guards the expected PBI-021 sections and the
  rule that generated `build/` artifacts are not committed.

Initial release licensing:

- Source-data redistribution for the initial public release was confirmed by
  the maintainer on 2026-05-16.
- Top-level `LICENSE` records Creative Commons Attribution 4.0 International
  (`CC-BY-4.0`) for repository data, documentation and generated data exports,
  with an explicit note that source references from PIG / Jaskinie Polski and
  TPN should be retained for attribution.

After PBI-020:

- `uv run python scripts/build_release_artifacts.py --generated-at
  2026-05-16T12:00:00Z` generated the full local dry-run artifact set.
- The local dry-run reported 814 objects, 814 caves, 1381 measurements and
  1381 validation warnings.
- `uv run ruff format src tests scripts` reformatted the new release-artifact
  test file.
- `uv run ruff format --check src tests scripts` passed.
- `uv run ruff check src tests scripts` passed.
- `uv run pytest` passed with 89 tests.
- `uv run python scripts/validate.py` exited 0 and reported 1381
  `MISSING_HORIZONTAL_ACCURACY` warnings from the already imported PIG/TPN
  source-record measurements.

After PBI-021:

- A temporary copy of `data/caves/C-0002.yml` and
  `data/objects/KSW/KSW-0001.yml` with an added exercise measurement `m-003`
  validated successfully; the only issues were the two existing
  `MISSING_HORIZONTAL_ACCURACY` warnings from source-record PIG/TPN
  measurements.
- `uv run pytest tests/test_operational_docs.py` passed with 2 tests.
- `uv run ruff format --check src tests scripts` passed.
- `uv run ruff check src tests scripts` passed.
- `uv run pytest` passed with 91 tests.
- `uv run python scripts/validate.py` exited 0 and still reported only 1381
  `MISSING_HORIZONTAL_ACCURACY` warnings from imported source-record
  measurements.

After maintainer review of PIG `POINT_OUTSIDE_VALLEYS` on 2026-05-16:

- The maintainer confirmed that all 46 PIG `POINT_OUTSIDE_VALLEYS` rows are
  correctly outside configured `VALLEYS` polygons and approved them for final
  data.
- `build/staging/review/decisions-point-outside-valleys.yml` materialized 46
  PIG caves, 46 PIG objects under `data/objects/PL/PL-0001.yml` through
  `data/objects/PL/PL-0046.yml`, and 42 clean TPN measurement additions for
  those newly accepted objects.
- Four TPN rows targeting accepted `PL` objects remain excluded because they
  still have `TPN_MATCH_DISTANCE_REVIEW`: records 126, 493, 747 and 889.
- Current final YAML inventory is 860 objects, 860 caves, 1469 measurements and
  0 relations.
- Validation has 0 errors and 1557 warnings: 1469
  `MISSING_HORIZONTAL_ACCURACY` warnings from source-record measurements and 88
  `MEASUREMENT_OUTSIDE_VALLEYS` warnings for the reviewed fallback-`PL`
  measurements.

After maintainer acceptance of TPN distance-review and TPN-only rows on
2026-05-16:

- The maintainer approved all remaining `TPN_MATCH_DISTANCE_REVIEW` rows and
  all `TPN_NEW_ONLY` rows, including TPN-only `POINT_OUTSIDE_VALLEYS` rows.
- `build/staging/review/decisions-tpn-distance-and-new.yml` materialized 248
  TPN measurement additions plus 142 new TPN-only caves and 142 new TPN-only
  objects; `apply_review.py` reported 532 decisions, 780 written YAML files and
  0 review issues.
- Left for later from the TPN staging report: 5 `TPN_NR_INWENT_AMBIGUOUS` rows
  and the one clean duplicate match for `Smocza Jama` / row 476.
- Current final YAML inventory is 1002 objects, 1002 caves, 1859 measurements
  and 0 relations.
- `best-measurements` exports now include flattened reference columns
  `nr_inwent`, `pig_id`, `pig_url` and `tpn_globalid`.
- The rebuilt best-measurements export has 999 best rows from TPN and 3 best
  rows still from PIG.
- Validation has 0 errors and 2048 warnings: 1859
  `MISSING_HORIZONTAL_ACCURACY`, 101 `MEASUREMENT_OUTSIDE_VALLEYS`, 72
  `MEASUREMENT_DISTANCE_OUTLIER` and 16 `OBJECT_PREFIX_MISMATCH`.
