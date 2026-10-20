"""Verify separately authorized manual pins without changing TPN application evidence.

Only the read-only batch check uses this adjustment. A migration receipt never
authorizes the batch planner/applier to overwrite a later catalog edit.
"""

from __future__ import annotations

import re
import tempfile
from copy import deepcopy
from pathlib import Path

import yaml

from .tpn_api import require
from .tpn_best_guard import assess_protection
from .tpn_normalization import canonical, exact_json
from .tpn_snapshot import sha256, validate_time
from .tpn_source_state import git, hash_value
from .yaml_io import load_unique_yaml

MANIFEST = "docs/asdlc/verification/PBI-099-protection-manifest.json"
RECEIPT = "docs/asdlc/verification/PBI-099-manual-selection.json"
RECEIPT_FIELDS = {
    "format",
    "format_version",
    "batch_id",
    "batch_plan_hash",
    "basis_commit",
    "proposal_manifest_sha256",
    "authorization",
    "applied_at",
    "applied_by",
    "objects",
}
PIN_FIELDS = {"object_id", "path", "before_sha256", "after_sha256"}
PROPOSAL_FIELDS = {
    "object_id",
    "path",
    "preimage_sha256",
    "before",
    "after",
    "evidence",
    "approval_status",
}


def _regular_file(root, relative):
    path = root / relative
    require(path.resolve() == path and path.is_file(), "unsafe/symlink manual selection file")
    return path


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def verified_manual_selection_tree(root, *, batch_id, plan_hash, expected_tree):
    """Return expected hashes including only exact approved auto-to-manual pins.

    The original expected tree and its receipt are retained. The caller must
    still compare the complete actual data tree with this verified adjustment.
    """
    root = Path(root).resolve()
    receipt_path = root / RECEIPT
    if not receipt_path.exists() and not receipt_path.is_symlink():
        return expected_tree
    receipt = exact_json(_regular_file(root, RECEIPT).read_bytes())
    require(set(receipt) == RECEIPT_FIELDS, "invalid manual selection receipt fields")
    require(
        receipt["format"] == "tpn-protected-best-manual-selection"
        and type(receipt["format_version"]) is int
        and receipt["format_version"] == 1,
        "invalid manual selection receipt format/version",
    )
    if receipt["batch_id"] != batch_id:
        return expected_tree
    hash_value(receipt["batch_plan_hash"])
    require(receipt["batch_plan_hash"] == plan_hash, "manual selection batch plan mismatch")
    authorization = receipt["authorization"]
    require(
        isinstance(authorization, dict)
        and set(authorization) == {"source", "text"}
        and authorization["source"] == "explicit-user-request"
        and _text(authorization["text"]),
        "explicit manual selection authorization required",
    )
    require(_text(receipt["applied_by"]), "manual selection operator required")
    validate_time(receipt["applied_at"])
    basis = receipt["basis_commit"]
    require(
        isinstance(basis, str) and re.fullmatch(r"[0-9a-f]{40}", basis) is not None,
        "invalid manual selection basis commit",
    )
    git(root, "merge-base", "--is-ancestor", basis, "HEAD")
    app_path = f"data/source_reviews/tpn/{batch_id}/application.json"
    basis_application = git(root, "show", basis + ":" + app_path)
    require(
        basis_application == _regular_file(root, app_path).read_bytes(),
        "manual selection basis application changed",
    )
    original = exact_json(basis_application)
    require(
        original["plan_hash"] == plan_hash and original["result_tree"] == expected_tree,
        "manual selection basis result mismatch",
    )
    manifest_raw = _regular_file(root, MANIFEST).read_bytes()
    hash_value(receipt["proposal_manifest_sha256"])
    require(
        manifest_raw == git(root, "show", basis + ":" + MANIFEST)
        and sha256(manifest_raw) == receipt["proposal_manifest_sha256"],
        "immutable manual selection proposal manifest mismatch",
    )
    manifest = exact_json(manifest_raw)
    require(
        manifest.get("format") == "tpn-best-protection-audit"
        and type(manifest.get("format_version")) is int
        and manifest["format_version"] == 1
        and manifest.get("approval_status") == "pending",
        "invalid original protection manifest",
    )
    proposals = manifest.get("migration_proposals")
    require(isinstance(proposals, list) and bool(proposals), "missing original manual proposals")
    by_id = {}
    for proposal in proposals:
        require(
            isinstance(proposal, dict) and set(proposal) == PROPOSAL_FIELDS,
            "invalid original manual proposal fields",
        )
        identity, relative = proposal["object_id"], proposal["path"]
        require(
            isinstance(identity, str)
            and re.fullmatch(r"[A-Z]{3}-[0-9]{4,}", identity) is not None
            and relative == f"data/objects/{identity[:3]}/{identity}.yml"
            and identity not in by_id,
            "unsafe/duplicate original manual proposal",
        )
        by_id[identity] = proposal
    pins = receipt["objects"]
    require(isinstance(pins, list) and len(pins) == len(by_id), "manual proposal set mismatch")
    result, seen = dict(expected_tree), set()
    with tempfile.TemporaryDirectory(prefix="tpn-manual-selection-") as folder:
        before_path = Path(folder) / "before.yml"
        for pin in pins:
            require(
                isinstance(pin, dict) and set(pin) == PIN_FIELDS,
                "invalid manual selection object fields",
            )
            identity = pin["object_id"]
            require(
                isinstance(identity, str) and identity in by_id and identity not in seen,
                "unknown/duplicate manual selection object",
            )
            seen.add(identity)
            proposal = by_id[identity]
            relative = proposal["path"]
            require(pin["path"] == relative, "manual selection path mismatch")
            for field in ("before_sha256", "after_sha256"):
                hash_value(pin[field])
            before_raw = git(root, "show", basis + ":" + relative)
            key = relative.removeprefix("data/")
            require(
                sha256(before_raw)
                == pin["before_sha256"]
                == proposal["preimage_sha256"]
                == expected_tree.get(key),
                "manual selection preimage mismatch",
            )
            current_path = _regular_file(root, relative)
            require(
                sha256(current_path.read_bytes()) == pin["after_sha256"],
                "manual selection result hash mismatch",
            )
            before_path.write_bytes(before_raw)
            try:
                before, current = load_unique_yaml(before_path), load_unique_yaml(current_path)
            except yaml.YAMLError as exc:
                raise ValueError("invalid manual selection YAML: " + str(exc)) from exc
            require(
                isinstance(before, dict)
                and before.get("id") == identity
                and isinstance(proposal["before"], dict)
                and before.get("best_measurement") == proposal["before"]
                and proposal["before"].get("mode") == "auto"
                and isinstance(proposal["after"], dict)
                and set(proposal["after"]) == {"mode", "measurement_id", "reason"}
                and proposal["after"]["mode"] == "manual"
                and proposal["after"]["measurement_id"] == proposal["before"]["measurement_id"]
                and _text(proposal["after"]["reason"])
                and proposal["approval_status"] == "pending",
                "invalid original auto-to-manual proposal",
            )
            protection = assess_protection(before)
            require(
                protection["protected"] and protection["evidence"] == proposal["evidence"],
                "original manual proposal lacks matching protection evidence",
            )
            wanted = deepcopy(before)
            wanted["best_measurement"] = {
                **proposal["after"],
                "updated_at": receipt["applied_at"],
                "updated_by": receipt["applied_by"],
            }
            wanted.update(updated_at=receipt["applied_at"], updated_by=receipt["applied_by"])
            require(
                canonical(current) == canonical(wanted),
                "manual selection delta differs from authorized pin",
            )
            result[key] = pin["after_sha256"]
    return result
