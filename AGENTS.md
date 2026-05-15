# Agent instructions for gps-kataster-obiektow-tatr

This repository is managed in a lightweight AS-DLC mode. Treat the files in
the repo as the durable project memory; do not rely on chat history.

## Canonical context

Read these files before making changes:

1. `specyfikacja_gps_kataster_obiektow_tatr_v_2.md` - current project
   specification and domain model.
2. `docs/asdlc/backlog_v1.md` - V1 backlog, PBI order, scope and verification.
3. `docs/asdlc/context.md` - compact current state and operating agreements.

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

- YAML in `data/` is the future source of truth.
- SQLite, GeoJSON, GPX, CSV and Shapefile outputs are generated artifacts.
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
