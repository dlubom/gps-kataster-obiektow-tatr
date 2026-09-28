import csv
import io
import json
import sqlite3
import subprocess
import sys
import zipfile
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import shapefile
import yaml

from gps_kataster_obiektow_tatr.best_measurements_export import (
    BestMeasurementsExportValidationError,
    _empty_row,
    _write_shapefile_zip,
    export_best_measurements,
)
from gps_kataster_obiektow_tatr.build_db import build_sqlite_database
from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "export_best_measurements.py"
KSW_LAT = 49.23459299
KSW_LON = 19.87589498
GENERATED_AT = "2026-05-16T12:00:00Z"


def test_exports_geojson_csv_gpx_and_shapefile_zip(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    output_dir = tmp_path / "build" / "exports"
    _write_sample_data(data_dir)

    result = export_best_measurements(
        data_dir=data_dir,
        output_dir=output_dir,
        generated_at=GENERATED_AT,
    )

    assert result.feature_count == 1
    assert result.geojson_path == output_dir / "best-measurements.geojson"
    assert result.csv_path == output_dir / "best-measurements.csv"
    assert result.gpx_path == output_dir / "best-measurements.gpx"
    assert result.shapefile_zip_path == output_dir / "best-measurements.shp.zip"
    assert result.metadata_path == output_dir / "metadata.json"

    geojson = json.loads(result.geojson_path.read_text(encoding="utf-8"))
    feature = geojson["features"][0]
    assert geojson["type"] == "FeatureCollection"
    assert feature["geometry"] == {"type": "Point", "coordinates": [KSW_LON, KSW_LAT]}
    assert feature["properties"]["object_id"] == "KSW-0001"
    assert feature["properties"]["measurement_id"] == "m-002"
    assert feature["properties"]["source"] == "TPN"
    assert feature["properties"]["nr_inwent"] == "T.E-08.75"
    assert feature["properties"]["pig_id"] == "1094"
    assert (
        feature["properties"]["pig_url"]
        == "https://jaskiniepolski.pgi.gov.pl/Details/Information/1094"
    )
    assert feature["properties"]["tpn_globalid"] == "{38626571-CAA6-4317-8900-D61A995020E9}"
    assert feature["properties"]["object_notes"] == "Object terrain note."
    assert feature["properties"]["cave_notes"] == "Cave catalog note."
    assert feature["properties"]["measurement_notes"] == "TPN measurement note."
    assert "m-001" not in result.geojson_path.read_text(encoding="utf-8")

    csv_rows = list(csv.DictReader(result.csv_path.open(encoding="utf-8", newline="")))
    assert len(csv_rows) == 1
    assert csv_rows[0]["object_id"] == "KSW-0001"
    assert csv_rows[0]["measurement_id"] == "m-002"
    assert csv_rows[0]["lat"] == str(KSW_LAT)
    assert csv_rows[0]["lon"] == str(KSW_LON)
    assert csv_rows[0]["x_1992"]
    assert csv_rows[0]["y_1992"]
    assert csv_rows[0]["nr_inwent"] == "T.E-08.75"
    assert csv_rows[0]["pig_id"] == "1094"
    assert csv_rows[0]["pig_url"] == "https://jaskiniepolski.pgi.gov.pl/Details/Information/1094"
    assert csv_rows[0]["tpn_globalid"] == "{38626571-CAA6-4317-8900-D61A995020E9}"
    assert csv_rows[0]["object_notes"] == "Object terrain note."
    assert csv_rows[0]["cave_notes"] == "Cave catalog note."
    assert csv_rows[0]["measurement_notes"] == "TPN measurement note."

    gpx_root = ET.parse(result.gpx_path).getroot()
    waypoints = gpx_root.findall("{http://www.topografix.com/GPX/1/1}wpt")
    assert len(waypoints) == 1
    assert waypoints[0].attrib["lat"] == str(KSW_LAT)
    assert waypoints[0].attrib["lon"] == str(KSW_LON)
    assert waypoints[0].findtext("{http://www.topografix.com/GPX/1/1}name") == "KSW-0001"
    assert "TPN measurement note." in (
        waypoints[0].findtext("{http://www.topografix.com/GPX/1/1}desc") or ""
    )

    with zipfile.ZipFile(result.shapefile_zip_path) as archive:
        assert set(archive.namelist()) == {
            "best-measurements.shp",
            "best-measurements.shx",
            "best-measurements.dbf",
            "best-measurements.prj",
            "best-measurements.cpg",
        }
        archive.extractall(tmp_path / "shp")

    with shapefile.Reader(str(tmp_path / "shp" / "best-measurements")) as reader:
        shape = reader.shape(0)
        record = reader.record(0)

    pl_1992 = wgs84_to_1992(lat=KSW_LAT, lon=KSW_LON)
    assert list(shape.points[0]) == [pl_1992.y_1992, pl_1992.x_1992]
    assert record["object_id"] == "KSW-0001"
    assert record["meas_id"] == "m-002"
    assert record["nr_inwent"] == "T.E-08.75"
    assert record["pig_id"] == "1094"
    assert record["tpn_gid"] == "{38626571-CAA6-4317-8900-D61A995020E9}"
    assert record["obj_notes"] == "Object terrain note."
    assert record["cave_notes"] == "Cave catalog note."
    assert record["meas_notes"] == "TPN measurement note."


def test_export_writes_metadata_snapshot(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    output_dir = tmp_path / "build" / "exports"
    object_data = _valid_object()
    object_data.pop("cave_id")
    _write_yaml(data_dir / "objects" / "KSW" / "KSW-0001.yml", object_data)
    cave_data = _valid_cave()
    cave_data["object_ids"] = []
    _write_yaml(data_dir / "caves" / "C-0001.yml", cave_data)

    result = export_best_measurements(
        data_dir=data_dir,
        output_dir=output_dir,
        generated_at=GENERATED_AT,
    )

    expected_metadata = {
        "metadata_schema_version": 1,
        "data_schema_version": 1,
        "generated_at": GENERATED_AT,
        "counts": {
            "objects": 1,
            "caves": 1,
            "relations": 0,
            "measurements": 2,
            "validation_warnings": 1,
            "validation_errors": 0,
        },
    }
    assert result.metadata == expected_metadata
    assert json.loads(result.metadata_path.read_text(encoding="utf-8")) == expected_metadata


def test_dbf_truncates_utf8_at_character_boundary_without_changing_full_exports(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    output_dir = tmp_path / "exports"
    notes = "a" * 253 + "ó"
    object_data = _valid_object()
    object_data["notes"] = notes
    _write_yaml(data_dir / "objects" / "KSW" / "KSW-0001.yml", object_data)
    _write_yaml(data_dir / "caves" / "C-0001.yml", _valid_cave())

    result = export_best_measurements(
        data_dir=data_dir, output_dir=output_dir, generated_at=GENERATED_AT
    )

    with (
        zipfile.ZipFile(result.shapefile_zip_path) as archive,
        shapefile.Reader(
            shp=io.BytesIO(archive.read("best-measurements.shp")),
            shx=io.BytesIO(archive.read("best-measurements.shx")),
            dbf=io.BytesIO(archive.read("best-measurements.dbf")),
            encoding="utf-8",
            encodingErrors="strict",
        ) as reader,
    ):
        records = list(reader.iterRecords())
        assert reader.numShapes == 1

    assert len(records) == 1
    assert records[0]["object_id"] == "KSW-0001"
    assert records[0]["obj_notes"] == "a" * 253
    assert "\ufffd" not in records[0]["obj_notes"]
    assert (
        json.loads(result.geojson_path.read_text(encoding="utf-8"))["features"][0]["properties"][
            "object_notes"
        ]
        == notes
    )
    with result.csv_path.open(encoding="utf-8", newline="") as csv_file:
        assert list(csv.DictReader(csv_file))[0]["object_notes"] == notes

    sqlite_path = tmp_path / "katalog.sqlite"
    build_sqlite_database(data_dir=data_dir, output_path=sqlite_path, generated_at=GENERATED_AT)
    with sqlite3.connect(sqlite_path) as connection:
        assert connection.execute("SELECT notes FROM objects WHERE id = 'KSW-0001'").fetchone() == (
            notes,
        )


@pytest.mark.parametrize(
    ("name", "notes", "expected_name", "expected_notes"),
    [
        ("a" * 118 + "ó", "a" * 252 + "ó", "a" * 118 + "ó", "a" * 252 + "ó"),
        ("a" * 119 + "ó", "a" * 253 + "ó", "a" * 119, "a" * 253),
        ("Ž" * 61, "Č" * 128, "Ž" * 60, "Č" * 127),
    ],
)
def test_dbf_name_and_notes_respect_utf8_byte_boundaries(
    tmp_path: Path, name: str, notes: str, expected_name: str, expected_notes: str
) -> None:
    data_dir = tmp_path / "data"
    object_data = _valid_object()
    object_data["name_local"] = name
    object_data["notes"] = notes
    _write_yaml(data_dir / "objects" / "KSW" / "KSW-0001.yml", object_data)
    _write_yaml(data_dir / "caves" / "C-0001.yml", _valid_cave())

    result = export_best_measurements(
        data_dir=data_dir, output_dir=tmp_path / "exports", generated_at=GENERATED_AT
    )
    with (
        zipfile.ZipFile(result.shapefile_zip_path) as archive,
        shapefile.Reader(
            shp=io.BytesIO(archive.read("best-measurements.shp")),
            shx=io.BytesIO(archive.read("best-measurements.shx")),
            dbf=io.BytesIO(archive.read("best-measurements.dbf")),
            encoding="utf-8",
            encodingErrors="strict",
        ) as reader,
    ):
        record = reader.record(0)
        assert reader.numRecords == reader.numShapes == 1
        assert reader.shape(0).shapeType == shapefile.POINT

    assert record["object_id"] == "KSW-0001"
    assert record["name_local"] == expected_name
    assert record["obj_notes"] == expected_notes
    assert "\ufffd" not in str(record)
    properties = json.loads(result.geojson_path.read_text(encoding="utf-8"))["features"][0][
        "properties"
    ]
    assert properties["name_local"] == name
    assert properties["object_notes"] == notes


def test_dbf_all_text_fields_use_their_declared_byte_widths(tmp_path: Path) -> None:
    # Exercise the writer boundary directly, including fields whose domain IDs/enums
    # cannot be made overlong in valid YAML.
    long_text = "ą" * 255
    row = replace(
        _empty_row(),
        object_id=long_text,
        name_local=long_text,
        category=long_text,
        cave_id=long_text,
        measurement_id=long_text,
        source=long_text,
        nr_inwent=long_text,
        pig_id=long_text,
        pig_url=long_text,
        tpn_globalid=long_text,
        observed_date=long_text,
        verification_status=long_text,
        object_notes=long_text,
        cave_notes=long_text,
        measurement_notes=long_text,
    )
    zip_path = tmp_path / "all-text-fields.shp.zip"
    _write_shapefile_zip((row,), zip_path)

    with (
        zipfile.ZipFile(zip_path) as archive,
        shapefile.Reader(
            shp=io.BytesIO(archive.read("best-measurements.shp")),
            shx=io.BytesIO(archive.read("best-measurements.shx")),
            dbf=io.BytesIO(archive.read("best-measurements.dbf")),
            encoding="utf-8",
            encodingErrors="strict",
        ) as reader,
    ):
        record = reader.record(0)
        text_fields = [field for field in reader.fields[1:] if field.field_type == "C"]
        assert reader.numRecords == reader.numShapes == 1
        assert len(text_fields) == 15
        for field in text_fields:
            assert record[field.name] == "ą" * (field.size // 2)
            assert len(record[field.name].encode("utf-8")) <= field.size
            assert "\ufffd" not in record[field.name]


def test_export_cli_writes_artifacts(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    output_dir = tmp_path / "build" / "exports"
    _write_sample_data(data_dir)

    result = subprocess.run(
        [
            sys.executable,
            str(EXPORT_SCRIPT),
            "--data-dir",
            str(data_dir),
            "--output-dir",
            str(output_dir),
            "--generated-at",
            GENERATED_AT,
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (output_dir / "best-measurements.geojson").exists()
    assert (output_dir / "best-measurements.csv").exists()
    assert (output_dir / "best-measurements.gpx").exists()
    assert (output_dir / "best-measurements.shp.zip").exists()
    assert (output_dir / "metadata.json").exists()
    assert "best-measurements export: 1 features" in result.stdout


def test_export_rejects_invalid_yaml(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    object_path = data_dir / "objects" / "KSW" / "KSW-0001.yml"
    object_data = yaml.safe_load(object_path.read_text(encoding="utf-8"))
    object_data["best_measurement"]["measurement_id"] = "m-999"
    _write_yaml(object_path, object_data)

    with pytest.raises(BestMeasurementsExportValidationError) as exc_info:
        export_best_measurements(data_dir=data_dir, output_dir=tmp_path / "exports")

    assert "BEST_MEASUREMENT_MISSING" in {issue.code for issue in exc_info.value.issues}
    assert not (tmp_path / "exports" / "best-measurements.geojson").exists()


def _write_sample_data(data_dir: Path) -> None:
    _write_yaml(data_dir / "objects" / "KSW" / "KSW-0001.yml", _valid_object())
    _write_yaml(data_dir / "caves" / "C-0001.yml", _valid_cave())


def _valid_object() -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "KSW-0001",
        "category": "jaskinia_otwor",
        "name_local": "Test Cave - main entrance",
        "cave_id": "C-0001",
        "id_assignment": {
            "method": "auto",
            "assigned_from_measurement_id": "m-001",
            "assigned_prefix": "KSW",
            "prefix_override_reason": None,
        },
        "external_refs": [
            {
                "system": "TPN",
                "ref_type": "source_globalid",
                "external_id": "{38626571-CAA6-4317-8900-D61A995020E9}",
                "scope": "object",
                "notes": "TPN point reference.",
            }
        ],
        "measurements": [
            _measurement("m-001", source="PIG", observed_date="2026-05-15"),
            _measurement("m-002", source="TPN", observed_date="2026-05-16"),
        ],
        "best_measurement": {
            "mode": "auto",
            "measurement_id": "m-002",
            "reason": None,
            "updated_at": "2026-05-16T10:30:00Z",
            "updated_by": "dl",
        },
        "attachments": [],
        "notes": "Object terrain note.",
        "created_at": "2026-05-15T10:00:00Z",
        "created_by": "dl",
        "updated_at": "2026-05-16T10:30:00Z",
        "updated_by": "dl",
    }


def _valid_cave() -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "C-0001",
        "name": "Test Cave",
        "system_name": None,
        "external_refs": [
            {
                "system": "NR_INWENT",
                "ref_type": "inventory_number",
                "external_id": "T.E-08.75",
                "scope": "cave",
                "notes": "Inventory number belongs to the cave/catalog entry.",
            },
            {
                "system": "PIG",
                "ref_type": "catalog_id",
                "external_id": "1094",
                "url": "https://jaskiniepolski.pgi.gov.pl/Details/Information/1094",
                "scope": "cave",
                "notes": "PIG catalog record identifier.",
            },
        ],
        "object_ids": ["KSW-0001"],
        "notes": "Cave catalog note.",
        "created_at": "2026-05-15T10:00:00Z",
        "created_by": "dl",
        "updated_at": "2026-05-16T10:30:00Z",
        "updated_by": "dl",
    }


def _measurement(
    measurement_id: str,
    *,
    source: str,
    observed_date: str,
) -> dict[str, object]:
    pl_1992 = wgs84_to_1992(lat=KSW_LAT, lon=KSW_LON)
    return {
        "id": measurement_id,
        "lat": KSW_LAT,
        "lon": KSW_LON,
        "x_1992": pl_1992.x_1992,
        "y_1992": pl_1992.y_1992,
        "elevation_m": 1240.0,
        "elevation_datum": "unknown",
        "elevation_source": "source_record",
        "horizontal_accuracy_m": 5.0,
        "vertical_accuracy_m": 8.0,
        "source": source,
        "source_ref": f"{source}:{measurement_id}",
        "observed_at": None,
        "observed_date": observed_date,
        "source_date": None,
        "method": "source_record",
        "device": None,
        "tags": ["fixture"],
        "verification_status": "nieweryfikowany",
        "verified_by": None,
        "verified_at": None,
        "notes": f"{source} measurement note.",
        "created_at": "2026-05-15T10:00:00Z",
        "created_by": "dl",
    }


def _write_yaml(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(deepcopy(data), sort_keys=False), encoding="utf-8")
