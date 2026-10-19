"""Strict read-only source-state input. Only main supplies accepted CLI state."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path, PurePosixPath

from .tpn_api import globalid, require
from .tpn_normalization import exact_json
from .tpn_snapshot import validate_time

STATE_PATH = "data/source_state/tpn/state.json"
STATE_KEYS = {
    "format",
    "format_version",
    "accepted_snapshot_hash",
    "policy_hash",
    "bindings",
    "resolutions",
    "deferred",
}
RESOLUTION_KEYS = {
    "globalid",
    "revision_hash",
    "snapshot_hash",
    "status",
    "target",
    "preimage",
    "catalog_hash",
    "policy_hash",
    "reviewed_by",
    "reviewed_at",
    "reason",
    "batch_id",
    "changes_hash",
    "applied_locations",
    "result_hashes",
    "result_catalog_hash",
    "absence",
}


def hash_value(value: object) -> None:
    require(
        isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
        "invalid SHA-256",
    )


def path_hashes(value: object) -> None:
    require(isinstance(value, dict), "invalid preimage/result hashes")
    for path, checksum in value.items():
        require(
            isinstance(path, str)
            and not PurePosixPath(path).is_absolute()
            and ".." not in PurePosixPath(path).parts
            and "\\" not in path
            and str(PurePosixPath(path)) == path,
            "unsafe state path",
        )
        require(
            path.startswith(("data/objects/", "data/caves/", "data/relations/")),
            "invalid target path",
        )
        hash_value(checksum)


def validate_state(state: dict, policy_hash: str) -> None:
    require(isinstance(state, dict) and set(state) == STATE_KEYS, "invalid source-state fields")
    require(
        state["format"] == "tpn-source-state"
        and type(state["format_version"]) is int
        and state["format_version"] == 1,
        "unsupported source-state version",
    )
    hash_value(state["accepted_snapshot_hash"])
    require(state["policy_hash"] == policy_hash, "state policy migration required")
    require(isinstance(state["bindings"], dict), "invalid bindings")
    for guid, target in state["bindings"].items():
        require(
            globalid(guid) == guid and isinstance(target, str) and bool(target), "invalid binding"
        )
    require(
        isinstance(state["resolutions"], list) and isinstance(state["deferred"], list),
        "invalid state lists",
    )
    seen = {}
    for item in state["resolutions"]:
        require(
            isinstance(item, dict) and set(item) == RESOLUTION_KEYS, "invalid resolution fields"
        )
        guid = globalid(item["globalid"])
        require(guid == item["globalid"], "noncanonical state GUID")
        for name in (
            "revision_hash",
            "snapshot_hash",
            "catalog_hash",
            "policy_hash",
            "changes_hash",
            "result_catalog_hash",
        ):
            hash_value(item[name])
        require(item["policy_hash"] == policy_hash, "resolution policy migration required")
        key = (guid, item["revision_hash"])
        require(key not in seen, "duplicate resolution")
        require(item["status"] in ("approve", "reject", "defer"), "invalid resolution status")
        for name in ("reviewed_by", "reason", "batch_id"):
            require(
                isinstance(item[name], str) and bool(item[name].strip()),
                f"missing resolution {name}",
            )
        validate_time(item["reviewed_at"])
        absence = item["absence"]
        if absence is not None:
            require(
                isinstance(absence, dict)
                and set(absence) == {"baseline", "previous_revision_hash"},
                "invalid absence evidence",
            )
            hash_value(absence["previous_revision_hash"])
            baseline = absence["baseline"]
            require(isinstance(baseline, dict), "invalid absence baseline")
            if baseline.get("kind") == "accepted_snapshot":
                require(set(baseline) == {"kind", "snapshot_hash"}, "invalid absence snapshot")
                hash_value(baseline["snapshot_hash"])
            else:
                require(
                    set(baseline) == {"kind", "path", "raw_sha256"}
                    and baseline["kind"] == "csv_bootstrap"
                    and baseline["path"] == "data/sources/tpn/tpn_otwory_jaskin.xlsx.-.Export.csv",
                    "invalid absence CSV",
                )
                hash_value(baseline["raw_sha256"])
        target = item["target"]
        require(
            target is None
            or (
                isinstance(target, dict)
                and set(target) == {"object_id", "cave_id"}
                and isinstance(target["object_id"], str)
                and bool(target["object_id"])
                and (target["cave_id"] is None or isinstance(target["cave_id"], str))
            ),
            "invalid target",
        )
        path_hashes(item["preimage"])
        path_hashes(item["result_hashes"])
        require(isinstance(item["applied_locations"], list), "invalid applied locations")
        locations = set()
        for applied in item["applied_locations"]:
            require(
                isinstance(applied, dict)
                and set(applied)
                == {"location_hash", "measurement_id", "source_snapshot_hash", "csv_evidence"},
                "invalid applied location",
            )
            hash_value(applied["location_hash"])
            hash_value(applied["source_snapshot_hash"])
            evidence = applied["csv_evidence"]
            if evidence is not None:
                require(
                    isinstance(evidence, dict)
                    and set(evidence) == {"kind", "path", "raw_sha256"}
                    and evidence["kind"] == "csv_bootstrap"
                    and evidence["path"] == "data/sources/tpn/tpn_otwory_jaskin.xlsx.-.Export.csv",
                    "invalid bootstrap evidence",
                )
                hash_value(evidence["raw_sha256"])
            require(
                applied["location_hash"] not in locations
                and isinstance(applied["measurement_id"], str)
                and bool(applied["measurement_id"]),
                "duplicate/invalid applied location",
            )
            locations.add(applied["location_hash"])
        require(
            item["status"] == "approve" or not item["applied_locations"],
            "non-approve applied locations",
        )
        seen[key] = item
    deferred = set()
    for item in state["deferred"]:
        require(
            isinstance(item, dict) and set(item) == {"globalid", "revision_hash", "snapshot_hash"},
            "invalid deferred evidence",
        )
        key = (item["globalid"], item["revision_hash"])
        require(
            key not in deferred
            and key in seen
            and seen[key]["status"] == "defer"
            and seen[key]["snapshot_hash"] == item["snapshot_hash"],
            "missing/duplicate deferred resolution",
        )
        deferred.add(key)
    require(
        deferred == {key for key, item in seen.items() if item["status"] == "defer"},
        "lost deferred queue",
    )


def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)
    require(
        result.returncode == 0, "git read failed: " + result.stderr.decode(errors="replace").strip()
    )
    return result.stdout


def read_accepted_state(repo: Path) -> tuple[dict | None, str]:
    """No --state/--ref escape hatch: candidates on a PR cannot become accepted.

    The operator fetches origin before running. GitHub permissions/human merge
    are enforced by the delivery process, not claimed from untrusted authors.
    """
    commit = (
        git(repo, "rev-parse", "--verify", "refs/remotes/origin/main^{commit}").decode().strip()
    )
    paths = git(repo, "ls-tree", "--name-only", commit, "--", STATE_PATH).decode().splitlines()
    if not paths:
        return None, commit
    require(paths == [STATE_PATH], "invalid accepted state path")
    return exact_json(git(repo, "show", f"{commit}:{STATE_PATH}")), commit
