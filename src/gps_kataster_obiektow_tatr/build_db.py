"""Validate one PostgreSQL catalogue and publish its verified portable dump."""

from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from gps_kataster_obiektow_tatr.data_loader import DEFAULT_DATA_DIR, require_data_directory
from gps_kataster_obiektow_tatr.postgres import verify_dump
from gps_kataster_obiektow_tatr.report_formatting import utc_timestamp
from gps_kataster_obiektow_tatr.validator import (
    ValidationIssue,
    history_checked_catalog,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DUMP_PATH = REPO_ROOT / "build" / "katalog.dump"


@dataclass(frozen=True, slots=True)
class BuildDatabaseResult:
    dump_path: Path
    metadata: dict[str, str]
    validation_issues: tuple[ValidationIssue, ...]


def build_database(
    *,
    data_dir=DEFAULT_DATA_DIR,
    output_path=DEFAULT_DUMP_PATH,
    generated_at=None,
    base_ref="origin/main",
    history_repo=REPO_ROOT,
):
    require_data_directory(Path(data_dir))
    with history_checked_catalog(data_dir, base_ref=base_ref, history_repo=history_repo) as (
        catalog,
        dataset,
        issues,
    ):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".dump-", dir=output_path.parent) as temporary:
            staged = Path(temporary) / output_path.name
            catalog.dump(staged)
            verify_dump(catalog, staged)
            staged.replace(output_path)
        return BuildDatabaseResult(
            output_path,
            _build_metadata(
                dataset, generated_at=generated_at or utc_timestamp(), validation_issues=issues
            ),
            issues,
        )


def _build_metadata(dataset, *, generated_at, validation_issues):
    return {
        "generated_at": generated_at,
        "schema_version": "2",
        "object_count": str(len(dataset.objects)),
        "cave_count": str(len(dataset.caves)),
        "relation_count": str(len(dataset.relations)),
        "measurement_count": str(sum(len(r.data["measurements"]) for r in dataset.objects)),
        "validation_warning_count": str(sum(i.severity == "warning" for i in validation_issues)),
        "validation_error_count": str(sum(i.severity == "error" for i in validation_issues)),
    }


@contextmanager
def staged_artifact_directory(
    output_dir: Path, *, data_dir=DEFAULT_DATA_DIR, history_repo=REPO_ROOT
):
    """Commit a whole directory with one atomic exchange, only after all writers pass."""
    from gps_kataster_obiektow_tatr.catalog_records import _exchange_directories

    output_dir = Path(output_dir)
    _check_artifact_destination(output_dir, Path(data_dir), Path(history_repo))
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".exports-", dir=output_dir.parent))
    try:
        yield stage
        _check_artifact_destination(output_dir, Path(data_dir), Path(history_repo))
        if output_dir.exists():
            names = {p.name for p in stage.iterdir()}
            if any(
                p.name not in names or p.is_symlink() or not p.is_file()
                for p in output_dir.iterdir()
            ):
                raise ValueError(
                    "Artifact destination contains unmanaged entries; choose another directory"
                )
            _exchange_directories(stage, output_dir)
        else:
            stage.rename(output_dir)
    finally:
        # After commit this is the old directory; cleanup must not misreport publication.
        shutil.rmtree(stage, ignore_errors=True)


def _check_artifact_destination(output_dir: Path, data_dir: Path, history_repo: Path) -> None:
    destination, source = output_dir.resolve(), data_dir.resolve()
    if (
        destination.is_relative_to(source)
        or source.is_relative_to(destination)
        or any(root.resolve().is_relative_to(destination) for root in (REPO_ROOT, history_repo))
        or ".git" in output_dir.parts
        or ".git" in destination.parts
    ):
        raise ValueError("Artifact destination overlaps source data or a Git repository")
    if output_dir.is_symlink() or (output_dir.exists() and not output_dir.is_dir()):
        raise ValueError("Artifact destination must be a real directory, never a symlink")


def check_artifact_set(output_dir: Path, paths: tuple[Path, ...]) -> None:
    """Reject missing, extra, repeated or non-local files before publication."""
    if (
        len(set(paths)) != len(paths)
        or any(p.parent != output_dir or p.is_symlink() or not p.is_file() for p in paths)
        or set(output_dir.iterdir()) != set(paths)
    ):
        raise ValueError("Output directory differs from the expected artifact set")
