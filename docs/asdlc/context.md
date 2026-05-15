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

PBI-004 is next:

- define JSON Schema files for object, cave and relation YAML,
- add `schema/CHANGELOG.md` for `schema_version: 1`.

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
