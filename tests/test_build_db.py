import json
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
    _create_schema,
    _insert_measurements,
    build_sqlite_database,
)
from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992
from gps_kataster_obiektow_tatr.data_loader import DataKind, LoadedYamlRecord
from gps_kataster_obiektow_tatr.validator import validate_data_dir

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


@pytest.mark.parametrize("value", [2**63, -(2**63) - 1, -(2**63)])
def test_build_sqlite_database_stores_large_finite_elevation_as_real(
    tmp_path: Path, value: int
) -> None:
    data_dir = tmp_path / "data"
    sqlite_path = tmp_path / "catalog.sqlite"
    obj = _valid_object()
    obj["measurements"][0]["elevation_m"] = value
    _write_yaml(data_dir / "objects" / "KSW" / "KSW-0001.yml", obj)
    _write_yaml(data_dir / "caves" / "C-0001.yml", _valid_cave())

    assert not [issue for issue in validate_data_dir(data_dir) if issue.severity == "error"]
    build_sqlite_database(data_dir=data_dir, output_path=sqlite_path, generated_at=GENERATED_AT)

    with _connect(sqlite_path) as connection:
        row = connection.execute(
            "SELECT elevation_m, typeof(elevation_m) AS storage_type FROM measurements "
            "WHERE object_id = 'KSW-0001' AND id = 'm-001'"
        ).fetchone()
    assert row["storage_type"] == "real"
    assert row["elevation_m"] == float(value)


@pytest.mark.parametrize(
    "field",
    (
        "lat",
        "lon",
        "x_1992",
        "y_1992",
        "elevation_m",
        "horizontal_accuracy_m",
        "vertical_accuracy_m",
    ),
)
def test_measurement_real_fields_bind_large_finite_int_as_float(field: str) -> None:
    measurement = _measurement("m-001", source="PIG", observed_date="2026-05-15")
    measurement[field] = 2**63
    obj = _valid_object()
    obj["measurements"] = [measurement]
    record = LoadedYamlRecord(
        kind=DataKind.OBJECT,
        path=Path("KSW-0001.yml"),
        data=obj,
        raw_data=obj,
    )

    with sqlite3.connect(":memory:") as connection:
        _create_schema(connection)
        _insert_measurements(connection, (record,))
        row = connection.execute(
            f"SELECT {field}, typeof({field}) FROM measurements WHERE id = 'm-001'"
        ).fetchone()
    assert row == (float(2**63), "real")


def test_unrepresentable_number_preserves_existing_database(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    sqlite_path = tmp_path / "catalog.sqlite"
    _write_sample_data(data_dir)
    build_sqlite_database(data_dir=data_dir, output_path=sqlite_path, generated_at=GENERATED_AT)
    before = sqlite_path.read_bytes()

    obj = _valid_object()
    obj["measurements"][0]["elevation_m"] = 10**400
    _write_yaml(data_dir / "objects" / "KSW" / "KSW-0001.yml", obj)

    with pytest.raises(BuildDatabaseValidationError) as exc_info:
        build_sqlite_database(data_dir=data_dir, output_path=sqlite_path, generated_at=GENERATED_AT)
    assert any(
        issue.code == "NON_FINITE_NUMBER"
        and issue.path == data_dir / "objects" / "KSW" / "KSW-0001.yml"
        and "measurements[0].elevation_m" in issue.description
        for issue in exc_info.value.issues
    )
    assert sqlite_path.read_bytes() == before
    assert not sqlite_path.with_name("catalog.sqlite.tmp").exists()


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


# Distinct, fixed coordinates prevent the wrong history row from satisfying best.
# The EPSG:2180 values are fixture data, not calculated by the SQLite builder.
SEMANTIC_BEST = (49.23479299, 19.87579498, 152289.37229830585, 563736.7149809276)


@pytest.fixture(
    params=[
        (mode, reverse) for mode in ("populated", "null", "omitted") for reverse in (False, True)
    ]
)
def semantic_sqlite(request: pytest.FixtureRequest, tmp_path: Path):
    mode, reverse = request.param
    data_dir = tmp_path / "data"
    object_path = data_dir / "objects" / "KSW" / "KSW-0001.yml"
    obj = _valid_object()
    obj["name_local"] = "Otwór Żółty"
    obj["notes"] = "Notatka obiektu, nie pomiaru."
    obj["id_assignment"].update(
        method="manual", prefix_override_reason="Trwały prefix po decyzji terenowej."
    )
    first, second = obj["measurements"]
    first.update(
        source="wlasne",
        source_ref="GNSS:sesja-Żółta/17",
        elevation_m=1234.56,
        elevation_datum="PL-EVRF2007-NH",
        elevation_source="gnss",
        horizontal_accuracy_m=0.25,
        vertical_accuracy_m=0.0,
        observed_at="2026-05-15T09:12:13Z",
        source_date="2026-05-14",
        method="gnss",
        device="Odbiornik Żółty",
        tags=["gnss", "żółty"],
        verification_status="zweryfikowany",
        verified_by="recenzent",
        verified_at="2026-05-16T08:09:10Z",
        notes="Notatka sesji GNSS.",
        created_by="pomiarowy",
    )
    second.update(
        lat=SEMANTIC_BEST[0],
        lon=SEMANTIC_BEST[1],
        x_1992=SEMANTIC_BEST[2],
        y_1992=SEMANTIC_BEST[3],
        source="PIG",
        observed_date="2026-05-13",
        tags=[],
    )
    measurement_optional = (
        "elevation_m",
        "elevation_datum",
        "elevation_source",
        "horizontal_accuracy_m",
        "vertical_accuracy_m",
        "source_ref",
        "observed_at",
        "source_date",
        "device",
        "verified_by",
        "verified_at",
        "notes",
    )
    for field in measurement_optional:
        second[field] = None
    obj["best_measurement"].update(
        mode="manual", reason="Wskazanie starszego pomiaru katalogowego.", updated_by="operator"
    )
    obj["external_refs"] = [
        {
            "system": "TPN",
            "ref_type": "source_globalid",
            "external_id": "{ŻÓŁTY-17}",
            "url": "https://example.org/tpn/17",
            "scope": "object",
            "notes": "Ref punktu.",
        },
        {
            "system": "inne",
            "ref_type": "other",
            "external_id": "pole-18",
            "url": None,
            "scope": None,
            "notes": None,
        },
    ]
    obj["attachments"] = [
        {
            "id": "a-001",
            "kind": "raport_gnss",
            "measurement_id": "m-001",
            "path": "https://example.org/raport/żółty.pdf",
            "caption": "Raport Żółty",
            "date": "2026-05-15",
            "created_at": "2026-05-17T10:11:12Z",
            "created_by": "autor",
        },
        {
            "id": "a-002",
            "kind": "inne",
            "measurement_id": None,
            "path": "https://example.org/notatka",
            "caption": None,
            "date": None,
            "created_at": "2026-05-18T11:12:13Z",
            "created_by": "archiwista",
        },
    ]
    cave = _valid_cave()
    cave.update(name="Jaskinia Żółta", system_name="System Żółty", notes="Notatka jaskini.")
    cave["external_refs"].append(
        {
            "system": "NR_INWENT",
            "ref_type": "inventory_number",
            "external_id": "T.Ż.17",
            "url": None,
            "scope": None,
            "notes": None,
        }
    )
    if mode != "populated":
        for record, fields in (
            (obj, ("name_local", "notes")),
            (cave, ("system_name", "notes")),
        ):
            for field in fields:
                if mode == "null":
                    record[field] = None
                else:
                    record.pop(field)
    if mode == "omitted":
        for field in measurement_optional:
            second.pop(field)
        for ref in (obj["external_refs"][1], cave["external_refs"][1]):
            for field in ("url", "scope", "notes"):
                ref.pop(field)
        for field in ("measurement_id", "caption", "date"):
            obj["attachments"][1].pop(field)
    if reverse:
        obj["measurements"].reverse()
    _write_yaml(object_path, obj)
    _write_yaml(data_dir / "caves" / "C-0001.yml", cave)
    sqlite_path = tmp_path / "semantic.sqlite"
    result = build_sqlite_database(
        data_dir=data_dir, output_path=sqlite_path, generated_at=GENERATED_AT
    )
    with _connect(sqlite_path) as connection:
        yield connection, result, object_path, mode


def test_sqlite_best_fields_follow_explicit_measurement(semantic_sqlite) -> None:
    connection, _, _, mode = semantic_sqlite
    row = dict(connection.execute("SELECT * FROM objects").fetchone())
    assert row == {
        "id": "KSW-0001",
        "schema_version": 1,
        "category": "jaskinia_otwor",
        "name_local": "Otwór Żółty" if mode == "populated" else None,
        "cave_id": "C-0001",
        "id_assignment_method": "manual",
        "assigned_from_measurement_id": "m-001",
        "assigned_prefix": "KSW",
        "prefix_override_reason": "Trwały prefix po decyzji terenowej.",
        "best_measurement_id": "m-002",
        "computed_best_measurement_id": "m-001",
        "best_lat": SEMANTIC_BEST[0],
        "best_lon": SEMANTIC_BEST[1],
        "best_x_1992": SEMANTIC_BEST[2],
        "best_y_1992": SEMANTIC_BEST[3],
        "best_geom_wgs84": "POINT(19.87579498 49.23479299)",
        "best_geom_1992": "POINT(563736.7149809276 152289.37229830585)",
        "notes": "Notatka obiektu, nie pomiaru." if mode == "populated" else None,
        "created_at": "2026-05-15T10:00:00Z",
        "created_by": "dl",
        "updated_at": "2026-05-16T10:30:00Z",
        "updated_by": "dl",
    }
    best = dict(connection.execute("SELECT * FROM best_measurements").fetchone())
    assert best == {
        "object_id": "KSW-0001",
        "mode": "manual",
        "measurement_id": "m-002",
        "computed_best_measurement_id": "m-001",
        "reason": "Wskazanie starszego pomiaru katalogowego.",
        "updated_at": "2026-05-16T10:30:00Z",
        "updated_by": "operator",
    }


def test_sqlite_preserves_measurement_provenance_and_nulls(semantic_sqlite) -> None:
    connection, _, _, _ = semantic_sqlite
    rows = [dict(row) for row in connection.execute("SELECT * FROM measurements ORDER BY id")]
    assert rows == [
        {
            "object_id": "KSW-0001",
            "id": "m-001",
            "lat": KSW_LAT,
            "lon": KSW_LON,
            "x_1992": 152267.22965516336,
            "y_1992": 563744.2498546313,
            "geom_wgs84": "POINT(19.87589498 49.23459299)",
            "geom_1992": "POINT(563744.2498546313 152267.22965516336)",
            "elevation_m": 1234.56,
            "elevation_datum": "PL-EVRF2007-NH",
            "elevation_source": "gnss",
            "horizontal_accuracy_m": 0.25,
            "vertical_accuracy_m": 0.0,
            "source": "wlasne",
            "source_ref": "GNSS:sesja-Żółta/17",
            "observed_at": "2026-05-15T09:12:13Z",
            "observed_date": "2026-05-15",
            "source_date": "2026-05-14",
            "method": "gnss",
            "device": "Odbiornik Żółty",
            "tags_json": '["gnss", "żółty"]',
            "verification_status": "zweryfikowany",
            "verified_by": "recenzent",
            "verified_at": "2026-05-16T08:09:10Z",
            "notes": "Notatka sesji GNSS.",
            "created_at": "2026-05-15T10:00:00Z",
            "created_by": "pomiarowy",
        },
        {
            "object_id": "KSW-0001",
            "id": "m-002",
            "lat": SEMANTIC_BEST[0],
            "lon": SEMANTIC_BEST[1],
            "x_1992": SEMANTIC_BEST[2],
            "y_1992": SEMANTIC_BEST[3],
            "geom_wgs84": "POINT(19.87579498 49.23479299)",
            "geom_1992": "POINT(563736.7149809276 152289.37229830585)",
            "elevation_m": None,
            "elevation_datum": None,
            "elevation_source": None,
            "horizontal_accuracy_m": None,
            "vertical_accuracy_m": None,
            "source": "PIG",
            "source_ref": None,
            "observed_at": None,
            "observed_date": "2026-05-13",
            "source_date": None,
            "method": "source_record",
            "device": None,
            "tags_json": "[]",
            "verification_status": "nieweryfikowany",
            "verified_by": None,
            "verified_at": None,
            "notes": None,
            "created_at": "2026-05-15T10:00:00Z",
            "created_by": "dl",
        },
    ]


def test_sqlite_preserves_cave_and_typed_external_references(semantic_sqlite) -> None:
    connection, _, _, mode = semantic_sqlite
    cave = dict(connection.execute("SELECT * FROM caves").fetchone())
    members = json.loads(cave.pop("object_ids_json"))
    assert members == ["KSW-0001"]
    assert cave == {
        "id": "C-0001",
        "schema_version": 1,
        "name": "Jaskinia Żółta",
        "system_name": "System Żółty" if mode == "populated" else None,
        "notes": "Notatka jaskini." if mode == "populated" else None,
        "created_at": "2026-05-15T10:00:00Z",
        "created_by": "dl",
        "updated_at": "2026-05-16T10:30:00Z",
        "updated_by": "dl",
    }
    assert [
        tuple(row)
        for row in connection.execute(
            "SELECT object_id, system, ref_type, external_id, url, scope, notes "
            "FROM object_external_refs ORDER BY external_id"
        )
    ] == [
        ("KSW-0001", "inne", "other", "pole-18", None, None, None),
        (
            "KSW-0001",
            "TPN",
            "source_globalid",
            "{ŻÓŁTY-17}",
            "https://example.org/tpn/17",
            "object",
            "Ref punktu.",
        ),
    ]
    assert [
        tuple(row)
        for row in connection.execute(
            "SELECT cave_id, system, ref_type, external_id, url, scope, notes "
            "FROM cave_external_refs ORDER BY external_id"
        )
    ] == [
        (
            "C-0001",
            "PIG",
            "catalog_id",
            "1094",
            "https://jaskiniepolski.pgi.gov.pl/Details/Information/1094",
            "cave",
            "PIG catalog record identifier.",
        ),
        ("C-0001", "NR_INWENT", "inventory_number", "T.Ż.17", None, None, None),
    ]


def test_sqlite_preserves_attachment_fields(semantic_sqlite) -> None:
    connection, _, _, _ = semantic_sqlite
    assert [
        tuple(row)
        for row in connection.execute(
            "SELECT object_id, id, kind, measurement_id, path, caption, date, "
            "created_at, created_by "
            "FROM attachments ORDER BY id"
        )
    ] == [
        (
            "KSW-0001",
            "a-001",
            "raport_gnss",
            "m-001",
            "https://example.org/raport/żółty.pdf",
            "Raport Żółty",
            "2026-05-15",
            "2026-05-17T10:11:12Z",
            "autor",
        ),
        (
            "KSW-0001",
            "a-002",
            "inne",
            None,
            "https://example.org/notatka",
            None,
            None,
            "2026-05-18T11:12:13Z",
            "archiwista",
        ),
    ]


def test_sqlite_metadata_and_flags_preserve_warning_semantics(semantic_sqlite) -> None:
    connection, result, object_path, _ = semantic_sqlite
    assert (
        _metadata(connection)
        == result.metadata
        == {
            "generated_at": GENERATED_AT,
            "schema_version": "1",
            "object_count": "1",
            "cave_count": "1",
            "relation_count": "0",
            "measurement_count": "2",
            "validation_warning_count": "2",
            "validation_error_count": "0",
        }
    )
    flags = [
        tuple(row)
        for row in connection.execute(
            "SELECT code, severity, path, description FROM validation_flags ORDER BY rowid"
        )
    ]
    assert flags == [
        (
            "MISSING_HORIZONTAL_ACCURACY",
            "warning",
            str(object_path),
            "Object KSW-0001 measurement m-002 has no horizontal_accuracy_m.",
        ),
        (
            "MISSING_SOURCE_REF",
            "warning",
            str(object_path),
            "Object KSW-0001 measurement m-002 has no source_ref.",
        ),
    ]
    assert [
        (issue.code, str(issue.severity), issue.path, issue.description)
        for issue in result.validation_issues
    ] == [
        (
            "MISSING_HORIZONTAL_ACCURACY",
            "warning",
            object_path,
            "Object KSW-0001 measurement m-002 has no horizontal_accuracy_m.",
        ),
        (
            "MISSING_SOURCE_REF",
            "warning",
            object_path,
            "Object KSW-0001 measurement m-002 has no source_ref.",
        ),
    ]
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
