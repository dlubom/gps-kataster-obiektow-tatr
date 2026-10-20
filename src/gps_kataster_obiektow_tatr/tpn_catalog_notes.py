"""Reconstruct the fixed PR #12 note correction without altering TPN decisions.

The receipt can supply only notes for an explicit set of records. All other
values come from the immutable reviewed commit. Used by check, never by apply.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .tpn_api import require
from .tpn_batch_actions import yaml_bytes
from .tpn_normalization import exact_json
from .tpn_snapshot import sha256, validate_time
from .tpn_source_state import STATE_PATH, git, hash_value, validate_state

BASE_COMMIT = "8c18ee573e5224b8f02044d4f4b823459b6cbcd7"
RECEIPT = "docs/asdlc/verification/PBI-101-catalog-notes.json"
OBJECTS = {
    "CHZ-0028",
    "CHZ-0029",
    "CHZ-0030",
    "CHZ-0031",
    "CHZ-0032",
    "KSW-0258",
    "KSW-0259",
    "KSW-0260",
    "MLW-0050",
    "MTW-0070",
    "MTW-0071",
    "MTW-0072",
    "MTW-0073",
    "MTZ-0069",
    "MTZ-0070",
    "MTZ-0071",
    "STR-0031",
    "STR-0032",
    "STR-0033",
    "STR-0034",
    "STR-0035",
    "STR-0036",
    "STR-0037",
    "STR-0038",
}
PATHS = {f"data/objects/{oid[:3]}/{oid}.yml" for oid in OBJECTS} | {
    f"data/caves/C-{number:04d}.yml" for number in [219, 981, *range(1005, 1031)]
}
FIELDS = {
    "format",
    "format_version",
    "base_commit",
    "applied_at",
    "applied_by",
    "authorization_quote",
    "notes",
    "result_hashes",
}


def _regular(root, relative):
    path = root / relative
    require(path.resolve() == path and path.is_file(), "unsafe/missing note correction file")
    return path


def _receipt(receipt):
    require(isinstance(receipt, dict) and set(receipt) == FIELDS, "invalid note receipt fields")
    require(
        receipt["format"] == "tpn-catalog-notes"
        and type(receipt["format_version"]) is int
        and receipt["format_version"] == 1
        and receipt["base_commit"] == BASE_COMMIT,
        "invalid note correction basis/version",
    )
    require(receipt["applied_by"] == "agent:codex", "invalid note correction operator")
    require(
        isinstance(receipt["authorization_quote"], str) and receipt["authorization_quote"].strip(),
        "explicit note correction authorization required",
    )
    validate_time(receipt["applied_at"])
    require(isinstance(receipt["result_hashes"], dict), "invalid note result hashes")
    notes = receipt["notes"]
    require(isinstance(notes, dict) and set(notes) == PATHS, "invalid note correction scope")
    for path, entry in notes.items():
        require(
            isinstance(entry, dict) and set(entry) == {"before_sha256", "after"},
            "invalid note correction entry",
        )
        hash_value(entry["before_sha256"])
        text = entry["after"]
        require(
            (text is None and "/objects/" in path)
            or (
                isinstance(text, str) and bool(text.strip()) and not re.search(r"\bD\d{3}\b", text)
            ),
            "invalid corrected note",
        )


def build_notes_files(base, receipt):
    """Derive only notes/audit and resolution context hashes from the fixed preimage."""
    from .tpn_batch import json_bytes, result_hashes

    _receipt(receipt)
    base = Path(base).resolve()
    files = {}
    for path in sorted(PATHS):
        raw = _regular(base, path).read_bytes()
        entry = receipt["notes"][path]
        require(sha256(raw) == entry["before_sha256"], "note correction preimage mismatch")
        value = yaml.safe_load(raw)
        value.update(
            notes=entry["after"],
            updated_at=receipt["applied_at"],
            updated_by=receipt["applied_by"],
        )
        files[path] = yaml_bytes(value)
    state = exact_json(_regular(base, STATE_PATH).read_bytes())
    validate_state(state, state["policy_hash"])
    hashes, catalog_hash = result_hashes(base, files)
    for resolution in state["resolutions"]:
        resolution["result_hashes"] = {p: hashes[p] for p in resolution["result_hashes"]}
        resolution["result_catalog_hash"] = catalog_hash
    validate_state(state, state["policy_hash"])
    files[STATE_PATH] = json_bytes(state)
    return files


def verified_notes_files(root, previous_files):
    """Overlay the correction only after proving the preceding D26 output unchanged."""
    from .tpn_batch import base_checkout
    from .tpn_d26_resolution import RECEIPT as PREVIOUS_RECEIPT

    root = Path(root).resolve()
    path = root / RECEIPT
    if not path.exists() and not path.is_symlink():
        return previous_files
    receipt = exact_json(_regular(root, RECEIPT).read_bytes())
    _receipt(receipt)
    git(root, "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD")
    with base_checkout(root, BASE_COMMIT) as base:
        require(
            _regular(root, PREVIOUS_RECEIPT).read_bytes()
            == _regular(base, PREVIOUS_RECEIPT).read_bytes(),
            "note correction changed original receipt",
        )
        require(
            all(_regular(base, p).read_bytes() == raw for p, raw in previous_files.items()),
            "note correction previous output mismatch",
        )
        files = build_notes_files(base, receipt)
    require(
        receipt["result_hashes"] == {p: sha256(raw) for p, raw in files.items()},
        "note correction derived result hashes mismatch",
    )
    return {**previous_files, **files}
