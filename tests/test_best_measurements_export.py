import csv
import json
import sqlite3
import subprocess
import sys
import zipfile
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import shapefile
import yaml

from gps_kataster_obiektow_tatr.best_measurements_export import (
    BestMeasurementsExportValidationError,
    export_best_measurements,
)
from gps_kataster_obiektow_tatr.build_db import BuildDatabaseValidationError, build_sqlite_database
from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "export_best_measurements.py"
KSW_LAT = 49.23459299
KSW_LON = 19.87589498
GENERATED_AT = "2026-05-16T12:00:00Z"


@pytest.mark.parametrize("mode", ["auto", "manual"])
def test_duplicate_local_measurement_id_blocks_exports_and_release(tmp_path, mode):
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    output = tmp_path / "output"
    build_release_artifacts(
        data_dir=data_dir, sqlite_path=output / "katalog.sqlite", output_dir=output / "exports"
    )
    before = {str(p.relative_to(output)): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    assert len(before) == 10
    source = data_dir / "objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(source.read_text())
    duplicate = deepcopy(obj["measurements"][1])
    duplicate["notes"] = "Second reading with ambiguous identity."
    obj["measurements"].append(duplicate)
    obj["best_measurement"].update(mode=mode, reason="Operator selection.")
    _write_yaml(source, obj)
    source_before = source.read_bytes()

    for target in (output, tmp_path / "new-output"):
        with pytest.raises(BestMeasurementsExportValidationError, match="DUPLICATE_MEASUREMENT_ID"):
            export_best_measurements(data_dir=data_dir, output_dir=target / "exports")
        with pytest.raises(BuildDatabaseValidationError, match="DUPLICATE_MEASUREMENT_ID"):
            build_release_artifacts(
                data_dir=data_dir,
                sqlite_path=target / "katalog.sqlite",
                output_dir=target / "exports",
            )
        for script, args in [
            (EXPORT_SCRIPT, ["--output-dir", str(target / "exports")]),
            (
                REPO_ROOT / "scripts/build_release_artifacts.py",
                [
                    "--sqlite-output",
                    str(target / "katalog.sqlite"),
                    "--output-dir",
                    str(target / "exports"),
                ],
            ),
            (REPO_ROOT / "scripts/validate.py", []),
        ]:
            result = subprocess.run(
                [sys.executable, str(script), "--data-dir", str(data_dir), *args],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 1
            assert "DUPLICATE_MEASUREMENT_ID" in result.stdout + result.stderr
            assert str(source) in result.stdout + result.stderr
            assert "Traceback" not in result.stdout + result.stderr
    assert {
        str(p.relative_to(output)): p.read_bytes() for p in output.rglob("*") if p.is_file()
    } == before
    assert not (tmp_path / "new-output").exists()
    assert source.read_bytes() == source_before


@pytest.mark.parametrize("note", ["a" * 253 + "ą", "TPN UWAGI: " + "źółć" * 90])
def test_dbf_notes_truncate_at_utf8_boundary(tmp_path, note):
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    path = data_dir / "objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(path.read_text())
    obj["measurements"][1]["notes"] = note
    _write_yaml(path, obj)
    result = export_best_measurements(
        data_dir=data_dir,
        output_dir=tmp_path / "exports",
        generated_at=GENERATED_AT,
    )
    assert (
        json.loads(result.geojson_path.read_text())["features"][0]["properties"][
            "measurement_notes"
        ]
        == note
    )
    with zipfile.ZipFile(result.shapefile_zip_path) as archive:
        archive.extractall(tmp_path / "shp")
    with shapefile.Reader(str(tmp_path / "shp/best-measurements"), encoding="utf-8") as reader:
        actual = reader.record(0)["meas_notes"]
    assert actual == note.encode("utf-8")[:254].decode("utf-8", errors="ignore")


def test_survey_network_manual_point_survives_newer_tpn_in_database_and_exports(tmp_path):
    data = tmp_path / "data"
    _write_sample_data(data)
    path = data / "objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(path.read_text())
    obj["measurements"][0].update(
        source="inne",
        method="siec_pomiarowa",
        source_ref="JKTZ:historical:Survey:entrance",
        elevation_source="other",
    )
    obj["best_measurement"].update(
        mode="manual", measurement_id="m-001", reason="Position from a cave survey network."
    )
    _write_yaml(path, obj)

    database = build_sqlite_database(data_dir=data, output_path=tmp_path / "katalog.sqlite")
    with sqlite3.connect(database.sqlite_path) as conn:
        assert conn.execute(
            "SELECT mode,measurement_id,computed_best_measurement_id FROM best_measurements"
        ).fetchone() == ("manual", "m-001", "m-002")
        assert conn.execute(
            "SELECT method,source_ref FROM measurements WHERE id='m-001'"
        ).fetchone() == ("siec_pomiarowa", "JKTZ:historical:Survey:entrance")

    result = export_best_measurements(data_dir=data, output_dir=tmp_path / "exports")
    with result.csv_path.open(encoding="utf-8", newline="") as stream:
        row = list(csv.DictReader(stream))[0]
    assert (row["best_mode"], row["measurement_id"], row["method"]) == (
        "manual",
        "m-001",
        "siec_pomiarowa",
    )
    assert row["verification_status"] == "nieweryfikowany"
    feature = json.loads(result.geojson_path.read_text())["features"][0]
    assert feature["properties"]["method"] == "siec_pomiarowa"


def test_tpn_best_context_readable_in_all_full_text_exports(tmp_path):
    data = tmp_path / "data"
    _write_sample_data(data)
    path = data / "objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(path.read_text())
    note = "Ręczna uwaga.\nTPN WER_LOK: niepewna\nTPN UWAGI: Trzeba uściślić położenie"
    obj["measurements"][1]["notes"] = note
    _write_yaml(path, obj)
    result = export_best_measurements(data_dir=data, output_dir=tmp_path / "exports")
    with result.csv_path.open(encoding="utf-8", newline="") as stream:
        assert list(csv.DictReader(stream))[0]["measurement_notes"] == note
    assert (
        json.loads(result.geojson_path.read_text())["features"][0]["properties"][
            "measurement_notes"
        ]
        == note
    )
    desc = ET.parse(result.gpx_path).findtext(".//{http://www.topografix.com/GPX/1/1}desc")
    assert note in desc
    database = build_sqlite_database(data_dir=data, output_path=tmp_path / "katalog.sqlite")
    with sqlite3.connect(database.sqlite_path) as conn:
        assert (
            conn.execute(
                "SELECT notes FROM measurements WHERE object_id='KSW-0001' AND id='m-002'"
            ).fetchone()[0]
            == note
        )


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
    assert (
        waypoints[0].findtext("{http://www.topografix.com/GPX/1/1}name")
        == "Test Cave - main entrance"
    )
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


@pytest.mark.parametrize(
    ("name_local", "expected_label"),
    [
        ("Jaskinia Żółta — otwór <górny> & wschodni", "Jaskinia Żółta — otwór <górny> & wschodni"),
        (None, "KSW-0001"),
        ("", "KSW-0001"),
        (" \t\n ", "KSW-0001"),
        ("missing", "KSW-0001"),
    ],
)
def test_gpx_labels_use_local_names_and_preserve_object_ids(
    tmp_path: Path, name_local: str | None, expected_label: str
) -> None:
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    object_data = _valid_object()
    if name_local == "missing":
        object_data.pop("name_local")
    else:
        object_data["name_local"] = name_local
    _write_yaml(data_dir / "objects/KSW/KSW-0001.yml", object_data)

    result = export_best_measurements(data_dir=data_dir, output_dir=tmp_path / "exports")

    ns = "{http://www.topografix.com/GPX/1/1}"
    waypoint = ET.parse(result.gpx_path).find(ns + "wpt")
    assert waypoint is not None
    assert waypoint.findtext(ns + "name") == expected_label
    description = waypoint.findtext(ns + "desc") or ""
    assert "object KSW-0001" in description
    assert "measurement m-002" in description
    assert "TPN measurement note." in description


def test_export_writes_metadata_snapshot(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    (data_dir / "relations").mkdir(parents=True)
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
    for name in ("objects", "caves", "relations"):
        (data_dir / name).mkdir(parents=True, exist_ok=True)
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
