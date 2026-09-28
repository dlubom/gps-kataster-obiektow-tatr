import csv
import hashlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import zipfile
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pytest
import shapefile
import yaml

from gps_kataster_obiektow_tatr import best_measurements_export, build_db
from gps_kataster_obiektow_tatr.best_measurements_export import export_best_measurements
from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_RELEASE_SCRIPT = REPO_ROOT / "scripts" / "build_release_artifacts.py"
KSW_LAT = 49.23459299
KSW_LON = 19.87589498
GENERATED_AT = "2026-05-16T12:00:00Z"


def test_build_release_artifacts_writes_full_expected_set(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    sqlite_path = tmp_path / "build" / "katalog.sqlite"
    output_dir = tmp_path / "build" / "exports"
    _write_sample_data(data_dir)

    result = build_release_artifacts(
        data_dir=data_dir,
        sqlite_path=sqlite_path,
        output_dir=output_dir,
        generated_at=GENERATED_AT,
    )

    assert result.artifact_paths == (
        sqlite_path,
        output_dir / "best-measurements.geojson",
        output_dir / "best-measurements.csv",
        output_dir / "best-measurements.gpx",
        output_dir / "best-measurements.shp.zip",
        output_dir / "katalog.sqlite.zip",
        output_dir / "metadata.json",
    )
    for artifact_path in result.artifact_paths:
        assert artifact_path.exists()

    with zipfile.ZipFile(output_dir / "katalog.sqlite.zip") as archive:
        assert archive.namelist() == ["katalog.sqlite"]

    assert result.export_result.metadata["counts"] == {
        "objects": 1,
        "caves": 1,
        "relations": 0,
        "measurements": 2,
        "validation_warnings": 0,
        "validation_errors": 0,
    }


def test_release_build_is_independent_of_clock_mtime_mode_and_output_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    source_paths = sorted(data_dir.rglob("*.yml"))

    def build_with_changed_environment(
        directory: str, *, year: int, month: int, day: int, file_mode: int
    ) -> tuple[dict[str, str], Path, Path]:
        run_dir = tmp_path / directory
        sqlite_path = run_dir / "katalog.sqlite"
        output_dir = run_dir / "exports"
        source_mtime_ns = datetime(year, month, day, tzinfo=UTC).timestamp() * 1_000_000_000
        for source_path in source_paths:
            os.utime(source_path, ns=(int(source_mtime_ns), int(source_mtime_ns)))

        original_write = zipfile.ZipFile.write

        def write_with_changed_file_metadata(
            archive: zipfile.ZipFile, filename: str | Path, *args: Any, **kwargs: Any
        ) -> None:
            # Existing archive.write() otherwise inherits the new file's real mtime.
            os.utime(filename, ns=(int(source_mtime_ns), int(source_mtime_ns)))
            os.chmod(filename, file_mode)
            original_write(archive, filename, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(
                shapefile.time,
                "localtime",
                lambda *_: datetime(year, month, day, 10, 11, 12).timetuple(),
            )
            patch.setattr(zipfile.ZipFile, "write", write_with_changed_file_metadata)
            result = build_release_artifacts(
                data_dir=data_dir,
                sqlite_path=sqlite_path,
                output_dir=output_dir,
                generated_at=GENERATED_AT,
            )

        assert len(result.artifact_paths) == 7
        hashes = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in result.artifact_paths
        }
        _read_back_release(sqlite_path, output_dir, expected_name="Test Cave - main entrance")
        return hashes, sqlite_path, output_dir

    first, _, first_exports = build_with_changed_environment(
        "first", year=2024, month=3, day=4, file_mode=0o600
    )
    second, _, second_exports = build_with_changed_environment(
        "second", year=2025, month=7, day=9, file_mode=0o644
    )
    assert set(first) == {
        "katalog.sqlite",
        "best-measurements.geojson",
        "best-measurements.csv",
        "best-measurements.gpx",
        "best-measurements.shp.zip",
        "katalog.sqlite.zip",
        "metadata.json",
    }
    assert first == second

    for output_dir in (first_exports, second_exports):
        for zip_name in ("best-measurements.shp.zip", "katalog.sqlite.zip"):
            with zipfile.ZipFile(output_dir / zip_name) as archive:
                for info in archive.infolist():
                    assert info.date_time == (2026, 5, 16, 12, 0, 0)
                    assert info.create_system == 3
                    assert info.external_attr >> 16 == 0o100644
                    assert info.compress_type == zipfile.ZIP_DEFLATED
                    assert not info.extra
                    assert not info.comment
        with zipfile.ZipFile(output_dir / "best-measurements.shp.zip") as archive:
            dbf = archive.read("best-measurements.dbf")
            assert dbf[1:4] == bytes((126, 5, 16))

    changed_object = _valid_object()
    changed_object["name_local"] = "Changed cave entrance"
    _write_yaml(data_dir / "objects" / "KSW" / "KSW-0001.yml", changed_object)
    changed = build_release_artifacts(
        data_dir=data_dir,
        sqlite_path=tmp_path / "changed" / "katalog.sqlite",
        output_dir=tmp_path / "changed" / "exports",
        generated_at=GENERATED_AT,
    )
    changed_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in changed.artifact_paths
    }
    for name in first.keys() - {"metadata.json"}:
        assert first[name] != changed_hashes[name], name
    assert first["metadata.json"] == changed_hashes["metadata.json"]
    _read_back_release(
        tmp_path / "changed" / "katalog.sqlite",
        tmp_path / "changed" / "exports",
        expected_name="Changed cave entrance",
    )


def test_release_build_uses_one_timestamp_when_not_supplied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    monkeypatch.setattr(build_db, "_utc_timestamp", lambda: "2026-05-16T23:59:59Z")
    monkeypatch.setattr(best_measurements_export, "_utc_timestamp", lambda: "2026-05-17T00:00:00Z")

    result = build_release_artifacts(
        data_dir=data_dir,
        sqlite_path=tmp_path / "build" / "katalog.sqlite",
        output_dir=tmp_path / "build" / "exports",
    )

    assert (
        result.sqlite_result.metadata["generated_at"]
        == result.export_result.metadata["generated_at"]
    )


@pytest.mark.parametrize(
    ("generated_at", "expected_zip_time", "expected_dbf_date"),
    [
        ("1980-01-01T00:00:00Z", (1980, 1, 1, 0, 0, 0), bytes((80, 1, 1))),
        ("1980-01-01T02:00:00+02:00", (1980, 1, 1, 0, 0, 0), bytes((80, 1, 1))),
        ("2107-12-31T23:59:59Z", (2107, 12, 31, 23, 59, 58), bytes((207, 12, 31))),
    ],
)
def test_release_timestamp_at_zip_boundaries(
    tmp_path: Path,
    generated_at: str,
    expected_zip_time: tuple[int, int, int, int, int, int],
    expected_dbf_date: bytes,
) -> None:
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)

    result = build_release_artifacts(
        data_dir=data_dir,
        sqlite_path=tmp_path / "build" / "katalog.sqlite",
        output_dir=tmp_path / "build" / "exports",
        generated_at=generated_at,
    )

    for zip_path in (result.export_result.shapefile_zip_path, result.sqlite_zip_path):
        with zipfile.ZipFile(zip_path) as archive:
            assert all(info.date_time == expected_zip_time for info in archive.infolist())
    with zipfile.ZipFile(result.export_result.shapefile_zip_path) as archive:
        assert archive.read("best-measurements.dbf")[1:4] == expected_dbf_date


@pytest.mark.parametrize("generated_at", ["1979-12-31T23:59:59Z", "2108-01-01T00:00:00Z"])
def test_release_rejects_timestamp_outside_zip_range_before_writing(
    tmp_path: Path, generated_at: str
) -> None:
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    sqlite_path = tmp_path / "build" / "katalog.sqlite"
    output_dir = tmp_path / "build" / "exports"

    with pytest.raises(ValueError, match="ZIP|1980|2107"):
        build_release_artifacts(
            data_dir=data_dir,
            sqlite_path=sqlite_path,
            output_dir=output_dir,
            generated_at=generated_at,
        )

    assert not sqlite_path.exists()
    assert not output_dir.exists()


def test_release_rejects_timestamp_without_timezone_before_writing(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    sqlite_path = tmp_path / "build" / "katalog.sqlite"

    with pytest.raises(ValueError, match="timezone"):
        build_release_artifacts(
            data_dir=data_dir,
            sqlite_path=sqlite_path,
            output_dir=tmp_path / "build" / "exports",
            generated_at="2026-05-16T12:00:00",
        )

    assert not sqlite_path.exists()


def test_export_rejects_explicit_empty_generated_at_before_writing(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    output_dir = tmp_path / "exports"

    with pytest.raises(ValueError, match="generated_at"):
        export_best_measurements(data_dir=data_dir, output_dir=output_dir, generated_at="")

    assert not output_dir.exists()


@pytest.mark.parametrize(
    "script_name", ["build_release_artifacts.py", "export_best_measurements.py"]
)
def test_cli_rejects_explicit_empty_generated_at_before_writing(
    tmp_path: Path, script_name: str
) -> None:
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    output_dir = tmp_path / "exports"
    sqlite_path = tmp_path / "katalog.sqlite"

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / script_name),
            "--data-dir",
            str(data_dir),
            "--output-dir",
            str(output_dir),
            "--sqlite-output",
            str(sqlite_path),
            "--generated-at",
            "",
        ]
        if script_name == "build_release_artifacts.py"
        else [
            sys.executable,
            str(REPO_ROOT / "scripts" / script_name),
            "--data-dir",
            str(data_dir),
            "--output-dir",
            str(output_dir),
            "--generated-at",
            "",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "generated_at" in result.stderr
    assert not output_dir.exists()
    assert not sqlite_path.exists()


def test_build_release_artifacts_cli_is_local_dry_run(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    sqlite_path = tmp_path / "build" / "katalog.sqlite"
    output_dir = tmp_path / "build" / "exports"
    _write_sample_data(data_dir)

    result = subprocess.run(
        [
            sys.executable,
            str(BUILD_RELEASE_SCRIPT),
            "--data-dir",
            str(data_dir),
            "--sqlite-output",
            str(sqlite_path),
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
    for filename in (
        "best-measurements.geojson",
        "best-measurements.csv",
        "best-measurements.gpx",
        "best-measurements.shp.zip",
        "katalog.sqlite.zip",
        "metadata.json",
    ):
        assert (output_dir / filename).exists()
    assert sqlite_path.exists()
    assert "release artifacts: 1 objects, 1 caves, 2 measurements" in result.stdout


def _read_back_release(sqlite_path: Path, output_dir: Path, *, expected_name: str) -> None:
    with sqlite3.connect(sqlite_path) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("SELECT id, name_local FROM objects").fetchall() == [
            ("KSW-0001", expected_name)
        ]
        assert connection.execute(
            "SELECT value FROM metadata WHERE key = 'generated_at'"
        ).fetchone() == (GENERATED_AT,)

    with zipfile.ZipFile(output_dir / "katalog.sqlite.zip") as archive:
        assert archive.namelist() == ["katalog.sqlite"]
        assert archive.testzip() is None
        assert archive.read("katalog.sqlite") == sqlite_path.read_bytes()

    geojson = json.loads((output_dir / "best-measurements.geojson").read_text(encoding="utf-8"))
    assert geojson["generated_at"] == GENERATED_AT
    assert [feature["id"] for feature in geojson["features"]] == ["KSW-0001"]
    assert geojson["features"][0]["properties"]["name_local"] == expected_name

    with (output_dir / "best-measurements.csv").open(encoding="utf-8", newline="") as csv_file:
        csv_rows = list(csv.DictReader(csv_file))
    assert len(csv_rows) == 1
    assert csv_rows[0]["object_id"] == "KSW-0001"
    assert csv_rows[0]["name_local"] == expected_name

    gpx = ET.parse(output_dir / "best-measurements.gpx")
    gpx_namespace = "{http://www.topografix.com/GPX/1/1}"
    assert gpx.findtext(f"{gpx_namespace}metadata/{gpx_namespace}time") == GENERATED_AT
    waypoints = gpx.findall(f"{gpx_namespace}wpt")
    assert len(waypoints) == 1
    assert waypoints[0].findtext(f"{gpx_namespace}name") == "KSW-0001"
    assert expected_name in (waypoints[0].findtext(f"{gpx_namespace}desc") or "")

    with zipfile.ZipFile(output_dir / "best-measurements.shp.zip") as archive:
        assert archive.namelist() == [
            "best-measurements.shp",
            "best-measurements.shx",
            "best-measurements.dbf",
            "best-measurements.prj",
            "best-measurements.cpg",
        ]
        assert archive.testzip() is None
        with shapefile.Reader(
            shp=io.BytesIO(archive.read("best-measurements.shp")),
            shx=io.BytesIO(archive.read("best-measurements.shx")),
            dbf=io.BytesIO(archive.read("best-measurements.dbf")),
            encoding="utf-8",
            encodingErrors="strict",
        ) as reader:
            assert reader.numRecords == 1
            assert reader.record(0)["object_id"] == "KSW-0001"
            assert reader.record(0)["name_local"] == expected_name
            pl_1992 = wgs84_to_1992(lat=KSW_LAT, lon=KSW_LON)
            assert list(reader.shape(0).points[0]) == [pl_1992.y_1992, pl_1992.x_1992]

    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["generated_at"] == GENERATED_AT
    assert metadata["counts"]["objects"] == 1


def _write_sample_data(data_dir: Path) -> None:
    _write_yaml(data_dir / "objects" / "KSW" / "KSW-0001.yml", _valid_object())
    _write_yaml(data_dir / "caves" / "C-0001.yml", _valid_cave())


def _valid_object() -> dict[str, Any]:
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
        "notes": None,
        "created_at": "2026-05-15T10:00:00Z",
        "created_by": "dl",
        "updated_at": "2026-05-16T10:30:00Z",
        "updated_by": "dl",
    }


def _valid_cave() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": "C-0001",
        "name": "Test Cave",
        "system_name": None,
        "external_refs": [
            {
                "system": "PIG",
                "ref_type": "catalog_id",
                "external_id": "1094",
                "url": "https://jaskiniepolski.pgi.gov.pl/Details/Information/1094",
                "scope": "cave",
                "notes": "PIG catalog record identifier.",
            }
        ],
        "object_ids": ["KSW-0001"],
        "notes": None,
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
) -> dict[str, Any]:
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
        "notes": None,
        "created_at": "2026-05-15T10:00:00Z",
        "created_by": "dl",
    }


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(deepcopy(data), sort_keys=False), encoding="utf-8")
