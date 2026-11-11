"""Native GDAL GeoPackage production and independent complete readback."""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from contextlib import closing
from pathlib import Path

from gps_kataster_obiektow_tatr.export_data import (
    FULL_FIELDS,
    NUMERIC_FIELDS,
    ExportData,
    ExportRecord,
)

_CatalogueTables = Mapping[str, Sequence[ExportRecord]]
# The first field is the domain ID. The boolean declares NOT NULL.
_CATALOGUE_FIELDS = {
    "caves": {"cave_id": True, "name": True, "system_cave_id": False},
    "objects": {"object_id": True, "name": False, "cave_id": False, "category": True},
}
_CATALOGUE_FK = {"caves": "system_cave_id", "objects": "cave_id"}


def _run(command):
    return subprocess.run(command, check=True, capture_output=True, text=True, timeout=180)


def write_geopackage(export_data: ExportData, output_path: Path) -> None:
    """Write EPSG:2180 points and full catalogue tables, then verify all data."""
    binary = shutil.which("ogr2ogr")
    if not binary:
        raise ValueError("ogr2ogr unavailable; GeoPackage generation/readback is mandatory")
    layers = {"best": export_data.selected, "measurements": export_data.history}
    with tempfile.TemporaryDirectory(prefix="kataster-gpkg-") as temporary:
        for index, (layer, records) in enumerate(layers.items()):
            # A non-exported schema feature declares nullable types for empty/all-null columns.
            dummy = {key: 0.0 if key in NUMERIC_FIELDS else "" for key in FULL_FIELDS}
            features = [
                {
                    "type": "Feature",
                    "properties": {**dummy, "real_record": 0},
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                }
            ]
            for record in records:
                props = {key: record.get(key) for key in FULL_FIELDS}
                features.append(
                    {
                        "type": "Feature",
                        "properties": {**props, "real_record": 1},
                        "geometry": {
                            "type": "Point",
                            "coordinates": [record["y_1992"], record["x_1992"]],
                        },
                    }
                )
            source = Path(temporary) / f"{layer}.geojson"
            source.write_text(
                json.dumps(
                    {
                        "type": "FeatureCollection",
                        "name": "source",
                        "crs": {"type": "name", "properties": {"name": "EPSG:2180"}},
                        "features": features,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            query = (
                "SELECT "
                + ",".join('"' + key + '"' for key in FULL_FIELDS)
                + ", geometry FROM source WHERE real_record = 1"
            )
            _run(
                [
                    binary,
                    *(["-update"] if index else []),
                    "-f",
                    "GPKG",
                    str(output_path),
                    str(source),
                    "-nln",
                    layer,
                    "-nlt",
                    "POINT",
                    "-a_srs",
                    "EPSG:2180",
                    "-dialect",
                    "SQLITE",
                    "-sql",
                    query,
                ]
            )
    catalogue_tables = {
        "caves": tuple(
            {"cave_id": r["cave_id"], "name": r["cave_name"], "system_cave_id": r["system_cave_id"]}
            for r in export_data.caves
        ),
        "objects": export_data.objects,
    }
    _write_catalogue_tables(output_path, catalogue_tables)
    verify_geopackage(output_path, layers, catalogue_tables=catalogue_tables, binary=binary)


def _write_catalogue_tables(path: Path, catalogue_tables: _CatalogueTables) -> None:
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN")
        # A cave can precede its parent in ID order. Enforce the references at commit.
        db.execute("PRAGMA defer_foreign_keys=ON")
        db.execute(
            """CREATE TABLE caves (
                fid INTEGER PRIMARY KEY,
                cave_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                system_cave_id TEXT REFERENCES caves(cave_id)
            )"""
        )
        db.execute(
            """CREATE TABLE objects (
                fid INTEGER PRIMARY KEY,
                object_id TEXT NOT NULL UNIQUE,
                name TEXT,
                cave_id TEXT REFERENCES caves(cave_id),
                category TEXT NOT NULL
            )"""
        )
        for table, fields in _CATALOGUE_FIELDS.items():
            id_field = next(iter(fields))
            records = sorted(catalogue_tables[table], key=lambda row: row[id_field])
            columns = ",".join(fields)
            placeholders = ",".join("?" for _ in fields)
            db.executemany(
                f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
                (tuple(row[field] for field in fields) for row in records),
            )
            db.execute(
                "INSERT INTO gpkg_contents (table_name, data_type, identifier) "
                "VALUES (?, 'attributes', ?)",
                (table, table),
            )


def verify_geopackage(
    path: Path, layers, *, catalogue_tables: _CatalogueTables, binary=None
) -> None:
    """Read all four tables with SQLite and GDAL and check the catalogue constraints."""
    if catalogue_tables.keys() != _CATALOGUE_FIELDS.keys():
        raise ValueError("GeoPackage readback requires expected caves and objects")

    binary = binary or shutil.which("ogr2ogr")
    if not binary:
        raise ValueError("ogr2ogr unavailable; GeoPackage readback is mandatory")
    with closing(sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)) as db:
        if (
            db.execute("PRAGMA application_id").fetchone() != (0x47504B47,)
            or db.execute("PRAGMA user_version").fetchone()[0] < 10200
        ):
            raise ValueError("GeoPackage header must declare version 1.2 or newer")
        if (
            db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]
            or db.execute("PRAGMA foreign_key_check").fetchall()
        ):
            raise ValueError("GeoPackage integrity check failed")
        if db.execute(
            "SELECT table_name,geometry_type_name,srs_id,z,m "
            "FROM gpkg_geometry_columns ORDER BY table_name"
        ).fetchall() != [("best", "POINT", 2180, 0, 0), ("measurements", "POINT", 2180, 0, 0)]:
            raise ValueError("GeoPackage layer geometry/CRS declaration differs")
        for layer, records in layers.items():
            fields = {row[1]: row[2].upper() for row in db.execute(f"PRAGMA table_info({layer})")}
            expected_fields = {
                key: "REAL" if key in NUMERIC_FIELDS else "TEXT" for key in FULL_FIELDS
            }
            if any(fields.get(key) != declared for key, declared in expected_fields.items()):
                raise ValueError(f"GeoPackage {layer} field declarations differ")
            columns = ",".join('"' + key + '"' for key in FULL_FIELDS)
            stored = db.execute(
                f"SELECT {columns} FROM {layer} ORDER BY object_id,measurement_id"
            ).fetchall()
            wanted = [
                tuple(r.get(k) for k in FULL_FIELDS)
                for r in sorted(records, key=lambda r: (r["object_id"], r["measurement_id"]))
            ]
            if stored != wanted:
                raise ValueError(f"GeoPackage {layer} stored attributes differ")
            readback = json.loads(
                _run(
                    [binary, "-f", "GeoJSON", "/vsistdout/", str(path), layer, "-lco", "RFC7946=NO"]
                ).stdout
            )
            if (
                readback.get("crs", {}).get("properties", {}).get("name")
                != "urn:ogc:def:crs:EPSG::2180"
            ):
                raise ValueError(f"GeoPackage {layer} GDAL CRS differs")
            actual = readback["features"]
            expected = {(r["object_id"], r["measurement_id"]): r for r in records}
            if len(expected) != len(records) or len(actual) != len(records):
                raise ValueError(f"GeoPackage {layer} counts/identities differ")
            seen = set()
            for feature in actual:
                props = feature["properties"]
                key = props.get("object_id"), props.get("measurement_id")
                if key in seen or key not in expected:
                    raise ValueError(f"GeoPackage {layer} duplicate/unexpected composite ID")
                seen.add(key)
                record = expected[key]
                normalized = dict(props)
                for field in (
                    "tags_json",
                    "object_external_refs",
                    "cave_external_refs",
                    "attachments",
                    "relations",
                ):
                    if isinstance(normalized.get(field), (dict, list)):
                        normalized[field] = json.dumps(
                            normalized[field], ensure_ascii=False, sort_keys=True
                        )
                # GDAL GeoJSON serializes double values with limited decimal precision.
                # Stored GeoPackage doubles above must match exactly; this separate
                # GDAL readback accepts only serialization rounding below 10 nanometres.
                for field in NUMERIC_FIELDS:
                    actual_value, expected_value = normalized.get(field), record.get(field)
                    if (
                        isinstance(actual_value, (int, float))
                        and isinstance(expected_value, (int, float))
                        and abs(actual_value - expected_value) <= 1e-8
                    ):
                        normalized[field] = expected_value
                if normalized != {k: record.get(k) for k in FULL_FIELDS}:
                    raise ValueError(
                        f"GeoPackage {layer} attributes differ for {key}: "
                        + repr(
                            {
                                k: (normalized.get(k), record.get(k))
                                for k in set(normalized) | set(FULL_FIELDS)
                                if normalized.get(k) != record.get(k)
                            }
                        )
                    )
                geom = feature["geometry"]
                if (
                    geom is None
                    or geom["type"] != "Point"
                    or len(geom["coordinates"]) != 2
                    or any(
                        abs(a - b) > 1e-8
                        for a, b in zip(
                            geom["coordinates"], [record["y_1992"], record["x_1992"]], strict=True
                        )
                    )
                ):
                    raise ValueError(f"GeoPackage {layer} geometry differs for {key}")

        _verify_catalogue_tables(db, path, catalogue_tables, binary)


def _verify_catalogue_tables(db, path, catalogue_tables, binary):
    for table, fields in _CATALOGUE_FIELDS.items():
        id_field = next(iter(fields))
        _verify_catalogue_schema(db, table, fields, id_field)
        stored = db.execute(
            f"SELECT {','.join(fields)} FROM {table} ORDER BY {id_field}"
        ).fetchall()
        expected = sorted(catalogue_tables[table], key=lambda row: row[id_field])
        if stored != [tuple(row[field] for field in fields) for row in expected]:
            raise ValueError(f"GeoPackage {table} stored attributes differ")

        readback = json.loads(
            _run(
                [
                    binary,
                    "-f",
                    "GeoJSON",
                    "/vsistdout/",
                    str(path),
                    table,
                    "-lco",
                    "AUTODETECT_JSON_STRINGS=NO",
                ]
            ).stdout
        )
        features = readback["features"]
        actual = sorted(
            (feature["properties"] for feature in features),
            key=lambda row: str(row.get(id_field)),
        )
        if any(feature["geometry"] is not None for feature in features) or actual != [
            {field: row[field] for field in fields} for row in expected
        ]:
            raise ValueError(f"GeoPackage {table} GDAL attributes/geometry differ")

    _verify_system_cycles(dict(db.execute("SELECT cave_id,system_cave_id FROM caves")))


def _verify_catalogue_schema(db, table, fields, id_field):
    registration = db.execute(
        "SELECT data_type,min_x,min_y,max_x,max_y,srs_id FROM gpkg_contents WHERE table_name=?",
        (table,),
    ).fetchall()
    if registration != [("attributes", None, None, None, None, None)]:
        raise ValueError(f"GeoPackage {table} attribute registration differs")
    table_type = db.execute("SELECT type FROM sqlite_schema WHERE name=?", (table,)).fetchone()
    declarations = [
        (name, kind.upper(), required, pk, hidden)
        for _, name, kind, required, _, pk, hidden in db.execute(f"PRAGMA table_xinfo({table})")
    ]
    if table_type != ("table",) or declarations != [
        ("fid", "INTEGER", 0, 1, 0),
        *((field, "TEXT", required, 0, 0) for field, required in fields.items()),
    ]:
        raise ValueError(f"GeoPackage {table} field declarations differ")

    indexes = db.execute(f"PRAGMA index_list({table})").fetchall()
    if any(origin == "pk" for _, _, _, origin, _ in indexes):
        raise ValueError(f"GeoPackage {table} fid must be an integer rowid")
    if not any(
        db.execute("SELECT name FROM pragma_index_info(?)", (name,)).fetchall() == [(id_field,)]
        for _, name, unique, _, partial in indexes
        if unique and not partial
    ):
        raise ValueError(f"GeoPackage {table} requires UNIQUE {id_field}")
    references = [
        (parent, source, target)
        for _, _, parent, source, target, *_ in db.execute(f"PRAGMA foreign_key_list({table})")
    ]
    if references != [("caves", _CATALOGUE_FK[table], "cave_id")]:
        raise ValueError(f"GeoPackage {table} foreign key declaration differs")


def _verify_system_cycles(parents):
    checked = set()
    for cave_id in parents:
        chain = set()
        while cave_id is not None and cave_id not in checked:
            if cave_id in chain:
                raise ValueError(f"GeoPackage caves system cycle at {cave_id}")
            chain.add(cave_id)
            cave_id = parents[cave_id]
        checked.update(chain)
