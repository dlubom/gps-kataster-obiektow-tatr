"""Immutable snapshot publication and offline byte/semantic readback (PBI-096)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from .tpn_api import (
    ENDPOINT,
    SnapshotError,
    Transport,
    acquire,
    http_get,
    integer,
    parse_json,
    query_params,
    require,
    summarize,
    validate_layer,
)

SNAPSHOTS = Path("data/sources/tpn/snapshots")
POLICY = Path("docs/asdlc/tpn_sync_contract.md")
ROLES = {
    "layer.json": "schema",
    "layer-after.json": "schema_after",
    "count-before.json": "count_before",
    "count-after.json": "count_after",
    "ids-before.json": "ids_before",
    "ids-after.json": "ids_after",
    "policy.md": "policy",
}


def canonical(value: object) -> bytes:
    """Manifest values are strings, integer counts/IDs and booleans, never floats."""
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def snapshot_hash(manifest: dict) -> str:
    """Sorted path/hash inventory plus canonical manifest excluding its own hash."""
    body = {k: v for k, v in manifest.items() if k != "snapshot_hash"}
    prefix = (SNAPSHOTS / manifest["snapshot_id"]).as_posix()
    inventory = [(item["path"], item["raw_sha256"]) for item in manifest["files"]]
    inventory.append((prefix + "/manifest.json", sha256(canonical(body))))
    return sha256(canonical(sorted(inventory)))


def timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def validate_time(value: object) -> datetime:
    require(
        isinstance(value, str)
        and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z", value) is not None,
        "timestamp must be ISO UTC with Z",
    )
    return datetime.fromisoformat(value)


def validate_id(snapshot_id: object) -> None:
    require(
        isinstance(snapshot_id, str)
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", snapshot_id) is not None,
        "invalid snapshot_id",
    )


def make_manifest(
    raw: dict[str, bytes], snapshot_id: str, page_size: int, started_at: str, fetched_at: str
) -> dict:
    validate_id(snapshot_id)
    require(validate_time(started_at) <= validate_time(fetched_at), "reversed acquisition interval")
    prefix = (SNAPSHOTS / snapshot_id).as_posix()
    checks, pages = summarize(raw, prefix, page_size)
    # The complete accepted policy is archived, not merely its version label.
    require(
        raw["policy.md"].decode("utf-8").startswith("# Kontrakt integracji TPN"),
        "missing TPN policy text",
    )
    manifest = {
        "format": "tpn-source-manifest",
        "format_version": 1,
        "snapshot_id": snapshot_id,
        "policy_version": "tpn-sync-v1",
        "policy_hash": sha256(raw["policy.md"]),
        "source": {
            "endpoint": ENDPOINT,
            "layer_id": 6,
            "layer_name": "Jaskinie",
            "geometry_type": "esriGeometryPoint",
            "schema_hash": sha256(raw["layer.json"]),
        },
        "query": query_params(page_size),
        "started_at": started_at,
        "fetched_at": fetched_at,
        "checks": checks,
        "pages": pages,
        "files": [
            {
                "path": f"{prefix}/{name}",
                "role": ROLES.get(name, "page"),
                "raw_sha256": sha256(value),
            }
            for name, value in sorted(raw.items())
        ],
    }
    manifest["snapshot_hash"] = snapshot_hash(manifest)
    return manifest


def _read_snapshot(path: Path, *, expected_id: str | None = None) -> dict:
    require(path.is_dir() and not path.is_symlink(), "snapshot must be a real directory")
    entries = list(path.iterdir())
    require(all(p.is_file() and not p.is_symlink() for p in entries), "invalid file/symlink")
    raw = {p.name: p.read_bytes() for p in entries}
    require("manifest.json" in raw, "missing manifest; snapshot not published")
    manifest = parse_json(raw.pop("manifest.json"))
    validate_id(manifest.get("snapshot_id"))
    require(manifest["snapshot_id"] == (expected_id or path.name), "snapshot directory/ID mismatch")
    expected = make_manifest(
        raw,
        manifest["snapshot_id"],
        manifest["query"]["resultRecordCount"],
        manifest["started_at"],
        manifest["fetched_at"],
    )
    # Rebuilding from raw data validates structure, every field/type, file paths, hashes,
    # protocol completeness and summary consistency. A rehashed false summary still fails.
    require(canonical(manifest) == canonical(expected), "manifest does not match raw transcript")
    return manifest


def verify_snapshot(path: Path) -> dict:
    """No network, writes or trust in complete=true; replay the entire transcript."""
    try:
        return _read_snapshot(Path(path))
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        raise SnapshotError(f"snapshot verification failed: {exc}") from exc


def write_bytes(path: Path, content: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    require(path.read_bytes() == content, f"write readback mismatch: {path.name}")


def publish(parent: Path, snapshot_id: str, raw: dict[str, bytes], manifest: dict) -> Path:
    """Verify in private staging, reserve destination exclusively, manifest last."""
    destination = parent / snapshot_id
    with tempfile.TemporaryDirectory(prefix=".partial-", dir=parent) as temporary:
        staging = Path(temporary)
        for name, value in raw.items():
            write_bytes(staging / name, value)
        write_bytes(staging / "manifest.json", canonical(manifest) + b"\n")
        _read_snapshot(staging, expected_id=snapshot_id)
        # mkdir cannot replace even an existing empty directory or a concurrent writer.
        destination.mkdir()
        try:
            for name in sorted(raw):
                os.link(staging / name, destination / name)
            # Replay final payloads before publishing the manifest as the commit marker.
            require(
                {p.name: p.read_bytes() for p in destination.iterdir()} == raw,
                "publication readback mismatch",
            )
            os.link(staging / "manifest.json", destination / "manifest.json")
            verify_snapshot(destination)
            for path in destination.iterdir():
                path.chmod(0o444)
        except BaseException:
            shutil.rmtree(destination)
            raise
    return destination


def fetch_snapshot(
    repo_root: Path,
    snapshot_id: str,
    page_size: int = 2000,
    attempts: int = 2,
    transport: Transport | None = None,
) -> Path:
    """Fetch only; catalog/domain loaders and synchronization state are not called."""
    validate_id(snapshot_id)
    require(integer(page_size, 1), "page_size must be a positive integer")
    require(integer(attempts, 1) and attempts <= 3, "attempts must be 1..3")
    repo_root = Path(repo_root).resolve()
    parent = repo_root / SNAPSHOTS
    destination = parent / snapshot_id
    require(not destination.exists() and not destination.is_symlink(), "snapshot already exists")
    # Refuse redirected output paths, including a symlink higher in the directory chain.
    require(parent.resolve() == parent, "snapshot parent must not contain symlinks")
    try:
        policy = (repo_root / POLICY).read_bytes()
        for attempt in range(attempts):
            started = timestamp()
            try:
                raw = acquire(transport or http_get, page_size)
                raw["policy.md"] = policy
                size = min(page_size, validate_layer(parse_json(raw["layer.json"])))
                manifest = make_manifest(raw, snapshot_id, size, started, timestamp())
                break
            except (SnapshotError, OSError, TypeError, KeyError, OverflowError) as exc:
                if attempt + 1 == attempts:
                    raise SnapshotError(
                        f"acquisition failed after {attempts} attempt(s): {exc}"
                    ) from exc
                if transport is None:
                    time.sleep(1)
        parent.mkdir(parents=True, exist_ok=True)
        return publish(parent, snapshot_id, raw, manifest)
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        raise SnapshotError(f"snapshot fetch failed: {exc}") from exc
