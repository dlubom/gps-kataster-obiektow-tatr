"""Control cases for the independent release audit, not catalogue expectations."""

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from pyproj import Geod

SPEC = importlib.util.spec_from_file_location(
    "audit_release_data", Path(__file__).resolve().parents[1] / "scripts/audit_release_data.py"
)


def auditor():
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
    return module


def test_names_preserve_opening_markers_and_polish_letters():
    audit = auditor()
    assert audit.normalize_name("  ŻÓŁTA\u00a0  I  ") == audit.normalize_name("żółta i")
    assert audit.normalize_name("Żółta I") != audit.normalize_name("Żółta II")
    assert audit.normalize_name("Łąka") != audit.normalize_name("Laka")
    assert audit.normalize_name(" \t\n") == ""


def test_guid_canonicalization_rejects_invalid_and_compares_braces_case():
    audit = auditor()
    assert audit.canonical_guid("{ABCD1234-1234-1234-1234-123456789ABC}") == (
        audit.canonical_guid("abcd1234-1234-1234-1234-123456789abc")
    )
    assert audit.canonical_guid("unknown") is None
    assert audit.canonical_guid("{{abcd1234-1234-1234-1234-123456789abc}}") is None


def test_sqlite_rowid_and_dbf_padding_are_storage_details():
    audit = auditor()
    rows = [{"rowid": 10, "object_id": "A", "system": "TPN", "notes": "źródło"}]
    assert audit.reference_payload(rows, "object_id") == [{"system": "TPN", "notes": "źródło"}]
    assert audit.dbf_text("ó" * 126 + " ó") == "ó" * 126


def test_near_pairs_use_geodesic_distance_all_pairs_and_inclusive_boundary():
    audit = auditor()
    geod = Geod(ellps="WGS84")
    lon, lat, _ = geod.fwd(19.8, 49.2, 90, 0.999)
    lon2, lat2, _ = geod.fwd(19.8, 49.2, 90, 1.001)
    points = [
        {"object_id": "A", "lon": 19.8, "lat": 49.2},
        {"object_id": "B", "lon": lon, "lat": lat},
        {"object_id": "C", "lon": lon2, "lat": lat2},
    ]
    pairs = audit.nearby_pairs(points)
    assert {(a, b) for a, b, _ in pairs} == {("A", "B"), ("B", "C")}
    boundary = geod.inv(19.8, 49.2, lon, lat)[2]
    assert audit.nearby_pairs(points[:2], threshold_m=boundary)
    assert not audit.nearby_pairs(points[:2], threshold_m=boundary - 1e-8)


def tables():
    return {
        "objects": [
            {"id": "A", "name_local": "Otwór I", "cave_id": "C"},
            {"id": "B", "name_local": "Otwór II", "cave_id": "C"},
        ],
        "caves": [{"id": "C", "name": "Jaskinia", "object_ids_json": '["A", "B"]'}],
        "measurements": [
            {"object_id": "A", "id": "m-1", "source": "PIG", "tags_json": '["pig"]'},
            {"object_id": "B", "id": "m-1", "source": "PIG", "tags_json": '["pig"]'},
        ],
        "object_external_refs": [],
        "cave_external_refs": [
            {"cave_id": "C", "system": "PIG", "ref_type": "catalog_id", "external_id": "1"},
            {
                "cave_id": "C",
                "system": "NR_INWENT",
                "ref_type": "inventory_number",
                "external_id": "T.A-1.1",
            },
        ],
    }


def test_shared_cave_number_and_local_measurement_ids_are_not_duplicates():
    findings, _ = auditor().catalog_findings(tables())
    assert findings == []


def test_globalid_collision_is_detected_but_multiple_guids_are_reviewed():
    data = tables()
    guid = "abcd1234-1234-1234-1234-123456789abc"
    data["object_external_refs"] = [
        {"object_id": "A", "system": "TPN", "ref_type": "source_globalid", "external_id": guid},
        {
            "object_id": "B",
            "system": "TPN",
            "ref_type": "source_globalid",
            "external_id": "{" + guid.upper() + "}",
        },
        {
            "object_id": "A",
            "system": "TPN",
            "ref_type": "source_globalid",
            "external_id": "abcd1234-1234-1234-1234-123456789abd",
        },
    ]
    findings, _ = auditor().catalog_findings(data)
    assert any(f["rule"] == "TPN_GUID_COLLISION" for f in findings)
    assert any(f["rule"] == "TPN_MULTIPLE_GUIDS" and f["status"] == "review" for f in findings)


def test_pig_without_inventory_and_tpn_without_tag_or_ref_are_reported():
    data = tables()
    data["cave_external_refs"] = data["cave_external_refs"][:1]
    data["measurements"].append({"object_id": "A", "id": "m-2", "source": "TPN", "tags_json": "[]"})
    findings, _ = auditor().catalog_findings(data)
    rules = {f["rule"] for f in findings}
    assert {"PIG_INVENTORY_MISSING", "TPN_TAG_MISSING", "TPN_OBJECT_REF_MISSING"} <= rules


def test_comparison_does_not_hide_duplicate_rows_or_changed_coordinate():
    audit = auditor().Audit()
    audit.compare(
        "TEST", [{"object_id": "A", "lat": 49.1}] * 2, [{"object_id": "A", "lat": 49.2}], ["lat"]
    )
    assert audit.checks[0]["status"] == "violated"
    assert len(audit.findings) == 3


def test_source_digest_failure_stops_audit(tmp_path):
    module = auditor()
    assets = []
    for name in module.REQUIRED:
        data = b"source"
        if name == "statistics.json":
            data = json.dumps({"release": {"version": "v1.2.0", "source_commit": "sha"}}).encode()
        (tmp_path / name).write_bytes(data)
        assets.append(
            {
                "name": name,
                "size": len(data),
                "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
                "url": "https://example.invalid/" + name,
            }
        )
    (tmp_path / "release.json").write_text(
        json.dumps(
            {
                "assets": assets,
                "tagName": "v1.2.0",
                "url": "https://example.invalid/release",
                "publishedAt": "2026-10-23T15:08:50Z",
            }
        )
    )
    assert module.snapshot(tmp_path, "sha")["release"] == "v1.2.0"
    (tmp_path / "best-measurements.csv").write_bytes(b"modified")
    with pytest.raises(ValueError, match="Source integrity failure"):
        module.snapshot(tmp_path, "sha")


def test_sqlite_geometry_check_detects_axis_swap_and_missing_wkt():
    module = auditor()
    good = {
        "id": "A",
        "lat": 49.2,
        "lon": 19.8,
        "x_1992": 150000.0,
        "y_1992": 560000.0,
        "geom_wgs84": "POINT(19.8 49.2)",
        "geom_1992": "POINT(560000 150000)",
    }
    assert (
        module.sqlite_geometry_findings(
            {"measurements": [{**good, "object_id": "A"}], "objects": []}
        )
        == []
    )
    bad = {**good, "geom_wgs84": "POINT(49.2 19.8)", "geom_1992": None}
    findings = module.sqlite_geometry_findings(
        {"measurements": [{**bad, "object_id": "A"}], "objects": []}
    )
    assert len(findings) == 2
    assert {f["evidence"]["column"] for f in findings} == {"geom_wgs84", "geom_1992"}


def test_gpx_description_source_date_and_notes_are_compared(tmp_path):
    module = auditor()
    row = {
        "object_id": "TST-0001",
        "measurement_id": "m-001",
        "lat": 49.2,
        "lon": 19.8,
        "name_local": "Otwór",
        "category": "jaskinia_otwor",
        "elevation_m": None,
        "observed_at": None,
        "observed_date": "2026-10-23",
        "source": "TPN",
        "object_notes": "uwaga obiektu",
        "cave_notes": "uwaga jaskini",
        "measurement_notes": "uwaga pomiaru",
    }
    with (tmp_path / "best-measurements.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    (tmp_path / "best-measurements.geojson").write_text(
        json.dumps(
            {
                "features": [
                    {
                        "id": row["object_id"],
                        "properties": row,
                        "geometry": {"type": "Point", "coordinates": [19.8, 49.2]},
                    }
                ]
            }
        )
    )
    (tmp_path / "best-measurements.gpx").write_text(
        '<gpx xmlns="http://www.topografix.com/GPX/1/1"><wpt lat="49.2" lon="19.8">'
        "<name>Otwór</name><type>jaskinia_otwor</type><desc>Otwór; object TST-0001; "
        "measurement m-001; source WRONG; observed 1900-01-01</desc></wpt></gpx>"
    )

    class StopAfterGpx(module.Audit):
        def compare(self, label, *args, **kwargs):
            super().compare(label, *args, **kwargs)
            if label == "GPX_SQLITE":
                raise StopIteration

    audit = StopAfterGpx()
    with pytest.raises(StopIteration):
        module.audit_formats(audit, tmp_path, {}, [row])
    assert any(
        f["rule"] == "GPX_SQLITE" and f["evidence"].get("field") == "desc" for f in audit.findings
    )
