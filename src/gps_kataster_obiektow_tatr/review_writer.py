"""Recoverable review batches for handled I/O failures (not crash transactions)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import yaml

RECOVERY_DIRECTORY = ".review-recovery"


class ReviewWriteError(Exception):
    """A failed batch, with an explicit distinction for required manual recovery."""

    def __init__(self, description: str, *, recovery_required: bool = False) -> None:
        super().__init__(description)
        self.code = "REVIEW_RECOVERY_REQUIRED" if recovery_required else "REVIEW_WRITE_FAILED"


def check_review_recovery(data_dir: Path) -> None:
    """Refuse to start even a dry-run while recovery evidence remains."""
    recovery = data_dir / RECOVERY_DIRECTORY
    if recovery.exists() or recovery.is_symlink():
        raise ReviewWriteError(
            f"Recovery evidence exists at {recovery}. Stop review and follow "
            "docs/asdlc/staging_review_decisions.md#odzyskiwanie-po-bledzie-zapisu; "
            "do not delete backups or retry decisions before recovery.",
            recovery_required=True,
        )


def write_review_batch(data_dir: Path, records: dict[Path, dict[str, Any]]) -> tuple[Path, ...]:
    """Prepare all bytes and backups, replace files, and roll back handled errors."""
    check_review_recovery(data_dir)
    if not records:
        return ()
    recovery = data_dir / RECOVERY_DIRECTORY
    try:
        # Serialization cannot touch a final file, even when a later record fails.
        serialized = {
            path: yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
            for path, data in records.items()
        }
        data_dir.mkdir(parents=True, exist_ok=True)
        recovery.mkdir()  # Exclusive claim; never remove another operation's evidence.
    except (OSError, yaml.YAMLError, UnicodeError) as exc:
        if recovery.exists():
            check_review_recovery(data_dir)
        raise ReviewWriteError(f"Preparation failed before final writes: {exc}") from exc

    attempted: list[tuple[Path, Path | None]] = []
    entries = []
    try:
        for index, (path, contents) in enumerate(serialized.items()):
            backup = recovery / f"{index}.original"
            staged = recovery / f"{index}.prepared"
            existed = path.exists()
            if existed:
                shutil.copy2(path, backup)
            staged.write_text(contents, encoding="utf-8")
            if existed:
                shutil.copymode(backup, staged)
            entries.append(
                {"path": str(path.relative_to(data_dir)), "original": existed, "index": index}
            )
        # No final changes until the complete recovery map is saved.
        (recovery / "manifest.json").write_text(
            json.dumps({"entries": entries}, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        for entry, path in zip(entries, serialized, strict=True):
            path.parent.mkdir(parents=True, exist_ok=True)
            backup = recovery / f"{entry['index']}.original" if entry["original"] else None
            attempted.append((path, backup))
            (recovery / f"{entry['index']}.prepared").replace(path)
        # This marker differentiates cleanup failure from an incomplete commit.
        (recovery / "committed.tmp").write_text(
            "All final replacements completed.\n", encoding="utf-8"
        )
        (recovery / "committed.tmp").replace(recovery / "COMMITTED")
    except (OSError, UnicodeError) as exc:
        failures = _rollback(attempted, recovery)
        if failures:
            raise ReviewWriteError(
                f"Write failed: {exc}. Rollback incomplete: {'; '.join(failures)}. "
                f"Preserved backups at {recovery}; follow "
                "docs/asdlc/staging_review_decisions.md#odzyskiwanie-po-bledzie-zapisu.",
                recovery_required=True,
            ) from exc
        _cleanup(recovery, "Original bytes restored; new files removed")
        raise ReviewWriteError(f"Write failed; original files restored: {exc}") from exc
    _cleanup(recovery, "All final files committed; do not replay decisions")
    return tuple(records)


def _rollback(attempted: list[tuple[Path, Path | None]], recovery: Path) -> list[str]:
    failures = []
    for path, backup in reversed(attempted):
        try:
            if backup is None:
                path.unlink(missing_ok=True)
            else:
                # Retain backups if restoration itself fails.
                restore = recovery / "restore.tmp"
                shutil.copy2(backup, restore)
                restore.replace(path)
        except OSError as exc:
            failures.append(f"{path}: {exc}")
    return failures


def _cleanup(recovery: Path, state: str) -> None:
    try:
        shutil.rmtree(recovery)
    except OSError as exc:
        raise ReviewWriteError(
            f"{state}. Recovery cleanup failed at {recovery}: {exc}. "
            "Inspect the catalog and follow "
            "docs/asdlc/staging_review_decisions.md#odzyskiwanie-po-bledzie-zapisu "
            "before retrying.",
            recovery_required=True,
        ) from exc
