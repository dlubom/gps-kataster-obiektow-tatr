import sqlite3
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml

from gps_kataster_obiektow_tatr.build_db import (
    BuildDatabaseValidationError,
    build_sqlite_database,
)
from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_DB_SCRIPT = REPO_ROOT / "scripts" / "build_db.py"
KSW_LAT = 49.23459299
KSW_LON = 19.87589498
GENERATED_AT = "2026-05-16T12:00:00Z"


def test_build_sqlite_database_writes_logical_tables_and_metadata(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    sqlite_path = tmp_path / "build" / "katalog.sqlite"
    _write_sample_data(data_dir)

    result = build_sqlite_database(
        data_dir=data_dir,
        output_path=sqlite_path,
        generated_at=GENERATED_AT,
    )

    assert result.sqlite_path == sqlite_path
    assert sqlite_path.exists()

    with _connect(sqlite_path) as connection:
        table_names = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        metadata = _metadata(connection)
        object_row = connection.execute("SELECT * FROM objects WHERE id = 'KSW-0001'").fetchone()
        measurement_rows = connection.execute(
            "SELECT id, source, geom_wgs84, geom_1992 FROM measurements ORDER BY id"
        ).fetchall()
        best_row = connection.execute(
            "SELECT * FROM best_measurements WHERE object_id = 'KSW-0001'"
        ).fetchone()
        cave_refs = connection.execute("SELECT * FROM cave_external_refs").fetchall()
        object_refs = connection.execute("SELECT * FROM object_external_refs").fetchall()

    assert table_names >= {
        "objects",
        "caves",
        "measurements",
        "object_external_refs",
        "cave_external_refs",
        "attachments",
        "relations",
        "best_measurements",
        "validation_flags",
        "metadata",
    }
    assert metadata["generated_at"] == GENERATED_AT
    assert metadata["object_count"] == str(len(list((data_dir / "objects").rglob("*.yml"))))
    assert metadata["cave_count"] == str(len(list((data_dir / "caves").rglob("*.yml"))))
    assert metadata["relation_count"] == str(len(list((data_dir / "relations").rglob("*.yml"))))
    assert metadata["measurement_count"] == "2"
    assert metadata["validation_error_count"] == "0"

    pl_1992 = wgs84_to_1992(lat=KSW_LAT, lon=KSW_LON)
    assert object_row["best_measurement_id"] == "m-002"
    assert object_row["computed_best_measurement_id"] == "m-002"
    assert object_row["best_geom_wgs84"] == f"POINT({KSW_LON} {KSW_LAT})"
    assert object_row["best_geom_1992"] == f"POINT({pl_1992.y_1992} {pl_1992.x_1992})"
    assert [row["id"] for row in measurement_rows] == ["m-001", "m-002"]
    assert measurement_rows[1]["source"] == "TPN"
    assert best_row["mode"] == "auto"
    assert best_row["measurement_id"] == "m-002"
    assert best_row["computed_best_measurement_id"] == "m-002"
    assert cave_refs[0]["external_id"] == "1094"
    assert object_refs[0]["external_id"] == "{38626571-CAA6-4317-8900-D61A995020E9}"


def test_build_db_cli_creates_sqlite(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    sqlite_path = tmp_path / "build" / "katalog.sqlite"
    _write_sample_data(data_dir)

    result = subprocess.run(
        [
            sys.executable,
            str(BUILD_DB_SCRIPT),
            "--data-dir",
            str(data_dir),
            "--output",
            str(sqlite_path),
            "--generated-at",
            GENERATED_AT,
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert sqlite_path.exists()
    assert "SQLite build: 1 objects, 1 caves, 2 measurements" in result.stdout


def test_build_sqlite_database_rejects_invalid_yaml(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    sqlite_path = tmp_path / "build" / "katalog.sqlite"
    object_data = _valid_object()
    object_data["best_measurement"]["measurement_id"] = "m-999"
    _write_yaml(data_dir / "objects" / "KSW" / "KSW-0001.yml", object_data)
    _write_yaml(data_dir / "caves" / "C-0001.yml", _valid_cave())

    with pytest.raises(BuildDatabaseValidationError) as exc_info:
        build_sqlite_database(
            data_dir=data_dir,
            output_path=sqlite_path,
            generated_at=GENERATED_AT,
        )

    assert "BEST_MEASUREMENT_MISSING" in {issue.code for issue in exc_info.value.issues}
    assert not sqlite_path.exists()


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
    measurement = {
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
    if source == "wlasne":
        measurement["method"] = "gps_receiver"
    return measurement


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(deepcopy(data), sort_keys=False), encoding="utf-8")


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def _metadata(connection: sqlite3.Connection) -> dict[str, str]:
    return {row["key"]: row["value"] for row in connection.execute("SELECT * FROM metadata")}
