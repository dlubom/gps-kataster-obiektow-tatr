"""Native GDAL GeoPackage production and independent complete readback."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from gps_kataster_obiektow_tatr.export_data import FULL_FIELDS, NUMERIC_FIELDS, ExportData


def _run(command):
    return subprocess.run(command, check=True, capture_output=True, text=True, timeout=180)


def write_geopackage(export_data: ExportData, output_path: Path) -> None:
    """Write declared EPSG2180 Point layers, even when empty, then verify all data."""
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
        verify_geopackage(output_path, layers, binary=binary)


def verify_geopackage(path: Path, layers, *, binary=None) -> None:
    """GDAL reads geometry/attributes; SQLite independently checks declarations and IDs."""
    import sqlite3

    binary = binary or shutil.which("ogr2ogr")
    if not binary:
        raise ValueError("ogr2ogr unavailable; GeoPackage readback is mandatory")
    with sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True) as db:
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
