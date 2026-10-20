"""Note corrections cannot authorize changes to survey history or identity."""

import importlib
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
from gps_kataster_obiektow_tatr.tpn_d26_resolution import verified_d26_resolution_tree
from gps_kataster_obiektow_tatr.tpn_normalization import canonical
from gps_kataster_obiektow_tatr.tpn_snapshot import sha256

REPO = Path(__file__).resolve().parents[1]
BASE = "8c18ee573e5224b8f02044d4f4b823459b6cbcd7"
BATCH = "pbi-101-20261019"
STATE = "data/source_state/tpn/state.json"


def module():
    return importlib.import_module("gps_kataster_obiektow_tatr.tpn_catalog_notes")


@pytest.fixture(scope="module")
def original():
    with base_checkout(REPO, BASE) as base:
        yield base


@pytest.fixture(scope="module")
def preceding_tree():
    with base_checkout(REPO, "d1f958bc9a2bdcfa8a0dd620cfeaace589ca5d60") as base:
        return current_nonbatch(base, BATCH)


def verify_correction(root, preceding_tree):
    receipt = json.loads(
        (root / "docs/asdlc/verification/PBI-101-D26-resolution.json").read_bytes()
    )
    return verified_d26_resolution_tree(
        root,
        batch_id=BATCH,
        plan_hash=receipt["original_plan_hash"],
        expected_tree=preceding_tree,
    )


def receipt_for(base):
    return {
        "format": "tpn-catalog-notes",
        "format_version": 1,
        "base_commit": BASE,
        "applied_at": "2026-10-20T19:45:00Z",
        "applied_by": "agent:codex",
        "authorization_quote": "Popraw opisy w PR #12; zachowaj historię pomiarów.",
        "notes": {
            p: {
                "before_sha256": sha256((base / p).read_bytes()),
                "after": "Bibliografia jaskini." if "/caves/" in p else None,
            }
            for p in module().PATHS
        },
        "result_hashes": {},
    }


@pytest.fixture(scope="module")
def correction(original):
    receipt = receipt_for(original)
    files = module().build_notes_files(original, receipt)
    receipt["result_hashes"] = {p: sha256(raw) for p, raw in files.items()}
    return receipt, files


@pytest.fixture
def corrected(original, correction, tmp_path):
    root = tmp_path / "catalog"
    shutil.copytree(original, root)
    (root / ".git").write_text(f"gitdir: {REPO / '.git'}\n")
    receipt, files = deepcopy(correction)
    for relative, raw in files.items():
        (root / relative).write_bytes(raw)
    (root / module().RECEIPT).write_bytes(canonical(receipt) + b"\n")
    return root, receipt


def test_only_notes_and_audit_change_all_other_values_are_preserved(original, correction):
    _, files = correction
    assert set(files) == module().PATHS | {STATE}
    for p in module().PATHS:
        before = yaml.safe_load((original / p).read_bytes())
        after = yaml.safe_load(files[p])
        # Replace the old duplicated description; a null entrance note clears it.
        assert after["notes"] == ("Bibliografia jaskini." if "/caves/" in p else None)
        for field in ("notes", "updated_at", "updated_by"):
            before.pop(field)
            after.pop(field)
        assert before == after, p
    before = json.loads((original / STATE).read_bytes())
    after = json.loads(files[STATE])
    for state in (before, after):
        for resolution in state["resolutions"]:
            resolution.pop("result_hashes")
            resolution.pop("result_catalog_hash")
    assert before == after


def test_check_accepts_correction_but_original_batch_replay_is_rejected(corrected):
    root, _ = corrected
    assert check_batch(root, BATCH)["noop"]
    changes, decisions = load_batch(root, BATCH)
    reviewers = {d["reviewed_by"] for d in decisions["decisions"] if d["reviewed_by"]}
    with pytest.raises(ValueError, match="previous result/output changed"):
        plan_batch(root, changes, decisions, reviewers=reviewers)


@pytest.mark.parametrize("change", ["measurement", "best", "reference", "binding", "unrelated"])
def test_recomputed_receipt_does_not_accept_foreign_changes(corrected, preceding_tree, change):
    root, receipt = corrected
    p = "data/objects/MLW/MLW-0050.yml"
    if change == "binding":
        p = STATE
        value = json.loads((root / p).read_bytes())
        value["bindings"][next(iter(value["bindings"]))] = "MTZ-0067"
        raw = canonical(value) + b"\n"
    else:
        if change == "unrelated":
            p = "data/objects/MTW/MTW-0062.yml"
        value = yaml.safe_load((root / p).read_bytes())
        if change == "measurement":
            value["measurements"][0]["lat"] += 0.001
        elif change == "best":
            value["best_measurement"]["measurement_id"] = "m-002"
        elif change == "reference":
            value["external_refs"] = []
        else:
            value["notes"] = "foreign edit"
        raw = yaml.safe_dump(value).encode()
    (root / p).write_bytes(raw)
    receipt["result_hashes"][p] = sha256(raw)
    (root / module().RECEIPT).write_bytes(canonical(receipt) + b"\n")
    with pytest.raises(ValueError):
        verify_correction(root, preceding_tree)


@pytest.mark.parametrize("change", ["path", "preimage", "field", "base", "operator", "marker"])
def test_receipt_cannot_expand_scope_or_skip_preimage(original, change):
    receipt = receipt_for(original)
    p = next(iter(receipt["notes"]))
    if change == "path":
        receipt["notes"]["data/objects/MTW/MTW-0062.yml"] = receipt["notes"].pop(p)
    elif change == "preimage":
        receipt["notes"][p]["before_sha256"] = "0" * 64
    elif change == "field":
        receipt["notes"][p]["measurements"] = []
    elif change == "base":
        receipt["base_commit"] = "0" * 40
    elif change == "operator":
        receipt["applied_by"] = "user"
    else:
        receipt["notes"][p]["after"] = "[D004; TPN guid] opis"
    with pytest.raises(ValueError):
        module().build_notes_files(original, receipt)


def test_missing_receipt_and_modified_prior_receipt_are_rejected(corrected, preceding_tree):
    root, receipt = corrected
    path = root / module().RECEIPT
    path.unlink()
    with pytest.raises(ValueError):
        verify_correction(root, preceding_tree)
    path.write_bytes(canonical(receipt) + b"\n")
    prior = root / "docs/asdlc/verification/PBI-101-D26-resolution.json"
    value = json.loads(prior.read_bytes())
    value["notes"]["D004"] = "Rewritten historical decision"
    prior.write_bytes(canonical(value) + b"\n")
    with pytest.raises(ValueError):
        verify_correction(root, preceding_tree)
