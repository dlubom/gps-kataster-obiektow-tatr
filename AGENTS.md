# Agent instructions for gps-kataster-obiektow-tatr

This repository uses lightweight AS-DLC. Keep durable project knowledge in
current repository files; use Git and PRs for implementation history.

## Canonical context

Read these files before making changes:

1. `specyfikacja_gps_kataster_obiektow_tatr_v_2.md` - current project
   specification and domain model.
2. `docs/asdlc/context.md` - current state, open questions and source decisions.
3. `docs/operations.md` - runtime, editing and verification commands.
4. `docs/asdlc/backlog_v1.md` - consult when choosing or changing PBI scope.

## Scope and documentation

- Implement the requested task; new work requires a user instruction.
- Keep behavior in the specification and operational docs. Update context and
  backlog only when decisions, unresolved questions or task status change.
- Keep source provenance and unresolved data decisions. Do not retain completed
  task cards, superseded document versions or execution logs in the working tree;
  Git and PRs retain that history. Record verification in the PR and CI.
- Never revert user changes unless explicitly requested.

## Git and delivery

- Inspect status and fetch origin. Start new work from current `origin/main` in
  an isolated branch. For an explicitly requested continuation of an open PR,
  use its current remote head in a separate worktree. Never resume a stale branch
  merely by name or restore the abandoned `codex/review-remediation` series.
- Commit small completed steps with readable conventional messages. Run the
  verification appropriate to the change unless the user limits it; record
  exactly what was and was not checked. Confirm remote SHA after pushing.
- Main changes only through PRs with successful `Validate code and data` for
  that SHA. The single-maintainer policy requires 0 approving reviews; preserve
  required CI and the empty bypass list. An unverified change remains in its PR.
- Do not merge, tag or publish a release without a separate user instruction.

## Current V1 boundaries

- YAML records in `data/` are the source of truth; `schema/catalog.sql` defines
  the database model. Canonical files contain source geometry, cave membership
  and Best policy; derived fields belong to read models and exports.
- Temporary PostgreSQL 18 / PostGIS 3.6 owns integrity, automatic Best and derived
  coordinates. Use the digest-pinned image in `compose.yaml` / `postgres.py`;
  no permanent production database is maintained.
- PostgreSQL dump, GeoPackage, GeoJSON, GPX, CSV, Excel and Shapefile are generated
  artifacts. A complete build must restore the dump and read back the GeoPackage.
- Full verification: `uv sync --frozen`, then `uv run --frozen python scripts/check_project.py
  --base-ref origin/main` (one disposable server for the full gate). See
  `docs/operations.md` for Docker/native requirements. Missing history baselines
  block writes/builds; never replace an event's real base with candidate HEAD.
- Existing measurements and their order are immutable; corrections append a new
  measurement. Unknown bibliography is legal and reported as a warning.
- `Obiekt` is a concrete field object / point.
- `Jaskinia` is a logical/catalog entity grouping one or more objects.
- TPN `GLOBALID` generally belongs to `Obiekt.external_refs`.
- PIG `ID`, PIG `Link` and `NR_INWENT` generally belong to
  `Jaskinia.external_refs`.
- Frontend, PWA, GitHub API integration, permanent Geoportal importer and
  cyclic external synchronization are outside V1.
