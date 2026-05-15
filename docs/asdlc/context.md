# AS-DLC project context

Last updated: 2026-05-15

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

PBI-010 is next:

- implement local validation rules with error/warning severity,
- include rule code, severity, file and description in reports,
- exit nonzero only when validation errors are present.

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
