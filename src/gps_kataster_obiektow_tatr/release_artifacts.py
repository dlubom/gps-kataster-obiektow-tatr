"""Atomically publish all thirteen artifacts from one validated PostgreSQL state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gps_kataster_obiektow_tatr.best_measurements_export import (
    DEFAULT_EXPORT_DIR,
    BestMeasurementsExportResult,
    relocate_export_result,
    write_best_measurements,
)
from gps_kataster_obiektow_tatr.build_db import (
    REPO_ROOT,
    check_artifact_set,
    staged_artifact_directory,
)
from gps_kataster_obiektow_tatr.data_loader import DEFAULT_DATA_DIR, require_data_directory
from gps_kataster_obiektow_tatr.excel_export import write_excel_export
from gps_kataster_obiektow_tatr.export_data import prepare_export_data
from gps_kataster_obiektow_tatr.geopackage import write_geopackage
from gps_kataster_obiektow_tatr.postgres import verify_dump
from gps_kataster_obiektow_tatr.release_statistics import write_release_statistics
from gps_kataster_obiektow_tatr.validator import history_checked_catalog

RELEASE_ONLY_FILENAMES = (
    "katalog.dump",
    "katalog.gpkg",
    "statistics.json",
    "statistics.md",
    "katalog.xlsx",
)


@dataclass(frozen=True, slots=True)
class ReleaseArtifactsResult:
    dump_path: Path
    geopackage_path: Path
    export_result: BestMeasurementsExportResult
    statistics_paths: tuple[Path, Path]
    excel_path: Path

    @property
    def artifact_paths(self):
        return (
            self.dump_path,
            self.geopackage_path,
            *self.export_result.artifact_paths,
            *self.statistics_paths,
            self.excel_path,
        )

    @property
    def validation_issues(self):
        return self.export_result.validation_issues


def build_release_artifacts(
    *,
    data_dir=DEFAULT_DATA_DIR,
    output_dir=DEFAULT_EXPORT_DIR,
    generated_at=None,
    release_version=None,
    source_commit=None,
    base_ref="origin/main",
    history_repo=REPO_ROOT,
):
    output_dir = Path(output_dir)
    if output_dir.is_symlink() or (output_dir.exists() and not output_dir.is_dir()):
        raise ValueError("Artifact destination must be a real directory, never a symlink")
    require_data_directory(Path(data_dir))
    with (
        history_checked_catalog(data_dir, base_ref=base_ref, history_repo=history_repo) as (
            catalog,
            dataset,
            issues,
        ),
        staged_artifact_directory(
            output_dir, data_dir=data_dir, history_repo=history_repo
        ) as stage,
    ):
        export_data = prepare_export_data(dataset, generated_at=generated_at)
        result = write_best_measurements(export_data, output_dir=stage, validation_issues=issues)
        dump, geopackage, *statistics, excel = (stage / name for name in RELEASE_ONLY_FILENAMES)
        catalog.dump(dump)
        verify_dump(catalog, dump)
        write_geopackage(export_data, geopackage)
        write_release_statistics(
            export_data,
            output_dir=stage,
            release_version=release_version,
            source_commit=source_commit,
        )
        write_excel_export(
            export_data,
            output_path=excel,
            release_version=release_version,
            source_commit=source_commit,
        )
        staged_result = ReleaseArtifactsResult(dump, geopackage, result, tuple(statistics), excel)
        check_artifact_set(stage, staged_result.artifact_paths)
    result = relocate_export_result(result, output_dir)
    return ReleaseArtifactsResult(
        output_dir / dump.name,
        output_dir / geopackage.name,
        result,
        tuple(output_dir / p.name for p in statistics),
        output_dir / excel.name,
    )
