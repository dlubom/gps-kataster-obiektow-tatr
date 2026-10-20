"""The narrowly authorized D26 supplement is derived, never trusted by its hashes."""

import importlib
import importlib.util
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from gps_kataster_obiektow_tatr.tpn_batch import (
    base_checkout,
    check_batch,
    current_nonbatch,
    load_batch,
    plan_batch,
)
from gps_kataster_obiektow_tatr.tpn_changes import Catalog
from gps_kataster_obiektow_tatr.tpn_normalization import canonical
from gps_kataster_obiektow_tatr.tpn_snapshot import sha256

REPO = Path(__file__).resolve().parents[1]
BASE = "d1f958bc9a2bdcfa8a0dd620cfeaace589ca5d60"
BATCH = "pbi-101-20261019"
RECEIPT = "docs/asdlc/verification/PBI-101-D26-resolution.json"


def module():
    name = "gps_kataster_obiektow_tatr.tpn_d26_resolution"
    assert importlib.util.find_spec(name) is not None, "D26 supplement verifier is not implemented"
    return importlib.import_module(name)


@pytest.fixture(scope="module")
def immutable_base():
    with base_checkout(REPO, BASE) as base:
        yield base


def receipt_for(base):
    changes = json.loads((base / f"data/source_reviews/tpn/{BATCH}/changes.json").read_bytes())
    app = json.loads((base / f"data/source_reviews/tpn/{BATCH}/application.json").read_bytes())
    return {
        "format": "tpn-d26-resolution",
        "format_version": 1,
        "batch_id": BATCH,
        "base_commit": BASE,
        "snapshot_hash": changes["snapshot_hash"],
        "original_plan_hash": app["plan_hash"],
        "applied_at": "2026-10-20T15:00:00Z",
        "applied_by": "agent:codex",
        "authorization_quote": "Zastosuj decyzje dla D001–D026 i zachowaj całą historię.",
        "notes": {
            f"D{i:03d}": "Decyzja użytkownika; dokumentacja źródłowa zachowana."
            for i in range(1, 27)
        },
        "result_hashes": {},
    }


def test_build_derives_fixed_grouping_and_preserves_all_existing_history(immutable_base):
    supplement = module()
    before = Catalog(immutable_base)
    files, mapping = supplement.build_d26_files(immutable_base, receipt_for(immutable_base))
    assert set(mapping) == {f"D{i:03d}" for i in range(1, 27)}
    assert mapping["D003"] == mapping["D014"]
    assert mapping["D008"] == mapping["D010"]
    assert mapping["D009"] != mapping["D021"]
    assert mapping["D022"] == "MLW-0050"
    objects = {
        yaml.safe_load(raw)["id"]: yaml.safe_load(raw)
        for p, raw in files.items()
        if p.startswith("data/objects/")
    }
    caves = {
        yaml.safe_load(raw)["id"]: yaml.safe_load(raw)
        for p, raw in files.items()
        if p.startswith("data/caves/")
    }
    assert len(objects.keys() - before.objects.keys()) == 23
    assert len(caves.keys() - before.caves.keys()) == 21
    assert objects[mapping["D002"]]["cave_id"] == objects[mapping["D010"]]["cave_id"]
    assert objects[mapping["D006"]]["cave_id"] == "C-0219"
    assert len(objects[mapping["D014"]]["measurements"]) == 2
    assert (
        objects[mapping["D014"]]["measurements"][0]["lat"]
        != objects[mapping["D014"]]["measurements"][1]["lat"]
    )
    old_s = before.objects["MLW-0050"]
    assert objects["MLW-0050"]["measurements"][:-1] == old_s["measurements"]
    assert (
        objects["MLW-0050"]["best_measurement"]["measurement_id"]
        == old_s["best_measurement"]["measurement_id"]
    )
    assert objects["MLW-0050"]["best_measurement"]["mode"] == "manual"
    assert set(
        p
        for p in files
        if p.startswith("data/objects/") and yaml.safe_load(files[p])["id"] in before.objects
    ) == {before.paths["MLW-0050"]}
    state = json.loads(files["data/source_state/tpn/state.json"])
    old_state = json.loads((immutable_base / "data/source_state/tpn/state.json").read_bytes())
    assert len(state["resolutions"]) == len(old_state["resolutions"])
    assert state["deferred"] == []
    selected = {entry["globalid"] for entry in old_state["deferred"]}
    context_fields = {"result_hashes", "result_catalog_hash"}
    assert [
        {k: v for k, v in r.items() if k not in context_fields}
        for r in state["resolutions"]
        if r["globalid"] not in selected
    ] == [
        {k: v for k, v in r.items() if k not in context_fields}
        for r in old_state["resolutions"]
        if r["globalid"] not in selected
    ]


@pytest.fixture(scope="module")
def derived_supplement(immutable_base):
    receipt = receipt_for(immutable_base)
    files, mapping = module().build_d26_files(immutable_base, receipt)
    receipt["result_hashes"] = {p: sha256(raw) for p, raw in files.items()}
    return receipt, files, mapping


@pytest.fixture
def resolved_root(immutable_base, derived_supplement, tmp_path):
    root = tmp_path / "catalog"
    shutil.copytree(immutable_base, root)
    # Git is read only: the fixture reads the immutable real commit without modifying refs.
    (root / ".git").write_text(f"gitdir: {REPO / '.git'}\n")
    receipt, files, mapping = deepcopy(derived_supplement)
    for relative, raw in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    (root / RECEIPT).write_bytes(canonical(receipt) + b"\n")
    return root, receipt, mapping, current_nonbatch(immutable_base, BATCH)


def verify(fixture):
    root, receipt, _, expected = fixture
    return module().verified_d26_resolution_tree(
        root, batch_id=BATCH, plan_hash=receipt["original_plan_hash"], expected_tree=expected
    )


def test_exact_supplement_passes_and_leaves_original_evidence_unchanged(resolved_root):
    root, _, _, _ = resolved_root
    before = {
        p.as_posix(): p.read_bytes()
        for p in (root / f"data/source_reviews/tpn/{BATCH}").rglob("*")
        if p.is_file()
    }
    assert verify(resolved_root) == current_nonbatch(root, BATCH)
    assert before == {
        p.as_posix(): p.read_bytes()
        for p in (root / f"data/source_reviews/tpn/{BATCH}").rglob("*")
        if p.is_file()
    }


def test_check_integration_accepts_supplement_but_original_replay_does_not(resolved_root):
    root, _, _, _ = resolved_root
    assert check_batch(root, BATCH)["noop"]
    changes, decisions = load_batch(root, BATCH)
    reviewers = {d["reviewed_by"] for d in decisions["decisions"] if d["reviewed_by"]}
    with pytest.raises(ValueError, match="previous result/output changed"):
        plan_batch(root, changes, decisions, reviewers=reviewers)


def test_missing_receipt_and_other_batches_cannot_use_supplement(resolved_root):
    root, receipt, _, expected = resolved_root
    assert (
        module().verified_d26_resolution_tree(
            root,
            batch_id="another-batch",
            plan_hash=receipt["original_plan_hash"],
            expected_tree=expected,
        )
        == expected
    )
    (root / RECEIPT).unlink()
    assert verify(resolved_root) == expected
    with pytest.raises(ValueError, match="actual diff/output"):
        check_batch(root, BATCH)


def test_changed_preimage_and_original_review_table_are_rejected(resolved_root):
    root, receipt, _, expected = resolved_root
    changed = dict(expected)
    changed["objects/MLW/MLW-0050.yml"] = "0" * 64
    with pytest.raises(ValueError, match="base preimage"):
        module().verified_d26_resolution_tree(
            root, batch_id=BATCH, plan_hash=receipt["original_plan_hash"], expected_tree=changed
        )
    table = root / "docs/asdlc/verification/PBI-101-review/remaining-26.json"
    data = json.loads(table.read_bytes())
    data["entries"][0]["globalid"] = "0" * 36
    table.write_bytes(canonical(data) + b"\n")
    with pytest.raises(ValueError, match="immutable original"):
        verify(resolved_root)


@pytest.mark.parametrize("tamper", ["measurement", "prior_history", "best", "state", "unrelated"])
def test_recomputed_receipt_hashes_do_not_authorize_foreign_changes(resolved_root, tamper):
    root, receipt, mapping, _ = resolved_root
    if tamper == "state":
        relative = "data/source_state/tpn/state.json"
        value = json.loads((root / relative).read_bytes())
        value["bindings"][next(iter(value["bindings"]))] = "MLW-0050"
        raw = canonical(value) + b"\n"
    else:
        oid = "MLW-0050" if tamper in ("prior_history", "best") else mapping["D001"]
        if tamper == "unrelated":
            oid = "MTW-0062"
        relative = f"data/objects/{oid[:3]}/{oid}.yml"
        value = yaml.safe_load((root / relative).read_bytes())
        if tamper == "best":
            value["best_measurement"]["measurement_id"] = "m-002"
        elif tamper == "unrelated":
            value["notes"] = "foreign edit"
        else:
            value["measurements"][0]["lat"] += 0.001
        raw = yaml.safe_dump(value, allow_unicode=True, sort_keys=True).encode()
    (root / relative).write_bytes(raw)
    receipt["result_hashes"][relative] = sha256(raw)
    (root / RECEIPT).write_bytes(canonical(receipt) + b"\n")
    with pytest.raises(ValueError):
        verify(resolved_root)


@pytest.mark.parametrize(
    "field,value",
    [
        ("base_commit", "0" * 40),
        ("snapshot_hash", "0" * 64),
        ("original_plan_hash", "0" * 64),
        ("applied_by", "user"),
        ("format_version", True),
        ("authorization_quote", " "),
        ("mapping", {"D003": "MTW-0062"}),
    ],
)
def test_receipt_cannot_change_basis_or_mapping(resolved_root, field, value):
    root, receipt, _, _ = resolved_root
    receipt[field] = value
    (root / RECEIPT).write_bytes(canonical(receipt) + b"\n")
    with pytest.raises(ValueError):
        verify(resolved_root)


def test_unknown_notes_keys_and_missing_generated_hash_are_rejected(resolved_root):
    root, receipt, _, _ = resolved_root
    original = deepcopy(receipt)
    receipt["notes"]["D027"] = "unrelated"
    (root / RECEIPT).write_bytes(canonical(receipt) + b"\n")
    with pytest.raises(ValueError):
        verify(resolved_root)
    original["result_hashes"].pop(next(iter(original["result_hashes"])))
    (root / RECEIPT).write_bytes(canonical(original) + b"\n")
    with pytest.raises(ValueError):
        verify(resolved_root)
