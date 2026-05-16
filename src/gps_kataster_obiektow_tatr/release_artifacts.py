"""Build the release artifact set from source-of-truth YAML records."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

from gps_kataster_obiektow_tatr.best_measurements_export import (
    DEFAULT_EXPORT_DIR,
    BestMeasurementsExportResult,
    export_best_measurements,
)
from gps_kataster_obiektow_tatr.build_db import (
    DEFAULT_SQLITE_PATH,
    BuildDatabaseResult,
    build_sqlite_database,
)
from gps_kataster_obiektow_tatr.data_loader import DEFAULT_DATA_DIR
from gps_kataster_obiektow_tatr.validator import ValidationIssue

SQLITE_ZIP_FILENAME = "katalog.sqlite.zip"


@dataclass(frozen=True, slots=True)
class ReleaseArtifactsResult:
    """Summary of a completed release artifact build."""

    sqlite_result: BuildDatabaseResult
    export_result: BestMeasurementsExportResult
    sqlite_zip_path: Path

    @property
    def artifact_paths(self) -> tuple[Path, ...]:
        """Return all generated artifact paths in release upload order."""

        return (
            self.sqlite_result.sqlite_path,
            self.export_result.geojson_path,
            self.export_result.csv_path,
            self.export_result.gpx_path,
            self.export_result.shapefile_zip_path,
            self.sqlite_zip_path,
            self.export_result.metadata_path,
        )

    @property
    def validation_issues(self) -> tuple[ValidationIssue, ...]:
        """Return validation issues captured by the export pass."""

        return self.export_result.validation_issues


def build_release_artifacts(
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    sqlite_path: Path = DEFAULT_SQLITE_PATH,
    output_dir: Path = DEFAULT_EXPORT_DIR,
    generated_at: str | None = None,
) -> ReleaseArtifactsResult:
    """Build SQLite, export best measurements and zip the SQLite snapshot."""

    sqlite_result = build_sqlite_database(
        data_dir=data_dir,
        output_path=sqlite_path,
        generated_at=generated_at,
    )
    export_result = export_best_measurements(
        data_dir=data_dir,
        output_dir=output_dir,
        generated_at=generated_at,
    )
    sqlite_zip_path = output_dir / SQLITE_ZIP_FILENAME
    _write_sqlite_zip(sqlite_result.sqlite_path, sqlite_zip_path)

    return ReleaseArtifactsResult(
        sqlite_result=sqlite_result,
        export_result=export_result,
        sqlite_zip_path=sqlite_zip_path,
    )


def _write_sqlite_zip(sqlite_path: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = zip_path.with_name(f"{zip_path.name}.tmp")
    if tmp_path.exists():
        tmp_path.unlink()

    try:
        with zipfile.ZipFile(tmp_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(sqlite_path, arcname=sqlite_path.name)
        tmp_path.replace(zip_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
