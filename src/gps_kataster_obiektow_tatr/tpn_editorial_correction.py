"""Reproduce the authorized PR #12 note/tag correction from a fixed Git preimage."""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import yaml

from .tpn_api import require
from .tpn_editorial_notes import clean_cave, clean_object
from .tpn_normalization import exact_json
from .tpn_snapshot import sha256, validate_time
from .tpn_source_state import STATE_PATH, git, hash_value, validate_state

BASE_COMMIT = "87a19510580364f96a85edea69e0099ffc4f9a4d"
RECEIPT = "docs/asdlc/verification/PBI-101-editorial-correction.json"
BATCH_ID = "pbi-101-20261019"
PREVIOUS_RECEIPTS = (
    "docs/asdlc/verification/PBI-099-protection-manifest.json",
    "docs/asdlc/verification/PBI-099-manual-selection.json",
    "docs/asdlc/verification/PBI-101-D26-resolution.json",
    "docs/asdlc/verification/PBI-101-review/remaining-26.json",
    "docs/asdlc/verification/PBI-101-catalog-notes.json",
)
FIELDS = {
    "format",
    "format_version",
    "base_commit",
    "applied_at",
    "applied_by",
    "authorization_quote",
    "before_catalog_hash",
    "result_hashes",
}


def regular(root, relative):
    path = root / relative
    require(path.resolve() == path and path.is_file(), "unsafe/missing editorial correction file")
    return path


def validate_receipt(receipt):
    require(
        isinstance(receipt, dict) and set(receipt) == FIELDS, "invalid editorial receipt fields"
    )
    require(
        receipt["format"] == "tpn-editorial-correction"
        and type(receipt["format_version"]) is int
        and receipt["format_version"] == 1
        and receipt["base_commit"] == BASE_COMMIT,
        "invalid editorial correction basis/version",
    )
    require(receipt["applied_by"] == "agent:codex", "invalid editorial operator")
    require(
        isinstance(receipt["authorization_quote"], str)
        and bool(receipt["authorization_quote"].strip()),
        "editorial authorization required",
    )
    validate_time(receipt["applied_at"])
    hash_value(receipt["before_catalog_hash"])
    require(isinstance(receipt["result_hashes"], dict), "invalid editorial result hashes")


def build_editorial_files(base, receipt):
    """Derive edits; no untrusted receipt field can select data, coordinates or best."""
    from .tpn_batch import json_bytes, result_hashes
    from .tpn_changes import Catalog

    validate_receipt(receipt)
    base = Path(base).resolve()
    catalog = Catalog(base)
    require(catalog.hash == receipt["before_catalog_hash"], "editorial catalog preimage mismatch")
    objects = list(catalog.objects.values())
    files = {}
    for kind, entities in (("object", catalog.objects), ("cave", catalog.caves)):
        for ident, before in sorted(entities.items()):
            after = (
                clean_object(deepcopy(before))
                if kind == "object"
                else clean_cave(deepcopy(before), objects)
            )
            if before == after:
                continue
            after.update(updated_at=receipt["applied_at"], updated_by=receipt["applied_by"])
            files[catalog.paths[ident]] = yaml.safe_dump(
                after, allow_unicode=True, sort_keys=False
            ).encode()
    state = exact_json(regular(base, STATE_PATH).read_bytes())
    validate_state(state, state["policy_hash"])
    hashes, catalog_hash = result_hashes(base, files)
    for resolution in state["resolutions"]:
        resolution["result_hashes"] = {p: hashes[p] for p in resolution["result_hashes"]}
        resolution["result_catalog_hash"] = catalog_hash
    validate_state(state, state["policy_hash"])
    files[STATE_PATH] = json_bytes(state)
    return files


def verified_editorial_files(root, previous_files):
    """Check-only overlay; original application/replay remains bound to old bytes."""
    from .tpn_batch import base_checkout

    root = Path(root).resolve()
    path = root / RECEIPT
    if not path.exists() and not path.is_symlink():
        return previous_files
    receipt = exact_json(regular(root, RECEIPT).read_bytes())
    validate_receipt(receipt)
    git(root, "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD")
    with base_checkout(root, BASE_COMMIT) as base:
        for relative in PREVIOUS_RECEIPTS:
            require(
                regular(root, relative).read_bytes() == regular(base, relative).read_bytes(),
                "editorial changed historical receipt",
            )
        require(
            all(regular(base, p).read_bytes() == raw for p, raw in previous_files.items()),
            "editorial preceding output mismatch",
        )
        files = build_editorial_files(base, receipt)
    require(
        receipt["result_hashes"] == {p: sha256(raw) for p, raw in files.items()},
        "editorial derived result hashes mismatch",
    )
    return {**previous_files, **files}


@contextmanager
def editorial_preimage(root, batch_id):
    """Run the unchanged older guards against their immutable pre-editorial bytes."""
    from .tpn_batch import base_checkout

    root = Path(root).resolve()
    path = root / RECEIPT
    if batch_id != BATCH_ID or (not path.exists() and not path.is_symlink()):
        yield root
        return
    validate_receipt(exact_json(regular(root, RECEIPT).read_bytes()))
    git(root, "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD")
    with base_checkout(root, BASE_COMMIT) as base:
        gitdir = git(root, "rev-parse", "--absolute-git-dir").decode().strip()
        (base / ".git").write_text(f"gitdir: {gitdir}\n")
        yield base


def verified_editorial_tree(root, batch_id, expected_tree):
    from .tpn_batch import base_checkout, current_nonbatch

    root = Path(root).resolve()
    path = root / RECEIPT
    if batch_id != BATCH_ID or (not path.exists() and not path.is_symlink()):
        return expected_tree
    with base_checkout(root, BASE_COMMIT) as base:
        require(
            current_nonbatch(base, batch_id) == expected_tree, "editorial preceding tree mismatch"
        )
    files = verified_editorial_files(root, {})
    result = dict(expected_tree)
    for relative, raw in files.items():
        require(regular(root, relative).read_bytes() == raw, "editorial actual result mismatch")
        result[relative.removeprefix("data/")] = sha256(raw)
    return result
