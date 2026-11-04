#!/usr/bin/env python3
"""Read an existing release package and optionally compare it to a frozen baseline."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sqlite3
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from contextlib import closing
from datetime import date, datetime
from math import isclose
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import shapefile
from openpyxl import load_workbook

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gps_kataster_obiektow_tatr.best_measurements_export import GPX_GROUPS, GPX_NS  # noqa: E402
from gps_kataster_obiektow_tatr.data_loader import load_dataset  # noqa: E402
from gps_kataster_obiektow_tatr.excel_export import BEST_COLUMNS, FULL_COLUMNS  # noqa: E402
from gps_kataster_obiektow_tatr.prefix_resolver import resolve_prefix  # noqa: E402

STEM = "best-measurements"
GROUP_FILES = tuple(group[0] for group in GPX_GROUPS)
SHAPE_MEMBERS = {STEM + suffix for suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg")}
TEXT_FILES = (
    STEM + ".csv",
    STEM + ".geojson",
    STEM + ".gpx",
    *GROUP_FILES,
    "metadata.json",
    "statistics.json",
    "statistics.md",
)
COORDS = ("lat", "lon", "x_1992", "y_1992")


def require(condition, label: str) -> None:
    if not condition:
        raise ValueError(label)


def read_db(path: Path) -> tuple[list[tuple], dict[str, list[dict]]]:
    with closing(sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)) as db:
        require(db.execute("PRAGMA integrity_check").fetchall() == [("ok",)], "SQLite integrity")
        require(not db.execute("PRAGMA foreign_key_check").fetchall(), "SQLite foreign keys")
        schema = db.execute(
            "SELECT type, name, sql FROM sqlite_schema ORDER BY type, name"
        ).fetchall()
        db.row_factory = sqlite3.Row
        tables = {}
        for kind, name, _ in schema:
            if kind == "table":
                identifier = '"' + name.replace('"', '""') + '"'
                tables[name] = [dict(row) for row in db.execute(f"SELECT * FROM {identifier}")]
    return schema, tables


def check_fields(row: dict, expected: dict, keys, label: str) -> None:
    for key in keys:
        require(row[key] == expected.get(key), f"{label}.{key}")


def check_db_source(tables: dict, data_dir: Path) -> tuple[dict, dict]:
    dataset = load_dataset(data_dir)
    objects = {record.data["id"]: record.data for record in dataset.objects}
    caves = {record.data["id"]: record.data for record in dataset.caves}
    relations = {record.data["id"]: record.data for record in dataset.relations}
    history = {
        (oid, measurement["id"]): measurement
        for oid, obj in objects.items()
        for measurement in obj["measurements"]
    }
    selected = {oid: obj["best_measurement"]["measurement_id"] for oid, obj in objects.items()}
    for table, source in (("objects", objects), ("caves", caves), ("relations", relations)):
        require(
            Counter(row["id"] for row in tables[table]) == Counter(source.keys()),
            f"SQLite {table} IDs",
        )
        for row in tables[table]:
            label = f"SQLite {table}/{row['id']}"
            raw = source[row["id"]]
            common = {"id", "schema_version", "notes"}
            if table == "objects":
                common.update({"category", "name_local", "cave_id"})
                assignment = dict(raw["id_assignment"])
                assignment["id_assignment_method"] = assignment.pop("method")
                check_fields(row, assignment, assignment.keys(), label)
                require(row["best_measurement_id"] == selected[row["id"]], f"{label} Best ID")
                best = history[row["id"], selected[row["id"]]]
                for key in COORDS:
                    require(row[f"best_{key}"] == best[key], f"{label} Best {key}")
            elif table == "caves":
                common.update({"name", "system_name"})
                require(json.loads(row["object_ids_json"]) == raw["object_ids"], f"{label} members")
            else:
                common.update({"from_object_id", "to_object_id", "relation_type"})
            if table != "relations":
                common.update({"created_at", "created_by", "updated_at", "updated_by"})
            check_fields(row, raw, common, label)

    require(
        Counter((row["object_id"], row["id"]) for row in tables["measurements"])
        == Counter(history.keys()),
        "SQLite measurement IDs",
    )
    for row in tables["measurements"]:
        key = row["object_id"], row["id"]
        raw = history[key]
        label = f"SQLite measurement {key}"
        check_fields(
            row, raw, row.keys() - {"object_id", "tags_json", "geom_wgs84", "geom_1992"}, label
        )
        require(json.loads(row["tags_json"]) == raw["tags"], f"{label}.tags")
        require(
            row["geom_wgs84"] == f"POINT({float(raw['lon'])} {float(raw['lat'])})", f"{label} WGS84"
        )
        require(
            row["geom_1992"] == f"POINT({float(raw['y_1992'])} {float(raw['x_1992'])})",
            f"{label} PL-1992",
        )
    require(
        Counter(row["object_id"] for row in tables["best_measurements"])
        == Counter(selected.keys()),
        "SQLite Best objects",
    )
    for row in tables["best_measurements"]:
        oid = row["object_id"]
        check_fields(
            row,
            objects[oid]["best_measurement"],
            row.keys() - {"object_id", "computed_best_measurement_id"},
            f"SQLite Best {oid}",
        )

    for table, owner, source, field in (
        ("object_external_refs", "object_id", objects, "external_refs"),
        ("cave_external_refs", "cave_id", caves, "external_refs"),
        ("attachments", "object_id", objects, "attachments"),
    ):
        rows = tables[table]
        require(
            len(rows) == sum(len(item[field]) for item in source.values()), f"SQLite {table} count"
        )
        grouped = {}
        for row in rows:
            grouped.setdefault(row[owner], []).append(row)
        for owner_id, item in source.items():
            actual = grouped.get(owner_id, [])
            if table == "attachments":
                actual = sorted(actual, key=lambda row: row["id"])
                expected = sorted(item[field], key=lambda row: row["id"])
            else:
                expected = item[field]
            for row, raw in zip(actual, expected, strict=True):
                check_fields(row, raw, row.keys() - {"rowid", owner}, f"SQLite {table}/{owner_id}")
    return selected, history


def archive_contents(path: Path) -> dict[str, bytes]:
    with ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), f"{path.name}: duplicate ZIP members")
        return {name: archive.read(name) for name in names}


def csv_value(value) -> str:
    if isinstance(value, float):
        return format(value, ".12g")
    return "" if value is None else str(value)


def check_exports(
    directory: Path, sqlite_path: Path, tables: dict, selected: dict, history: dict
) -> None:
    with (directory / (STEM + ".csv")).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    require(Counter(row["object_id"] for row in rows) == Counter(selected.keys()), "CSV object IDs")
    for row in rows:
        oid = row["object_id"]
        mid = selected[oid]
        measurement = history[oid, mid]
        require(row["measurement_id"] == mid, f"CSV {oid} Best measurement")
        for field in (
            *COORDS,
            "elevation_m",
            "source",
            "source_ref",
            "observed_date",
            "method",
            "observed_at",
            "verification_status",
            "horizontal_accuracy_m",
            "vertical_accuracy_m",
        ):
            require(row[field] == csv_value(measurement.get(field)), f"CSV {oid}.{field}")
    csv_by_object = {row["object_id"]: row for row in rows}
    geojson = json.loads((directory / (STEM + ".geojson")).read_text(encoding="utf-8"))
    require(geojson["type"] == "FeatureCollection", "GeoJSON feature collection")
    features = geojson["features"]
    require(
        Counter(feature["id"] for feature in features) == Counter(selected.keys()), "GeoJSON IDs"
    )
    for feature in features:
        oid = feature["id"]
        row = csv_by_object[oid]
        require(
            {key: csv_value(value) for key, value in feature["properties"].items()} == row,
            f"GeoJSON {oid} properties",
        )
        point = history[oid, selected[oid]]
        require(
            feature["geometry"] == {"type": "Point", "coordinates": [point["lon"], point["lat"]]},
            f"GeoJSON {oid} geometry",
        )

    region_by_object = {
        oid: resolve_prefix(lat=history[oid, mid]["lat"], lon=history[oid, mid]["lon"]).prefix
        for oid, mid in selected.items()
    }
    check_gpx(directory / (STEM + ".gpx"), csv_by_object)
    for filename, _, prefixes in GPX_GROUPS:
        check_gpx(
            directory / filename,
            {oid: row for oid, row in csv_by_object.items() if region_by_object[oid] in prefixes},
        )
    check_shape(directory / (STEM + ".shp.zip"), selected, history)
    check_workbook(directory / "katalog.xlsx", csv_by_object, history, selected)

    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    statistics = json.loads((directory / "statistics.json").read_text(encoding="utf-8"))
    counts = {key: len(tables[key]) for key in ("objects", "caves", "measurements", "relations")}
    flags = Counter(row["severity"] for row in tables["validation_flags"])
    require(
        metadata["counts"]
        == {**counts, "validation_errors": flags["error"], "validation_warnings": flags["warning"]},
        "metadata.json counts",
    )
    require(
        statistics["counts"] == {key: counts[key] for key in ("objects", "caves", "measurements")},
        "statistics.json counts",
    )
    for branch, records in (("selected_points", rows), ("measurement_history", history.values())):
        for key in ("source", "verification_status"):
            require(
                statistics[branch][f"by_{key}"] == Counter(record[key] for record in records),
                f"statistics.json {branch}.{key}",
            )
    markdown = (directory / "statistics.md").read_text(encoding="utf-8")
    require(
        statistics["generated_at"] in markdown and markdown.count("<details>") == 3,
        "statistics.md timestamp or language sections",
    )
    require(
        archive_contents(directory / "katalog.sqlite.zip")
        == {sqlite_path.name: sqlite_path.read_bytes()},
        "SQLite ZIP payload differs from standalone SQLite",
    )


def check_gpx(path: Path, expected: dict) -> None:
    root = ET.parse(path).getroot()
    ns = {"g": GPX_NS}
    require(root.tag == f"{{{GPX_NS}}}gpx", f"{path.name} GPX root")
    object_ids = []
    for waypoint in root.findall("g:wpt", ns):
        desc = waypoint.findtext("g:desc", namespaces=ns)
        object_id = desc.split("; object ", 1)[1].split(";", 1)[0]
        object_ids.append(object_id)
        row = expected[object_id]
        require(f"; measurement {row['measurement_id']}; " in desc, f"{path.name} {object_id} Best")
        require(
            waypoint.attrib == {key: row[key] for key in ("lat", "lon")},
            f"{path.name} {object_id} point",
        )
        require(
            waypoint.findtext("g:ele", default="", namespaces=ns) == row["elevation_m"],
            f"{path.name} {object_id} elevation",
        )
    require(Counter(object_ids) == Counter(expected.keys()), f"{path.name} object IDs")


def check_shape(path: Path, selected: dict, history: dict) -> None:
    members = archive_contents(path)
    require(members.keys() == SHAPE_MEMBERS, "Shapefile ZIP member names")
    require(members[STEM + ".cpg"].strip() == b"UTF-8", "Shapefile encoding")
    with shapefile.Reader(
        **{suffix: io.BytesIO(members[f"{STEM}.{suffix}"]) for suffix in ("shp", "shx", "dbf")}
    ) as reader:
        require(reader.shapeType == shapefile.POINT, "Shapefile geometry type")
        object_ids = []
        for feature in reader.iterShapeRecords():
            oid = feature.record["object_id"]
            object_ids.append(oid)
            mid = selected[oid]
            measurement = history[oid, mid]
            require(feature.record["meas_id"] == mid, f"Shapefile {oid} Best")
            require(
                [tuple(point) for point in feature.shape.points]
                == [(measurement["y_1992"], measurement["x_1992"])],
                f"Shapefile {oid} geometry",
            )
            for key, places in (("lat", 8), ("lon", 8), ("x_1992", 3), ("y_1992", 3)):
                require(
                    feature.record[key] == float(f"{measurement[key]:.{places}f}"),
                    f"Shapefile {oid}.{key}",
                )
        require(Counter(object_ids) == Counter(selected.keys()), "Shapefile object IDs")


def xlsx_date(value: str) -> datetime | str:
    parsed = datetime.fromisoformat(value)
    return value if parsed.date() < date(1900, 1, 1) else parsed


def check_workbook(path: Path, csv_rows: dict, history: dict, selected: dict) -> None:
    with closing(load_workbook(path, read_only=True)) as workbook:
        require(workbook.sheetnames == ["Best", "Full"], "XLSX worksheets")
        for name, columns in (("Best", BEST_COLUMNS), ("Full", FULL_COLUMNS)):
            rows = workbook[name].iter_rows(min_row=6, values_only=True)
            require(next(rows) == tuple(column.title for column in columns), f"XLSX {name} headers")
            ids = []
            for values in rows:
                row = {column.key: value for column, value in zip(columns, values, strict=True)}
                oid, mid = row["object_id"], row["measurement_id"]
                ids.append((oid, mid))
                if name == "Best":
                    for column in columns:
                        value = csv_rows[oid][column.key] or None
                        if value is not None and column.number_format:
                            value = (
                                xlsx_date(value) if column.key == "observed_date" else float(value)
                            )
                        require(
                            row[column.key] == value,
                            f"XLSX Best {oid}.{column.key}",
                        )
                else:
                    point = history[oid, mid]
                    require(
                        row["selected"] == ("Tak" if selected[oid] == mid else "Nie"),
                        f"XLSX Full {oid}/{mid} selection",
                    )
                    for key in (*COORDS, "elevation_m"):
                        expected = point.get(key)
                        actual = row[key]
                        require(
                            (actual is None and expected is None)
                            or (
                                actual is not None
                                and expected is not None
                                and isclose(actual, expected, rel_tol=1e-15, abs_tol=0.0)
                            ),
                            f"XLSX Full {oid}/{mid}.{key}",
                        )
            expected_ids = selected.items() if name == "Best" else history.keys()
            require(Counter(ids) == Counter(expected_ids), f"XLSX {name} measurement IDs")


def normalize_flag_paths(rows: list[dict], data_dir: Path | None) -> None:
    for row in rows:
        if row["path"] is None:
            continue
        path = Path(row["path"])
        if data_dir is not None and path.is_absolute() and path.is_relative_to(data_dir.resolve()):
            row["path"] = (Path("data") / path.relative_to(data_dir.resolve())).as_posix()
        elif "data" in path.parts:
            row["path"] = Path(*path.parts[path.parts.index("data") :]).as_posix()


def compare_baseline(
    baseline: Path, schema: list, tables: dict, exports: Path, data_dir: Path
) -> None:
    baseline_sqlite = baseline / "katalog.sqlite"
    baseline_schema, baseline_tables = read_db(baseline_sqlite)
    require(
        archive_contents(baseline / "exports/katalog.sqlite.zip")
        == {baseline_sqlite.name: baseline_sqlite.read_bytes()},
        "baseline SQLite ZIP payload differs from standalone SQLite",
    )
    require(schema == baseline_schema, "baseline SQLite schema differs")
    normalize_flag_paths(tables["validation_flags"], data_dir)
    normalize_flag_paths(baseline_tables["validation_flags"], None)
    for name, rows in tables.items():
        require(rows == baseline_tables[name], f"baseline SQLite table {name} differs")
    for filename in TEXT_FILES:
        require(
            (exports / filename).read_bytes() == (baseline / "exports" / filename).read_bytes(),
            f"baseline {filename} differs",
        )
    filename = STEM + ".shp.zip"
    actual = archive_contents(exports / filename)
    original = archive_contents(baseline / "exports" / filename)
    require(actual == original, f"baseline {filename} ZIP member payload differs")
    actual = archive_contents(exports / "katalog.xlsx")
    original = archive_contents(baseline / "exports/katalog.xlsx")
    # Archive timestamps are outside member contents. Match all workbook XML except
    # the package creation timestamp, which is independently set by the writer.
    for contents in (actual, original):
        core = ET.fromstring(contents["docProps/core.xml"])
        created = core.find("{http://purl.org/dc/terms/}created")
        if created is not None:
            created.text = ""
        contents["docProps/core.xml"] = ET.tostring(core)
    require(actual == original, "baseline katalog.xlsx workbook payload differs")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--sqlite-path", type=Path, required=True)
    parser.add_argument("--exports-dir", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path)
    args = parser.parse_args()
    try:
        schema, tables = read_db(args.sqlite_path)
        selected, history = check_db_source(tables, args.data_dir)
        check_exports(args.exports_dir, args.sqlite_path, tables, selected, history)
        if args.baseline_dir:
            compare_baseline(args.baseline_dir, schema, tables, args.exports_dir, args.data_dir)
    except (
        OSError,
        ValueError,
        KeyError,
        IndexError,
        sqlite3.Error,
        ET.ParseError,
        BadZipFile,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        f"OK: {len(selected)} selected points, {len(history)} measurements, all release formats"
        + (" match baseline" if args.baseline_dir else " verified")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
