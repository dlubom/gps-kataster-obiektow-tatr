"""Export selected best measurements to release-friendly formats."""

from __future__ import annotations

import csv
import json
import tempfile
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import shapefile

from gps_kataster_obiektow_tatr.data_loader import DEFAULT_DATA_DIR, require_data_directory
from gps_kataster_obiektow_tatr.export_data import (
    BEST_FIELDS,
    BestMeasurementExportRow,
    ExportData,
    prepare_export_data,
)
from gps_kataster_obiektow_tatr.validator import (
    ValidationIssue,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXPORT_DIR = REPO_ROOT / "build" / "exports"
GEOJSON_FILENAME = "best-measurements.geojson"
CSV_FILENAME = "best-measurements.csv"
GPX_FILENAME = "best-measurements.gpx"
GPX_GROUP_LIMIT = 500
GPX_GROUPS = (
    (
        "chocholowska-lejowa-koscieliska.gpx",
        "Chochołowska — Lejowa — Kościeliska",
        frozenset({"CHZ", "CHW", "LEJ", "KSZ", "KSW"}),
    ),
    (
        "mietusia-sucha-woda.gpx",
        "Od Miętusiej po Suchą Wodę",
        frozenset(
            {
                "MTZ",
                "MTW",
                "STN",
                "MLZ",
                "MLW",
                "BRA",
                "STR",
                "DZI",
                "BIA",
                "BYZ",
                "BYW",
                "OLC",
                "SUW",
            }
        ),
    ),
    ("pozostale-pl-sk.gpx", "Pozostałe PL/SK poza regionami dolin", frozenset({"PL", "SK"})),
)
SHAPEFILE_ZIP_FILENAME = "best-measurements.shp.zip"
METADATA_FILENAME = "metadata.json"
RELEASE_METADATA_SCHEMA_VERSION = 1
DATA_SCHEMA_VERSION = 1
GPX_NS = "http://www.topografix.com/GPX/1/1"
EPSG_2180_PRJ = (
    'PROJCS["ETRF2000-PL_CS92",'
    'GEOGCS["GCS_ETRS_1989",'
    'DATUM["D_ETRS_1989",'
    'SPHEROID["GRS_1980",6378137.0,298.257222101]],'
    'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],'
    'PROJECTION["Transverse_Mercator"],'
    'PARAMETER["False_Easting",500000.0],'
    'PARAMETER["False_Northing",-5300000.0],'
    'PARAMETER["Central_Meridian",19.0],'
    'PARAMETER["Scale_Factor",0.9993],'
    'PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'
)


@dataclass(frozen=True, slots=True)
class BestMeasurementsExportResult:
    """Summary of a completed best-measurements export."""

    output_dir: Path
    geojson_path: Path
    csv_path: Path
    gpx_path: Path
    grouped_gpx_paths: tuple[Path, ...]
    shapefile_zip_path: Path
    metadata_path: Path
    metadata: dict[str, Any]
    feature_count: int
    validation_issues: tuple[ValidationIssue, ...]

    @property
    def artifact_paths(self) -> tuple[Path, ...]:
        return (
            self.geojson_path,
            self.csv_path,
            self.gpx_path,
            *self.grouped_gpx_paths,
            self.shapefile_zip_path,
            self.metadata_path,
        )


class GpxGroupingError(ValueError):
    """Raised before export writes when a regional GPX cannot meet its contract."""


def export_best_measurements(
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    output_dir: Path = DEFAULT_EXPORT_DIR,
    generated_at: str | None = None,
    base_ref: str = "origin/main",
    history_repo: Path = REPO_ROOT,
) -> BestMeasurementsExportResult:
    """Validate one SQL catalogue and atomically export selected measurements."""

    from gps_kataster_obiektow_tatr.build_db import check_artifact_set, staged_artifact_directory
    from gps_kataster_obiektow_tatr.release_artifacts import RELEASE_ONLY_FILENAMES
    from gps_kataster_obiektow_tatr.validator import history_checked_catalog

    output_dir = Path(output_dir)
    require_data_directory(Path(data_dir))
    with history_checked_catalog(data_dir, base_ref=base_ref, history_repo=history_repo) as (
        _,
        dataset,
        issues,
    ):
        if any(
            (output_dir / name).exists() or (output_dir / name).is_symlink()
            for name in RELEASE_ONLY_FILENAMES
        ):
            raise ValueError(
                "Destination contains full release artifacts; "
                "use scripts/build_release_artifacts.py "
                "to rebuild the complete package or choose another --output-dir."
            )
        with staged_artifact_directory(
            output_dir, data_dir=data_dir, history_repo=history_repo
        ) as stage:
            result = write_best_measurements(
                prepare_export_data(dataset, generated_at=generated_at),
                output_dir=stage,
                validation_issues=issues,
            )
            check_artifact_set(stage, result.artifact_paths)
        return relocate_export_result(result, output_dir)


def relocate_export_result(result, output_dir):
    return replace(
        result,
        output_dir=output_dir,
        **{
            key: output_dir / getattr(result, key).name
            for key in (
                "geojson_path",
                "csv_path",
                "gpx_path",
                "shapefile_zip_path",
                "metadata_path",
            )
        },
        grouped_gpx_paths=tuple(output_dir / p.name for p in result.grouped_gpx_paths),
    )


def write_best_measurements(
    export_data: ExportData, *, output_dir: Path, validation_issues=()
) -> BestMeasurementsExportResult:
    """Format the already validated SQL read model; never reload or choose Best."""
    rows = export_data.best
    groups = _group_gpx_rows(export_data)
    timestamp = export_data.generated_at

    output_dir.mkdir(parents=True, exist_ok=True)
    geojson_path = output_dir / GEOJSON_FILENAME
    csv_path = output_dir / CSV_FILENAME
    gpx_path = output_dir / GPX_FILENAME
    grouped_gpx_paths = tuple(output_dir / filename for filename, _, _ in GPX_GROUPS)
    shapefile_zip_path = output_dir / SHAPEFILE_ZIP_FILENAME
    metadata_path = output_dir / METADATA_FILENAME
    metadata = _build_release_metadata(
        export_data,
        generated_at=timestamp,
        validation_issues=validation_issues,
    )

    _write_geojson(rows, geojson_path, generated_at=timestamp)
    _write_csv(rows, csv_path)
    _write_gpx(rows, gpx_path, generated_at=timestamp)
    for path, (_, name, _), group_rows in zip(grouped_gpx_paths, GPX_GROUPS, groups, strict=True):
        _write_gpx(group_rows, path, generated_at=timestamp, name=name)
    _write_shapefile_zip(rows, shapefile_zip_path)
    _write_metadata(metadata, metadata_path)

    return BestMeasurementsExportResult(
        output_dir=output_dir,
        geojson_path=geojson_path,
        csv_path=csv_path,
        gpx_path=gpx_path,
        grouped_gpx_paths=grouped_gpx_paths,
        shapefile_zip_path=shapefile_zip_path,
        metadata_path=metadata_path,
        metadata=metadata,
        feature_count=len(rows),
        validation_issues=validation_issues,
    )


def _group_gpx_rows(
    export_data: ExportData,
) -> tuple[tuple[BestMeasurementExportRow, ...], ...]:
    """Keep whole valleys together using the selected measurement's SQL region."""

    groups: list[list[BestMeasurementExportRow]] = [[] for _ in GPX_GROUPS]
    group_by_region = {
        region: index for index, (_, _, regions) in enumerate(GPX_GROUPS) for region in regions
    }
    for row in export_data.best:
        region = export_data.gpx_regions.get(row.object_id)
        if region not in group_by_region:
            raise GpxGroupingError(
                f"GPX group missing for object {row.object_id}: region {region!r}"
            )
        groups[group_by_region[region]].append(row)
    for (filename, _, _), group in zip(GPX_GROUPS, groups, strict=True):
        if len(group) > GPX_GROUP_LIMIT:
            raise GpxGroupingError(
                f"GPX group {filename}: {len(group)} waypoints exceeds limit {GPX_GROUP_LIMIT}; "
                "revise the valley groups before exporting."
            )
    return tuple(tuple(group) for group in groups)


def _write_geojson(
    rows: tuple[BestMeasurementExportRow, ...],
    path: Path,
    *,
    generated_at: str,
) -> None:
    payload = {
        "type": "FeatureCollection",
        "name": "best-measurements",
        "generated_at": generated_at,
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": [
            {
                "type": "Feature",
                "id": row.object_id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [row.lon, row.lat],
                },
                "properties": _row_properties(row),
            }
            for row in rows
        ],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_csv(rows: tuple[BestMeasurementExportRow, ...], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=BEST_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(value) for key, value in _row_properties(row).items()})


def _write_gpx(
    rows: tuple[BestMeasurementExportRow, ...],
    path: Path,
    *,
    generated_at: str,
    name: str = "gps-kataster-obiektow-tatr best measurements",
) -> None:
    ET.register_namespace("", GPX_NS)
    gpx = ET.Element(_gpx_tag("gpx"), {"version": "1.1", "creator": "gps-kataster-obiektow-tatr"})
    metadata = ET.SubElement(gpx, _gpx_tag("metadata"))
    ET.SubElement(metadata, _gpx_tag("name")).text = name
    ET.SubElement(metadata, _gpx_tag("time")).text = generated_at

    for row in rows:
        waypoint = ET.SubElement(
            gpx,
            _gpx_tag("wpt"),
            {"lat": _float_text(row.lat), "lon": _float_text(row.lon)},
        )
        if row.elevation_m is not None:
            ET.SubElement(waypoint, _gpx_tag("ele")).text = _float_text(row.elevation_m)
        if row.observed_at is not None:
            ET.SubElement(waypoint, _gpx_tag("time")).text = row.observed_at
        ET.SubElement(waypoint, _gpx_tag("name")).text = (
            row.name_local if row.name_local and row.name_local.strip() else row.object_id
        )
        ET.SubElement(waypoint, _gpx_tag("desc")).text = _gpx_description(row)
        ET.SubElement(waypoint, _gpx_tag("type")).text = row.category

    tree = ET.ElementTree(gpx)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def _write_shapefile_zip(rows: tuple[BestMeasurementExportRow, ...], path: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        base_path = tmp_dir / "best-measurements"
        writer = shapefile.Writer(str(base_path), shapeType=shapefile.POINT)
        try:
            _define_shapefile_fields(writer)
            for row in rows:
                writer.point(row.y_1992, row.x_1992)
                writer.record(
                    row.object_id,
                    _text_or_empty(row.name_local),
                    row.category,
                    _text_or_empty(row.cave_id),
                    row.measurement_id,
                    row.lat,
                    row.lon,
                    row.x_1992,
                    row.y_1992,
                    row.elevation_m,
                    row.source,
                    _text_or_empty(row.nr_inwent),
                    _text_or_empty(row.pig_id),
                    _text_or_empty(row.pig_url),
                    _text_or_empty(row.tpn_globalid),
                    row.observed_date,
                    row.verification_status,
                    _truncated_text(row.object_notes, max_length=254),
                    _truncated_text(row.cave_notes, max_length=254),
                    _truncated_text(row.measurement_notes, max_length=254),
                    row.cave_length_m,
                    row.cave_depth_m,
                    row.cave_denivelation_m,
                    _text_or_empty(row.cave_denivelation_qualifier),
                    _truncated_text(row.cave_morphometry_source_ref, max_length=254),
                )
        finally:
            writer.close()

        (tmp_dir / "best-measurements.prj").write_text(EPSG_2180_PRJ, encoding="ascii")
        (tmp_dir / "best-measurements.cpg").write_text("UTF-8\n", encoding="ascii")

        with zipfile.ZipFile(path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
                file_path = tmp_dir / f"best-measurements{suffix}"
                archive.write(file_path, arcname=file_path.name)


def _write_metadata(metadata: dict[str, Any], path: Path) -> None:
    path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _build_release_metadata(
    export_data: ExportData,
    *,
    generated_at: str,
    validation_issues: tuple[ValidationIssue, ...],
) -> dict[str, Any]:
    warning_count = sum(1 for issue in validation_issues if issue.severity == "warning")
    error_count = sum(1 for issue in validation_issues if issue.severity == "error")
    return {
        "metadata_schema_version": RELEASE_METADATA_SCHEMA_VERSION,
        "data_schema_version": DATA_SCHEMA_VERSION,
        "generated_at": generated_at,
        "counts": {
            "objects": len(export_data.best),
            "caves": export_data.cave_count,
            "relations": export_data.relation_count,
            "measurements": len(export_data.history),
            "validation_warnings": warning_count,
            "validation_errors": error_count,
        },
    }


def _define_shapefile_fields(writer: shapefile.Writer) -> None:
    writer.field("object_id", "C", size=40)
    writer.field("name_local", "C", size=120)
    writer.field("category", "C", size=32)
    writer.field("cave_id", "C", size=40)
    writer.field("meas_id", "C", size=40)
    writer.field("lat", "F", decimal=8)
    writer.field("lon", "F", decimal=8)
    writer.field("x_1992", "F", decimal=3)
    writer.field("y_1992", "F", decimal=3)
    writer.field("elev_m", "F", decimal=2)
    writer.field("source", "C", size=16)
    writer.field("nr_inwent", "C", size=40)
    writer.field("pig_id", "C", size=80)
    writer.field("pig_url", "C", size=254)
    writer.field("tpn_gid", "C", size=80)
    writer.field("obs_date", "C", size=10)
    writer.field("status", "C", size=24)
    writer.field("obj_notes", "C", size=254)
    writer.field("cave_notes", "C", size=254)
    writer.field("meas_notes", "C", size=254)
    writer.field("cave_len_m", "F", size=20, decimal=3)
    writer.field("cave_dep_m", "F", size=20, decimal=3)
    writer.field("cave_den_m", "F", size=20, decimal=3)
    writer.field("cave_den_q", "C", size=16)
    writer.field("cave_m_ref", "C", size=254)


def _row_properties(row: BestMeasurementExportRow) -> dict[str, Any]:
    return {key: getattr(row, key) for key in BEST_FIELDS}


def _csv_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return _float_text(value)
    return str(value)


def _text_or_empty(value: str | None) -> str:
    return "" if value is None else value


def _truncated_text(value: str | None, *, max_length: int) -> str:
    if value is None:
        return ""
    return value.encode("utf-8")[:max_length].decode("utf-8", errors="ignore")


def _float_text(value: float) -> str:
    return f"{value:.12g}"


def _gpx_description(row: BestMeasurementExportRow) -> str:
    parts = [
        row.name_local or row.object_id,
        f"object {row.object_id}",
        f"measurement {row.measurement_id}",
        f"source {row.source}",
        f"observed {row.observed_date}",
    ]
    denivelation_prefix = "~" if row.cave_denivelation_qualifier == "approximate" else ""
    for label, value, prefix in (
        ("długość jaskini", row.cave_length_m, ""),
        ("głębokość", row.cave_depth_m, ""),
        ("deniwelacja", row.cave_denivelation_m, denivelation_prefix),
    ):
        if value is not None:
            parts.append(f"{label} {prefix}{_float_text(value)} m")
    if row.cave_morphometry_source_ref:
        parts.append(f"morfometria: {row.cave_morphometry_source_ref}")
    for label, note in (
        ("object notes", row.object_notes),
        ("cave notes", row.cave_notes),
        ("measurement notes", row.measurement_notes),
    ):
        if note:
            parts.append(f"{label}: {note}")
    return "; ".join(parts)


def _gpx_tag(name: str) -> str:
    return f"{{{GPX_NS}}}{name}"
