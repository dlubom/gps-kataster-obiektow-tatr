# Agent instructions for gps-kataster-obiektow-tatr

This repository is managed in a lightweight AS-DLC mode. Treat the files in
the repo as the durable project memory; do not rely on chat history.

## Canonical context

Read these files before making changes:

1. `specyfikacja_gps_kataster_obiektow_tatr_v_2.md` - current project
   specification and domain model.
2. `docs/asdlc/backlog_v1.md` - V1 backlog, PBI order, scope and verification.
3. `docs/asdlc/context.md` - compact current state and operating agreements.
4. For the review-remediation series, `docs/asdlc/remediation_runbook.md`
   and `docs/asdlc/remediation_plan.md` - session protocol and PBI cards.

## Review remediation from 2026-09-05

- Use branch `codex/review-remediation`; fetch and inspect its current remote
  state before choosing work. Do not restart the series from `main`.
- Implement exactly one ready PBI per session unless the user explicitly
  requests more. Current statuses are in the remediation section of the
  backlog; use `context.md` for the latest handoff and verify it against Git.
- Follow the runbook's full verification, scoped commit, frequent push and
  remote-SHA/CI checks for each completed small step. Keep evidence in
  `docs/asdlc/verification/PBI-NNN.md`, including unfinished work.
- A clean session must be able to continue from tracked files and origin.
  Do not make continuation depend on chat, account memory, `build/` or `/tmp`.
- The current request authorizes planning and delivery of PBI-034. Start
  implementation PBI-035 only in a subsequent execution request.
- Do not merge to `main`, tag or publish a release as part of this series
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
