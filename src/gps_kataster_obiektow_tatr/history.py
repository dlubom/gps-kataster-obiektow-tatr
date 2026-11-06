"""Fail-closed history gate against an actual accepted Git revision."""

from __future__ import annotations

import io
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from gps_kataster_obiektow_tatr.data_loader import (
    CATALOG_FORMAT,
    DATA_DIRECTORIES,
    FORMAT_MARKER,
    LoadedDataset,
    load_yaml_dataset,
)
from gps_kataster_obiektow_tatr.validator import (
    ValidationIssue,
    ValidationSeverity,
    validate_records_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _source(m):
    geometry = (
        (m["input_srid"], m["input_x"], m["input_y"])
        if "input_srid" in m
        else (4326, m.get("lon"), m.get("lat"))
    )
    return geometry, m.get("elevation_m"), m.get("elevation_datum")


def compare_history(baseline: LoadedDataset, dataset: LoadedDataset, *, connection=None):
    """SQL protects source values and append-only order; Git extraction stays read-only."""
    if connection is None:
        from gps_kataster_obiektow_tatr.postgres import _server

        with _server() as (dsn, _), psycopg.connect(dsn, row_factory=dict_row) as owned:
            return compare_history(baseline, dataset, connection=owned)

    def payload(source):
        return Jsonb(
            [
                {
                    "id": r.data["id"],
                    "path": str(r.path),
                    "measurements": [
                        {"id": m["id"], "source": _source(m)} for m in r.data["measurements"]
                    ],
                }
                for r in source.objects
            ]
        )

    rows = connection.execute(
        (REPO_ROOT / "schema/history.sql").read_text(encoding="utf-8"),
        (payload(baseline), payload(dataset)),
    ).fetchall()
    return tuple(
        ValidationIssue(
            row["code"], ValidationSeverity.ERROR, Path(row["path"]), row["description"]
        )
        for row in rows
    )


def _validate_history_objects(dataset: LoadedDataset) -> LoadedDataset:
    """Check that history extraction is complete and unambiguous before comparison.

    These are extraction invariants, not a second production domain validator.
    The comparison uses source values from the accepted Git blobs.
    """
    object_ids = set()
    for record in dataset.objects:
        obj = record.data
        oid = obj.get("id")
        if not isinstance(oid, str) or not re.fullmatch(r"[A-Z]{2,3}-[0-9]{4,}", oid):
            raise ValueError("Invalid baseline object identity")
        if oid in object_ids or record.path.stem != oid:
            raise ValueError("Ambiguous baseline object identity")
        object_ids.add(oid)
        measurements = obj.get("measurements")
        if not isinstance(measurements, list) or not measurements:
            raise ValueError(f"Incomplete measurement history for {oid}")
        ids = set()
        for m in measurements:
            if not isinstance(m, dict):
                raise ValueError(f"Incomplete measurement in {oid}")
            mid = m.get("id")
            if not isinstance(mid, str) or not re.fullmatch(r"m-[0-9]{3,}", mid) or mid in ids:
                raise ValueError(f"Ambiguous baseline measurement identity in {oid}")
            ids.add(mid)
            native = any(k in m for k in ("input_srid", "input_x", "input_y"))
            keys = ("input_srid", "input_x", "input_y") if native else ("lat", "lon")
            if any(k not in m for k in keys):
                raise ValueError(f"Incomplete source geometry for {oid}/{mid}")
            if native and (type(m["input_srid"]) is not int or m["input_srid"] not in (4326, 2180)):
                raise ValueError(f"Unsupported source geometry for {oid}/{mid}")
            for key in (*keys, "elevation_m"):
                value = m.get(key)
                if value is None and key == "elevation_m":
                    continue
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                ):
                    raise ValueError(f"Invalid source {key} for {oid}/{mid}")
            if m.get("elevation_datum") is not None and not isinstance(m["elevation_datum"], str):
                raise ValueError(f"Invalid elevation datum for {oid}/{mid}")
        assignment = obj.get("id_assignment", {})
        best = obj.get("best_measurement", {})
        if assignment.get("assigned_from_measurement_id") not in ids or best.get("mode") not in (
            "auto",
            "manual",
        ):
            raise ValueError(f"Incomplete baseline object measurement links for {oid}")
        if best["mode"] == "manual" and best.get("measurement_id") not in ids:
            raise ValueError(f"Incomplete baseline Best policy for {oid}")
    return dataset


def _git_baseline(base_ref: str, repo_root: Path, data_path: str) -> LoadedDataset:
    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo_root), *args], stderr=subprocess.PIPE)

    sha = (
        git("rev-parse", "--verify", "--end-of-options", f"{base_ref}^{{commit}}").decode().strip()
    )
    if git("cat-file", "-t", f"{sha}:{data_path}").strip() != b"tree":
        raise ValueError(f"No baseline catalogue tree at {base_ref}:{data_path}")
    paths = git("ls-tree", "-r", "--name-only", "-z", sha, "--", data_path).decode().split("\0")
    paths = [
        p
        for p in paths
        if p
        and (
            Path(p).relative_to(data_path).parts[0] in DATA_DIRECTORIES
            or Path(p).relative_to(data_path).name == "catalog.json"
        )
    ]
    if any("\n" in p or "\r" in p for p in paths):
        raise ValueError("Unsupported control character in baseline path")
    if not paths:
        raise ValueError(f"No baseline catalogue at {base_ref}:{data_path}")
    # One Git batch reads immutable blobs; no checkout or candidate-generated baseline.
    batch = subprocess.run(
        ["git", "-C", str(repo_root), "cat-file", "--batch"],
        input="".join(f"{sha}:{p}\n" for p in paths).encode(),
        capture_output=True,
        check=True,
    )
    blobs = io.BytesIO(batch.stdout)
    with tempfile.TemporaryDirectory(prefix="kataster-history-") as directory:
        root = Path(directory)
        for path in paths:
            header = blobs.readline().split()
            if len(header) != 3 or header[1] != b"blob":
                raise ValueError("Baseline contains an unreadable blob")
            size = int(header[2])
            content = blobs.read(size)
            if len(content) != size or blobs.read(1) != b"\n":
                raise ValueError("Incomplete Git baseline blob")
            relative = Path(path).relative_to(data_path)
            if ".." in relative.parts:
                raise ValueError("Unsafe baseline path")
            target = root / relative
            # Preserve only directories evidenced by accepted Git paths, including assets.
            target.parent.mkdir(parents=True, exist_ok=True)
            if (
                len(relative.parts) > 1
                and relative.suffix not in (".sql", ".yml", ".yaml")
                and relative.name not in (FORMAT_MARKER, ".gitkeep")
            ):
                continue
            # A top-level entity path may itself be a file: the shared guard must see it.
            target.write_bytes(content)
        baseline = load_yaml_dataset(root)
        marker = root / FORMAT_MARKER
        if marker.exists():
            if json.loads(marker.read_text(encoding="utf-8")) != CATALOG_FORMAT:
                raise ValueError("Unsupported YAML baseline format")
        else:
            if issues := validate_records_schema(baseline.records()):
                raise ValueError(f"Incomplete legacy baseline record: {issues[0].path.name}")
        return _validate_history_objects(baseline)


def check_history(
    base_ref: str,
    dataset: LoadedDataset,
    *,
    repo_root: Path = REPO_ROOT,
    data_path: str = "data",
    connection=None,
) -> tuple[ValidationIssue, ...]:
    """Compare with Git, never candidate-generated baselines; unavailable ref blocks."""
    try:
        baseline = _git_baseline(base_ref, repo_root, data_path)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        return (
            ValidationIssue(
                "HISTORY_BASELINE_UNAVAILABLE",
                ValidationSeverity.ERROR,
                None,
                f"Cannot read accepted Git baseline {base_ref!r}: {exc}",
            ),
        )
    return compare_history(baseline, dataset, connection=connection)
