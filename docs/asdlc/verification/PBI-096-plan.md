# PBI-096 Implementation Plan

> Execution: inline using executing-plans; accepted PBI-095 design and explicit
> instruction authorize routine implementation decisions without another gate.

**Goal:** complete, replayable public TPN snapshot; no catalog changes.
**Architecture:** stdlib HTTP adapter and strict API validation; separate immutable
snapshot writer/offline reader; thin fetch/verify CLI. No new dependency.
**Tech Stack:** Python 3.12, urllib, hashlib, pytest, existing Ruff/CI.
**Spec:** ../tpn_sync_contract.md §2–4 and ../tpn_sync_examples.md §1.

## Constraints and review focus

- Fixed Topografia /6 identity; all 22 declarations / 21 attributes; EPSG:4326.
- Reject schema drift, duplicate JSON keys, non-finite values, invalid dates/GUID/XY.
- Equal counts are insufficient: compare full ID sets, page sequence and GUIDs.
- Short pages continue when exceededTransferLimit=true; zero progress fails closed.
- Restart the entire acquisition on retry, maximum 3 attempts; no mixed attempts.
- Files are never overwritten. Manifest only published after byte/hash/content readback.
- Offline replay derives manifest checks from raw responses, rejects extra/missing files,
  bad paths/symlinks and forged summaries, even with recomputed hashes.
- Persist exact policy text as policy.md and its hash; no revision/location hashes yet.
- Same XY for different GUIDs is legal: validate geometry, do not decide object identity.

## One delivery unit: adapter, storage, CLI and proof

Files: src/gps_kataster_obiektow_tatr/tpn_api.py (fetch/validate),
tpn_snapshot.py (publish/replay), scripts/fetch_tpn_snapshot.py (CLI),
tests/test_tpn_snapshot.py and tests/fixtures/tpn_api/ (offline scenarios).

Interfaces: fetch_snapshot(repo_root, snapshot_id, page_size=2000, attempts=2,
transport=None) -> Path; verify_snapshot(path) -> manifest dict.
Transport: callable(endpoint, params) -> exact response bytes, with bounded timeout.

- [x] Write synthetic multi-page fixtures and failure tests; run to confirm RED.
- [x] Implement API adapter and strict schema/feature/count/ID checks.
- [x] Implement staged exclusive publication and offline semantic/hash replay.
- [x] Add CLI fetch/verify, error and no-overwrite tests; confirm GREEN.
- [x] Run full live download to data/sources/tpn/snapshots/ with page size 500.
- [x] Run Ruff, complete pytest, YAML validation, artifact build/readback,
      protected-file hash comparison and targeted mutations.
- [x] Independent final review; repair demonstrated defects and rerun affected checks.
- [x] Update PBI log/backlogs/context/handoff, commit/push, verify remote SHA and CI.

No PBI-097 implementation, schedule, merge, tag or release. Final CI receipt goes
in PR description to avoid recursive commits recording their own SHA.

## Execution record

Implemented inline on the explicitly requested existing PR branch. 73 snapshot
tests pass, live readback succeeds, 8/8 isolated guard mutations killed.
Independent review found no P1/P2; strict flag/CRS types reproduced RED and fixed.
Power-loss directory durability remains documented rather than adding a new
filesystem recovery subsystem. Detailed evidence: [PBI-096](PBI-096.md).

Implementation delivered as a511e0b52a65253194e2a4752d1319227e201563;
CI 39255804981 passed all jobs/steps. Final documentation receipt SHA/CI
is recorded in PR #12 after its own validation. Stop at PBI-096.
