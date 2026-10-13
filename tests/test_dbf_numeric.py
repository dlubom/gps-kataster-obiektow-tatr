import csv
import hashlib
import io
import json
import sqlite3
import subprocess
import sys
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest
import shapefile
import yaml
from test_best_measurements_export import (
    GENERATED_AT,
    REPO_ROOT,
    _valid_cave,
    _valid_object,
    _write_yaml,
)

from gps_kataster_obiektow_tatr import best_measurements_export
from gps_kataster_obiektow_tatr.best_measurements_export import (
    _empty_row,
    _write_shapefile_zip,
    export_best_measurements,
)
from gps_kataster_obiektow_tatr.build_db import build_sqlite_database
from gps_kataster_obiektow_tatr.dbf_numeric import DbfNumericOverflowError, validate_dbf_number
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts
from gps_kataster_obiektow_tatr.validator import validate_data_dir


def _write_numeric_data(data_dir: Path, value: float | int | None) -> None:
    first = _valid_object()
    # Exercise the preflight's repository-relative attachment resolution as well.
    first["attachments"] = [
        {
            "id": "a-001",
            "kind": "inne",
            "path": "schema/object.schema.json",
            "created_at": GENERATED_AT,
            "created_by": "dl",
        }
    ]
    second = _valid_object()
    second["id"] = "KSW-0002"
    second["external_refs"] = []
    second["measurements"][1]["elevation_m"] = value
    cave = _valid_cave()
    cave["object_ids"].append("KSW-0002")
    _write_yaml(data_dir / "objects/KSW/KSW-0001.yml", first)
    _write_yaml(data_dir / "objects/KSW/KSW-0002.yml", second)
    _write_yaml(data_dir / "caves/C-0001.yml", cave)


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }


@pytest.mark.parametrize("value", [1e50, -1e50])
@pytest.mark.parametrize("release", [False, True])
@pytest.mark.parametrize("existing", [False, True])
def test_dbf_overflow_blocks_entire_export_before_writes(tmp_path, value, release, existing):
    data_dir = tmp_path / "data"
    _write_numeric_data(data_dir, value)
    assert not [issue for issue in validate_data_dir(data_dir) if issue.severity == "error"]
    source_before = _snapshot(data_dir)
    build_dir = tmp_path / "build"
    sqlite_path = build_dir / "db/katalog.sqlite"
    output_dir = build_dir / "exports"
    if existing:
        sqlite_path.parent.mkdir(parents=True)
        sqlite_path.write_bytes(b"previous sqlite")
        output_dir.mkdir(parents=True)
        for name in (
            "best-measurements.geojson",
            "best-measurements.csv",
            "best-measurements.gpx",
            "best-measurements.shp.zip",
            "katalog.sqlite.zip",
            "metadata.json",
            "unrelated.txt",
        ):
            (output_dir / name).write_bytes(b"previous " + name.encode())
    before = _snapshot(build_dir)

    with pytest.raises(ValueError, match="DBF") as caught:
        if release:
            build_release_artifacts(
                data_dir=data_dir,
                sqlite_path=sqlite_path,
                output_dir=output_dir,
                generated_at=GENERATED_AT,
            )
        else:
            export_best_measurements(
                data_dir=data_dir,
                output_dir=output_dir,
                generated_at=GENERATED_AT,
            )

    message = str(caught.value)
    assert all(part in message for part in ("KSW-0002", "elev_m", "50", "2", str(value)))
    assert _snapshot(build_dir) == before
    assert _snapshot(data_dir) == source_before
    if not existing:
        assert not build_dir.exists()


@pytest.mark.parametrize(
    ("attribute", "field", "decimal"),
    [
        ("lat", "lat", 8),
        ("lon", "lon", 8),
        ("x_1992", "x_1992", 3),
        ("y_1992", "y_1992", 3),
        ("elevation_m", "elev_m", 2),
    ],
)
@pytest.mark.parametrize("value", [1e50, -1e50])
def test_dbf_each_numeric_field_rejects_truncation(tmp_path, attribute, field, decimal, value):
    row = replace(_empty_row(), object_id="KSW-0001", **{attribute: value})
    path = tmp_path / "existing.zip"
    path.write_bytes(b"previous archive")
    with pytest.raises(ValueError, match="DBF") as caught:
        _write_shapefile_zip((_empty_row(), row), path)
    assert field in str(caught.value)
    assert "KSW-0001" in str(caught.value)
    assert str(decimal) in str(caught.value)
    assert path.read_bytes() == b"previous archive"


def _read_dbf(path: Path, index: int = 0):
    with zipfile.ZipFile(path) as archive:
        dbf = archive.read("best-measurements.dbf")
        with shapefile.Reader(
            shp=io.BytesIO(archive.read("best-measurements.shp")),
            shx=io.BytesIO(archive.read("best-measurements.shx")),
            dbf=io.BytesIO(dbf),
            encoding="utf-8",
            encodingErrors="strict",
        ) as reader:
            fields = reader.fields[1:]
            record = reader.record(index)
    header = int.from_bytes(dbf[8:10], "little")
    length = int.from_bytes(dbf[10:12], "little")
    offset = header + index * length + 1
    raw = {}
    for field in fields:
        raw[field.name] = dbf[offset : offset + field.size].decode("utf-8")
        offset += field.size
    return record, raw


@pytest.mark.parametrize(
    "attribute,field,decimal",
    [
        ("lat", "lat", 8),
        ("lon", "lon", 8),
        ("x_1992", "x_1992", 3),
        ("y_1992", "y_1992", 3),
        ("elevation_m", "elev_m", 2),
    ],
)
@pytest.mark.parametrize("negative", [False, True])
def test_dbf_numeric_boundary_keeps_all_50_characters(
    tmp_path, attribute, field, decimal, negative
):
    values = {
        (8, False): (9.999999999999998e40, "99999999999999981277195531206711524196352.00000000"),
        (8, True): (-9.999999999999998e39, "-9999999999999997885934389197745317478400.00000000"),
        (3, False): (9.999999999999998e45, "9999999999999997396096989903011409954252783616.000"),
        (3, True): (-9.999999999999998e44, "-999999999999999771300963996006876032842858496.000"),
        (2, False): (9.999999999999998e46, "99999999999999984102174700855949311516153479168.00"),
        (2, True): (-9.999999999999998e45, "-9999999999999997396096989903011409954252783616.00"),
    }
    value, expected = values[decimal, negative]
    row = replace(_empty_row(), **{attribute: value})
    path = tmp_path / "boundary.zip"
    _write_shapefile_zip((row,), path)
    record, raw = _read_dbf(path)
    assert record[field] == value
    assert raw[field] == expected


@pytest.mark.parametrize("field_type", ["F", "N"])
@pytest.mark.parametrize(
    "value,width,decimal,expected",
    [
        (99.99, 5, 2, "99.99"),
        (-9.99, 5, 2, "-9.99"),
        (1.236, 5, 2, " 1.24"),
        (-1.236, 5, 2, "-1.24"),
        (0, 5, 2, " 0.00"),
        (None, 5, 2, "*****"),
        (99999, 5, 0, "99999"),
        (-9999, 5, 0, "-9999"),
        (99.9, 2, 0, "99"),
        (-9.9, 2, 0, "-9"),
        (2**63 + 1, 19, 0, "9223372036854775809"),
    ],
)
def test_dbf_number_accepts_complete_representation(field_type, value, width, decimal, expected):
    validate_dbf_number(
        value, object_id="KSW-0001", field_name="test_num", width=width, decimal=decimal
    )
    stream = io.BytesIO()
    with shapefile.Writer(dbf=stream) as writer:
        writer.field("test_num", field_type, size=width, decimal=decimal)
        writer.record(value)
    dbf = stream.getvalue()
    header = int.from_bytes(dbf[8:10], "little")
    assert dbf[header + 1 : header + 1 + width].decode("ascii") == expected


@pytest.mark.parametrize(
    "value,width,decimal",
    [
        (99.996, 5, 2),
        (-9.996, 5, 2),
        (100000, 5, 0),
        (-10000, 5, 0),
        (9.999996, 7, 5),
        (-0.999996, 7, 5),
        (1e49, 50, 2),
        (-1e49, 50, 2),
        (99.96, 4, 1),
    ],
)
def test_dbf_number_rejects_overflow_including_rounding(value, width, decimal):
    with pytest.raises(DbfNumericOverflowError) as caught:
        validate_dbf_number(
            value, object_id="KSW-0001", field_name="test_num", width=width, decimal=decimal
        )
    message = str(caught.value)
    assert all(part in message for part in ("DBF", "KSW-0001", "test_num", repr(value)))
    assert f"width={width}" in message
    assert f"decimal={decimal}" in message


@pytest.mark.parametrize(
    "value,expected_raw,expected_dbf",
    [
        (None, "*" * 50, None),
        (2**63, "9223372036854775808.00", float(2**63)),
        (1e46, "9999999999999999931398190359470212947659194368.00", 1e46),
        (-1e46, "-9999999999999999931398190359470212947659194368.00", -1e46),
        (1.236, "1.24", 1.24),
        (-1.236, "-1.24", -1.24),
    ],
)
def test_dbf_legal_values_read_back_and_release_is_repeatable(
    tmp_path, value, expected_raw, expected_dbf
):
    data_dir = tmp_path / "data"
    _write_numeric_data(data_dir, value)
    before = _snapshot(data_dir)
    hashes = []
    for directory in ("first", "second"):
        result = build_release_artifacts(
            data_dir=data_dir,
            sqlite_path=tmp_path / directory / "katalog.sqlite",
            output_dir=tmp_path / directory / "exports",
            generated_at=GENERATED_AT,
        )
        hashes.append(
            {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in result.artifact_paths}
        )
        with sqlite3.connect(result.sqlite_result.sqlite_path) as db:
            assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert db.execute("PRAGMA foreign_key_check").fetchall() == []
            assert db.execute(
                "SELECT elevation_m FROM measurements WHERE object_id='KSW-0002' AND id='m-002'"
            ).fetchone() == (None if value is None else float(value),)
        properties = json.loads(result.export_result.geojson_path.read_text())["features"][1][
            "properties"
        ]
        assert properties["elevation_m"] == value
        with result.export_result.csv_path.open(newline="") as stream:
            row = list(csv.DictReader(stream))[1]
            if value is None:
                assert row["elevation_m"] == ""
            else:
                assert float(row["elevation_m"]) == pytest.approx(value, rel=1e-11)
        record, raw = _read_dbf(result.export_result.shapefile_zip_path, 1)
        assert record["object_id"] == "KSW-0002"
        assert record["elev_m"] == expected_dbf
        assert raw["elev_m"] == expected_raw.rjust(50)
    assert hashes[0] == hashes[1]
    assert len(hashes[0]) == 7
    assert _snapshot(data_dir) == before


@pytest.mark.parametrize("release", [False, True])
@pytest.mark.parametrize("existing", [False, True])
def test_cli_dbf_overflow_preserves_artifacts(tmp_path, release, existing):
    data_dir = tmp_path / "data"
    _write_numeric_data(data_dir, -1e50)
    output_dir = tmp_path / "build/exports"
    sqlite_path = tmp_path / "build/katalog.sqlite"
    if existing:
        output_dir.mkdir(parents=True)
        for name in (
            "best-measurements.geojson",
            "best-measurements.csv",
            "best-measurements.gpx",
            "best-measurements.shp.zip",
            "katalog.sqlite.zip",
            "metadata.json",
        ):
            (output_dir / name).write_bytes(b"previous artifact")
        sqlite_path.write_bytes(b"previous sqlite")
    before = _snapshot(tmp_path / "build")
    command = [
        sys.executable,
        str(
            REPO_ROOT
            / "scripts"
            / ("build_release_artifacts.py" if release else "export_best_measurements.py")
        ),
        "--data-dir",
        str(data_dir),
        "--output-dir",
        str(output_dir),
    ]
    if release:
        command += ["--sqlite-output", str(sqlite_path)]
    result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=REPO_ROOT)
    assert result.returncode == 1
    assert all(part in result.stderr for part in ("DBF", "KSW-0002", "elev_m", "50", "2"))
    assert "Traceback" not in result.stderr
    assert "wrote:" not in result.stdout
    assert _snapshot(tmp_path / "build") == before
    if not existing:
        assert not (tmp_path / "build").exists()


@pytest.mark.parametrize("field_type", ["F", "N"])
@pytest.mark.parametrize(
    "value,expected", [(99.99, "99.99"), (-9.99, "-9.99"), (99.996, None), (-9.996, None)]
)
def test_dbf_writer_honors_declared_numeric_width_and_precision(
    tmp_path, monkeypatch, field_type, value, expected
):
    fields = tuple(
        (name, field_type, 5, 2) if name == "elev_m" else (name, typ, width, decimal)
        for name, typ, width, decimal in best_measurements_export._SHAPEFILE_FIELDS
    )
    monkeypatch.setattr(best_measurements_export, "_SHAPEFILE_FIELDS", fields)
    row = replace(_empty_row(), elevation_m=value)
    path = tmp_path / "declared.zip"
    if expected is None:
        with pytest.raises(DbfNumericOverflowError):
            _write_shapefile_zip((row,), path)
        assert not path.exists()
    else:
        _write_shapefile_zip((row,), path)
        record, raw = _read_dbf(path)
        assert record["elev_m"] == value
        assert raw["elev_m"] == expected


@pytest.mark.parametrize("value", [1e50, -1e50])
def test_dbf_limit_does_not_restrict_standalone_sqlite(tmp_path, value):
    data_dir = tmp_path / "data"
    _write_numeric_data(data_dir, value)
    before = _snapshot(data_dir)
    path = tmp_path / "katalog.sqlite"
    build_sqlite_database(data_dir=data_dir, output_path=path, generated_at=GENERATED_AT)
    with sqlite3.connect(path) as db:
        assert db.execute(
            "SELECT elevation_m FROM measurements WHERE object_id='KSW-0002' AND id='m-002'"
        ).fetchone() == (value,)
    assert _snapshot(data_dir) == before


@pytest.mark.parametrize("value", [1e50, -1e50])
def test_dbf_limit_only_applies_to_exported_best_measurement(tmp_path, value):
    data_dir = tmp_path / "data"
    _write_numeric_data(data_dir, 1240.0)
    path = data_dir / "objects/KSW/KSW-0002.yml"

    obj = yaml.safe_load(path.read_text())
    obj["measurements"][0]["elevation_m"] = value
    _write_yaml(path, obj)
    before = _snapshot(data_dir)
    result = build_release_artifacts(
        data_dir=data_dir,
        sqlite_path=tmp_path / "katalog.sqlite",
        output_dir=tmp_path / "exports",
        generated_at=GENERATED_AT,
    )
    with sqlite3.connect(result.sqlite_result.sqlite_path) as db:
        assert db.execute(
            "SELECT elevation_m FROM measurements WHERE object_id='KSW-0002' AND id='m-001'"
        ).fetchone() == (value,)
    record, _ = _read_dbf(result.export_result.shapefile_zip_path, 1)
    assert record["elev_m"] == 1240.0
    assert _snapshot(data_dir) == before
