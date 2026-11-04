"""Publish complete artifact sets while preserving prior files on write errors."""

from __future__ import annotations

from pathlib import Path
from shutil import copy2, rmtree
from tempfile import mkdtemp


def publish_artifacts(sources: tuple[Path, ...], destinations: tuple[Path, ...]) -> None:
    """Prepare replacements before writing and roll back a failed publication."""

    targets = tuple(path.parent.resolve() / path.name for path in destinations)
    if len(set(targets)) != len(targets) or any(
        target in other.parents for target in targets for other in targets
    ):
        raise ValueError("Artifact destinations overlap.")
    for target in targets:
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise OSError(f"Artifact destination is not a regular file: {target}")

    work_dirs: dict[Path, Path] = {}
    pending: list[tuple[Path, Path, Path | None]] = []
    published: list[tuple[Path, Path | None]] = []
    retained: set[Path] = set()
    try:
        for index, (source, target) in enumerate(zip(sources, targets, strict=True)):
            parent = target.parent
            if parent not in work_dirs:
                parent.mkdir(parents=True, exist_ok=True)
                # A replacement and its backup must be on the destination filesystem.
                work_dirs[parent] = Path(mkdtemp(prefix=".kataster-publish-", dir=parent))
            work_dir = work_dirs[parent]
            replacement = work_dir / f"{index}.new"
            copy2(source, replacement)
            backup = None
            if target.exists():
                backup = work_dir / f"{index}.old"
                copy2(target, backup)
            pending.append((replacement, target, backup))

        for replacement, target, backup in pending:
            replacement.replace(target)
            published.append((target, backup))
    except BaseException as publication_error:
        rollback_errors = []
        for target, backup in reversed(published):
            try:
                if backup is None:
                    target.unlink()
                else:
                    backup.replace(target)
            except OSError as exc:
                if backup is not None:
                    retained.add(backup.parent)
                    exc.add_note(f"Previous artifact is recoverable at {backup}")
                rollback_errors.append(exc)
        if rollback_errors:
            raise BaseExceptionGroup(
                "Artifact publication and rollback both failed",
                [publication_error, *rollback_errors],
            ) from None
        raise
    finally:
        for directory in work_dirs.values():
            if directory not in retained:
                rmtree(directory, ignore_errors=True)
