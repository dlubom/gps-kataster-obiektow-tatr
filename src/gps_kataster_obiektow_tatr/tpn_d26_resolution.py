"""Reconstruct the explicitly authorized, fixed D001–D026 catalog supplement.

This is a read-only exception for one historical batch, not a replay permission.
The receipt supplies audit text; it cannot select targets, fields or coordinates.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .best_measurement import select_default_best_measurement_id
from .staging_review import _dataset_with_review_changes
from .tpn_api import require
from .tpn_batch_actions import DomainPlan, measurement, next_id, yaml_bytes
from .tpn_best_guard import plan_best_action
from .tpn_normalization import canonical, digest, exact_json, normalize_feature
from .tpn_snapshot import sha256, validate_time
from .tpn_source_state import STATE_PATH, git, hash_value, validate_state

BATCH_ID = "pbi-101-20261019"
BASE_COMMIT = "d1f958bc9a2bdcfa8a0dd620cfeaace589ca5d60"
RECEIPT = "docs/asdlc/verification/PBI-101-D26-resolution.json"
TABLE = "docs/asdlc/verification/PBI-101-review/remaining-26.json"
PREFIX = f"data/source_reviews/tpn/{BATCH_ID}"
IDS = {f"D{i:03d}" for i in range(1, 27)}
FIELDS = {
    "format",
    "format_version",
    "batch_id",
    "base_commit",
    "snapshot_hash",
    "original_plan_hash",
    "applied_at",
    "applied_by",
    "authorization_quote",
    "notes",
    "result_hashes",
}
ALIASES = {"D003": "D014", "D008": "D010"}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _regular(root, relative):
    path = root / relative
    require(path.resolve() == path and path.is_file(), "unsafe/missing D26 evidence file")
    return path


def _receipt(receipt):
    require(isinstance(receipt, dict) and set(receipt) == FIELDS, "invalid D26 receipt fields")
    require(
        receipt["format"] == "tpn-d26-resolution"
        and type(receipt["format_version"]) is int
        and receipt["format_version"] == 1
        and receipt["batch_id"] == BATCH_ID
        and receipt["base_commit"] == BASE_COMMIT,
        "invalid D26 receipt basis/version",
    )
    require(receipt["applied_by"] == "agent:codex", "invalid D26 operator")
    require(_text(receipt["authorization_quote"]), "explicit D26 authorization required")
    validate_time(receipt["applied_at"])
    for key in ("snapshot_hash", "original_plan_hash"):
        hash_value(receipt[key])
    notes = receipt["notes"]
    require(
        isinstance(notes, dict) and set(notes) == IDS and all(_text(v) for v in notes.values()),
        "D26 notes must cover exactly D001–D026",
    )
    require(isinstance(receipt["result_hashes"], dict), "invalid D26 result hashes")
    for path, checksum in receipt["result_hashes"].items():
        require(
            isinstance(path, str)
            and path.startswith("data/")
            and Path(path).as_posix() == path
            and ".." not in Path(path).parts
            and "\\" not in path,
            "invalid D26 result path",
        )
        hash_value(checksum)


def _inputs(base, receipt):
    _receipt(receipt)
    changes_raw = _regular(base, PREFIX + "/changes.json").read_bytes()
    changes = exact_json(changes_raw)
    application = exact_json(_regular(base, PREFIX + "/application.json").read_bytes())
    table = exact_json(_regular(base, TABLE).read_bytes())
    state = exact_json(_regular(base, STATE_PATH).read_bytes())
    require(
        changes["batch_id"] == BATCH_ID
        and changes["snapshot_hash"] == table["snapshot_hash"] == receipt["snapshot_hash"]
        and application["plan_hash"] == receipt["original_plan_hash"]
        and digest(application["plan"]) == application["plan_hash"]
        and application["changes_hash"] == sha256(changes_raw),
        "D26 snapshot/original plan mismatch",
    )
    validate_state(state, changes["policy_hash"])
    entries = {r["proposal_id"]: r for r in table["entries"]}
    require(len(table["entries"]) == 26 and set(entries) == IDS, "invalid original D26 table")
    original_rows = {r["change_id"]: r for r in changes["records"]}
    resolutions = {(r["globalid"], r["revision_hash"]): r for r in state["resolutions"]}
    require(
        {r["globalid"] for r in state["deferred"]} == {r["globalid"] for r in entries.values()}
        and len(state["deferred"]) == 26,
        "D26 original defer preimage mismatch",
    )
    rows = {}
    for ident, entry in entries.items():
        row = original_rows[entry["change_id"]]
        source = row["source_after"]
        require(
            entry["globalid"] == row["globalid"]
            and row["target"] is None
            and entry["user_decision"] == "defer"
            # The human review table was serialized through binary floats.
            # Raw API values below remain bound by exact normalization/hashes.
            and {
                **entry["location"],
                "lat": float(entry["location"]["lat"]),
                "lon": float(entry["location"]["lon"]),
            }
            == {
                **source["location"],
                "lat": float(source["location"]["lat"]),
                "lon": float(source["location"]["lon"]),
            }
            and canonical(entry["metadata"]) == canonical(source["metadata"])
            and canonical(entry["source_time"]) == canonical(source["source_time"])
            and resolutions[(row["globalid"], row["revision_hash"])]["status"] == "defer",
            "D26 source/table/preimage mismatch",
        )
        normalized = normalize_feature(source["raw"])
        without_fetch = deepcopy(source)
        without_fetch["source_time"].pop("fetched_at", None)
        require(canonical(normalized) == canonical(without_fetch), "D26 raw source mismatch")
        rows[ident] = row
    return changes, application, state, rows


def _note(ident, row, receipt):
    meta = row["source_after"]["metadata"]
    metrics = "; ".join(
        f"{field}={canonical(meta[field]).decode()}"
        for field in ("DLUGOSC", "GLEBOKOSC", "PRZEWYZSZE", "DENIWELACJ")
        if meta[field] is not None
    )
    result = f"[{ident}; TPN {row['globalid']}] {receipt['notes'][ident]}"
    if metrics:
        result += "\nMetryka źródła TPN: " + metrics + "."
    return result


def _append_note(entity, fragment):
    before = entity.get("notes") or ""
    entity["notes"] = before + ("\n" if before else "") + fragment


def build_d26_files(base, receipt):
    """Return deterministic full-repository output paths and D-to-object mapping.

    During receipt preparation result_hashes may be empty. Verification requires
    it to equal these derived outputs; no hash in the receipt selects a mutation.
    """
    from .tpn_batch import json_bytes, make_state, result_hashes

    base = Path(base).resolve()
    changes, application, previous, rows = _inputs(base, receipt)
    domain = DomainPlan(base, changes, {"decisions": []})
    audit = {"reviewed_at": receipt["applied_at"], "reviewed_by": receipt["applied_by"]}
    mapping = {}
    for ident in sorted(IDS - ALIASES.keys() - {"D022"}):
        row = rows[ident]
        key = "okno-ciemniak" if ident in ("D002", "D010") else ident.lower()
        if ident != "D006" and ("cave", key) not in domain.keys:
            domain.create_cave({"cave_key": key}, row, audit)
        action = {
            "object_key": ident.lower(),
            "location_hash": row["location_hash"],
            "initial_best": "first_measurement",
            "category": "jaskinia_otwor",
        }
        if ident != "D006":
            action["cave_key"] = key
        domain.new_object(action, row, audit)
        oid = domain.row_targets[row["change_id"]]
        mapping[ident] = oid
        if ident == "D006":
            domain.link_cave({"object_key": ident.lower(), "cave_id": "C-0219"}, row, audit)

    mapping["D022"] = "MLW-0050"
    for ident, primary in [*ALIASES.items(), ("D022", "D022")]:
        row, oid = rows[ident], mapping[primary]
        mapping[ident] = oid
        domain.attach_source(
            {
                "target": {"kind": "object", "id": oid},
                "reference": {
                    "system": "TPN",
                    "ref_type": "source_globalid",
                    "external_id": row["globalid"],
                },
                "evidence": receipt["notes"][ident],
            },
            row,
            audit,
        )
        obj = domain.objects[oid]
        point = row["source_after"]["location"]
        require(
            all(
                (float(point["lat"]), float(point["lon"])) != (m["lat"], m["lon"])
                for m in obj["measurements"]
            ),
            "D26 exact API location already present",
        )
        mid = next_id("m-", {m["id"] for m in obj["measurements"]}, 3)
        added = measurement(row, mid, audit, legacy=True)
        obj["measurements"].append(added)
        if ident == "D022":
            before = domain.catalog.objects[oid]
            selected = before["best_measurement"]["measurement_id"]
            mode = before["best_measurement"]["mode"]
            if select_default_best_measurement_id(obj["measurements"]) != selected:
                mode = "manual"
            choice = {
                "action": "keep",
                "measurement_id": selected,
                "resulting_mode": mode,
                "reason": receipt["notes"][ident],
            }
            best = plan_best_action(before, [added], choice)
            require(best["can_apply"], "D26 existing best protected against mode change")
            obj["best_measurement"] = {
                **best["after"],
                "updated_at": audit["reviewed_at"],
                "updated_by": audit["reviewed_by"],
            }
        else:
            obj["best_measurement"]["measurement_id"] = select_default_best_measurement_id(
                obj["measurements"]
            )
        domain.applied[row["change_id"]].append(
            {
                "location_hash": row["location_hash"],
                "measurement_id": mid,
                "source_snapshot_hash": changes["snapshot_hash"],
                "csv_evidence": None,
            }
        )
        domain.row_targets[row["change_id"]] = oid
        domain.touch(oid, audit)

    for ident in sorted(IDS):
        row, oid = rows[ident], mapping[ident]
        obj = domain.objects[oid]
        fragment = _note(ident, row, receipt)
        _append_note(obj, fragment)
        cid = obj["cave_id"]
        if cid not in domain.catalog.caves:
            _append_note(domain.caves[cid], fragment)

    future = _dataset_with_review_changes(
        domain.dataset, data_dir=base / "data", objects=domain.objects, caves=domain.caves
    )
    domain.validate(future)
    files = {
        domain.paths[ident]: yaml_bytes(domain.objects.get(ident, domain.caves.get(ident)))
        for ident in sorted(domain.dirty)
    }
    decisions = []
    for ident in sorted(IDS):
        row, oid = rows[ident], mapping[ident]
        preimage = domain.catalog.context(oid)[1] if oid in domain.catalog.objects else {}
        decisions.append(
            {
                **audit,
                "change_id": row["change_id"],
                "globalid": row["globalid"],
                "revision_hash": row["revision_hash"],
                "status": "approve",
                "reason": f"Suplement D26: {ident}. {receipt['notes'][ident]}",
                "preimage": preimage,
            }
        )
    current_changes = {**changes, "catalog_hash": domain.catalog.hash}
    state = make_state(
        current_changes,
        {"decisions": decisions, "changes_hash": application["changes_hash"]},
        previous,
        domain,
        files,
    )
    after_hashes, after_catalog = result_hashes(base, files)
    for resolution in state["resolutions"]:
        target = resolution["target"]
        paths = []
        if target:
            oid, cid = target["object_id"], target["cave_id"]
            paths = [domain.paths[oid]] + ([domain.paths[cid]] if cid else [])
            paths.extend(
                domain.paths[r["id"]]
                for r in domain.catalog.relations
                if oid in (r.get("from_object_id"), r.get("to_object_id"))
            )
        resolution["result_hashes"] = {p: after_hashes[p] for p in sorted(paths)}
        resolution["result_catalog_hash"] = after_catalog
    validate_state(state, changes["policy_hash"])
    require(not state["deferred"], "D26 supplement must resolve all original defers")
    files[STATE_PATH] = json_bytes(state)
    return files, mapping


def verified_d26_resolution_tree(root, *, batch_id, plan_hash, expected_tree):
    """Adjust check-only expectations after reconstructing the one authorized delta."""
    if batch_id != BATCH_ID:
        return expected_tree
    root = Path(root).resolve()
    receipt_path = root / RECEIPT
    if not receipt_path.exists() and not receipt_path.is_symlink():
        return expected_tree
    receipt = exact_json(_regular(root, RECEIPT).read_bytes())
    _receipt(receipt)
    require(receipt["original_plan_hash"] == plan_hash, "D26 original plan binding mismatch")
    git(root, "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD")
    from .tpn_batch import base_checkout, current_nonbatch

    with base_checkout(root, BASE_COMMIT) as base:
        require(
            current_nonbatch(base, BATCH_ID) == expected_tree, "D26 base preimage tree mismatch"
        )
        for relative in (
            PREFIX + "/changes.json",
            PREFIX + "/application.json",
            PREFIX + "/decisions.yml",
            TABLE,
        ):
            require(
                _regular(root, relative).read_bytes() == _regular(base, relative).read_bytes(),
                "D26 immutable original evidence changed",
            )
        files, _ = build_d26_files(base, receipt)
    wanted = {path: sha256(raw) for path, raw in files.items()}
    require(receipt["result_hashes"] == wanted, "D26 derived result hashes mismatch")
    from .tpn_catalog_notes import verified_notes_files

    files = verified_notes_files(root, files)
    wanted = {path: sha256(raw) for path, raw in files.items()}
    result = dict(expected_tree)
    for relative, checksum in wanted.items():
        require(
            sha256(_regular(root, relative).read_bytes()) == checksum, "D26 actual result mismatch"
        )
        result[relative.removeprefix("data/")] = checksum
    return result
