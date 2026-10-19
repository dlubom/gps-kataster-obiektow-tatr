"""PBI-100: real plans on isolated catalogs, no production decisions."""

import json
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from test_tpn_changes import GUID, GUID2, csv_source, feature, snapshot

from gps_kataster_obiektow_tatr import tpn_changes
from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992
from gps_kataster_obiektow_tatr.tpn_normalization import canonical

REPO = Path(__file__).resolve().parents[1]


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args]).decode().strip()


def hashes(root):
    from gps_kataster_obiektow_tatr.tpn_snapshot import sha256

    return {
        str(p.relative_to(root)): sha256(p.read_bytes())
        for p in (root / "data").rglob("*")
        if p.is_file()
    }


@pytest.fixture
def batch_repo(tmp_path):
    for folder in ("config", "data/shapes", "schema"):
        shutil.copytree(REPO / folder, tmp_path / folder)
    (tmp_path / "docs/asdlc").mkdir(parents=True)
    shutil.copyfile(
        REPO / "docs/asdlc/tpn_sync_contract.md", tmp_path / "docs/asdlc/tpn_sync_contract.md"
    )
    for folder in ("objects/KSW", "caves", "relations"):
        (tmp_path / "data" / folder).mkdir(parents=True)
    obj = yaml.safe_load((REPO / "tests/fixtures/schema/valid-object.yml").read_text())
    obj["external_refs"][0]["external_id"] = GUID
    obj["attachments"] = []
    m = obj["measurements"][0]
    m.update(lat=49.2, lon=19.8, source_ref="TPN:" + GUID, notes="Ręczna uwaga")
    point = wgs84_to_1992(m["lat"], m["lon"])
    m.update(x_1992=point.x_1992, y_1992=point.y_1992)
    (tmp_path / "data/objects/KSW/KSW-0001.yml").write_text(yaml.safe_dump(obj, allow_unicode=True))
    shutil.copyfile(
        REPO / "tests/fixtures/schema/valid-cave.yml", tmp_path / "data/caves/C-0001.yml"
    )
    csv_source(tmp_path, [feature()])
    snap = snapshot(tmp_path, "fixture", [feature(lon=19.801)])
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    git(tmp_path, "config", "user.name", "Fixture")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "fixture base")
    git(tmp_path, "update-ref", "refs/remotes/origin/main", "HEAD")
    return tmp_path, snap


def prepare(batch_repo, actions=None, status="approve"):
    from gps_kataster_obiektow_tatr.tpn_batch import prepare_batch

    root, snap = batch_repo
    head = git(root, "rev-parse", "HEAD")
    report = tpn_changes.compare(
        root, snap, batch_id="fixture-batch", base_commit=head, protect_best=True
    )
    report["accepted_state_commit"] = head
    proposal = {
        "change_id": report["records"][0]["change_id"],
        "target": report["records"][0]["target"],
        "preimage": report["records"][0]["preimage"],
        "actions": actions or [],
        "conflict_acknowledgements": report["records"][0]["conflicts"],
        "candidate_acknowledgements": [],
    }
    changes, decisions = prepare_batch(root, report, [proposal])
    d = decisions["decisions"][0]
    d.update(
        status=status,
        reviewed_by="human",
        reviewed_at="2026-10-19T14:00:00Z",
        reason="Fixture review",
    )
    return changes, decisions


def append_action(key="new-location", mode="manual", kind="keep"):
    from gps_kataster_obiektow_tatr.tpn_normalization import normalize_feature

    loc = normalize_feature(feature(lon=19.801))["location_hash"]
    best = {"action": kind, "resulting_mode": mode, "reason": "Zachować punkt eksportu"}
    best["measurement_id" if kind == "keep" else "measurement_key"] = (
        "m-001" if kind == "keep" else key
    )
    return {
        "action": "append_measurement",
        "object_id": "KSW-0001",
        "measurement_key": key,
        "location_hash": loc,
        "best_action": best,
    }


def test_append_preserves_history_height_and_best_and_replay(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch, check_batch, plan_batch

    root, _ = batch_repo
    old = yaml.safe_load((root / "data/objects/KSW/KSW-0001.yml").read_text())
    changes, decisions = prepare(batch_repo, [append_action()])
    before = hashes(root)
    plan = plan_batch(root, changes, decisions, reviewers={"human"})
    assert hashes(root) == before
    assert plan["best_changes"][0]["after"]["measurement_id"] == "m-001"
    assert "KSW-0001" in plan["diff"] and plan["export_changes"]
    apply_batch(root, changes, decisions, reviewers={"human"})
    new = yaml.safe_load((root / "data/objects/KSW/KSW-0001.yml").read_text())
    assert new["measurements"][0] == old["measurements"][0]
    assert new["measurements"][1]["elevation_m"] is None
    assert new["measurements"][1]["verification_status"] == "nieweryfikowany"
    assert new["measurements"][1]["horizontal_accuracy_m"] is None
    assert new["best_measurement"]["measurement_id"] == "m-001"
    after = hashes(root)
    assert apply_batch(root, changes, decisions, reviewers={"human"})["noop"]
    assert hashes(root) == after
    check_batch(root, "fixture-batch")


def test_defer_queue_and_pending_gate(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch, check_batch

    root, _ = batch_repo
    changes, decisions = prepare(batch_repo, status="pending")
    decisions["decisions"][0].update(reviewed_by=None, reviewed_at=None)
    apply_batch(root, changes, decisions, reviewers={"human"})
    with pytest.raises(ValueError, match="pending"):
        check_batch(root, "fixture-batch")
    decisions["decisions"][0].update(
        status="defer", reviewed_by="human", reviewed_at="2026-10-19T14:00:00Z"
    )
    apply_batch(root, changes, decisions, reviewers={"human"})
    state = json.loads((root / "data/source_state/tpn/state.json").read_bytes())
    assert len(state["deferred"]) == 1
    check_batch(root, "fixture-batch")


@pytest.mark.parametrize(
    "tamper", ["hash", "unknown", "version", "reviewer", "conflict", "preimage", "payload"]
)
def test_invalid_batch_writes_nothing(batch_repo, tamper):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch

    root, _ = batch_repo
    changes, decisions = prepare(batch_repo, [append_action()])
    if tamper == "hash":
        decisions["snapshot_hash"] = "0" * 64
    if tamper == "unknown":
        decisions["extra"] = "no"
    if tamper == "version":
        decisions["format_version"] = True
    if tamper == "reviewer":
        decisions["decisions"][0]["reviewed_by"] = "bot"
    if tamper == "conflict":
        changes["execution"]["proposals"][0]["conflict_acknowledgements"] = []
    if tamper == "preimage":
        decisions["decisions"][0]["preimage"] = {}
    if tamper == "payload":
        decisions["decisions"][0]["actions"][0]["lat"] = 1
    before = hashes(root)
    with pytest.raises(ValueError):
        apply_batch(root, changes, decisions, reviewers={"human"})
    assert hashes(root) == before


def test_write_failure_keeps_catalog_and_state_together(batch_repo, monkeypatch):
    from gps_kataster_obiektow_tatr import tpn_batch, tpn_transaction

    root, _ = batch_repo
    changes, decisions = prepare(batch_repo, [append_action()])
    before = hashes(root)

    def fail(*args):
        raise OSError("injected swap failure")

    monkeypatch.setattr(tpn_transaction, "exchange_directories", fail)
    with pytest.raises(OSError):
        tpn_batch.apply_batch(root, changes, decisions, reviewers={"human"})
    assert hashes(root) == before


def test_changed_result_blocks_replay_and_replan(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch

    root, _ = batch_repo
    changes, decisions = prepare(batch_repo, [append_action()])
    apply_batch(root, changes, decisions, reviewers={"human"})
    path = root / "data/objects/KSW/KSW-0001.yml"
    path.write_text(path.read_text() + "\n# human edit\n")
    before = hashes(root)
    with pytest.raises(ValueError, match="result|output"):
        apply_batch(root, changes, decisions, reviewers={"human"})
    decisions["decisions"][0].update(status="reject", actions=[])
    with pytest.raises(ValueError):
        apply_batch(root, changes, decisions, reviewers={"human"})
    assert hashes(root) == before


def recommit(root):
    git(root, "add", ".")
    git(root, "commit", "-qm", "fixture update")
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")


def many(batch_repo, actions_by_guid, statuses=None):
    from gps_kataster_obiektow_tatr.tpn_batch import prepare_batch

    root, snap = batch_repo
    head = git(root, "rev-parse", "HEAD")
    report = tpn_changes.compare(
        root, snap, batch_id="fixture-batch", base_commit=head, protect_best=True
    )
    report["accepted_state_commit"] = head
    proposals = []
    for r in report["records"]:
        if not (r["requires_review"] or r["actionable"]):
            continue
        proposals.append(
            {
                "change_id": r["change_id"],
                "target": r["target"],
                "preimage": r["preimage"],
                "actions": actions_by_guid.get(r["globalid"], []),
                "conflict_acknowledgements": r["conflicts"],
                "candidate_acknowledgements": [c["key"] for c in r["candidates"]],
            }
        )
    changes, decisions = prepare_batch(root, report, proposals)
    for d in decisions["decisions"]:
        d.update(
            status=(statuses or {}).get(d["globalid"], "approve"),
            reviewed_by="human",
            reviewed_at="2026-10-19T14:00:00Z",
            reason="Fixture review",
        )
        if d["status"] in ("reject", "defer"):
            d["actions"] = []
    return changes, decisions


def test_metadata_notes_preserve_text_and_null_needs_explicit_clear(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch
    from gps_kataster_obiektow_tatr.tpn_normalization import normalize_feature

    root, _ = batch_repo
    rev = normalize_feature(feature(lon=19.801))["revision_hash"]
    obj = yaml.safe_load((root / "data/objects/KSW/KSW-0001.yml").read_text())
    obj["notes"] = "Ręczna nazwa i notatka"
    (root / "data/objects/KSW/KSW-0001.yml").write_text(yaml.safe_dump(obj, allow_unicode=True))
    recommit(root)
    action = {
        "action": "update_metadata",
        "target": {"kind": "object", "id": "KSW-0001"},
        "field": "notes",
        "before": obj["notes"],
        "after": obj["notes"] + "\n[TPN " + rev + "] opis",
        "append_text": "opis",
        "revision_hash": rev,
    }
    changes, decisions = prepare(batch_repo, [action])
    apply_batch(root, changes, decisions, reviewers={"human"})
    result = yaml.safe_load((root / "data/objects/KSW/KSW-0001.yml").read_text())
    assert result["notes"] == action["after"]
    assert result["measurements"] == obj["measurements"]
    before = hashes(root)
    assert apply_batch(root, changes, decisions, reviewers={"human"})["noop"]
    assert hashes(root) == before


@pytest.mark.parametrize("protection", ["gnss", "manual", "own_verified", "historical_gnss"])
def test_protection_blocks_select_and_pending_manifest_migration(batch_repo, protection):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch

    root, _ = batch_repo
    path = root / "data/objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(path.read_text())
    if protection == "manual":
        obj["best_measurement"].update(mode="manual", reason="Human")
    elif protection == "own_verified":
        obj["measurements"][0].update(source="wlasne", verification_status="zweryfikowany")
    elif protection == "historical_gnss":
        old = deepcopy(obj["measurements"][0])
        old.update(id="m-009", method="gnss", source="inne", verification_status="odrzucony")
        obj["measurements"].append(old)
    else:
        obj["measurements"][0].update(method="gnss", source="inne")
    path.write_text(yaml.safe_dump(obj, allow_unicode=True))
    recommit(root)
    changes, decisions = prepare(batch_repo, [append_action(kind="select_new")])
    before = hashes(root)
    with pytest.raises(ValueError, match="PROTECTED"):
        apply_batch(root, changes, decisions, reviewers={"human"})
    assert hashes(root) == before
    if protection == "gnss":
        changes, decisions = prepare(batch_repo, [append_action()])
        with pytest.raises(ValueError, match="migration_manifest_approval_required"):
            apply_batch(root, changes, decisions, reviewers={"human"})
        assert hashes(root) == before


@pytest.mark.parametrize("relink", [False, True])
def test_multiple_guids_one_object_plan_ids_and_best_together(batch_repo, relink):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch
    from gps_kataster_obiektow_tatr.tpn_normalization import normalize_feature

    root, _ = batch_repo
    path = root / "data/objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(path.read_text())
    obj["external_refs"].append(
        {"system": "TPN", "ref_type": "source_globalid", "external_id": GUID2}
    )
    path.write_text(yaml.safe_dump(obj, allow_unicode=True))
    csv_source(root, [feature(), feature(guid=GUID2, oid=2)])
    snap = snapshot(root, "two", [feature(lon=19.801), feature(guid=GUID2, oid=2, lon=19.802)])
    if relink:
        cave = yaml.safe_load((root / "data/caves/C-0001.yml").read_text())
        cave.update(id="C-0002", name="Confirmed destination cave", object_ids=[])
        (root / "data/caves/C-0002.yml").write_text(yaml.safe_dump(cave, allow_unicode=True))
    recommit(root)
    a, b = append_action(), append_action(key="location-2")
    b["location_hash"] = normalize_feature(feature(guid=GUID2, oid=2, lon=19.802))["location_hash"]
    changes, decisions = many((root, snap), {GUID: [a], GUID2: [b]})
    if relink:
        from gps_kataster_obiektow_tatr.tpn_snapshot import sha256

        proposal = next(
            p for p in changes["execution"]["proposals"] if p["change_id"].startswith(GUID + ":")
        )
        action = {"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0002"}
        proposal["actions"].insert(0, action)
        proposal["preimage"]["data/caves/C-0002.yml"] = sha256(
            (root / "data/caves/C-0002.yml").read_bytes()
        )
        decision = next(d for d in decisions["decisions"] if d["globalid"] == GUID)
        decision["actions"] = deepcopy(proposal["actions"])
        decision["preimage"] = deepcopy(proposal["preimage"])
        decisions["changes_hash"] = sha256(canonical(changes) + b"\n")
    plan = apply_batch(root, changes, decisions, reviewers={"human"})
    obj = yaml.safe_load(path.read_text())
    assert [m["id"] for m in obj["measurements"]] == ["m-001", "m-002", "m-003"]
    assert obj["best_measurement"]["measurement_id"] == "m-001"
    assert len(plan["best_changes"]) == 1
    assert len(plan["measurement_map"]) == 2
    if relink:
        assert obj["cave_id"] == "C-0002"


def test_bad_last_decision_and_conflicting_best_write_nothing(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch

    root, snap = batch_repo
    a = append_action()
    b = deepcopy(a)
    b["measurement_key"] = "another"
    changes, decisions = prepare(batch_repo, [a, b])
    before = hashes(root)
    with pytest.raises(ValueError, match="already in history"):
        apply_batch(root, changes, decisions, reviewers={"human"})
    assert hashes(root) == before


def test_real_diff_gate_detects_catalog_and_state_tampering(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch, check_batch

    root, _ = batch_repo
    changes, decisions = prepare(batch_repo, [append_action()])
    apply_batch(root, changes, decisions, reviewers={"human"})
    path = root / "data/source_state/tpn/state.json"
    state = json.loads(path.read_bytes())
    state["resolutions"][0]["reason"] = "forged"
    path.write_bytes(canonical(state) + b"\n")
    with pytest.raises(ValueError, match="diff|output"):
        check_batch(root, "fixture-batch")


def test_forged_receipt_cannot_authorize_overwriting_human_edit(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch

    root, _ = batch_repo
    changes, decisions = prepare(batch_repo, [append_action()])
    apply_batch(root, changes, decisions, reviewers={"human"})
    path = root / "data/objects/KSW/KSW-0001.yml"
    path.write_text(path.read_text() + "\n# human edit\n")
    receipt = root / "data/source_reviews/tpn/fixture-batch/application.json"
    data = json.loads(receipt.read_bytes())
    data["result_tree"]["objects/KSW/KSW-0001.yml"] = hashes(root)["data/objects/KSW/KSW-0001.yml"]
    receipt.write_bytes(canonical(data) + b"\n")
    decisions["decisions"][0].update(status="reject", actions=[])
    before = hashes(root)
    with pytest.raises(ValueError):
        apply_batch(root, changes, decisions, reviewers={"human"})
    assert hashes(root) == before


def test_config_change_invalidates_decision(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch

    root, _ = batch_repo
    changes, decisions = prepare(batch_repo, [append_action()])
    with (root / "config/prefixes.yml").open("a") as f:
        f.write("\n# changed\n")
    before = hashes(root)
    with pytest.raises(ValueError):
        apply_batch(root, changes, decisions, reviewers={"human"})
    assert hashes(root) == before


@pytest.mark.parametrize("wrong_target", [False, True])
def test_new_opening_link_existing_cave_and_whole_batch_ids(batch_repo, wrong_target):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch, check_batch, prepare_batch
    from gps_kataster_obiektow_tatr.tpn_normalization import normalize_feature

    root, _ = batch_repo
    f = feature(guid=GUID2, oid=2, lon=19.81, name="Nowy otwór")
    f["attributes"]["GENEZA"] = "jaskinia"
    f["geometry"]["y"] = 49.25
    snap = snapshot(root, "new-opening", [feature(lon=19.801), f])
    recommit(root)
    head = git(root, "rev-parse", "HEAD")
    report = tpn_changes.compare(
        root,
        snap,
        batch_id="fixture-batch",
        base_commit=head,
        protect_best=True,
        candidate_policy=__import__(
            "gps_kataster_obiektow_tatr.tpn_candidates", fromlist=["CandidatePolicy"]
        ).CandidatePolicy(),
    )
    report["accepted_state_commit"] = head
    proposals = []
    from gps_kataster_obiektow_tatr.tpn_snapshot import sha256

    for r in report["records"]:
        is_new = r["globalid"] == GUID2
        proposals.append(
            {
                "change_id": r["change_id"],
                "target": {"cave_id": "C-0001"} if is_new else r["target"],
                "preimage": {
                    "data/caves/C-0001.yml": sha256((root / "data/caves/C-0001.yml").read_bytes())
                }
                if is_new
                else r["preimage"],
                "actions": [
                    {
                        "action": "new_object",
                        "object_key": "new-opening",
                        "location_hash": normalize_feature(f)["location_hash"],
                        "initial_best": "first_measurement",
                    },
                    {"action": "link_cave", "object_key": "new-opening", "cave_id": "C-0001"},
                ]
                if is_new
                else [],
                "conflict_acknowledgements": r["conflicts"],
                "candidate_acknowledgements": [c["key"] for c in r["candidates"]],
            }
        )
    if wrong_target:
        from gps_kataster_obiektow_tatr.tpn_changes import Catalog

        p = next(p for p in proposals if p["change_id"].startswith(GUID2 + ":"))
        p["target"], p["preimage"], _ = Catalog(root).context("KSW-0001")
    changes, decisions = prepare_batch(root, report, proposals)
    for d in decisions["decisions"]:
        d.update(
            status="approve",
            reviewed_by="human",
            reviewed_at="2026-10-19T14:00:00Z",
            reason="Confirmed separate opening",
        )
    if wrong_target:
        before = hashes(root)
        with pytest.raises(ValueError, match="cannot target an existing object"):
            apply_batch(root, changes, decisions, reviewers={"human"})
        assert hashes(root) == before
        return
    plan = apply_batch(root, changes, decisions, reviewers={"human"})
    oid = plan["id_map"]["object:new-opening"]
    cave = yaml.safe_load((root / "data/caves/C-0001.yml").read_text())
    obj = yaml.safe_load((root / f"data/objects/{oid.split('-')[0]}/{oid}.yml").read_text())
    assert obj["cave_id"] == "C-0001" and cave["object_ids"] == ["KSW-0001", oid]
    check_batch(root, "fixture-batch")


def test_metadata_only_source_cannot_create_observation(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch
    from gps_kataster_obiektow_tatr.tpn_normalization import normalize_feature

    root, _ = batch_repo
    f = feature(name="Nowa nazwa")
    snap = snapshot(root, "metadata", [f])
    recommit(root)
    a = append_action()
    a["location_hash"] = normalize_feature(f)["location_hash"]
    changes, decisions = prepare((root, snap), [a])
    before = hashes(root)
    with pytest.raises(ValueError, match="metadata/date-only"):
        apply_batch(root, changes, decisions, reviewers={"human"})
    assert hashes(root) == before


def test_reject_and_defer_remain_valid_after_other_approved_changes(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch
    from gps_kataster_obiektow_tatr.tpn_normalization import exact_json

    root, _ = batch_repo
    f = feature(guid=GUID2, oid=2, name="Review later")
    snap = snapshot(root, "mixed", [feature(lon=19.801), f])
    recommit(root)
    changes, decisions = many((root, snap), {GUID: [append_action()]}, {GUID2: "defer"})
    apply_batch(root, changes, decisions, reviewers={"human"})
    state = exact_json((root / "data/source_state/tpn/state.json").read_bytes())
    result = tpn_changes.compare(
        root, snap, batch_id="cycle-two", base_commit=git(root, "rev-parse", "HEAD"), state=state
    )
    deferred = next(r for r in result["records"] if r["globalid"] == GUID2)
    assert deferred["review_status"] == "defer"
    assert not deferred["actionable"]
    assert result["deferred"][0]["status"] == "active"


@pytest.mark.parametrize("when", ["before", "after"])
def test_process_crash_has_whole_old_or_whole_new_tree(batch_repo, when):
    import sys

    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch, check_batch

    root, _ = batch_repo
    changes, decisions = prepare(batch_repo, [append_action()])
    (root / "inputs.json").write_bytes(canonical({"changes": changes, "decisions": decisions}))
    before = hashes(root)
    code = """
import sys,os,json
from pathlib import Path
from gps_kataster_obiektow_tatr import tpn_batch,tpn_transaction
root=Path(sys.argv[1]); data=json.loads((root/'inputs.json').read_bytes())
old=tpn_transaction.exchange_directories
def crash(a,b):
    if sys.argv[2]=='after': old(a,b)
    os._exit(23)
tpn_transaction.exchange_directories=crash
tpn_batch.apply_batch(root,data['changes'],data['decisions'],reviewers={'human'})
"""
    proc = subprocess.run([sys.executable, "-c", code, str(root), when], capture_output=True)
    assert proc.returncode == 23, proc.stderr.decode()
    if when == "before":
        assert hashes(root) == before
    else:
        obj = yaml.safe_load((root / "data/objects/KSW/KSW-0001.yml").read_text())
        assert len(obj["measurements"]) == 2
        check_batch(root, "fixture-batch")
    plan = apply_batch(root, changes, decisions, reviewers={"human"})
    assert plan["noop"] == (when == "after")
    check_batch(root, "fixture-batch")


def test_cli_prepare_preview_apply_and_gate(batch_repo):
    import sys

    root, snap = batch_repo
    head = git(root, "rev-parse", "HEAD")
    report = tpn_changes.compare(
        root, snap, batch_id="cli-batch", base_commit=head, protect_best=True
    )
    report["accepted_state_commit"] = head
    (root / "report.json").write_bytes(canonical(report))

    def cli(*args):
        return subprocess.run(
            [
                sys.executable,
                str(REPO / "scripts/review_tpn_batch.py"),
                "--repo-root",
                str(root),
                *args,
            ],
            capture_output=True,
            text=True,
        )

    assert cli("prepare", "--changes", str(root / "report.json")).returncode == 0
    before = hashes(root)
    assert cli("dry-run", "--batch-id", "cli-batch", "--reviewer", "human").returncode == 0
    assert hashes(root) == before
    denied = cli("check", "--batch-id", "cli-batch")
    assert denied.returncode == 1 and "pending" in denied.stderr
    path = root / "data/source_reviews/tpn/cli-batch/decisions.yml"
    decisions = yaml.safe_load(path.read_text())
    decisions["decisions"][0].update(
        status="defer",
        reviewed_by="human",
        reviewed_at="2026-10-19T14:00:00Z",
        reason="Need evidence",
    )
    path.write_text(yaml.safe_dump(decisions, allow_unicode=True))
    preview = cli("dry-run", "--batch-id", "cli-batch", "--reviewer", "human")
    applied = cli("apply", "--batch-id", "cli-batch", "--reviewer", "human")
    assert applied.returncode == 0, applied.stderr
    assert json.loads(preview.stdout) == json.loads(applied.stdout)
    assert cli("check", "--batch-id", "cli-batch").returncode == 0
    assert cli("prepare", "--changes", str(root / "report.json")).returncode == 1
    after = hashes(root)
    path.write_text(path.read_text() + "\nformat: tpn-decisions\n")
    assert cli("apply", "--batch-id", "cli-batch", "--reviewer", "human").returncode == 1
    assert {k: v for k, v in hashes(root).items() if k != str(path.relative_to(root))} == {
        k: v for k, v in after.items() if k != str(path.relative_to(root))
    }


def test_new_object_requires_pbi098_qualification_report(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch
    from gps_kataster_obiektow_tatr.tpn_normalization import normalize_feature

    root, _ = batch_repo
    f = feature(guid=GUID2, oid=2, lon=19.86, name="Wyjątkowy nowy otwór")
    f["geometry"]["y"] = 49.24
    f["attributes"]["GENEZA"] = "jaskinia"
    snap = snapshot(root, "no-candidates", [f])
    recommit(root)
    a = [
        {"action": "create_cave", "cave_key": "new"},
        {
            "action": "new_object",
            "object_key": "new",
            "cave_key": "new",
            "location_hash": normalize_feature(f)["location_hash"],
            "initial_best": "first_measurement",
        },
    ]
    changes, decisions = many((root, snap), {GUID2: a})
    before = hashes(root)
    with pytest.raises(ValueError, match="PBI-098|qualification"):
        apply_batch(root, changes, decisions, reviewers={"human"})
    assert hashes(root) == before


@pytest.mark.parametrize("final_status", ["reject", "defer", "approve"])
def test_pending_automatic_new_proposal_replans_from_base(batch_repo, final_status):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch, check_batch, prepare_batch
    from gps_kataster_obiektow_tatr.tpn_candidates import CandidatePolicy

    root, _ = batch_repo
    f = feature(guid=GUID2, oid=2, lon=19.86, name="Unikatowy samodzielny otwór")
    f["geometry"]["y"] = 49.24
    f["attributes"].update(GENEZA="jaskinia", WER_LOK=None, UWAGI=None, OPIS=None, TATER=None)
    (root / "data/sources/pig").mkdir()
    (root / "data/sources/pig/pig_otwory_jaskin_.xlsx.-.Export.csv").write_text(
        "ID,Nazwa,Inne nazwy,Nr inw.\n"
    )
    snap = snapshot(root, "automatic", [feature(lon=19.801), f])
    recommit(root)
    head = git(root, "rev-parse", "HEAD")
    report = tpn_changes.compare(
        root,
        snap,
        batch_id="fixture-batch",
        base_commit=head,
        protect_best=True,
        candidate_policy=CandidatePolicy(),
    )
    report["accepted_state_commit"] = head
    proposals = []
    for r in report["records"]:
        is_new = r["globalid"] == GUID2
        if is_new:
            assert r["new_record_qualification"]["status"] == "automatic_proposal"
        proposals.append(
            {
                "change_id": r["change_id"],
                "target": r["target"],
                "preimage": r["preimage"],
                "actions": [
                    {"action": "create_cave", "cave_key": "new"},
                    {
                        "action": "new_object",
                        "object_key": "new",
                        "cave_key": "new",
                        "location_hash": r["location_hash"],
                        "initial_best": "first_measurement",
                    },
                ]
                if is_new
                else [],
                "conflict_acknowledgements": r["conflicts"],
                "candidate_acknowledgements": [c["key"] for c in r["candidates"]],
            }
        )
    changes, decisions = prepare_batch(root, report, proposals)
    for d in decisions["decisions"]:
        if d["globalid"] != GUID2:
            d.update(
                status="approve",
                reviewed_by="human",
                reviewed_at="2026-10-19T14:00:00Z",
                reason="Keep old",
            )
    plan = apply_batch(root, changes, decisions, reviewers={"human"})
    oid = plan["id_map"]["object:new"]
    cid = plan["id_map"]["cave:new"]
    assert (root / f"data/objects/{oid.split('-')[0]}/{oid}.yml").exists()
    with pytest.raises(ValueError, match="pending"):
        check_batch(root, "fixture-batch")
    for d in decisions["decisions"]:
        if d["globalid"] == GUID2:
            d.update(
                status=final_status,
                reviewed_by="human",
                reviewed_at="2026-10-19T15:00:00Z",
                reason="Human disposition",
            )
            if final_status != "approve":
                d["actions"] = []
    apply_batch(root, changes, decisions, reviewers={"human"})
    assert (root / f"data/objects/{oid.split('-')[0]}/{oid}.yml").exists() == (
        final_status == "approve"
    )
    assert (root / f"data/caves/{cid}.yml").exists() == (final_status == "approve")
    check_batch(root, "fixture-batch")
    after = hashes(root)
    assert apply_batch(root, changes, decisions, reviewers={"human"})["noop"]
    assert hashes(root) == after


def test_gate_requires_archived_decisions_and_survives_human_merge(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch, check_batch

    root, _ = batch_repo
    changes, decisions = prepare(batch_repo, [append_action()])
    apply_batch(root, changes, decisions, reviewers={"human"})
    archive = next((root / "data/source_reviews/tpn/fixture-batch/applications").glob("*.json"))
    raw = archive.read_bytes()
    archive.unlink()
    with pytest.raises((ValueError, OSError)):
        check_batch(root, "fixture-batch")
    archive.write_bytes(raw)
    recommit(root)  # Simulate this exact candidate being accepted on main by a human.
    check_batch(root, "fixture-batch")
    assert apply_batch(root, changes, decisions, reviewers={"human"})["noop"]


@pytest.mark.parametrize("bad", ["name_local", "lat", "verification_status"])
def test_measurement_fields_cannot_be_rewritten_via_metadata(batch_repo, bad):
    from gps_kataster_obiektow_tatr.tpn_batch import prepare_batch

    root, snap = batch_repo
    head = git(root, "rev-parse", "HEAD")
    report = tpn_changes.compare(
        root, snap, batch_id="fixture-batch", base_commit=head, protect_best=True
    )
    report["accepted_state_commit"] = head
    r = report["records"][0]
    p = {
        "change_id": r["change_id"],
        "target": r["target"],
        "preimage": r["preimage"],
        "actions": [
            {
                "action": "update_metadata",
                "target": {"kind": "measurement", "id": "KSW-0001", "measurement_id": "m-001"},
                "field": bad,
                "before": None,
                "after": "changed",
            }
        ],
        "conflict_acknowledgements": r["conflicts"],
        "candidate_acknowledgements": [],
    }
    before = hashes(root)
    with pytest.raises(ValueError):
        prepare_batch(root, report, [p])
    assert hashes(root) == before


def test_missing_modification_date_defers_new_measurement(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch
    from gps_kataster_obiektow_tatr.tpn_normalization import normalize_feature

    root, _ = batch_repo
    f = feature(lon=19.801)
    f["attributes"]["LAST_EDITED_DATE"] = None
    snap = snapshot(root, "without-date", [f])
    recommit(root)
    a = append_action()
    a["location_hash"] = normalize_feature(f)["location_hash"]
    changes, decisions = prepare((root, snap), [a])
    before = hashes(root)
    with pytest.raises(ValueError, match="modification date"):
        apply_batch(root, changes, decisions, reviewers={"human"})
    assert hashes(root) == before


def test_unprotected_select_new_is_explicit_and_preview_matches_exports(batch_repo, tmp_path):
    from gps_kataster_obiektow_tatr.best_measurements_export import export_best_measurements
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch, plan_batch

    root, _ = batch_repo
    changes, decisions = prepare(batch_repo, [append_action(kind="select_new")])
    preview = plan_batch(root, changes, decisions, reviewers={"human"})
    actual = apply_batch(root, changes, decisions, reviewers={"human"})
    assert actual == preview
    expected = preview["export_changes"][0]["after"]["best"]
    assert expected["measurement_id"] == "m-002"
    result = export_best_measurements(
        data_dir=root / "data", output_dir=root / "exports", generated_at="2026-10-19T00:00:00Z"
    )
    import csv

    with result.csv_path.open() as stream:
        row = next(csv.DictReader(stream))
    assert row["measurement_id"] == expected["measurement_id"]
    assert float(row["lat"]) == expected["lat"] and float(row["lon"]) == expected["lon"]


def test_unsupported_action_and_yaml_duplicate_are_rejected_before_mutation(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch

    root, _ = batch_repo
    changes, decisions = prepare(batch_repo)
    decisions["decisions"][0]["actions"] = [{"action": "execute", "command": "$(touch /tmp/never)"}]
    before = hashes(root)
    with pytest.raises(ValueError, match="unsupported action"):
        apply_batch(root, changes, decisions, reviewers={"human"})
    assert hashes(root) == before


def test_original_source_bytes_preserved_and_source_drift_blocks_replay(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch

    root, snap = batch_repo
    changes, decisions = prepare(batch_repo, [append_action()])
    inputs = {k: v for k, v in hashes(root).items() if k.startswith("data/sources/")}
    apply_batch(root, changes, decisions, reviewers={"human"})
    assert {k: v for k, v in hashes(root).items() if k.startswith("data/sources/")} == inputs
    p = snap / "page-0.json"
    p.chmod(0o644)  # Deliberate tampering with an isolated snapshot fixture.
    p.write_bytes(p.read_bytes() + b"\n")
    before = hashes(root)
    with pytest.raises(ValueError):
        apply_batch(root, changes, decisions, reviewers={"human"})
    assert hashes(root) == before


@pytest.mark.parametrize("duplicate_location", [False, True])
def test_attach_new_guid_and_append_are_separate_idempotent_actions(batch_repo, duplicate_location):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch, check_batch, prepare_batch
    from gps_kataster_obiektow_tatr.tpn_candidates import CandidatePolicy
    from gps_kataster_obiektow_tatr.tpn_changes import Catalog
    from gps_kataster_obiektow_tatr.tpn_normalization import normalize_feature

    root, _ = batch_repo
    f = feature(guid=GUID2, oid=2, lon=19.8000000001 if duplicate_location else 19.802)
    snap = snapshot(root, "attach", [feature(lon=19.801), f])
    recommit(root)
    head = git(root, "rev-parse", "HEAD")
    report = tpn_changes.compare(
        root,
        snap,
        batch_id="fixture-batch",
        base_commit=head,
        protect_best=True,
        candidate_policy=CandidatePolicy(),
    )
    report["accepted_state_commit"] = head
    proposals = []
    for r in report["records"]:
        target, preimage, _ = Catalog(root).context("KSW-0001")
        actions = []
        if r["globalid"] == GUID2:
            a = append_action(key="second-guid")
            a["location_hash"] = normalize_feature(f)["location_hash"]
            actions = [
                {
                    "action": "attach_source",
                    "target": {"kind": "object", "id": "KSW-0001"},
                    "reference": {
                        "system": "TPN",
                        "ref_type": "source_globalid",
                        "external_id": GUID2,
                    },
                    "evidence": "Confirmed same opening from source plan",
                },
                a,
            ]
        proposals.append(
            {
                "change_id": r["change_id"],
                "target": target,
                "preimage": preimage,
                "actions": actions,
                "conflict_acknowledgements": r["conflicts"],
                "candidate_acknowledgements": [c["key"] for c in r["candidates"]],
            }
        )
    changes, decisions = prepare_batch(root, report, proposals)
    for d in decisions["decisions"]:
        d.update(
            status="approve",
            reviewed_by="human",
            reviewed_at="2026-10-19T14:00:00Z",
            reason="Confirmed identity and preserve best",
        )
    if duplicate_location:
        before = hashes(root)
        with pytest.raises(ValueError, match="already in history"):
            apply_batch(root, changes, decisions, reviewers={"human"})
        assert hashes(root) == before
        return
    apply_batch(root, changes, decisions, reviewers={"human"})
    obj = yaml.safe_load((root / "data/objects/KSW/KSW-0001.yml").read_text())
    assert len(obj["external_refs"]) == 2 and len(obj["measurements"]) == 2
    state = json.loads((root / "data/source_state/tpn/state.json").read_bytes())
    assert state["bindings"][GUID2] == "KSW-0001"
    after = hashes(root)
    assert apply_batch(root, changes, decisions, reviewers={"human"})["noop"]
    assert hashes(root) == after
    check_batch(root, "fixture-batch")


def test_source_disappearance_never_removes_catalog_history(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch, check_batch

    root, _ = batch_repo
    snap = snapshot(root, "disappeared", [])
    recommit(root)
    changes, decisions = prepare((root, snap))
    before = {
        k: v for k, v in hashes(root).items() if k.startswith(("data/objects/", "data/caves/"))
    }
    apply_batch(root, changes, decisions, reviewers={"human"})
    assert {
        k: v for k, v in hashes(root).items() if k.startswith(("data/objects/", "data/caves/"))
    } == before
    check_batch(root, "fixture-batch")


def test_config_change_during_staging_aborts_before_exchange(batch_repo, monkeypatch):
    from gps_kataster_obiektow_tatr import tpn_batch, tpn_transaction

    root, _ = batch_repo
    changes, decisions = prepare(batch_repo, [append_action()])
    original = tpn_transaction.shutil.copytree

    def change_config(*args, **kwargs):
        result = original(*args, **kwargs)
        with (root / "config/prefixes.yml").open("a") as f:
            f.write("\n# concurrent edit\n")
        return result

    monkeypatch.setattr(tpn_transaction.shutil, "copytree", change_config)
    before = hashes(root)
    with pytest.raises(ValueError, match="configuration/main changed"):
        tpn_batch.apply_batch(root, changes, decisions, reviewers={"human"})
    assert hashes(root) == before


def test_config_change_after_last_plan_is_not_adopted_as_baseline(batch_repo, monkeypatch):
    from gps_kataster_obiektow_tatr import tpn_batch

    root, _ = batch_repo
    changes, decisions = prepare(batch_repo, [append_action()])
    old = tpn_batch._plan
    calls = 0

    def change_after_plan(*args, **kwargs):
        nonlocal calls
        result = old(*args, **kwargs)
        calls += 1
        if calls == 2:
            with (root / "config/prefixes.yml").open("a") as stream:
                stream.write("\n# concurrent after plan\n")
        return result

    monkeypatch.setattr(tpn_batch, "_plan", change_after_plan)
    before = hashes(root)
    with pytest.raises(ValueError, match="configuration/main changed"):
        tpn_batch.apply_batch(root, changes, decisions, reviewers={"human"})
    assert hashes(root) == before


def test_rereview_keeps_csv_provenance_of_existing_location(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch, prepare_batch
    from gps_kataster_obiektow_tatr.tpn_normalization import exact_json

    root, _ = batch_repo
    f = feature(lon=19.8000000000002)
    snap = snapshot(root, "bootstrap-epsilon", [f])
    recommit(root)
    changes, decisions = prepare((root, snap))
    apply_batch(root, changes, decisions, reviewers={"human"})
    recommit(root)
    # Local metadata changes require another review of the same source revision.
    p = root / "data/objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(p.read_text())
    obj["name_local"] = "Confirmed local name"
    p.write_text(yaml.safe_dump(obj, allow_unicode=True))
    recommit(root)
    state = exact_json((root / "data/source_state/tpn/state.json").read_bytes())
    head = git(root, "rev-parse", "HEAD")
    report = tpn_changes.compare(
        root, snap, batch_id="second-cycle", base_commit=head, state=state, protect_best=True
    )
    report["accepted_state_commit"] = head
    changes, decisions = prepare_batch(root, report)
    # Explicitly acknowledge local metadata; no source action is authorized.
    for proposal in changes["execution"]["proposals"]:
        row = next(r for r in report["records"] if r["change_id"] == proposal["change_id"])
        proposal["conflict_acknowledgements"] = row["conflicts"]
    from gps_kataster_obiektow_tatr.tpn_snapshot import sha256

    decisions["changes_hash"] = sha256(canonical(changes) + b"\n")
    for d in decisions["decisions"]:
        d.update(
            status="approve",
            reviewed_by="human",
            reviewed_at="2026-10-19T16:00:00Z",
            reason="Keep local metadata and original source evidence",
        )
    apply_batch(root, changes, decisions, reviewers={"human"})
    state = exact_json((root / "data/source_state/tpn/state.json").read_bytes())
    resolution = next(r for r in state["resolutions"] if r["globalid"] == GUID)
    assert resolution["applied_locations"][0]["csv_evidence"] is not None
    result = tpn_changes.compare(root, snap, batch_id="third-cycle", base_commit=head, state=state)
    assert result["records"][0]["history"]["current_matches"]


def test_best_guard_sees_metadata_planned_in_same_batch(batch_repo):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch
    from gps_kataster_obiektow_tatr.tpn_normalization import normalize_feature

    root, _ = batch_repo
    rev = normalize_feature(feature(lon=19.801))["revision_hash"]
    note = {
        "action": "update_metadata",
        "target": {"kind": "measurement", "id": "KSW-0001", "measurement_id": "m-001"},
        "field": "notes",
        "before": "Ręczna uwaga",
        "append_text": "Nowy dowód: pomiar geodezyjny",
        "after": "Ręczna uwaga\n[TPN " + rev + "] Nowy dowód: pomiar geodezyjny",
        "revision_hash": rev,
    }
    changes, decisions = prepare(batch_repo, [note, append_action(kind="select_new")])
    before = hashes(root)
    with pytest.raises(ValueError, match="PROTECTED"):
        apply_batch(root, changes, decisions, reviewers={"human"})
    assert hashes(root) == before
