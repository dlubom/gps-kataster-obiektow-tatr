"""GeoPackage catalogue tables and readback, independent of point coverage."""

import json
import sqlite3
from dataclasses import replace

import pytest

from gps_kataster_obiektow_tatr import geopackage
from gps_kataster_obiektow_tatr.data_loader import LoadedDataset
from gps_kataster_obiektow_tatr.export_data import prepare_export_data

LAYERS = {"best": (), "measurements": ()}
CAVES = (
    {"cave_id": "C-0001", "name": "Śnieżna", "system_cave_id": "C-0002"},
    {"cave_id": "C-0002", "name": "Wielka Śnieżna", "system_cave_id": None},
)
OBJECTS = (
    {
        "object_id": "MLZ-0001",
        "name": "Otwór główny",
        "cave_id": "C-0001",
        "category": "jaskinia_otwor",
    },
    {"object_id": "MLZ-0002", "name": None, "cave_id": None, "category": "ponor"},
    {"object_id": "MLZ-0003", "name": '["Ł"]', "cave_id": None, "category": "ponor"},
    {"object_id": "MLZ-0004", "name": "", "cave_id": None, "category": "ponor"},
)


@pytest.fixture
def empty_export():
    return prepare_export_data(LoadedDataset(objects=(), caves=(), relations=()))


@pytest.fixture
def catalogue_gpkg(tmp_path, empty_export):
    path = tmp_path / "katalog.gpkg"
    caves = tuple(
        {
            "cave_id": row["cave_id"],
            "cave_name": row["name"],
            "system_cave_id": row["system_cave_id"],
        }
        for row in reversed(CAVES)
    )
    geopackage.write_geopackage(replace(empty_export, caves=caves, objects=OBJECTS[::-1]), path)
    return path


def test_gpkg_has_two_spatial_and_two_attribute_tables(catalogue_gpkg):
    with sqlite3.connect(catalogue_gpkg) as db:
        assert db.execute(
            "SELECT table_name,data_type,srs_id FROM gpkg_contents ORDER BY table_name"
        ).fetchall() == [
            ("best", "features", 2180),
            ("caves", "attributes", None),
            ("measurements", "features", 2180),
            ("objects", "attributes", None),
        ]
        assert (
            db.execute(
                "SELECT min_x,min_y,max_x,max_y FROM gpkg_contents "
                "WHERE data_type='attributes' ORDER BY table_name"
            ).fetchall()
            == [(None,) * 4] * 2
        )
        assert db.execute(
            "SELECT table_name FROM gpkg_geometry_columns ORDER BY table_name"
        ).fetchall() == [("best",), ("measurements",)]
        assert db.execute("PRAGMA application_id").fetchone() == (0x47504B47,)
        assert db.execute("PRAGMA user_version").fetchone()[0] >= 10200


def test_gpkg_catalogue_preserves_all_ids_and_nulls(catalogue_gpkg):
    with sqlite3.connect(catalogue_gpkg) as db:
        db.row_factory = sqlite3.Row
        assert db.execute("SELECT COUNT(*) FROM best").fetchone()[0] == 0
        assert (
            tuple(
                dict(row)
                for row in db.execute("SELECT cave_id,name,system_cave_id FROM caves ORDER BY fid")
            )
            == CAVES
        )
        assert (
            tuple(
                dict(row)
                for row in db.execute(
                    "SELECT object_id,name,cave_id,category FROM objects ORDER BY fid"
                )
            )
            == OBJECTS
        )
        assert not db.execute("SELECT 1 FROM objects WHERE cave_id='C-0002'").fetchall()


def test_empty_gpkg_declares_catalogue_schema(tmp_path, empty_export):
    path = tmp_path / "empty.gpkg"
    geopackage.write_geopackage(empty_export, path)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        assert db.execute("SELECT * FROM caves").fetchall() == []
        assert db.execute("SELECT * FROM objects").fetchall() == []
        assert [r[1:4] + r[5:6] for r in db.execute("PRAGMA table_info(caves)")] == [
            ("fid", "INTEGER", 0, 1),
            ("cave_id", "TEXT", 1, 0),
            ("name", "TEXT", 1, 0),
            ("system_cave_id", "TEXT", 0, 0),
        ]
        assert [r[1:4] + r[5:6] for r in db.execute("PRAGMA table_info(objects)")] == [
            ("fid", "INTEGER", 0, 1),
            ("object_id", "TEXT", 1, 0),
            ("name", "TEXT", 0, 0),
            ("cave_id", "TEXT", 0, 0),
            ("category", "TEXT", 1, 0),
        ]
        db.execute("INSERT INTO caves(cave_id,name) VALUES ('C-0001','Śnieżna')")
        db.execute("INSERT INTO objects(object_id,category) VALUES ('MLZ-0001','ponor')")
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            db.execute("INSERT INTO caves(cave_id,name) VALUES ('C-0001','Drugi wpis')")
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            db.execute("INSERT INTO objects(object_id,category) VALUES ('MLZ-0001','ponor')")
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            db.execute("UPDATE caves SET system_cave_id='C-9999'")
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            db.execute("UPDATE objects SET cave_id='C-9999'")


@pytest.mark.parametrize(
    ("statements", "error"),
    [
        (["DELETE FROM objects WHERE object_id='MLZ-0002'"], "objects.*attributes differ"),
        (
            ["INSERT INTO caves(cave_id,name) VALUES ('C-9999','Nadmiar')"],
            "caves.*attributes differ",
        ),
        (
            ["UPDATE objects SET object_id='MLZ-9999' WHERE object_id='MLZ-0002'"],
            "objects.*attributes differ",
        ),
        (["UPDATE objects SET name='' WHERE object_id='MLZ-0002'"], "objects.*attributes differ"),
        (
            [
                "ALTER TABLE objects RENAME TO old_objects",
                "CREATE TABLE objects (fid INTEGER PRIMARY KEY, object_id TEXT NOT NULL, "
                "name TEXT, cave_id TEXT REFERENCES caves(cave_id), category TEXT NOT NULL)",
                "INSERT INTO objects SELECT * FROM old_objects",
                "INSERT INTO objects(object_id,category) VALUES ('MLZ-0002','ponor')",
                "DROP TABLE old_objects",
            ],
            "objects.*UNIQUE",
        ),
    ],
    ids=["missing", "extra", "wrong-id-same-count", "changed-null", "duplicate"],
)
def test_gpkg_rejects_missing_extra_duplicate_or_changed_catalogue_row(
    catalogue_gpkg, statements, error
):
    with sqlite3.connect(catalogue_gpkg) as db:
        assert db.execute("SELECT name FROM sqlite_schema WHERE name='objects'").fetchone()
        for statement in statements:
            db.execute(statement)

    with pytest.raises(ValueError, match=error):
        geopackage.verify_geopackage(
            catalogue_gpkg, LAYERS, catalogue_tables={"caves": CAVES, "objects": OBJECTS}
        )


@pytest.mark.parametrize(
    ("statement", "error"),
    [
        ("UPDATE objects SET cave_id='C-9999' WHERE object_id='MLZ-0001'", "integrity check"),
        ("UPDATE caves SET system_cave_id='C-9999' WHERE cave_id='C-0001'", "integrity check"),
        (
            "UPDATE gpkg_contents SET srs_id=2180 WHERE table_name='objects'",
            "objects.*registration",
        ),
        ("DELETE FROM gpkg_contents WHERE table_name='caves'", "caves.*registration"),
        (
            "UPDATE gpkg_contents SET data_type='features' WHERE table_name='objects'",
            "objects.*registration",
        ),
        ("PRAGMA user_version=10100", "GeoPackage header"),
    ],
)
def test_gpkg_rejects_bad_catalogue_fk_or_registration(catalogue_gpkg, statement, error):
    with sqlite3.connect(catalogue_gpkg) as db:
        assert db.execute("SELECT name FROM sqlite_schema WHERE name='objects'").fetchone()
        db.execute(statement)

    with pytest.raises(ValueError, match=error):
        geopackage.verify_geopackage(
            catalogue_gpkg, LAYERS, catalogue_tables={"caves": CAVES, "objects": OBJECTS}
        )


@pytest.mark.parametrize("parent", ["C-0001", "C-0002"])
def test_gpkg_rejects_system_cycle_even_when_snapshot_matches(catalogue_gpkg, parent):
    with sqlite3.connect(catalogue_gpkg) as db:
        assert db.execute("SELECT name FROM sqlite_schema WHERE name='caves'").fetchone()
        db.execute("UPDATE caves SET system_cave_id=? WHERE cave_id='C-0002'", (parent,))
    caves = (CAVES[0], {**CAVES[1], "system_cave_id": parent})

    with pytest.raises(ValueError, match="system cycle"):
        geopackage.verify_geopackage(
            catalogue_gpkg, LAYERS, catalogue_tables={"caves": caves, "objects": OBJECTS}
        )


def test_gpkg_rejects_catalogue_gdal_readback_mismatch(catalogue_gpkg, monkeypatch):
    run = geopackage._run

    def corrupt_readback(command):
        result = run(command)
        if "/vsistdout/" in command and "objects" in command:
            payload = json.loads(result.stdout)
            payload["features"][0]["properties"]["category"] = "changed"
            result.stdout = json.dumps(payload)
        return result

    monkeypatch.setattr(geopackage, "_run", corrupt_readback)
    with pytest.raises(ValueError, match="objects.*GDAL.*differ"):
        geopackage.verify_geopackage(
            catalogue_gpkg, LAYERS, catalogue_tables={"caves": CAVES, "objects": OBJECTS}
        )
