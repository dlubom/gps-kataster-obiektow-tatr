#!/usr/bin/env python3
"""Independently audit a frozen published release; never read or modify YAML.

Exit 0 means the audit ran, not that the dataset passed. Read report.json.
All inputs must match the GitHub SHA-256 receipt in release.json.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import sqlite3
import tempfile
import unicodedata
import uuid
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime
from itertools import combinations
from pathlib import Path
from xml.etree import ElementTree as ET

import openpyxl
import pyproj
import shapefile
from pyproj import Geod, Transformer

GEOD = Geod(ellps="WGS84")
TRANSFORM = Transformer.from_crs(4326, 2180, always_xy=True)
TABLES = (
    "objects",
    "caves",
    "measurements",
    "best_measurements",
    "object_external_refs",
    "cave_external_refs",
    "attachments",
    "relations",
    "metadata",
    "validation_flags",
)
REQUIRED = {
    "best-measurements.csv",
    "best-measurements.geojson",
    "best-measurements.gpx",
    "best-measurements.shp.zip",
    "katalog.sqlite.zip",
    "katalog.xlsx",
    "metadata.json",
    "statistics.json",
    "statistics.md",
}
CATALOG_RULES = (
    "OBJECT_ID_DUPLICATE",
    "CAVE_ID_DUPLICATE",
    "MEASUREMENT_KEY_DUPLICATE",
    "OBJECT_NAME_EMPTY",
    "CAVE_NAME_EMPTY",
    "OBJECT_NAME_DUPLICATE",
    "OBJECT_NAME_NORMALIZED_DUPLICATE",
    "OBJECT_CAVE_LINK",
    "CAVE_OBJECT_LINK",
    "TPN_GUID_INVALID",
    "TPN_GUID_COLLISION",
    "TPN_MULTIPLE_GUIDS",
    "TPN_TAG_MISSING",
    "TPN_OBJECT_REF_MISSING",
    "TPN_MEASUREMENT_REF_MISMATCH",
    "PIG_INVENTORY_MISSING",
    "PIG_CATALOG_COLLISION",
    "INVENTORY_CAVE_COLLISION",
)


def normalize_name(value):
    return " ".join(unicodedata.normalize("NFC", value or "").split()).casefold()


def canonical_guid(value):
    try:
        text = (value or "").strip()
        if text.startswith("{") and text.endswith("}"):
            text = text[1:-1]
        if not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", text):
            return None
        return str(uuid.UUID(text))
    except (ValueError, AttributeError):
        return None


def nearby_pairs(points, threshold_m=1.0):
    """All unordered pairs, horizontal ellipsoidal WGS84 distance, inclusive."""
    pairs = []
    for a, b in combinations(points, 2):
        distance = GEOD.inv(float(a["lon"]), float(a["lat"]), float(b["lon"]), float(b["lat"]))[2]
        if math.isfinite(distance) and distance <= threshold_m:
            pairs.append((a["object_id"], b["object_id"], distance))
    return pairs


def finding(rule, object_ids=(), cave_ids=(), evidence=None, status="violation"):
    return {
        "rule": rule,
        "status": status,
        "object_ids": sorted(set(object_ids)),
        "cave_ids": sorted(set(cave_ids)),
        "evidence": evidence or {},
    }


def groups(rows, key):
    result = defaultdict(list)
    for row in rows:
        result[row[key]].append(row)
    return result


def reference_payload(rows, owner):
    return [{k: v for k, v in row.items() if k not in {owner, "rowid"}} for row in rows]


def dbf_text(text):
    # DBF text has a 254-byte limit and space padding which readers remove.
    return text.encode("utf-8")[:254].decode("utf-8", errors="ignore").rstrip()


def sqlite_geometry_findings(tables):
    problems = []
    for table, prefix in (("measurements", ""), ("objects", "best_")):
        for row in tables[table]:
            for suffix, fields in (("wgs84", ("lon", "lat")), ("1992", ("y_1992", "x_1992"))):
                column = prefix + "geom_" + suffix
                expected = tuple(row[prefix + field] for field in fields)
                match = re.fullmatch(
                    r"POINT\s*\(\s*([-+\d.eE]+)\s+([-+\d.eE]+)\s*\)", row.get(column) or ""
                )
                try:
                    actual = tuple(float(v) for v in match.groups()) if match else None
                except ValueError:
                    actual = None
                if actual != expected:
                    problems.append(
                        finding(
                            "SQLITE_GEOMETRY",
                            [row.get("object_id", row["id"])],
                            evidence={
                                "table": table,
                                "column": column,
                                "record_id": row["id"],
                                "actual_wkt": row.get(column),
                                "expected_xy": expected,
                            },
                        )
                    )
    return problems


def catalog_findings(tables):
    """Identity/provenance checks; count before indexing so collisions survive."""
    findings = []
    objects, caves, measurements = (tables[k] for k in ("objects", "caves", "measurements"))
    for rows, keys, rule in (
        (objects, ("id",), "OBJECT_ID_DUPLICATE"),
        (caves, ("id",), "CAVE_ID_DUPLICATE"),
        (measurements, ("object_id", "id"), "MEASUREMENT_KEY_DUPLICATE"),
    ):
        for key, count in Counter(tuple(r[k] for k in keys) for r in rows).items():
            if count > 1:
                findings.append(finding(rule, evidence={"key": key, "count": count}))
    ob = {r["id"]: r for r in objects}
    ca = {r["id"]: r for r in caves}
    ms = groups(measurements, "object_id")
    ore = groups(tables["object_external_refs"], "object_id")
    cre = groups(tables["cave_external_refs"], "cave_id")
    for rows, name, rule, owner in (
        (objects, "name_local", "OBJECT_NAME_EMPTY", "object_ids"),
        (caves, "name", "CAVE_NAME_EMPTY", "cave_ids"),
    ):
        for row in rows:
            if not normalize_name(row.get(name)):
                findings.append(finding(rule, **{owner: [row["id"]]}))
    for norm, rule in (
        (lambda v: v, "OBJECT_NAME_DUPLICATE"),
        (normalize_name, "OBJECT_NAME_NORMALIZED_DUPLICATE"),
    ):
        names = defaultdict(list)
        for obj in objects:
            if normalize_name(obj.get("name_local")):
                names[norm(obj["name_local"])].append(obj["id"])
        for name, ids in sorted(names.items()):
            if len(ids) > 1:
                findings.append(finding(rule, ids, evidence={"name": name}))
    for obj in objects:
        cave_id = obj.get("cave_id")
        if cave_id and (
            cave_id not in ca or obj["id"] not in json.loads(ca[cave_id]["object_ids_json"])
        ):
            findings.append(finding("OBJECT_CAVE_LINK", [obj["id"]], [cave_id]))
    for cave in caves:
        for oid in json.loads(cave["object_ids_json"]):
            if oid not in ob or ob[oid].get("cave_id") != cave["id"]:
                findings.append(finding("CAVE_OBJECT_LINK", [oid], [cave["id"]]))
    guid_owners = defaultdict(set)
    tpn_objects, pig_objects, pig_caves = set(), set(), set()
    for obj in objects:
        oid = obj["id"]
        refs = [r for r in ore[oid] if r["system"] == "TPN" and r["ref_type"] == "source_globalid"]
        guids = set()
        for ref in refs:
            guid = canonical_guid(ref["external_id"])
            if not guid:
                findings.append(finding("TPN_GUID_INVALID", [oid], evidence={"ref": ref}))
            else:
                guids.add(guid)
                guid_owners[guid].add(oid)
        tpn = [m for m in ms[oid] if m["source"] == "TPN" or "tpn" in json.loads(m["tags_json"])]
        if refs or tpn:
            tpn_objects.add(oid)
            if not guids:
                findings.append(finding("TPN_OBJECT_REF_MISSING", [oid]))
        if len(guids) > 1:
            findings.append(
                finding(
                    "TPN_MULTIPLE_GUIDS", [oid], evidence={"guids": sorted(guids)}, status="review"
                )
            )
        for m in tpn:
            if m["source"] == "TPN" and "tpn" not in json.loads(m["tags_json"]):
                findings.append(
                    finding("TPN_TAG_MISSING", [oid], evidence={"measurement_id": m["id"]})
                )
            ref = m.get("source_ref") or ""
            guid = canonical_guid(ref[4:]) if ref.startswith("TPN:") else None
            if guid not in guids or guid is None:
                findings.append(
                    finding(
                        "TPN_MEASUREMENT_REF_MISMATCH",
                        [oid],
                        evidence={"measurement_id": m["id"], "source_ref": ref},
                    )
                )
        cave_id = obj.get("cave_id")
        if any(m["source"] == "PIG" or "pig" in json.loads(m["tags_json"]) for m in ms[oid]) or any(
            r["system"] == "PIG" for r in cre[cave_id]
        ):
            pig_objects.add(oid)
            pig_caves.add(cave_id)
            if not cave_id or not any(
                r["system"] == "NR_INWENT"
                and r["ref_type"] == "inventory_number"
                and (r["external_id"] or "").strip()
                for r in cre[cave_id]
            ):
                findings.append(
                    finding("PIG_INVENTORY_MISSING", [oid], [cave_id] if cave_id else [])
                )
    for guid, ids in sorted(guid_owners.items()):
        if len(ids) > 1:
            findings.append(finding("TPN_GUID_COLLISION", ids, evidence={"guid": guid}))
    for cave in caves:
        cid = cave["id"]
        if any(r["system"] == "PIG" for r in cre[cid]):
            pig_caves.add(cid)
            if not any(
                r["system"] == "NR_INWENT"
                and r["ref_type"] == "inventory_number"
                and (r["external_id"] or "").strip()
                for r in cre[cid]
            ) and not any(
                f["rule"] == "PIG_INVENTORY_MISSING" and cid in f["cave_ids"] for f in findings
            ):
                findings.append(finding("PIG_INVENTORY_MISSING", cave_ids=[cid]))
    for system, typ, rule in (
        ("PIG", "catalog_id", "PIG_CATALOG_COLLISION"),
        ("NR_INWENT", "inventory_number", "INVENTORY_CAVE_COLLISION"),
    ):
        owners = defaultdict(set)
        for ref in tables["cave_external_refs"]:
            if ref["system"] == system and ref["ref_type"] == typ:
                owners[normalize_name(ref["external_id"])].add(ref["cave_id"])
        for value, ids in sorted(owners.items()):
            if len(ids) > 1:
                findings.append(
                    finding(rule, cave_ids=ids, evidence={"value": value}, status="review")
                )
    return findings, {
        "objects": len(objects),
        "caves": len(caves),
        "measurements": len(measurements),
        "tpn_objects": len(tpn_objects),
        "tpn_distinct_guids": len(guid_owners),
        "pig_objects": len(pig_objects),
        "pig_caves": len(pig_caves),
    }


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(source, source_commit):
    release = json.loads((source / "release.json").read_text())
    if {a["name"] for a in release["assets"]} != REQUIRED:
        raise ValueError("Release asset set differs from the audited nine-file contract")
    assets = []
    for asset in sorted(release["assets"], key=lambda a: a["name"]):
        file = source / asset["name"]
        digest = sha256(file)
        if asset.get("digest") != "sha256:" + digest or file.stat().st_size != asset["size"]:
            raise ValueError(f"Source integrity failure: {file.name}")
        assets.append(
            {"name": file.name, "size": file.stat().st_size, "sha256": digest, "url": asset["url"]}
        )
    stats = json.loads((source / "statistics.json").read_text())
    if stats["release"] != {"version": release["tagName"], "source_commit": source_commit}:
        raise ValueError(
            "Release version/commit does not match statistics and pinned source commit"
        )
    return {
        "release": release["tagName"],
        "release_url": release["url"],
        "published_at": release["publishedAt"],
        "source_commit": source_commit,
        "release_receipt_sha256": sha256(source / "release.json"),
        "assets": assets,
    }


def read_tables(source):
    with zipfile.ZipFile(source / "katalog.sqlite.zip") as archive:
        if archive.namelist() != ["katalog.sqlite"]:
            raise ValueError("Unexpected SQLite archive members")
        data = archive.read("katalog.sqlite")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "catalog.sqlite"
        path.write_bytes(data)
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            db.row_factory = sqlite3.Row
            integrity = [r[0] for r in db.execute("PRAGMA integrity_check")]
            foreign_keys = [list(r) for r in db.execute("PRAGMA foreign_key_check")]
            tables = {
                name: [dict(r) for r in db.execute(f"SELECT * FROM {name} ORDER BY rowid")]
                for name in TABLES
            }
    return tables, {
        "integrity_check": integrity,
        "foreign_key_check": foreign_keys,
        "sqlite_sha256": hashlib.sha256(data).hexdigest(),
    }


def join_refs(refs, system, typ=None):
    return (
        ";".join(
            dict.fromkeys(
                r["external_id"]
                for r in refs
                if r["system"] == system and (typ is None or r["ref_type"] == typ)
            )
        )
        or None
    )


def expected_best(tables):
    ms = {(m["object_id"], m["id"]): m for m in tables["measurements"]}
    choices = {r["object_id"]: r for r in tables["best_measurements"]}
    ore, cre = (
        groups(tables["object_external_refs"], "object_id"),
        groups(tables["cave_external_refs"], "cave_id"),
    )
    hist = groups(tables["measurements"], "object_id")
    caves = {c["id"]: c for c in tables["caves"]}
    rows = []
    for obj in tables["objects"]:
        oid = obj["id"]
        choice = choices[oid]
        m = ms[oid, choice["measurement_id"]]
        refs = cre[obj["cave_id"]]
        guids = [
            r["external_id"]
            for r in ore[oid]
            if r["system"] == "TPN" and r["ref_type"] == "source_globalid"
        ]
        guids += [
            (h["source_ref"] or "")[4:]
            for h in hist[oid]
            if (h["source_ref"] or "").startswith("TPN:{")
        ]
        row = {k: v for k, v in m.items() if k not in {"id", "notes"}}
        row.update(
            object_id=oid,
            measurement_id=m["id"],
            category=obj["category"],
            name_local=obj["name_local"],
            cave_id=obj["cave_id"],
            best_mode=choice["mode"],
            computed_best_measurement_id=choice["computed_best_measurement_id"],
            best_reason=choice["reason"],
            nr_inwent=join_refs(refs, "NR_INWENT"),
            pig_id=join_refs(refs, "PIG", "catalog_id"),
            pig_url=join_refs(refs, "PIG", "url"),
            tpn_globalid=";".join(dict.fromkeys(guids)) or None,
            object_notes=obj["notes"],
            cave_notes=caves.get(obj["cave_id"], {}).get("notes"),
            measurement_notes=m["notes"],
        )
        rows.append(row)
    return rows


def value_equal(a, b, tolerance=0.0, field=""):
    if isinstance(a, (datetime, date)):
        a = a.isoformat()[:10]
    if isinstance(b, (datetime, date)):
        b = b.isoformat()[:10]
    if a in (None, "") or b in (None, ""):
        return a in (None, "") and b in (None, "")
    if isinstance(b, (int, float)) and not isinstance(b, bool):
        try:
            return math.isfinite(float(a)) and abs(float(a) - b) <= tolerance
        except (TypeError, ValueError):
            return False
    if field == "tpn_globalid":
        return {canonical_guid(v) for v in str(a).split(";")} == {
            canonical_guid(v) for v in str(b).split(";")
        }
    return a == b


class Audit:
    def __init__(self):
        self.findings = []
        self.checks = []

    def check(self, rule, checked, problems, evidence=None, success="passed"):
        self.findings.extend(problems)
        statuses = {p["status"] for p in problems}
        status = "violated" if "violation" in statuses else "review" if problems else success
        self.checks.append(
            {
                "rule": rule,
                "status": status,
                "checked": checked,
                "finding_count": len(problems),
                "evidence": evidence or {},
            }
        )

    def compare(self, label, actual, expected, fields, keys=("object_id",), tolerances=None):
        tolerances = tolerances or {}
        problems = []
        actual_keys = Counter(tuple(r[k] for k in keys) for r in actual)
        expected_keys = Counter(tuple(r[k] for k in keys) for r in expected)
        if actual_keys != expected_keys or any(n != 1 for n in actual_keys.values()):
            problems.append(
                finding(
                    label,
                    evidence={
                        "actual_keys": sorted(actual_keys.items()),
                        "expected_keys": sorted(expected_keys.items()),
                    },
                )
            )
        index = {tuple(r[k] for k in keys): r for r in expected}
        for row in actual:
            key = tuple(row[k] for k in keys)
            if key not in index:
                continue
            for field in fields:
                if not value_equal(
                    row.get(field), index[key].get(field), tolerances.get(field, 1e-8), field
                ):
                    problems.append(
                        finding(
                            label,
                            [row["object_id"]],
                            evidence={
                                "key": key,
                                "field": field,
                                "actual": row.get(field),
                                "expected": index[key].get(field),
                            },
                        )
                    )
        self.check(
            label,
            len(actual),
            problems,
            {
                "keys": keys,
                "fields": fields,
                "absolute_tolerances": tolerances,
                "default_numeric_tolerance": 1e-8,
            },
        )


def spreadsheet_rows(sheet):
    rows = list(sheet.values)
    header_index = next(i for i, row in enumerate(rows) if row[0] == "ID obiektu")
    headers = rows[header_index]
    return [
        dict(zip(headers, row, strict=True))
        for row in rows[header_index + 1 :]
        if any(v is not None for v in row)
    ], header_index + 2


XLS_FIELDS = {
    "ID obiektu": "object_id",
    "Nazwa obiektu": "name_local",
    "Rodzaj obiektu": "category",
    "Szerokość WGS84 [°]": "lat",
    "Długość WGS84 [°]": "lon",
    "Wysokość [m]": "elevation_m",
    "Źródło pomiaru": "source",
    "Weryfikacja": "verification_status",
    "Dokładność pozioma [m]": "horizontal_accuracy_m",
    "Data pomiaru": "observed_date",
    "Numer inwentarzowy": "nr_inwent",
    "ID pomiaru": "measurement_id",
    "Odniesienie do źródła": "source_ref",
    "ID jaskini": "cave_id",
    "Nazwa jaskini": "cave_name",
    "System jaskiniowy": "cave_system_name",
    "X PL-1992 [m]": "x_1992",
    "Y PL-1992 [m]": "y_1992",
    "Dokładność pionowa [m]": "vertical_accuracy_m",
    "Układ wysokości": "elevation_datum",
    "Źródło wysokości": "elevation_source",
    "Data źródła": "source_date",
    "Czas pomiaru (ISO 8601)": "observed_at",
    "Metoda pomiaru": "method",
    "Urządzenie": "device",
    "Tagi pomiaru (JSON)": "tags_json",
    "Zweryfikował": "verified_by",
    "Czas weryfikacji (ISO 8601)": "verified_at",
    "Uwagi pomiaru": "measurement_notes",
    "Uwagi obiektu": "object_notes",
    "Uwagi jaskini": "cave_notes",
    "ID PIG": "pig_id",
    "Link PIG": "pig_url",
    "GLOBALID TPN": "tpn_globalid",
    "Wybrany do eksportu": "selected",
    "Załączniki obiektu (JSON)": "attachments",
    "Relacje obiektu (JSON)": "relations",
    "Wersja schematu obiektu": "schema_version",
    "Sposób nadania ID": "id_assignment_method",
    "Pomiar użyty do nadania ID": "assigned_from_measurement_id",
    "Nadany prefiks": "assigned_prefix",
    "Powód nadpisania prefiksu": "prefix_override_reason",
    "Tryb wyboru punktu": "best_mode",
    "ID wybranego pomiaru": "best_measurement_id",
    "ID sugerowanego pomiaru": "computed_best_measurement_id",
    "Uzasadnienie wyboru": "best_reason",
    "Czas wyboru (ISO 8601)": "best_updated_at",
    "Wybrał pomiar": "best_updated_by",
    "Utworzono obiekt (ISO 8601)": "object_created_at",
    "Utworzył obiekt": "object_created_by",
    "Zmieniono obiekt (ISO 8601)": "object_updated_at",
    "Zmienił obiekt": "object_updated_by",
    "Zapisano pomiar (ISO 8601)": "measurement_created_at",
    "Zapisał pomiar": "measurement_created_by",
}


def audit_formats(audit, source, tables, expected):
    with (source / "best-measurements.csv").open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        csv_rows = list(reader)
        csv_fields = reader.fieldnames
    tolerances = {"lat": 5.1e-11, "lon": 5.1e-11}
    audit.compare("CSV_SQLITE", csv_rows, expected, csv_fields, tolerances=tolerances)
    geo = json.loads((source / "best-measurements.geojson").read_text())
    geo_rows = [
        {
            **f["properties"],
            "object_id": f["id"],
            "geometry_lon": f["geometry"]["coordinates"][0],
            "geometry_lat": f["geometry"]["coordinates"][1],
        }
        for f in geo["features"]
    ]
    geo_expected = [{**r, "geometry_lon": r["lon"], "geometry_lat": r["lat"]} for r in expected]
    audit.compare(
        "GEOJSON_SQLITE",
        geo_rows,
        geo_expected,
        [*csv_fields, "geometry_lon", "geometry_lat"],
        tolerances={"lat": 0, "lon": 0},
    )
    ns = {"g": "http://www.topografix.com/GPX/1/1"}
    gpx = []
    for wpt in ET.parse(source / "best-measurements.gpx").findall("g:wpt", ns):
        desc = wpt.findtext("g:desc", "", ns)
        match = re.search(r"object ([A-Z]+-\d+); measurement ([^;]+)", desc)
        if not match:
            raise ValueError("GPX identity/measurement description is not readable")
        gpx.append(
            {
                "object_id": match[1],
                "measurement_id": match[2],
                "lat": wpt.attrib["lat"],
                "lon": wpt.attrib["lon"],
                "name_local": wpt.findtext("g:name", None, ns),
                "category": wpt.findtext("g:type", None, ns),
                "elevation_m": wpt.findtext("g:ele", None, ns),
                "observed_at": wpt.findtext("g:time", None, ns),
                "desc": desc,
            }
        )
    audit.compare(
        "GPX_SQLITE",
        gpx,
        [
            {
                **row,
                "desc": "; ".join(
                    [
                        row["name_local"] or row["object_id"],
                        "object " + row["object_id"],
                        "measurement " + row["measurement_id"],
                        "source " + row["source"],
                        "observed " + row["observed_date"],
                        *[
                            label + ": " + row[key]
                            for label, key in (
                                ("object notes", "object_notes"),
                                ("cave notes", "cave_notes"),
                                ("measurement notes", "measurement_notes"),
                            )
                            if row[key]
                        ],
                    ]
                ),
            }
            for row in expected
        ],
        [
            "object_id",
            "measurement_id",
            "lat",
            "lon",
            "name_local",
            "category",
            "elevation_m",
            "observed_at",
            "desc",
        ],
        tolerances=tolerances,
    )
    with zipfile.ZipFile(source / "best-measurements.shp.zip") as archive:
        reader = shapefile.Reader(
            shp=io.BytesIO(archive.read("best-measurements.shp")),
            shx=io.BytesIO(archive.read("best-measurements.shx")),
            dbf=io.BytesIO(archive.read("best-measurements.dbf")),
            encoding="utf-8",
        )
        mapping = {
            "meas_id": "measurement_id",
            "elev_m": "elevation_m",
            "tpn_gid": "tpn_globalid",
            "obs_date": "observed_date",
            "status": "verification_status",
            "obj_notes": "object_notes",
            "meas_notes": "measurement_notes",
        }
        shp_rows = []
        for item in reader.iterShapeRecords():
            row = {mapping.get(k, k): v for k, v in item.record.as_dict().items()}
            row.update(geometry_x=item.shape.points[0][1], geometry_y=item.shape.points[0][0])
            shp_rows.append(row)
        shp_fields = [mapping.get(f[0], f[0]) for f in reader.fields[1:]]
        expected_shp = []
        for row in expected:
            r = {**row, "geometry_x": row["x_1992"], "geometry_y": row["y_1992"]}
            for name in ("object_notes", "cave_notes", "measurement_notes"):
                if r[name]:
                    r[name] = dbf_text(r[name])
            expected_shp.append(r)
        audit.compare(
            "SHAPEFILE_SQLITE",
            shp_rows,
            expected_shp,
            [*shp_fields, "geometry_x", "geometry_y"],
            tolerances={
                "lat": 5.1e-9,
                "lon": 5.1e-9,
                "x_1992": 0.00051,
                "y_1992": 0.00051,
                "elevation_m": 0.00501,
            },
        )
        actual_crs = pyproj.CRS.from_wkt(archive.read("best-measurements.prj").decode())
        expected_crs = pyproj.CRS(2180)
        audit.check(
            "SHAPEFILE_CRS",
            1,
            []
            if actual_crs.equals(expected_crs, ignore_axis_order=True)
            else [
                finding(
                    "SHAPEFILE_CRS",
                    status="review",
                    evidence={
                        "actual_wkt": actual_crs.to_wkt(),
                        "expected_epsg": 2180,
                        "actual_datum": actual_crs.datum.name,
                        "expected_datum": expected_crs.datum.name,
                        "actual_authority": actual_crs.to_authority(),
                        "note": "PROJ does not equate the declared CRS to EPSG:2180; "
                        "no displacement inferred.",
                    },
                )
            ],
        )
    book = openpyxl.load_workbook(source / "katalog.xlsx", read_only=True, data_only=True)
    best_raw, best_start = spreadsheet_rows(book["Best"])
    full_raw, full_start = spreadsheet_rows(book["Full"])
    if set(best_raw[0]) - XLS_FIELDS.keys() or set(full_raw[0]) - (
        XLS_FIELDS.keys() | {"Referencje obiektu (JSON)", "Referencje jaskini (JSON)"}
    ):
        raise ValueError("Unmapped spreadsheet columns; cannot claim full field coverage")
    stats = json.loads((source / "statistics.json").read_text())
    expected_description = "; ".join(
        [
            stats["release"]["version"],
            stats["release"]["source_commit"],
            stats["generated_at"],
            "CC BY 4.0",
        ]
    )
    audit.check(
        "XLSX_METADATA",
        1,
        []
        if book.properties.description == expected_description
        else [
            finding(
                "XLSX_METADATA",
                evidence={"actual": book.properties.description, "expected": expected_description},
            )
        ],
    )
    best_xls = [{XLS_FIELDS[k]: v for k, v in r.items() if k in XLS_FIELDS} for r in best_raw]
    full_xls = [{XLS_FIELDS[k]: v for k, v in r.items() if k in XLS_FIELDS} for r in full_raw]
    audit.compare("XLSX_BEST_SQLITE", best_xls, expected, list(best_xls[0]), tolerances=tolerances)
    choices = {r["object_id"]: r["measurement_id"] for r in tables["best_measurements"]}
    exp = {r["object_id"]: r for r in expected}
    caves = {r["id"]: r for r in tables["caves"]}
    objects = {r["id"]: r for r in tables["objects"]}
    best = {r["object_id"]: r for r in tables["best_measurements"]}
    attachments = groups(tables["attachments"], "object_id")
    full_expected = []
    for m in tables["measurements"]:
        row = {
            **exp[m["object_id"]],
            **m,
            "measurement_id": m["id"],
            "measurement_notes": m["notes"],
            "selected": "Tak" if m["id"] == choices[m["object_id"]] else "Nie",
        }
        cave = caves.get(row["cave_id"], {})
        row.update(cave_name=cave.get("name"), cave_system_name=cave.get("system_name"))
        obj, choice = objects[m["object_id"]], best[m["object_id"]]
        for key in (
            "schema_version",
            "id_assignment_method",
            "assigned_from_measurement_id",
            "assigned_prefix",
            "prefix_override_reason",
            "best_measurement_id",
        ):
            row[key] = obj[key]
        for key in ("created_at", "created_by", "updated_at", "updated_by"):
            row["object_" + key] = obj[key]
        for key in ("created_at", "created_by"):
            row["measurement_" + key] = m[key]
        for key in ("updated_at", "updated_by"):
            row["best_" + key] = choice[key]
        row["attachments"] = json.dumps(
            reference_payload(attachments[m["object_id"]], "object_id"),
            ensure_ascii=False,
            sort_keys=True,
        )
        row["relations"] = json.dumps(
            [
                r
                for r in tables["relations"]
                if m["object_id"] in {r["from_object_id"], r["to_object_id"]}
            ],
            ensure_ascii=False,
            sort_keys=True,
        )
        full_expected.append(row)
    audit.compare(
        "XLSX_FULL_SQLITE",
        full_xls,
        full_expected,
        list(full_xls[0]),
        keys=("object_id", "measurement_id"),
        tolerances=tolerances,
    )
    # JSON reference cells independently preserve every reference, not only flattened columns.
    ore, cre = (
        groups(tables["object_external_refs"], "object_id"),
        groups(tables["cave_external_refs"], "cave_id"),
    )
    problems = []
    for i, row in enumerate(full_raw, full_start):
        for header, refs, owner in (
            ("Referencje obiektu (JSON)", ore[row["ID obiektu"]], "object_id"),
            ("Referencje jaskini (JSON)", cre[row["ID jaskini"]], "cave_id"),
        ):
            target = reference_payload(refs, owner)
            if json.loads(row[header]) != target:
                problems.append(
                    finding(
                        "XLSX_REFERENCES_SQLITE",
                        [row["ID obiektu"]],
                        evidence={"row": i, "column": header},
                    )
                )
    audit.check("XLSX_REFERENCES_SQLITE", len(full_raw) * 2, problems)
    book.close()
    return csv_rows, {"Best_first_data_row": best_start, "Full_first_data_row": full_start}


def run(source, source_commit):
    manifest = snapshot(source, source_commit)
    tables, integrity = read_tables(source)
    audit = Audit()
    audit.check("SOURCE_DIGESTS", len(manifest["assets"]), [])
    audit.check(
        "SQLITE_INTEGRITY",
        1,
        []
        if integrity["integrity_check"] == ["ok"] and not integrity["foreign_key_check"]
        else [finding("SQLITE_INTEGRITY", evidence=integrity)],
    )
    audit.check(
        "SQLITE_GEOMETRY",
        2 * (len(tables["objects"]) + len(tables["measurements"])),
        sqlite_geometry_findings(tables),
    )
    findings, profile = catalog_findings(tables)
    for rule in CATALOG_RULES:
        audit.check(rule, profile, [f for f in findings if f["rule"] == rule])
    expected = expected_best(tables)
    csv_rows, layout = audit_formats(audit, source, tables, expected)
    invalid, mismatch, accuracy, dem = [], [], [], []
    for m in tables["measurements"]:
        coords = [m[k] for k in ("lat", "lon", "x_1992", "y_1992")]
        ev = {"measurement_id": m["id"], "coordinates": coords}
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in coords) or not (
            -90 <= coords[0] <= 90 and -180 <= coords[1] <= 180
        ):
            invalid.append(finding("COORDINATES_VALID", [m["object_id"]], evidence=ev))
            continue
        easting, northing = TRANSFORM.transform(m["lon"], m["lat"])
        error = math.hypot(northing - m["x_1992"], easting - m["y_1992"])
        if not math.isfinite(error) or error > 0.5:
            mismatch.append(
                finding(
                    "WGS84_PL1992_CONSISTENCY", [m["object_id"]], evidence={**ev, "error_m": error}
                )
            )
        for key in ("horizontal_accuracy_m", "vertical_accuracy_m"):
            if m[key] is not None and (not math.isfinite(m[key]) or m[key] < 0):
                accuracy.append(
                    finding(
                        "ACCURACY_VALUES",
                        [m["object_id"]],
                        evidence={"measurement_id": m["id"], "field": key, "value": m[key]},
                    )
                )
        if m["elevation_source"] == "dem" and not re.search(
            r"NMT|DEM|lidar|https?://", m["notes"] or "", re.I
        ):
            dem.append(
                finding(
                    "DEM_PROVENANCE",
                    [m["object_id"]],
                    evidence={"measurement_id": m["id"]},
                    status="review",
                )
            )
    for rule, problems in (
        ("COORDINATES_VALID", invalid),
        ("WGS84_PL1992_CONSISTENCY", mismatch),
        ("ACCURACY_VALUES", accuracy),
        ("DEM_PROVENANCE", dem),
    ):
        audit.check(rule, len(tables["measurements"]), problems)
    pairs = nearby_pairs(expected)
    indexed = {r["object_id"]: r for r in expected}
    problems = []
    for a, b, distance in pairs:
        evidence = {
            "distance_m": distance,
            "points": [
                {
                    k: indexed[oid][k]
                    for k in (
                        "object_id",
                        "name_local",
                        "cave_id",
                        "lat",
                        "lon",
                        "x_1992",
                        "y_1992",
                        "measurement_id",
                    )
                }
                for oid in (a, b)
            ],
        }
        problems.append(finding("POINTS_WITHIN_1M", [a, b], evidence=evidence))
    audit.check("POINTS_WITHIN_1M", len(expected) * (len(expected) - 1) // 2, problems)
    for fields, rule in (
        (("lat", "lon"), "EXACT_WGS84_DUPLICATE"),
        (("x_1992", "y_1992"), "EXACT_PL1992_DUPLICATE"),
    ):
        by_point = defaultdict(list)
        for r in expected:
            by_point[tuple(r[k] for k in fields)].append(r["object_id"])
        audit.check(
            rule,
            len(expected),
            [
                finding(rule, ids, evidence={"fields": fields, "coordinates": point})
                for point, ids in by_point.items()
                if len(ids) > 1
            ],
        )
    # Cached object best coordinates must agree with the chosen measurement.
    audit.compare(
        "SQLITE_BEST_CACHE",
        [
            {
                "object_id": r["id"],
                "measurement_id": r["best_measurement_id"],
                **{k: r["best_" + k] for k in ("lat", "lon", "x_1992", "y_1992")},
            }
            for r in tables["objects"]
        ],
        expected,
        ["measurement_id", "lat", "lon", "x_1992", "y_1992"],
    )
    metadata = json.loads((source / "metadata.json").read_text())
    stats = json.loads((source / "statistics.json").read_text())
    counts = {k: len(tables[k]) for k in ("objects", "caves", "measurements", "relations")}
    problems = []
    for k, count in counts.items():
        if metadata["counts"][k] != count or (k != "relations" and stats["counts"][k] != count):
            problems.append(finding("ARTIFACT_COUNTS", evidence={"table": k, "actual": count}))
    audit.check("ARTIFACT_COUNTS", 4, problems)
    db_metadata = {r["key"]: r["value"] for r in tables["metadata"]}
    problems = []
    for key, value in counts.items():
        if int(db_metadata[key[:-1] + "_count"]) != value:
            problems.append(finding("ARTIFACT_METADATA", evidence={"field": key}))
    if not (metadata["generated_at"] == stats["generated_at"] == db_metadata["generated_at"]):
        problems.append(finding("ARTIFACT_METADATA", evidence={"field": "generated_at"}))
    audit.check("ARTIFACT_METADATA", 5, problems)
    for key, field in (
        ("by_source", "source"),
        ("by_category", "category"),
        ("by_verification_status", "verification_status"),
    ):
        actual = dict(sorted(Counter(r[field] for r in expected).items()))
        audit.check(
            "STATISTICS_SELECTED_" + key.upper(),
            len(expected),
            []
            if stats["selected_points"][key] == actual
            else [finding("STATISTICS_SELECTED_" + key.upper(), evidence={"actual": actual})],
        )
    for key, field in (("by_source", "source"), ("by_verification_status", "verification_status")):
        actual = dict(sorted(Counter(r[field] for r in tables["measurements"]).items()))
        audit.check(
            "STATISTICS_HISTORY_" + key.upper(),
            len(tables["measurements"]),
            []
            if stats["measurement_history"][key] == actual
            else [finding("STATISTICS_HISTORY_" + key.upper(), evidence={"actual": actual})],
        )
    unknown = sum(r["horizontal_accuracy_m"] is None for r in expected)
    actual_accuracy = {"known": len(expected) - unknown, "unknown": unknown}
    audit.check(
        "STATISTICS_ACCURACY",
        len(expected),
        []
        if stats["selected_points"]["horizontal_accuracy"] == actual_accuracy
        else [finding("STATISTICS_ACCURACY", evidence=actual_accuracy)],
    )
    # All three language tables must carry the same independently counted numbers.
    numeric_rows = [[counts[k]] for k in ("objects", "caves", "measurements")]
    numeric_rows += [
        [sum(r["category"] == cat for r in expected)]
        for cat in ("jaskinia_otwor", "sztolnia", "ponor", "wywierzysko", "inne")
    ]
    numeric_rows += [
        [
            sum(r["source"] == src for r in expected),
            sum(r["source"] == src for r in tables["measurements"]),
        ]
        for src in ("TPN", "PIG", "wlasne", "geoportal", "publikacja", "inne")
    ]
    numeric_rows += [
        [
            sum(r["verification_status"] == state for r in expected),
            sum(r["verification_status"] == state for r in tables["measurements"]),
        ]
        for state in ("zweryfikowany", "nieweryfikowany", "odrzucony")
    ]
    numeric_rows += [[len(expected) - unknown], [unknown]]
    details = re.findall(r"<details>(.*?)</details>", (source / "statistics.md").read_text(), re.S)
    md_problems = []
    if len(details) != 3:
        md_problems.append(
            finding("STATISTICS_MARKDOWN", evidence={"language_count": len(details)})
        )
    for n, detail in enumerate(details):
        actual = [
            [int(v) for v in values if v]
            for values in re.findall(r"^\| [^|]+ \| (\d+) \|(?: (\d+) \|)?$", detail, re.M)
        ]
        if (
            actual != numeric_rows
            or stats["release"]["source_commit"] not in detail
            or ("**" + stats["release"]["version"] + "**") not in detail
        ):
            md_problems.append(
                finding(
                    "STATISTICS_MARKDOWN",
                    evidence={"language_index": n, "actual": actual, "expected": numeric_rows},
                )
            )
    audit.check("STATISTICS_MARKDOWN", 3, md_problems)
    profile["selected_horizontal_accuracy"] = {"known": len(expected) - unknown, "unknown": unknown}
    profile["selected_elevation_source"] = dict(
        sorted(Counter(r["elevation_source"] for r in expected).items())
    )
    profile["selected_elevation_datum"] = dict(
        sorted(Counter(r["elevation_datum"] for r in expected).items())
    )
    profile["history_elevation_source"] = dict(
        sorted(Counter(r["elevation_source"] for r in tables["measurements"]).items())
    )
    audit.check(
        "FIELD_POSITION_ACCURACY",
        len(expected),
        [],
        {
            "unknown": unknown,
            "reason": "No independent surveyed reference points were supplied; "
            "declared accuracy is not measured accuracy.",
        },
        success="unverifiable",
    )
    audit.check(
        "DEM_ENTRANCE_ALTITUDE",
        profile["selected_elevation_source"].get("dem", 0),
        [],
        {"reason": "DEM represents terrain, not verified entrance altitude."},
        success="unverifiable",
    )
    profile["artifact_layout"] = layout
    audit.findings.sort(key=lambda f: (f["rule"], f["object_ids"], f["cave_ids"]))
    for n, f in enumerate(audit.findings, 1):
        f["finding_id"] = f"A{n:04d}"
        f["locations"] = [f"katalog.sqlite:objects.id={oid}" for oid in f["object_ids"]] + [
            f"katalog.sqlite:caves.id={cid}" for cid in f["cave_ids"]
        ]
        for oid in f["object_ids"]:
            if oid in indexed:
                f.setdefault("names", {})[oid] = indexed[oid]["name_local"]
    return manifest, {
        "audit_schema_version": 1,
        "manifest_source_commit": source_commit,
        "profile": profile,
        "integrity": integrity,
        "checks": audit.checks,
        "findings": audit.findings,
        "summary": {
            "by_check_status": dict(Counter(c["status"] for c in audit.checks)),
            "by_finding_rule": dict(sorted(Counter(f["rule"] for f in audit.findings).items())),
            "by_finding_status": dict(Counter(f["status"] for f in audit.findings)),
        },
        "precision": {
            "distance": "WGS84 ellipsoid, unrounded SQLite selected coordinates, <= 1.0 m",
            "coordinate_consistency_m": 0.5,
            "csv_gpx_degree_tolerance": 5.1e-11,
            "shapefile_degree_tolerance": 5.1e-9,
            "shapefile_xy_m_tolerance": 0.00051,
            "shapefile_elevation_m_tolerance": 0.00501,
        },
        "runtime": {
            "pyproj": pyproj.__version__,
            "proj": pyproj.proj_version_str,
            "openpyxl": openpyxl.__version__,
            "pyshp": shapefile.__version__,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    manifest, report = run(args.input_dir, args.source_commit)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in (("manifest.json", manifest), ("report.json", report)):
        (args.output_dir / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )
    (args.output_dir / "release.json").write_bytes((args.input_dir / "release.json").read_bytes())
    with (args.output_dir / "findings.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            lineterminator="\n",
            fieldnames=[
                "finding_id",
                "rule",
                "status",
                "object_ids",
                "cave_ids",
                "names",
                "evidence",
                "locations",
            ],
        )
        writer.writeheader()
        for row in report["findings"]:
            writer.writerow(
                {
                    k: json.dumps(row.get(k, {}), ensure_ascii=False, sort_keys=True)
                    if isinstance(row.get(k), (dict, list))
                    else row.get(k, "")
                    for k in writer.fieldnames
                }
            )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
