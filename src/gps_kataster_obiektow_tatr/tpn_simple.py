"""Readable local views of a complete TPN source snapshot."""

from __future__ import annotations

import copy
import math
from collections.abc import Callable

from .tpn_download import LAYERS
from .tpn_elevation import ElevationError

AUDIT_FIELDS = {"CREATED_USER", "CREATED_DATE", "LAST_EDITED_USER", "LAST_EDITED_DATE"}
GENERATED_FIELDS = {"lat", "lon", "geometria_dodatkowa", "wysokosc_gruntu_nmt_m", "status_nmt"}


def _coordinates(geometry: dict | None) -> tuple:
    if geometry is None or (isinstance(geometry, dict) and geometry.get("x", "") is None):
        return None, None
    if not isinstance(geometry, dict) or any(
        type(geometry.get(axis)) not in (int, float)
        or not math.isfinite(geometry[axis])
        or not -bound <= geometry[axis] <= bound
        for axis, bound in (("x", 180), ("y", 90))
    ):
        raise ValueError("Invalid WGS84 geometry")
    return geometry["y"], geometry["x"]


def _decode(value, field: dict):
    domain = field.get("domain") or {}
    if domain.get("type") != "codedValue":
        return copy.deepcopy(value)
    matches = [
        item["name"]
        for item in domain["codedValues"]
        if type(item["code"]) is type(value) and item["code"] == value
    ]
    if len(matches) > 1:
        raise ValueError(f"Ambiguous domain for {field['name']}")
    return matches[0] if matches else copy.deepcopy(value)


def simplify_snapshot(snapshot: dict) -> dict:
    """Keep all object fields except editor audit, and expand declared code domains."""
    if snapshot.get("schema_version") != 1 or set(snapshot.get("layers", {})) != set(LAYERS):
        raise ValueError("Expected a complete three-layer TPN snapshot, schema_version 1")
    result = {}
    for name, layer in snapshot["layers"].items():
        feature_set = layer["feature_set"]
        crs = feature_set["spatialReference"]
        if crs.get("latestWkid", crs.get("wkid")) != 4326:
            raise ValueError(f"{name}: expected WGS84 coordinates")
        fields = {field["name"]: field for field in layer["metadata"]["fields"]}
        oid_fields = [
            key for key, field in fields.items() if field.get("type") == "esriFieldTypeOID"
        ]
        if len(oid_fields) != 1:
            raise ValueError(f"{name}: expected one source object ID field")
        features = feature_set["features"]
        ids = [feature["attributes"][oid_fields[0]] for feature in features]
        if (
            len(features) != layer["record_count"]
            or len(set(ids)) != len(ids)
            or sorted(ids) != sorted(layer["object_ids"])
        ):
            raise ValueError(f"{name}: incomplete or duplicate source records")
        rows = []
        expected_attrs = {
            key for key, field in fields.items() if field.get("type") != "esriFieldTypeGeometry"
        }
        for feature in features:
            attrs = feature["attributes"]
            if not expected_attrs.issubset(attrs):
                raise ValueError(f"{name}: incomplete source attributes")
            if GENERATED_FIELDS.intersection(attrs):
                raise ValueError(f"{name}: source fields collide with generated fields")
            lat, lon = _coordinates(feature.get("geometry"))
            row = {
                key: _decode(value, fields.get(key, {}))
                for key, value in attrs.items()
                if key not in AUDIT_FIELDS
            }
            row.update(lat=lat, lon=lon)
            extra = {
                key: value
                for key, value in (feature.get("geometry") or {}).items()
                if key not in {"x", "y"}
            }
            if extra:
                row["geometria_dodatkowa"] = copy.deepcopy(extra)
            rows.append(row)
        result[name] = rows
    return result


def enrich_simple(
    simple: dict,
    *,
    fetch: Callable,
    progress: Callable | None = None,
) -> tuple[dict, dict]:
    """Add ground heights, preserving explicit gaps and full evidence separately.

    Only genuine NO_DATA is a gap; transport, schema and model changes abort.
    The caller publishes the enriched file only when this function finishes.
    """
    result = copy.deepcopy(simple)
    evidence = {}
    done = 0
    total = sum(map(len, result.values()))
    for name, rows in result.items():
        evidence[name] = []
        for row in rows:
            detail = {key: row[key] for key in ("OBJECTID", "GLOBALID") if key in row}
            height = None
            status = "brak_wspolrzednych"
            if row["lat"] is not None and row["lon"] is not None:
                try:
                    reading = fetch(row["lat"], row["lon"])
                except ElevationError as exc:
                    if not str(exc).startswith("NO_DATA:"):
                        raise
                    status = "brak_danych"
                    detail["error"] = str(exc)
                    if hasattr(exc, "evidence"):
                        detail["result"] = exc.evidence
                else:
                    height = round(reading["elevation_m"], 2)
                    status = "ok"
                    detail["result"] = reading
            row["wysokosc_gruntu_nmt_m"] = height
            row["status_nmt"] = status
            detail["status"] = status
            evidence[name].append(detail)
            done += 1
            if progress is not None:
                progress(done, total)
    return result, evidence
