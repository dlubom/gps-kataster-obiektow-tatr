# QGIS release package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a portable QGIS 2D package to every release and PR preview, with authoritative GPS Best/Full data, online TPN basemaps and the latest stable released JKTZ traverses.

**Architecture:** A separate acquisition command resolves one public JKTZ release and verifies its archive checksum. The common release builder works offline with that local snapshot, writes deterministic point layers and a QGIS project, and packages relative paths and provenance. Before upload, pinned QGIS 3.44.15 and 4.0.1 containers load and render the actual relocated package offline and compare it with the source SQLite and JKTZ archive.

**Tech Stack:** Existing Python 3.12, stdlib XML/JSON/ZIP/SQLite/HTTP, pyshp, pyproj; native QGIS only for acceptance checks. No new Python runtime dependency.

**Spec:** Approved design below; main specification §6, §11–14 and §19.

## Approved design and approaches

The user approved the complete design after the `grilling` interview on 2026-10-28 and explicitly requested one PBI and PR. Considered delivery paths were a browser map and a portable QGIS project; the user selected QGIS. For this implementation, ordinary Python generation with native QGIS validation is preferred to making the data builder depend on an installed desktop PyQGIS runtime. A `.qgs` inside the outer ZIP is a supported native project format and avoids an unnecessary nested `.qgz` archive.

- New public asset: `katalog-qgis.zip`, also present in PR preview.
- GPS inputs come from this exact build's SQLite and Best export; preserve all measurements, manual Best choices, null accuracies, verification statuses, notes and coordinates.
- Separate Best, other non-rejected, rejected and difference-line layers; only Best is initially visible. A disabled Full layer provides the complete attribute table. A rejected-only Best remains in Best and is not repeated in the rejected layer.
- Difference lines connect each alternative position to that object's selected Best and report horizontal separation in PL-1992. They do not estimate accuracy or cave-wall distance. Coincident alternatives remain points but need no zero-length line.
- Start with the extent of all Best points, OSM at overview, selected TPN basemap visible after zoom; regional bookmarks. TPN image layers are mutually exclusive: RGB 2020 default, RGB 2018, NMT, NMPT. NMT/NMPT are images, not numerical elevation rasters; do not invent year/datum/accuracy.
- Resolve latest stable JKTZ once per CI build; package per-model Shapefile sets with original XYZ coordinates and EPSG:32634. The JKTZ group and all models are initially off. Preserve model prefixes rather than guessing GPS joins or cave identities.
- Keep JKTZ release tag, URLs, archive digest and CC BY-SA 4.0 attribution separate from GPS version/commit and CC BY 4.0. Do not reanchor JKTZ to newer GPS points.
- Runtime maps require internet. Generation and native package checks use local inputs and do not require map servers.
- A malformed/missing package blocks publication. Require native QGIS 3.44.15 and 4.0.1 validation before uploading release/preview assets. No plugins, project macros or executable project actions.
- Preserve source YAML and current exports. This is an additive artifact and CI change; no merge, tag or release is authorized by the implementation request.

## Global Constraints

- Python `>=3.12`; use `uv` and the existing lockfile.
- WGS84 `EPSG:4326` is the point geometry; project `EPSG:2180`; source `x_1992=N`, `y_1992=E`.
- Source data, Best logic, schemas and existing export contracts remain unchanged.
- One branch `codex/qgis-release` from main `13d734213328e5491c1a5c3171e2cb0fdcef705c`; one PBI-118 and draft PR.
- QGIS package contains relative local paths and records its exact external JKTZ input. Same local inputs/provenance produce the same QGIS ZIP bytes.
- QGIS test images: official `qgis/qgis:3.44.15-noble@sha256:907fb2cc44adc47a8eba64316c345f0675c226d11cddea47b16ef03097caea7e` and `qgis/qgis:4.0.1-trixie@sha256:9511f25e5e639ab89f641ea48ce3634f29f1083bf0f19f3bd35c05fd2ab351c7`.

## Review Focus

- A newer JKTZ release changes during a build: resolve once, validate the digest, use only the resolved archive thereafter; a later replay must supply that recorded snapshot.
- Empty catalog, rejected-only Best, shared local measurement IDs and coincident alternative positions: preserve complete disjoint point sets without invalid filters or fabricated lines.
- Corrupt/incomplete/duplicate archive members or unsafe names: reject before publishing the new QGIS asset; never execute or indiscriminately extract upstream archive contents.
- Offline/opening after relocation and HTML/XML-like source text: native loading must find relative files, preserve values and use safely escaped map tips.
- Coarse overview: explicitly hide TPN before its declared minimum zoom would trigger hundreds of fine tiles; retain OSM and points.

---

### Task 1: Resolve and validate a JKTZ input snapshot

**Files:** Create `src/gps_kataster_obiektow_tatr/jktz_snapshot.py`, `scripts/fetch_jktz_release.py`, `tests/test_jktz_snapshot.py` and a shared synthetic test snapshot helper.

**Interfaces:** `fetch_latest_jktz(output_dir: Path, *, token: str | None = None) -> Path` publishes one fresh input directory; `load_jktz_snapshot(source_dir: Path) -> JktzSnapshot` verifies metadata, SHA-256 and complete per-model Shapefile sets without networking. The immutable snapshot exposes version/provenance and selected source member bytes for Task 2.

- [ ] Write tests for a real synthetic PolyLineZ archive, byte-preserved geometry/attribution, checksum mismatch, missing sidecars, duplicate/unsafe members and interrupted acquisition preserving previous output.
- [ ] Run the tests and observe failures because the snapshot API does not exist.
- [ ] Implement bounded latest-release acquisition, explicit provenance, local validation and safe selected-member handling. Read an optional token only for the exact GitHub API host; never forward it to asset redirects.
- [ ] Run targeted tests, then the suite; commit the verified source-boundary step.

### Task 2: Generate the portable QGIS package offline

**Files:** Create `src/gps_kataster_obiektow_tatr/qgis_export.py`, project/style configuration resources and `tests/test_qgis_export.py`; extend the common builder and CLI only after direct package tests pass.

**Interfaces:** `write_qgis_export(*, sqlite_path: Path, best_geojson_path: Path, jktz_source_dir: Path, output_path: Path, generated_at: str, release_version: str | None, source_commit: str | None) -> Path`. The package manifest describes GPS and JKTZ inputs, local layer roles/counts/checksums and basemaps. Existing builder receives an explicit local `jktz_source_dir` and includes the new ZIP in `artifact_paths`.

- [ ] Write independently derived fixture assertions for selected/manual/rejected-only Best, full history and source attributes, correct geometry axes, positive-distance lines, empty/coincident cases, defaults, overview scale, model groups, relative paths and exact provenance.
- [ ] Run and observe the missing-exporter failures.
- [ ] Implement deterministic RFC 7946 point/line GeoJSON, conservative QGIS XML and atomic ZIP writing; retain original JKTZ Shapefile bytes and licensing files.
- [ ] Verify byte-identical QGIS ZIPs for identical inputs in two directories, and preservation of an existing asset on invalid input. Add invalid/missing Best and malformed-source mutations that tests reject.
- [ ] Integrate builder/CLI with an explicit local input directory and update existing integration fixtures to provide that real synthetic snapshot. Verify all previous data exports remain unchanged.
- [ ] Run targeted tests, then the suite; commit the verified generator step.

### Task 3: Native acceptance gates, CI delivery and documentation

**Files:** Create `scripts/verify_qgis_package.py` and `scripts/check_qgis_containers.sh`; extend `.github/workflows/release.yml`, `.github/workflows/pr-preview.yml`, preview CLI and workflow/package tests. Update specification, README PL/EN/SK, operations, artifact documentation, backlog/context and `docs/asdlc/verification/PBI-118.md`.

**Interfaces:** Native verifier takes `--package`, `--sqlite-zip` and `--jktz-source-dir`; it unpacks into a fresh directory, resolves actual providers, compares points against SQLite and model bytes against JKTZ, and renders local vectors without networking. The container wrapper runs both pinned images with `--network none`, read-only repository mount and writable temporary workspace.

- [ ] Write failing integration assertions for the 13th release asset, preview parity/checksum coverage and acquisition/native-check ordering before upload. Exercise actual upload arguments through the existing local `gh` stub.
- [ ] Implement common input acquisition in release and PR preview; run both native checks before upload. Raise preview timeout only to accommodate measured/native image pulls and checks.
- [ ] Validate the real latest JKTZ v1.4.12 input, all GPS records, relocated package and both native QGIS versions. Open the final project in the user's desktop QGIS for visual acceptance. Verify offline rendering, layer defaults and source attributes.
- [ ] Run full Ruff format/lint, pytest, YAML validation, real artifact build, independent artifact/source checks and targeted corruption/mutation checks; record evidence and limitations in PBI-118.
- [ ] Request one fresh whole-branch review; fix actionable findings with regression tests; commit and push verified changes.
- [ ] Create/attach the draft PR, confirm remote SHA and exact-SHA CI plus downloaded preview package; mark PBI status appropriately. Do not merge/tag/publish.

## Self-review and execution

All approved scope is owned by the three tasks. Source snapshot → exporter → native/CI acceptance are the only task interfaces. Tests derive expected IDs/coordinates/attributes from literals or independent SQLite/source readers, never exporter helpers. Native compatibility and external availability are distinct checks. The user already approved the complete design and requested implementation; execution proceeds inline without another planning approval round.
