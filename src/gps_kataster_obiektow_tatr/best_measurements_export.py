"""Export selected best measurements to release-friendly formats."""

from __future__ import annotations

import csv
import json
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import shapefile

from gps_kataster_obiektow_tatr.best_measurement import select_default_best_measurement_id
from gps_kataster_obiektow_tatr.data_loader import (
    DEFAULT_DATA_DIR,
    LoadedDataset,
    LoadedYamlRecord,
    load_dataset,
)
from gps_kataster_obiektow_tatr.validator import (
    ValidationIssue,
    format_issue,
    has_errors,
    validate_dataset,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXPORT_DIR = REPO_ROOT / "build" / "exports"
GEOJSON_FILENAME = "best-measurements.geojson"
CSV_FILENAME = "best-measurements.csv"
GPX_FILENAME = "best-measurements.gpx"
SHAPEFILE_ZIP_FILENAME = "best-measurements.shp.zip"
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
class BestMeasurementExportRow:
    """One selected best measurement ready for generated exports."""

    object_id: str
    category: str
    name_local: str | None
    cave_id: str | None
    measurement_id: str
    best_mode: str
    computed_best_measurement_id: str | None
    best_reason: str | None
    lat: float
    lon: float
    x_1992: float
    y_1992: float
    elevation_m: float | None
    source: str
    source_ref: str | None
    observed_at: str | None
    observed_date: str
    method: str
    verification_status: str
    horizontal_accuracy_m: float | None
    vertical_accuracy_m: float | None


@dataclass(frozen=True, slots=True)
class BestMeasurementsExportResult:
    """Summary of a completed best-measurements export."""

    output_dir: Path
    geojson_path: Path
    csv_path: Path
    gpx_path: Path
    shapefile_zip_path: Path
    feature_count: int
    validation_issues: tuple[ValidationIssue, ...]


class BestMeasurementsExportValidationError(ValueError):
    """Raised when source YAML has validation errors that block export."""

    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        self.issues = issues
        details = "\n".join(format_issue(issue) for issue in issues if issue.severity == "error")
        super().__init__(f"Cannot export best measurements from invalid YAML:\n{details}")


def export_best_measurements(
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    output_dir: Path = DEFAULT_EXPORT_DIR,
    generated_at: str | None = None,
) -> BestMeasurementsExportResult:
    """Validate YAML and export one best measurement per object."""

    dataset = load_dataset(data_dir)
    validation_issues = validate_dataset(dataset, data_dir=data_dir, repo_root=REPO_ROOT)
    if has_errors(validation_issues):
        raise BestMeasurementsExportValidationError(validation_issues)

    rows = _collect_best_measurement_rows(dataset)
    timestamp = generated_at or _utc_timestamp()

    output_dir.mkdir(parents=True, exist_ok=True)
    geojson_path = output_dir / GEOJSON_FILENAME
    csv_path = output_dir / CSV_FILENAME
    gpx_path = output_dir / GPX_FILENAME
    shapefile_zip_path = output_dir / SHAPEFILE_ZIP_FILENAME

    _write_geojson(rows, geojson_path, generated_at=timestamp)
    _write_csv(rows, csv_path)
    _write_gpx(rows, gpx_path, generated_at=timestamp)
    _write_shapefile_zip(rows, shapefile_zip_path)

    return BestMeasurementsExportResult(
        output_dir=output_dir,
        geojson_path=geojson_path,
        csv_path=csv_path,
        gpx_path=gpx_path,
        shapefile_zip_path=shapefile_zip_path,
        feature_count=len(rows),
        validation_issues=validation_issues,
    )


def _collect_best_measurement_rows(dataset: LoadedDataset) -> tuple[BestMeasurementExportRow, ...]:
    rows: list[BestMeasurementExportRow] = []

    for object_record in sorted(dataset.objects, key=lambda record: str(record.data["id"])):
        object_data = object_record.data
        best_measurement = _best_measurement_data(object_data)
        measurement_id = str(best_measurement["measurement_id"])
        measurement = _measurement_by_id(object_record, measurement_id)
        computed_best_measurement_id = select_default_best_measurement_id(
            _measurement_dicts(object_data.get("measurements"))
        )

        rows.append(
            BestMeasurementExportRow(
                object_id=str(object_data["id"]),
                category=str(object_data["category"]),
                name_local=_optional_str(object_data.get("name_local")),
                cave_id=_optional_str(object_data.get("cave_id")),
                measurement_id=measurement_id,
                best_mode=str(best_measurement["mode"]),
                computed_best_measurement_id=computed_best_measurement_id,
                best_reason=_optional_str(best_measurement.get("reason")),
                lat=_number(measurement["lat"]),
                lon=_number(measurement["lon"]),
                x_1992=_number(measurement["x_1992"]),
                y_1992=_number(measurement["y_1992"]),
                elevation_m=_optional_number(measurement.get("elevation_m")),
                source=str(measurement["source"]),
                source_ref=_optional_str(measurement.get("source_ref")),
                observed_at=_optional_str(measurement.get("observed_at")),
                observed_date=str(measurement["observed_date"]),
                method=str(measurement["method"]),
                verification_status=str(measurement["verification_status"]),
                horizontal_accuracy_m=_optional_number(measurement.get("horizontal_accuracy_m")),
                vertical_accuracy_m=_optional_number(measurement.get("vertical_accuracy_m")),
            )
        )

    return tuple(rows)


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
        writer = csv.DictWriter(csv_file, fieldnames=_csv_fieldnames())
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(value) for key, value in _row_properties(row).items()})


def _write_gpx(
    rows: tuple[BestMeasurementExportRow, ...],
    path: Path,
    *,
    generated_at: str,
) -> None:
    ET.register_namespace("", GPX_NS)
    gpx = ET.Element(_gpx_tag("gpx"), {"version": "1.1", "creator": "gps-kataster-obiektow-tatr"})
    metadata = ET.SubElement(gpx, _gpx_tag("metadata"))
    ET.SubElement(metadata, _gpx_tag("name")).text = "gps-kataster-obiektow-tatr best measurements"
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
        ET.SubElement(waypoint, _gpx_tag("name")).text = row.object_id
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
                    row.observed_date,
                    row.verification_status,
                )
        finally:
            writer.close()

        (tmp_dir / "best-measurements.prj").write_text(EPSG_2180_PRJ, encoding="ascii")
        (tmp_dir / "best-measurements.cpg").write_text("UTF-8\n", encoding="ascii")

        with zipfile.ZipFile(path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
                file_path = tmp_dir / f"best-measurements{suffix}"
                archive.write(file_path, arcname=file_path.name)


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
    writer.field("obs_date", "C", size=10)
    writer.field("status", "C", size=24)


def _row_properties(row: BestMeasurementExportRow) -> dict[str, Any]:
    return {
        "object_id": row.object_id,
        "category": row.category,
        "name_local": row.name_local,
        "cave_id": row.cave_id,
        "measurement_id": row.measurement_id,
        "best_mode": row.best_mode,
        "computed_best_measurement_id": row.computed_best_measurement_id,
        "best_reason": row.best_reason,
        "lat": row.lat,
        "lon": row.lon,
        "x_1992": row.x_1992,
        "y_1992": row.y_1992,
        "elevation_m": row.elevation_m,
        "source": row.source,
        "source_ref": row.source_ref,
        "observed_at": row.observed_at,
        "observed_date": row.observed_date,
        "method": row.method,
        "verification_status": row.verification_status,
        "horizontal_accuracy_m": row.horizontal_accuracy_m,
        "vertical_accuracy_m": row.vertical_accuracy_m,
    }


def _csv_fieldnames() -> list[str]:
    return list(_row_properties(_empty_row()).keys())


def _empty_row() -> BestMeasurementExportRow:
    return BestMeasurementExportRow(
        object_id="",
        category="",
        name_local=None,
        cave_id=None,
        measurement_id="",
        best_mode="",
        computed_best_measurement_id=None,
        best_reason=None,
        lat=0.0,
        lon=0.0,
        x_1992=0.0,
        y_1992=0.0,
        elevation_m=None,
        source="",
        source_ref=None,
        observed_at=None,
        observed_date="",
        method="",
        verification_status="",
        horizontal_accuracy_m=None,
        vertical_accuracy_m=None,
    )


def _measurement_by_id(
    object_record: LoadedYamlRecord,
    measurement_id: str,
) -> dict[str, Any]:
    for measurement in _measurement_dicts(object_record.data.get("measurements")):
        if measurement.get("id") == measurement_id:
            return measurement
    raise KeyError(f"Best measurement {measurement_id} missing for {object_record.data['id']}.")


def _best_measurement_data(object_data: dict[str, Any]) -> dict[str, Any]:
    best_measurement = object_data.get("best_measurement")
    if not isinstance(best_measurement, dict):
        raise KeyError(f"best_measurement missing for {object_data['id']}.")
    return best_measurement


def _measurement_dicts(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, dict))


def _number(value: object) -> float:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    raise TypeError(f"Expected numeric value, got {value!r}.")


def _optional_number(value: object) -> float | None:
    if value is None:
        return None
    return _number(value)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _csv_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return _float_text(value)
    return str(value)


def _text_or_empty(value: str | None) -> str:
    return "" if value is None else value


def _float_text(value: float) -> str:
    return f"{value:.12g}"


def _gpx_description(row: BestMeasurementExportRow) -> str:
    parts = [
        row.name_local or row.object_id,
        f"measurement {row.measurement_id}",
        f"source {row.source}",
        f"observed {row.observed_date}",
    ]
    return "; ".join(parts)


def _gpx_tag(name: str) -> str:
    return f"{{{GPX_NS}}}{name}"


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
