"""Protect the accepted YAML measurement history against edits and deletion."""

from __future__ import annotations

import io
import os
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

from gps_kataster_obiektow_tatr.data_loader import REPO_ROOT, LoadedDataset
from gps_kataster_obiektow_tatr.models import Measurement
from gps_kataster_obiektow_tatr.validator import ValidationIssue, ValidationSeverity
from gps_kataster_obiektow_tatr.yaml_io import load_unique_yaml_text

DEFAULT_BASE_REF = "origin/main"
_REVIEW_METADATA = frozenset({"tags", "verification_status", "verified_by", "verified_at", "notes"})
type _History = dict[str, tuple[Path, list[dict[str, Any]]]]


def check_measurement_history(
    dataset: LoadedDataset,
    *,
    repo_root: Path = REPO_ROOT,
    base_ref: str = DEFAULT_BASE_REF,
) -> tuple[ValidationIssue, ...]:
    """Require every accepted object's raw history to remain a prefix.

    The caller supplies a trusted accepted commit SHA or uses the remote-tracking
    main branch. The commit must exist and be an ancestor of the checkout.
    """
    try:
        baseline = _load_baseline(repo_root, base_ref)
    except (OSError, ValueError) as exc:
        return (
            _issue(
                "HISTORY_BASELINE_UNAVAILABLE",
                None,
                f"Cannot read accepted Git baseline {base_ref!r}: {exc}",
            ),
        )

    try:
        candidate = _index_history((record.path, record.raw_data) for record in dataset.objects)
    except ValueError as exc:
        return (_issue("MEASUREMENT_HISTORY_INVALID", None, str(exc)),)

    issues = []
    for object_id, (base_path, accepted) in baseline.items():
        if object_id not in candidate:
            issues.append(
                _issue(
                    "MEASUREMENT_HISTORY_OBJECT_REMOVED",
                    base_path,
                    f"{object_id}: object with accepted measurement history is missing",
                )
            )
            continue

        path, current = candidate[object_id]
        accepted_ids = [m["id"] for m in accepted]
        current_prefix = [m["id"] for m in current[: len(accepted)]]
        if accepted_ids != current_prefix:
            issues.append(
                _issue(
                    "MEASUREMENT_HISTORY_PREFIX_CHANGED",
                    path,
                    f"{object_id}: expected accepted measurement order {accepted_ids!r}, "
                    f"got {current_prefix!r}; append new measurements at the end",
                )
            )
            continue

        for before, after in zip(accepted, current, strict=False):
            changed_fields = sorted(
                field
                for field in (before.keys() | after.keys()) - _REVIEW_METADATA
                if field not in before
                or field not in after
                or type(before[field]) is not type(after[field])
                or before[field] != after[field]
            )
            if changed_fields:
                issues.append(
                    _issue(
                        "MEASUREMENT_HISTORY_CHANGED",
                        path,
                        f"{object_id}/{before['id']}: changed accepted fields "
                        f"{', '.join(changed_fields)}; append a new measurement for corrections",
                    )
                )
    return tuple(issues)


def _issue(code: str, path: Path | None, description: str) -> ValidationIssue:
    return ValidationIssue(code, ValidationSeverity.ERROR, path, description)


def _git(repo_root: Path, *args: str, stdin: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", "--no-replace-objects", "-C", str(repo_root), *args],
        input=stdin,
        check=False,
        capture_output=True,
    )
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip()
        raise ValueError(f"git {args[0]} failed: {detail or f'exit {result.returncode}'}")
    return result.stdout


def _accepted_commit(repo_root: Path, base_ref: str) -> str:
    if base_ref != DEFAULT_BASE_REF and not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", base_ref):
        raise ValueError(f"specify {DEFAULT_BASE_REF} or a full accepted Git commit SHA")
    if _git(repo_root, "rev-parse", "--show-prefix").strip():
        raise ValueError("repo_root must point to the Git worktree root")
    revision = f"refs/remotes/{base_ref}" if base_ref == DEFAULT_BASE_REF else base_ref
    commit = (
        _git(repo_root, "rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}")
        .decode("ascii")
        .strip()
    )
    head = _git(repo_root, "rev-parse", "--verify", "HEAD").decode("ascii").strip()
    if base_ref != DEFAULT_BASE_REF and head == commit:
        accepted_main = _git(repo_root, "rev-parse", "--verify", "refs/remotes/origin/main")
        if accepted_main.decode("ascii").strip() != commit:
            raise ValueError("the candidate HEAD is not the accepted main commit")
    try:
        _git(repo_root, "merge-base", "--is-ancestor", commit, head)
    except ValueError as exc:
        raise ValueError(f"cannot prove {commit} is an ancestor of the checkout: {exc}") from exc
    return commit


def _load_baseline(repo_root: Path, base_ref: str) -> _History:
    commit = _accepted_commit(repo_root, base_ref)
    entries = _git(repo_root, "ls-tree", "-r", "-z", commit, "--", "data/objects").split(b"\0")
    blobs = []
    for entry in filter(None, entries):
        info, name = entry.split(b"\t", 1)
        mode, kind, oid = info.split()
        path = repo_root / os.fsdecode(name)
        if mode not in {b"100644", b"100755"} or kind != b"blob":
            raise ValueError(f"{path}: baseline object tree must contain regular files")
        if path.suffix in {".yml", ".yaml"}:
            blobs.append((path, oid))
    if not blobs:
        raise ValueError("accepted commit contains no YAML object history under data/objects")

    batch = io.BytesIO(
        _git(
            repo_root,
            "cat-file",
            "--batch",
            stdin=b"".join(oid + b"\n" for _, oid in blobs),
        )
    )
    records = []
    for path, oid in blobs:
        header = batch.readline().split()
        if len(header) != 3 or header[:2] != [oid, b"blob"]:
            raise ValueError(f"{path}: unreadable baseline blob")
        size = int(header[2])
        content = batch.read(size)
        if len(content) != size or batch.read(1) != b"\n":
            raise ValueError(f"{path}: incomplete baseline blob")
        try:
            records.append((path, load_unique_yaml_text(content.decode("utf-8"))))
        except (yaml.YAMLError, UnicodeError, RecursionError) as exc:
            raise ValueError(f"{path}: invalid baseline YAML: {exc}") from exc
    return _index_history(records, baseline=True)


def _index_history(records: Iterable[tuple[Path, Any]], *, baseline: bool = False) -> _History:
    history: _History = {}
    for path, record in records:
        if not isinstance(record, dict):
            raise ValueError(f"{path}: object record must be a mapping")
        object_id = record.get("id")
        if not isinstance(object_id, str) or object_id != path.stem or object_id in history:
            raise ValueError(f"{path}: missing, conflicting or duplicate object ID {object_id!r}")
        measurements = record.get("measurements")
        if not isinstance(measurements, list) or not measurements:
            raise ValueError(f"{path}: {object_id} has no usable measurement history")
        ids = set()
        for measurement in measurements:
            if not isinstance(measurement, dict):
                raise ValueError(f"{path}: {object_id} measurement must be a mapping")
            measurement_id = measurement.get("id")
            if not isinstance(measurement_id, str) or not measurement_id or measurement_id in ids:
                raise ValueError(
                    f"{path}: {object_id} has invalid measurement ID {measurement_id!r}"
                )
            ids.add(measurement_id)
            if not all(isinstance(key, str) for key in measurement):
                raise ValueError(f"{path}: {object_id}/{measurement_id} has a non-string field")
            if baseline:
                Measurement.model_validate(measurement)
        history[object_id] = path, measurements
    return history
