# Agent instructions for gps-kataster-obiektow-tatr

This repository is managed in a lightweight AS-DLC mode. Treat the files in
the repo as the durable project memory; do not rely on chat history.

## Canonical context

Read these files before making changes:

1. `specyfikacja_gps_kataster_obiektow_tatr_v_2.md` - current project
   specification and domain model.
2. `docs/asdlc/context.md` - current state, open questions and source decisions.
3. `docs/operations.md` - runtime, editing and verification commands.
4. `docs/asdlc/backlog_v1.md` - consult when choosing or changing PBI scope.

For a PR #40 simplification task U03–U11, start at
`docs/asdlc/plans/PR-40/README.md`. It routes to the specification, design,
execution procedure and individual task cards, and owns their statuses.
Read the selected card before coding; implement only the requested task.

For cleanup tasks U12, U15, U16 and U17,
start at `docs/asdlc/plans/PR-40/next/README.md` and read its `spec.md`.
U13/U14 (retired IDs and deletion exceptions) were withdrawn from scope.
The cleanup preserves current history errors; these tasks are not yet implemented.

## Git and delivery

- The user abandoned the previous branch-based repair series on 2026-10-15.
  Its PBI-034–077 statuses do not apply to this checkout. Do not resume,
  merge or cherry-pick `codex/review-remediation` or other old branches.
- Start each new session from current `main`: inspect status, fetch origin,
  and on a clean checkout use `git switch main` and `git pull --ff-only`.
  Compare HEAD with `origin/main`; use the live tip, not the release SHA.
  New changes go on a branch from main and reach main only through a PR
  with a successful `Validate code and data` check. The permanent
  single-maintainer policy requires 0 approving GitHub reviews; retain
  the PR rule, required CI, and empty bypass list.
- Exception for an explicitly requested continuation of an active PR #40 task while PR #40
  is open: isolate work from its current remote head, as described in
  `docs/asdlc/plans/PR-40/development.md`. After the PR is merged, use current
  main and a new PR. Never resume a stale local branch merely by its name.
- New work requires a user instruction;
  implement exactly one ready PBI per session unless explicitly asked for more.
- Keep current behavior in the specification and operational docs. Record
  verification in the PR and CI; add separate research evidence only when it
  establishes source provenance or a data decision. Retain historical logs in Git
  rather than adding repeated step reports or completed implementation plans.
- Commit and push verified steps; confirm the remote SHA and CI for that SHA.
  Do not merge, tag or publish a release
  without a separate user instruction.

## Operating mode

- Use spec-anchored development: the spec defines current system intent.
- Use PBIs as execution units: small scope, explicit verification, commit after
  each completed step.
- Update `docs/asdlc/backlog_v1.md` when a PBI status changes.
- Update `docs/asdlc/context.md` when an important decision, data fact, or
  project status changes.
- Keep implementation conservative and close to the specification.
- Prefer deterministic scripts, schemas and tests over prompt-only decisions.
- Do not start bulk PIG/TPN import into final YAML until schema, fixtures and
  validator exist.

## Current V1 boundaries

- YAML records in `data/` are the source of truth; `schema/catalog.sql` defines
  the database model. Canonical files contain source geometry, cave membership
  and Best policy; derived fields belong to read models and exports.
- Temporary PostgreSQL 18 / PostGIS 3.6 owns integrity, automatic Best and derived
  coordinates. Use the digest-pinned image in `compose.yaml` / `postgres.py`;
  no permanent production database is maintained.
- PostgreSQL dump, GeoPackage, GeoJSON, GPX, CSV, Excel and Shapefile are generated
  artifacts. A complete build must restore the dump and read back the GeoPackage.
- Run `uv sync --frozen`, then `uv run --frozen python scripts/check_project.py
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

## Commit discipline

- Commit after every completed PBI or equivalent small step.
- Use conventional, readable commit messages, for example
  `chore: scaffold project structure`.
- Before committing, run the verification that matches the PBI.
- Never revert user changes unless explicitly requested.
