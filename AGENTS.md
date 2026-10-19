# Agent instructions for gps-kataster-obiektow-tatr

This repository is managed in a lightweight AS-DLC mode. Treat the files in
the repo as the durable project memory; do not rely on chat history.

## Canonical context

Read these files before making changes:

1. `specyfikacja_gps_kataster_obiektow_tatr_v_2.md` - current project
   specification and domain model.
2. `docs/asdlc/backlog_v1.md` - V1 backlog, PBI order, scope and verification.
3. `docs/asdlc/context.md` - compact current state and operating agreements.
4. `docs/asdlc/remediation_plan.md` and `docs/asdlc/remediation_runbook.md` -
   active repair scope and delivery procedure.
5. For TPN integration: `docs/asdlc/tpn_sync_handoff.md`,
   `tpn_sync_plan.md`, `tpn_sync_backlog.md`, `tpn_sync_contract.md` and
   `tpn_sync_examples.md` in `docs/asdlc/`, plus the latest PBI verification.

## Main remediation from 2026-10-15

- The user abandoned the previous branch-based repair series on 2026-10-15.
  Its PBI-034–077 statuses do not apply to this checkout. Do not resume,
  merge or cherry-pick `codex/review-remediation` or other old branches.
- PBI-078–086 are complete and PR #4 is merged into `main` at
  `89592969298cf04b547a694edf2755eb56209ae3`. Post-merge CI passed and
  release v1.0.3 is published; see `docs/asdlc/verification/v1.0.3.md`.
  The remediation branch is historical; do not resume it.
- Start each new session from current `main`: inspect status, fetch origin,
  and on a clean checkout use `git switch main` and `git pull --ff-only`.
  Compare HEAD with `origin/main`; use the live tip, not the release SHA.
  New changes go on a branch from main and through PR; main requires review.
  When the user explicitly asks to continue an open PR, inspect its live
  state and continue its branch instead; preserve other people's changes.
- No ready PBI remains in this series. New work requires a user instruction;
  implement exactly one ready PBI per session unless explicitly asked for more.
- For simple data corrections (no code/schema changes), explanations in YAML,
  the PR description and CI suffice; no separate or expanded Markdown report is required.
  Otherwise, keep evidence in `docs/asdlc/verification/PBI-NNN.md` so a clean
  checkout is sufficient to continue without chat history or `build/`.
- Commit and push verified steps; confirm remote SHA and CI for that SHA
  as described in the runbook. Do not merge, tag or publish a release
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
- Frontend, PWA, general GitHub API integration, permanent Geoportal/PIG
  importers and their cyclic synchronization are outside V1. The only
  extension is the reviewed TPN batch process in spec section 8.4;
  its future GitHub Actions may prepare one PR but never merge it.

## TPN integration — accepted contract, staged implementation

- PBI-095 defines the contract only. Read live statuses in the TPN backlog;
  execute one explicitly requested ready PBI and stop. Contract approval
  does not authorize implementing PBI-096–103 or enabling a schedule.
- Process the initial backlog before monthly checks. One PR per batch,
  explicit per-record decisions, human-only merge; no bot/agent merge,
  auto-merge, review approval, tag or release through the TPN process.
- Match typed `TPN/source_globalid`; a new GLOBALID is not proof of a new
  object. Several source GUIDs may belong to one previously merged object.
- Preserve measurement history, raw sources, manual best and GNSS/geodetic
  evidence regardless of source/status/unknown accuracy. Appending a
  measurement and selecting best are separate decisions (`keep/select_new`).
- If the field observation date is unknown, use TPN LAST_EDITED_DATE as
  the source-state date with an explicit explanatory measurement note.
  Missing modification date defers measurement creation; never use fetch time.
- Snapshots, revision decisions, preimages and defer history must be durable
  before catalog changes. A partial API read cannot justify deletion.
- Historical local JSON is optional for PBI-095 and is not in Git. Later
  cards must acquire/validate their own inputs; old counts/hashes are not
  acceptance targets. Current CSV/XLSX review is not the new sync protocol.

## Commit discipline

- Commit after every completed PBI or equivalent small step.
- Use conventional, readable commit messages, for example
  `chore: scaffold project structure`.
- Before committing, run the verification that matches the PBI.
- Never revert user changes unless explicitly requested.
