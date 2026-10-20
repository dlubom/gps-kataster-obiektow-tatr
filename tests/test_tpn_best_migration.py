"""Approved manual pins are verifiable without rewriting a TPN batch result."""

import json
from copy import deepcopy

import pytest
import yaml
from test_tpn_batch import batch_repo as batch_repo
from test_tpn_batch import git, prepare

from gps_kataster_obiektow_tatr.tpn_batch import apply_batch, check_batch, plan_batch
from gps_kataster_obiektow_tatr.tpn_best_guard import audit_catalog
from gps_kataster_obiektow_tatr.tpn_changes import Catalog
from gps_kataster_obiektow_tatr.tpn_normalization import canonical
from gps_kataster_obiektow_tatr.tpn_snapshot import sha256
from gps_kataster_obiektow_tatr.tpn_transaction import tree_hashes

MANIFEST = "docs/asdlc/verification/PBI-099-protection-manifest.json"
RECEIPT = "docs/asdlc/verification/PBI-099-manual-selection.json"
APPLIED_AT = "2026-10-20T07:11:59Z"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value) + b"\n")


def write_yaml(path, value):
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False))


@pytest.fixture
def migrated_batch(batch_repo):
    root, snap = batch_repo
    first = root / "data/objects/KSW/KSW-0001.yml"
    original = yaml.safe_load(first.read_text())
    original["measurements"][0]["method"] = "gnss"
    write_yaml(first, original)
    for number in (2, 3):
        obj = deepcopy(original)
        obj["id"] = f"KSW-{number:04}"
        obj["external_refs"] = []
        obj["measurements"][0]["source_ref"] = None
        write_yaml(first.with_name(obj["id"] + ".yml"), obj)
    cave = root / "data/caves/C-0001.yml"
    data = yaml.safe_load(cave.read_text())
    data["object_ids"] = ["KSW-0001", "KSW-0002", "KSW-0003"]
    write_yaml(cave, data)
    manifest = audit_catalog(Catalog(root))
    assert len(manifest["migration_proposals"]) == 3
    write_json(root / MANIFEST, manifest)
    git(root, "add", ".")
    git(root, "commit", "-qm", "protected auto best proposals")
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    changes, decisions = prepare((root, snap))
    apply_batch(root, changes, decisions, reviewers={"human"})
    app_path = root / "data/source_reviews/tpn/fixture-batch/application.json"
    application_bytes = app_path.read_bytes()
    application = json.loads(application_bytes)
    git(root, "add", ".")
    git(root, "commit", "-qm", "original applied batch")
    basis = git(root, "rev-parse", "HEAD")
    pins = []
    for proposal in manifest["migration_proposals"]:
        path = root / proposal["path"]
        before = path.read_bytes()
        obj = yaml.safe_load(before)
        obj["best_measurement"] = {
            **proposal["after"],
            "updated_at": APPLIED_AT,
            "updated_by": "agent:codex",
        }
        obj.update(updated_at=APPLIED_AT, updated_by="agent:codex")
        write_yaml(path, obj)
        pins.append(
            {
                "object_id": proposal["object_id"],
                "path": proposal["path"],
                "before_sha256": sha256(before),
                "after_sha256": sha256(path.read_bytes()),
            }
        )
    receipt = {
        "format": "tpn-protected-best-manual-selection",
        "format_version": 1,
        "batch_id": "fixture-batch",
        "batch_plan_hash": application["plan_hash"],
        "basis_commit": basis,
        "proposal_manifest_sha256": sha256((root / MANIFEST).read_bytes()),
        "authorization": {
            "source": "explicit-user-request",
            "text": "Apply the three proposed manual pins while retaining all measurements.",
        },
        "applied_at": APPLIED_AT,
        "applied_by": "agent:codex",
        "objects": pins,
    }
    write_json(root / RECEIPT, receipt)
    return root, changes, decisions, receipt, application_bytes


def test_approved_manual_pins_pass_check_without_changing_batch_receipt(migrated_batch):
    root, _, _, _, application_bytes = migrated_batch
    protected = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for folder in ("data/source_reviews", "data/source_state", "data/sources")
        for path in (root / folder).rglob("*")
        if path.is_file()
    }
    plan = check_batch(root, "fixture-batch")
    assert plan["noop"]
    assert (root / "data/source_reviews/tpn/fixture-batch/application.json").read_bytes() == (
        application_bytes
    )
    assert protected == {path: (root / path).read_bytes() for path in protected}


@pytest.mark.parametrize("operation", [apply_batch, plan_batch])
def test_migration_receipt_never_authorizes_apply_or_replay(migrated_batch, operation):
    root, changes, decisions, _, _ = migrated_batch
    before = tree_hashes(root / "data")
    with pytest.raises(ValueError, match="previous result/output changed"):
        operation(root, changes, decisions, reviewers={"human"})
    assert tree_hashes(root / "data") == before


def test_missing_receipt_keeps_original_exact_output_gate(migrated_batch):
    root, _, _, _, _ = migrated_batch
    (root / RECEIPT).unlink()
    with pytest.raises(ValueError, match="actual diff/output"):
        check_batch(root, "fixture-batch")


@pytest.mark.parametrize(
    "field,value",
    [
        ("authorization", None),
        ("authorization", {}),
        ("authorization", {"source": "explicit-user-request", "text": " "}),
        ("authorization", {"source": "automatic", "text": "untrusted"}),
        ("authorization", {"source": "explicit-user-request", "text": "ok", "extra": True}),
        ("applied_at", "2026-10-20"),
        ("applied_by", " "),
        ("format_version", True),
        ("batch_plan_hash", "0" * 64),
        ("proposal_manifest_sha256", "0" * 64),
        ("basis_commit", "HEAD"),
        ("unknown", True),
    ],
)
def test_invalid_authorization_and_basis_are_rejected(migrated_batch, field, value):
    root, _, _, receipt, _ = migrated_batch
    receipt[field] = value
    write_json(root / RECEIPT, receipt)
    with pytest.raises(ValueError):
        check_batch(root, "fixture-batch")


@pytest.mark.parametrize("field", ["authorization", "batch_plan_hash", "objects"])
def test_missing_receipt_fields_are_rejected(migrated_batch, field):
    root, _, _, receipt, _ = migrated_batch
    receipt.pop(field)
    write_json(root / RECEIPT, receipt)
    with pytest.raises(ValueError):
        check_batch(root, "fixture-batch")


@pytest.mark.parametrize("field", ["before_sha256", "after_sha256"])
def test_stale_object_hashes_are_rejected(migrated_batch, field):
    root, _, _, receipt, _ = migrated_batch
    receipt["objects"][0][field] = "0" * 64
    write_json(root / RECEIPT, receipt)
    with pytest.raises(ValueError):
        check_batch(root, "fixture-batch")


@pytest.mark.parametrize(
    "tamper", ["coordinates", "history", "status", "accuracy", "best_id", "reason", "notes"]
)
def test_updated_hash_cannot_hide_changes_outside_authorized_pin(migrated_batch, tamper):
    root, _, _, receipt, _ = migrated_batch
    pin = receipt["objects"][0]
    path = root / pin["path"]
    obj = yaml.safe_load(path.read_text())
    if tamper == "coordinates":
        obj["measurements"][0]["lat"] += 0.01
    elif tamper == "history":
        obj["measurements"].append({**obj["measurements"][0], "id": "m-002"})
    elif tamper == "status":
        obj["measurements"][0]["verification_status"] = "zweryfikowany"
    elif tamper == "accuracy":
        obj["measurements"][0]["horizontal_accuracy_m"] = 0.1
    elif tamper == "best_id":
        obj["best_measurement"]["measurement_id"] = "m-002"
    elif tamper == "reason":
        obj["best_measurement"]["reason"] = "Different selection rationale"
    else:
        obj["notes"] = "Unrelated catalog edit"
    write_yaml(path, obj)
    pin["after_sha256"] = sha256(path.read_bytes())
    write_json(root / RECEIPT, receipt)
    with pytest.raises(ValueError, match="authorized.*pin|manual.*delta"):
        check_batch(root, "fixture-batch")


@pytest.mark.parametrize("tamper", ["duplicate", "unknown", "missing", "path", "extra_key"])
def test_only_the_exact_proposed_object_set_is_allowed(migrated_batch, tamper):
    root, _, _, receipt, _ = migrated_batch
    if tamper == "duplicate":
        receipt["objects"].append(deepcopy(receipt["objects"][0]))
    elif tamper == "unknown":
        receipt["objects"][0]["object_id"] = "KSW-9999"
    elif tamper == "missing":
        receipt["objects"].pop()
    elif tamper == "path":
        receipt["objects"][0]["path"] = "data/objects/KSW/../KSW/KSW-0001.yml"
    else:
        receipt["objects"][0]["extra"] = True
    write_json(root / RECEIPT, receipt)
    with pytest.raises(ValueError):
        check_batch(root, "fixture-batch")


def test_changed_manifest_cannot_be_reauthorized_by_updating_its_hash(migrated_batch):
    root, _, _, receipt, _ = migrated_batch
    path = root / MANIFEST
    manifest = json.loads(path.read_bytes())
    manifest["migration_proposals"][0]["after"]["reason"] = "Forged proposal"
    write_json(path, manifest)
    receipt["proposal_manifest_sha256"] = sha256(path.read_bytes())
    write_json(root / RECEIPT, receipt)
    with pytest.raises(ValueError, match="manifest"):
        check_batch(root, "fixture-batch")


@pytest.mark.parametrize("which", [RECEIPT, MANIFEST, "data/objects/KSW/KSW-0001.yml"])
def test_symlinks_are_rejected_even_with_identical_bytes(migrated_batch, which):
    root, _, _, _, _ = migrated_batch
    path = root / which
    copied = root / "identical-copy"
    copied.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(copied)
    with pytest.raises(ValueError, match="symlink|unsafe"):
        check_batch(root, "fixture-batch")


@pytest.mark.parametrize("relative", ["data/caves/C-0001.yml", "data/source_state/tpn/state.json"])
def test_unrelated_catalog_and_source_state_changes_still_fail(migrated_batch, relative):
    root, _, _, _, _ = migrated_batch
    path = root / relative
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="actual diff/output"):
        check_batch(root, "fixture-batch")


def test_duplicate_yaml_keys_are_rejected(migrated_batch):
    root, _, _, receipt, _ = migrated_batch
    path = root / receipt["objects"][0]["path"]
    path.write_bytes(path.read_bytes() + b"\nupdated_by: agent:codex\n")
    receipt["objects"][0]["after_sha256"] = sha256(path.read_bytes())
    write_json(root / RECEIPT, receipt)
    with pytest.raises(ValueError, match="duplicate|manual.*YAML"):
        check_batch(root, "fixture-batch")


def test_duplicate_json_receipt_keys_are_rejected(migrated_batch):
    root, _, _, _, _ = migrated_batch
    path = root / RECEIPT
    raw = path.read_bytes()
    path.write_bytes(b'{"applied_by":"agent:codex",' + raw[1:])
    with pytest.raises(ValueError, match="duplicate JSON key"):
        check_batch(root, "fixture-batch")


def test_unrelated_basis_commit_is_rejected_even_with_identical_tree(migrated_batch):
    root, _, _, receipt, _ = migrated_batch
    tree = git(root, "rev-parse", "HEAD^{tree}")
    receipt["basis_commit"] = git(root, "commit-tree", tree, "-m", "unrelated identical basis")
    write_json(root / RECEIPT, receipt)
    with pytest.raises(ValueError, match="git read failed"):
        check_batch(root, "fixture-batch")


def test_receipt_for_another_batch_does_not_normalize_current_output(migrated_batch):
    root, _, _, receipt, _ = migrated_batch
    receipt["batch_id"] = "another-batch"
    write_json(root / RECEIPT, receipt)
    with pytest.raises(ValueError, match="actual diff/output"):
        check_batch(root, "fixture-batch")
