#!/usr/bin/env python3
"""Run the complete local/CI gate and read fresh artifacts against source YAML."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import platform
import sqlite3
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile
from collections import Counter
from collections.abc import Sequence
from contextlib import closing
from datetime import UTC, datetime
from importlib.metadata import distributions
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import shapefile
from pyproj import CRS, Transformer

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from gps_kataster_obiektow_tatr.data_loader import load_dataset  # noqa: E402
from gps_kataster_obiektow_tatr.validator import validate_dataset  # noqa: E402

GPX_NS = "{http://www.topografix.com/GPX/1/1}"
COORDINATES = ("lat", "lon", "x_1992", "y_1992")
ARTIFACTS = (
    "katalog.sqlite",
    "exports/best-measurements.csv",
    "exports/best-measurements.geojson",
    "exports/best-measurements.gpx",
    "exports/best-measurements.shp.zip",
    "exports/katalog.sqlite.zip",
    "exports/metadata.json",
)


class VerificationError(ValueError):
    """A gate or artifact contract failed."""


def require(condition: bool, message: str) -> None:
    """Keep checks enabled even when Python runs with optimization."""
    if not condition:
        raise VerificationError(message)


def equal(actual: Any, expected: Any, label: str) -> None:
    require(actual == expected, f"{label}: expected {expected!r}, got {actual!r}")


def numbers(actual: Sequence[Any], expected: Sequence[Any], label: str, tolerance=1e-6) -> None:
    equal(len(actual), len(expected), f"{label} dimensions")
    for value, reference in zip(actual, expected, strict=True):
        if reference is None:
            equal(value, None, label)
        else:
            require(
                value is not None
                and math.isclose(float(value), float(reference), rel_tol=0, abs_tol=tolerance),
                f"{label}: expected {expected!r}, got {actual!r}",
            )


def unique_index(rows, key, label: str) -> dict:
    result = {}
    for row in rows:
        identity = key(row)
        require(identity not in result, f"{label}: duplicate ID {identity}")
        result[identity] = row
    return result


def check_membership(objects: dict, caves: dict) -> None:
    for object_id, obj in objects.items():
        cave_id = obj.get("cave_id")
        if cave_id is not None:
            require(cave_id in caves, f"{object_id}: missing cave {cave_id}")
            equal(
                caves[cave_id].get("object_ids", []).count(object_id),
                1,
                f"{object_id} reverse link",
            )
    for cave_id, cave in caves.items():
        for object_id in cave.get("object_ids", []):
            require(object_id in objects, f"{cave_id}: missing object {object_id}")
            equal(objects[object_id].get("cave_id"), cave_id, f"{cave_id} forward link {object_id}")


def readback_artifacts(data_dir: Path, run_dir: Path, generated_at: str) -> dict:
    """Independently read all formats, without using exporter row-building helpers."""
    for name in ARTIFACTS:
        require((run_dir / name).is_file(), f"Missing fresh artifact: {name}")
    dataset = load_dataset(data_dir)
    objects = unique_index((r.data for r in dataset.objects), lambda r: r["id"], "YAML objects")
    caves = unique_index((r.data for r in dataset.caves), lambda r: r["id"], "YAML caves")
    relations = unique_index(
        (r.data for r in dataset.relations), lambda r: r["id"], "YAML relations"
    )
    check_membership(objects, caves)
    measurements = unique_index(
        ((oid, m) for oid, obj in objects.items() for m in obj["measurements"]),
        lambda item: (item[0], item[1]["id"]),
        "YAML measurements",
    )
    best = {
        oid: measurements[oid, obj["best_measurement"]["measurement_id"]][1]
        for oid, obj in objects.items()
    }
    issues = validate_dataset(dataset, data_dir=data_dir, repo_root=REPO_ROOT)
    warnings = Counter(i.code for i in issues if i.severity == "warning")
    counts = {
        "objects": len(objects),
        "caves": len(caves),
        "relations": len(relations),
        "measurements": len(measurements),
        "validation_warnings": sum(warnings.values()),
        "validation_errors": sum(i.severity == "error" for i in issues),
    }
    equal(counts["validation_errors"], 0, "YAML validation errors")
    exports = run_dir / "exports"
    metadata = json.loads((exports / "metadata.json").read_text(encoding="utf-8"))
    equal(
        metadata,
        {
            "metadata_schema_version": 1,
            "data_schema_version": 1,
            "generated_at": generated_at,
            "counts": counts,
        },
        "metadata.json",
    )
    check_sqlite(
        run_dir / "katalog.sqlite",
        objects,
        caves,
        relations,
        measurements,
        best,
        counts,
        warnings,
        generated_at,
    )
    with zipfile.ZipFile(exports / "katalog.sqlite.zip") as archive:
        check_zip(archive, ["katalog.sqlite"])
        equal(
            archive.read("katalog.sqlite"),
            (run_dir / "katalog.sqlite").read_bytes(),
            "zipped SQLite",
        )
    with (exports / "best-measurements.csv").open(encoding="utf-8", newline="") as stream:
        rows = unique_index(csv.DictReader(stream), lambda r: r["object_id"], "CSV")
    equal(rows.keys(), objects.keys(), "CSV IDs/count")
    for oid, row in rows.items():
        check_flat_row(row, objects[oid], best[oid], "CSV", text=True)
    geojson = json.loads((exports / "best-measurements.geojson").read_text(encoding="utf-8"))
    equal(geojson["type"], "FeatureCollection", "GeoJSON type")
    equal(geojson["generated_at"], generated_at, "GeoJSON timestamp")
    features = unique_index(geojson["features"], lambda f: f["id"], "GeoJSON")
    equal(features.keys(), objects.keys(), "GeoJSON IDs/count")
    for oid, feature in features.items():
        equal(feature["type"], "Feature", f"GeoJSON {oid} type")
        equal(feature["geometry"]["type"], "Point", f"GeoJSON {oid} geometry")
        numbers(
            feature["geometry"]["coordinates"],
            [best[oid]["lon"], best[oid]["lat"]],
            f"GeoJSON {oid} axes",
        )
        check_flat_row(feature["properties"], objects[oid], best[oid], "GeoJSON")
    gpx = ET.parse(exports / "best-measurements.gpx").getroot()
    equal(gpx.tag, GPX_NS + "gpx", "GPX root")
    equal(gpx.findtext(f"{GPX_NS}metadata/{GPX_NS}time"), generated_at, "GPX timestamp")
    waypoints = unique_index(
        gpx.findall(GPX_NS + "wpt"), lambda w: w.findtext(GPX_NS + "name"), "GPX"
    )
    equal(waypoints.keys(), objects.keys(), "GPX IDs/count")
    for oid, waypoint in waypoints.items():
        measurement = best[oid]
        numbers(
            [waypoint.attrib["lat"], waypoint.attrib["lon"]],
            [measurement["lat"], measurement["lon"]],
            f"GPX {oid} axes",
        )
        numbers(
            [waypoint.findtext(GPX_NS + "ele")],
            [measurement.get("elevation_m")],
            f"GPX {oid} elevation",
        )
        equal(waypoint.findtext(GPX_NS + "type"), objects[oid]["category"], f"GPX {oid} category")
        description = waypoint.findtext(GPX_NS + "desc") or ""
        require(
            f"; measurement {measurement['id']}; source {measurement['source']}; " in description,
            f"GPX {oid}: wrong selected measurement",
        )
    check_shapefile(exports / "best-measurements.shp.zip", objects, best)
    return {
        "counts": counts,
        "warnings_by_code": dict(sorted(warnings.items())),
        "artifact_sha256": {
            name: hashlib.sha256((run_dir / name).read_bytes()).hexdigest() for name in ARTIFACTS
        },
    }


def check_flat_row(row: dict, obj: dict, measurement: dict, label: str, *, text=False) -> None:
    expected = {
        "object_id": obj["id"],
        "cave_id": obj.get("cave_id"),
        "measurement_id": measurement["id"],
        "category": obj["category"],
        "best_mode": obj["best_measurement"]["mode"],
        "source": measurement["source"],
        "verification_status": measurement["verification_status"],
    }
    for field, value in expected.items():
        equal(
            row[field],
            ("" if value is None else str(value)) if text else value,
            f"{label} {obj['id']} {field}",
        )
    fields = (*COORDINATES, "elevation_m")
    numbers(
        [None if text and row[k] == "" else row[k] for k in fields],
        [measurement.get(k) for k in fields],
        f"{label} {obj['id']} coordinates",
    )


def check_zip(archive: zipfile.ZipFile, names: list[str]) -> None:
    equal(sorted(archive.namelist()), sorted(names), f"{archive.filename} ZIP entries")
    equal(archive.testzip(), None, f"{archive.filename} ZIP CRC")


def check_shapefile(path: Path, objects: dict, best: dict) -> None:
    with zipfile.ZipFile(path) as archive:
        check_zip(
            archive, [f"best-measurements.{ext}" for ext in ("shp", "shx", "dbf", "prj", "cpg")]
        )
        equal(
            archive.read("best-measurements.cpg").decode("ascii").strip(),
            "UTF-8",
            "Shapefile encoding",
        )
        crs = CRS.from_wkt(archive.read("best-measurements.prj").decode("ascii"))
        require(crs.is_projected, "Shapefile CRS must be projected")
        # The existing ESRI WKT has no EPSG authority and uses a datum alias.
        # Check its actual transform, not a name/authority-string comparison.
        transform = Transformer.from_crs(4326, crs, always_xy=True)
        reference_transform = Transformer.from_crs(4326, 2180, always_xy=True)
        for lon, lat in ((19.8, 49.2), (20.1, 49.3)):
            numbers(
                transform.transform(lon, lat),
                reference_transform.transform(lon, lat),
                "Shapefile CRS projection",
                0.001,
            )
        with shapefile.Reader(
            shp=io.BytesIO(archive.read("best-measurements.shp")),
            shx=io.BytesIO(archive.read("best-measurements.shx")),
            dbf=io.BytesIO(archive.read("best-measurements.dbf")),
            encoding="utf-8",
            encodingErrors="strict",
        ) as reader:
            # Decode every DBF field, including notes, and count shapes independently.
            records = list(reader.iterRecords())
            shapes = list(reader.iterShapes())
            equal(len(records), len(objects), "DBF count")
            equal(len(shapes), len(objects), "SHP count")
            equal(reader.numShapes, len(objects), "SHX count")
            for index, shape in enumerate(shapes):
                indexed_shape = reader.shape(index)
                equal(indexed_shape.shapeType, shape.shapeType, f"SHX {index} type")
                equal(list(indexed_shape.points), list(shape.points), f"SHX {index} points")
            rows = unique_index(
                zip(records, shapes, strict=True), lambda r: r[0]["object_id"], "DBF"
            )
            equal(rows.keys(), objects.keys(), "DBF IDs")
            for oid, (record, shape) in rows.items():
                measurement = best[oid]
                equal(record["meas_id"], measurement["id"], f"DBF {oid} measurement")
                equal(record["cave_id"], objects[oid].get("cave_id") or "", f"DBF {oid} cave")
                equal(record["category"], objects[oid]["category"], f"DBF {oid} category")
                equal(record["source"], measurement["source"], f"DBF {oid} source")
                equal(record["status"], measurement["verification_status"], f"DBF {oid} status")
                numbers(
                    [record[k] for k in ("lat", "lon")],
                    [measurement[k] for k in ("lat", "lon")],
                    f"DBF {oid} WGS84",
                    5.1e-9,
                )
                numbers(
                    [record[k] for k in ("x_1992", "y_1992")],
                    [measurement[k] for k in ("x_1992", "y_1992")],
                    f"DBF {oid} PL-1992",
                    0.00051,
                )
                numbers(
                    [record["elev_m"]],
                    [measurement.get("elevation_m")],
                    f"DBF {oid} elevation",
                    0.0051,
                )
                equal(shape.shapeType, shapefile.POINT, f"SHP {oid} type")
                equal(len(shape.points), 1, f"SHP {oid} points")
                numbers(
                    shape.points[0],
                    [measurement["y_1992"], measurement["x_1992"]],
                    f"SHP {oid} axes",
                )


def check_sqlite(
    path, objects, caves, relations, measurements, best, counts, warnings, generated_at
):
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        equal(db.execute("PRAGMA integrity_check").fetchall(), [("ok",)], "SQLite integrity")
        equal(db.execute("PRAGMA foreign_key_check").fetchall(), [], "SQLite foreign keys")
        db.row_factory = sqlite3.Row
        for table, expected in (("objects", objects), ("caves", caves), ("relations", relations)):
            rows = unique_index(db.execute(f"SELECT * FROM {table}"), lambda r: r["id"], table)
            equal(rows.keys(), expected.keys(), f"SQLite {table} IDs/count")
            if table == "caves":
                for cid, row in rows.items():
                    equal(
                        json.loads(row["object_ids_json"]),
                        caves[cid].get("object_ids", []),
                        f"SQLite {cid} members",
                    )
            elif table == "relations":
                for rid, row in rows.items():
                    for field in ("from_object_id", "to_object_id", "relation_type"):
                        equal(row[field], relations[rid][field], f"SQLite {rid} {field}")
            else:
                for oid, row in rows.items():
                    equal(row["cave_id"], objects[oid].get("cave_id"), f"SQLite {oid} cave")
                    equal(row["best_measurement_id"], best[oid]["id"], f"SQLite {oid} best")
                    numbers(
                        [row[f"best_{k}"] for k in COORDINATES],
                        [best[oid][k] for k in COORDINATES],
                        f"SQLite {oid} best coordinates",
                    )
                    check_wkt(
                        row["best_geom_wgs84"],
                        [best[oid]["lon"], best[oid]["lat"]],
                        f"SQLite {oid} best WGS84",
                    )
                    check_wkt(
                        row["best_geom_1992"],
                        [best[oid]["y_1992"], best[oid]["x_1992"]],
                        f"SQLite {oid} best PL-1992",
                    )
        rows = unique_index(
            db.execute("SELECT * FROM measurements"),
            lambda r: (r["object_id"], r["id"]),
            "SQLite measurements",
        )
        equal(rows.keys(), measurements.keys(), "SQLite measurement IDs/count")
        for identity, row in rows.items():
            measurement = measurements[identity][1]
            fields = (*COORDINATES, "elevation_m")
            numbers(
                [row[k] for k in fields],
                [measurement.get(k) for k in fields],
                f"SQLite {identity} coordinates",
            )
            check_wkt(
                row["geom_wgs84"],
                [measurement["lon"], measurement["lat"]],
                f"SQLite {identity} WGS84",
            )
            check_wkt(
                row["geom_1992"],
                [measurement["y_1992"], measurement["x_1992"]],
                f"SQLite {identity} PL-1992",
            )
        rows = unique_index(
            db.execute("SELECT * FROM best_measurements"), lambda r: r["object_id"], "SQLite best"
        )
        equal(rows.keys(), objects.keys(), "SQLite best IDs/count")
        for oid, row in rows.items():
            for field in ("measurement_id", "mode", "reason"):
                equal(
                    row[field],
                    objects[oid]["best_measurement"].get(field),
                    f"SQLite {oid} best {field}",
                )
        metadata = dict(db.execute("SELECT key, value FROM metadata"))
        equal(metadata["generated_at"], generated_at, "SQLite timestamp")
        equal(metadata["schema_version"], "1", "SQLite schema version")
        for name, key in (
            ("objects", "object"),
            ("caves", "cave"),
            ("relations", "relation"),
            ("measurements", "measurement"),
            ("validation_warnings", "validation_warning"),
            ("validation_errors", "validation_error"),
        ):
            equal(metadata[f"{key}_count"], str(counts[name]), f"SQLite {name} metadata")
        equal(
            Counter(
                row[0]
                for row in db.execute(
                    "SELECT code FROM validation_flags WHERE severity = 'warning'"
                )
            ),
            warnings,
            "SQLite warnings",
        )
        equal(
            db.execute("SELECT count(*) FROM validation_flags WHERE severity = 'error'").fetchone()[
                0
            ],
            0,
            "SQLite errors",
        )


def check_wkt(value: str, expected: list, label: str) -> None:
    require(value.startswith("POINT(") and value.endswith(")"), f"{label}: invalid WKT {value}")
    numbers(value[6:-1].split(), expected, label)


def hash_paths(root: Path, paths: Sequence[Path]) -> str:
    """Hash sorted path, type/mode and content hashes; no timestamps or absolute paths."""
    digest = hashlib.sha256()
    for path in sorted(set(paths)):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            payload, mode = str(path.readlink()).encode(), "symlink"
        elif path.is_file():
            payload, mode = path.read_bytes(), str(path.stat().st_mode & 0o111)
        else:
            payload, mode = b"", "missing"
        digest.update(
            json.dumps(
                [relative, mode, hashlib.sha256(payload).hexdigest()],
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode()
            + b"\n"
        )
    return digest.hexdigest()


def data_hash(root: Path) -> str:
    require(root.is_dir(), f"Missing data directory: {root}")
    return hash_paths(root, [p for p in root.rglob("*") if p.is_file() or p.is_symlink()])


def tree_identity(root: Path) -> dict:
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root)

    names = git("ls-files", "--cached", "--others", "--exclude-standard", "-z").decode().split("\0")
    paths = [root / n for n in names if n and Path(n).parts[0] != "build"]
    return {
        "base_sha": git("rev-parse", "HEAD").decode().strip(),
        "tree_sha256": hash_paths(root, paths),
        "git_status": git("status", "--short").decode(),
    }


def execute(command: list[str], cwd: Path, log_path: Path) -> int:
    """Preserve the command's exit code and combined output, including launch failures."""
    with log_path.open("w", encoding="utf-8") as log:
        try:
            return subprocess.run(
                command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, check=False
            ).returncode
        except OSError as exc:
            log.write(f"{type(exc).__name__}: {exc}\n")
            return 127


def verify_project(repo_root: Path = REPO_ROOT) -> tuple[int, Path]:
    """Fail fast, retain evidence, and check source immutability even on stage failure."""
    parent = repo_root / "build" / "verification"
    parent.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=parent))
    report_path = run_dir / "report.json"
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    report = {
        "report_schema_version": 1,
        "generated_at": generated_at,
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "packages": dict(sorted((d.metadata["Name"], d.version) for d in distributions())),
        "stages": [],
        "exit_code": 1,
    }
    code = 1
    try:
        report["source_before"] = tree_identity(repo_root)
        report["data_before_sha256"] = data_hash(repo_root / "data")
        commands = [
            ("uv-version", ["uv", "--version"]),
            ("git-version", ["git", "--version"]),
            (
                "format",
                [sys.executable, "-m", "ruff", "format", "--check", "src", "tests", "scripts"],
            ),
            ("lint", [sys.executable, "-m", "ruff", "check", "src", "tests", "scripts"]),
            ("tests", [sys.executable, "-m", "pytest"]),
            ("validate", [sys.executable, "scripts/validate.py"]),
            (
                "build",
                [
                    sys.executable,
                    "scripts/build_release_artifacts.py",
                    "--sqlite-output",
                    str(run_dir / "katalog.sqlite"),
                    "--output-dir",
                    str(run_dir / "exports"),
                    "--generated-at",
                    generated_at,
                ],
            ),
        ]
        for name, command in commands:
            started = time.monotonic()
            log_path = run_dir / f"{name}.log"
            code = execute(command, repo_root, log_path)
            report["stages"].append(
                {
                    "name": name,
                    "command": command,
                    "exit_code": code,
                    "log": log_path.name,
                    "seconds": round(time.monotonic() - started, 3),
                }
            )
            print(f"{name}: exit {code} ({log_path})", flush=True)
            if code:
                break
        if code == 0:
            stage = {
                "name": "readback",
                "command": [
                    "internal:readback_artifacts",
                    str(repo_root / "data"),
                    str(run_dir),
                    generated_at,
                ],
                "exit_code": 1,
            }
            report["stages"].append(stage)
            report["readback"] = readback_artifacts(repo_root / "data", run_dir, generated_at)
            stage["exit_code"] = 0
            print("readback: exit 0", flush=True)
    except Exception:
        code = 1
        report["error"] = traceback.format_exc()
    finally:
        try:
            report["source_after"] = tree_identity(repo_root)
            report["data_after_sha256"] = data_hash(repo_root / "data")
            require(
                report.get("data_before_sha256") == report["data_after_sha256"],
                "Source data changed during verification",
            )
            require(
                report.get("source_before") == report["source_after"],
                "Verified tree changed during verification",
            )
            report["immutability_exit_code"] = 0
        except Exception:
            code = code or 1
            report["immutability_exit_code"] = 1
            report["immutability_error"] = traceback.format_exc()
        report["exit_code"] = code
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(f"Verification exit {code}; report: {report_path}", flush=True)
    return code, report_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    code, _ = verify_project()
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
