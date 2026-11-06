"""Map canonical catalogue records to bound database values."""

from __future__ import annotations

import math
from typing import Any

from gps_kataster_obiektow_tatr.measurement_values import non_finite_measurement_fields
from gps_kataster_obiektow_tatr.urls import valid_absolute_url

ENTITY_TABLES = {
    "object": "objects",
    "cave": "caves",
    "relation": "relations",
    "publication": "publications",
}
COMMON = ("created_at", "created_by", "updated_at", "updated_by")
FIELDS = {
    "objects": (
        "schema_version",
        "id",
        "category",
        "name_local",
        "cave_id",
        "membership_ordinal",
        "bibliography_status",
        "bibliography_note",
        "notes",
        *COMMON,
    ),
    "caves": (
        "schema_version",
        "id",
        "name",
        "system_name",
        "bibliography_status",
        "bibliography_note",
        "notes",
        *COMMON,
    ),
    "relations": (
        "schema_version",
        "id",
        "from_object_id",
        "to_object_id",
        "relation_type",
        "notes",
    ),
    "publications": (
        "id",
        "citation",
        "authors",
        "title",
        "publication_year",
        "container_title",
        "issue",
        "url",
        "doi",
        "isbn",
    ),
    "measurements": (
        "id",
        "elevation_m",
        "elevation_datum",
        "elevation_source",
        "horizontal_accuracy_m",
        "vertical_accuracy_m",
        "source",
        "source_ref",
        "observed_at",
        "observed_date",
        "source_date",
        "method",
        "device",
        "verification_status",
        "verified_by",
        "verified_at",
        "notes",
        "created_at",
        "created_by",
    ),
    "best_policy": ("mode", "reason", "updated_at", "updated_by"),
    "external_refs": ("system", "ref_type", "external_id", "url", "scope", "notes"),
    "attachments": (
        "id",
        "kind",
        "measurement_id",
        "path",
        "caption",
        "date",
        "created_at",
        "created_by",
    ),
    "citations": ("publication_id", "locator", "name_in_source", "purpose", "notes"),
    "measurement_citations": ("publication_id", "locator", "notes"),
}
ASSIGNMENT = ("method", "assigned_from_measurement_id", "assigned_prefix", "prefix_override_reason")
COORDINATES = ("lat", "lon", "x_1992", "y_1992", "input_srid", "input_x", "input_y")
INTEGER_FIELDS = {"schema_version", "membership_ordinal", "publication_year", "input_srid"}
NUMBER_FIELDS = {"elevation_m", "horizontal_accuracy_m", "vertical_accuracy_m", *COORDINATES}


def _mapping(data: object, context: str) -> dict:
    if not isinstance(data, dict) or any(not isinstance(key, str) for key in data):
        raise ValueError(f"{context} must be a mapping with string keys")
    return data


def _scalar(context: str, key: str, value: object) -> None:
    if value is None:
        return  # Required fields and nullability belong to the SQL schema.
    if key in INTEGER_FIELDS:
        valid = type(value) is int
    elif key in NUMBER_FIELDS:
        valid = type(value) in (int, float) and math.isfinite(value)
    else:
        valid = isinstance(value, str) and "\x00" not in value
    if not valid:
        raise ValueError(f"Invalid scalar type or value for {context}.{key}")
    if key == "url" and not valid_absolute_url(value):
        raise ValueError(f"Invalid url for {context}.{key}: {value!r}")


def _presence(data: dict) -> str:
    # Field names are validated against a closed vocabulary before this function is called.
    return "{" + ",".join(sorted(data)) + "}"


def _values(table: str, data: dict, *, nested: tuple[str, ...] = ()) -> dict:
    _mapping(data, table)
    unknown = set(data) - set(FIELDS[table]) - set(nested)
    if unknown:
        raise ValueError(f"Unknown {table} fields: {sorted(unknown)}")
    values = {key: data[key] for key in FIELDS[table] if key in data}
    for key, value in values.items():
        _scalar(f"{table}[{data.get('id', '?')}]", key, value)
    return {"fields_present": _presence(data), **values}


def _children(data: dict, key: str) -> list:
    children = data.get(key, [])
    if not isinstance(children, list):
        raise ValueError(f"{key} must be a list")
    for index, child in enumerate(children):
        if key in ("tags", "object_ids"):
            if not isinstance(child, str) or "\x00" in child:
                raise ValueError(f"{key} must contain strings")
        else:
            _mapping(child, f"{key}[{index}]")
    return children


def record_rows(kind: str, data: dict[str, Any]) -> list[tuple[str, dict]]:
    """Return table names and values for the rows owned by one record."""
    kind = str(kind)
    table = ENTITY_TABLES[kind]
    d = dict(_mapping(data, kind))
    d.pop("computed_best_measurement_id", None)
    nested = {
        "object": (
            "id_assignment",
            "external_refs",
            "measurements",
            "best_measurement",
            "attachments",
            "citations",
        ),
        "cave": ("external_refs", "object_ids", "citations"),
    }.get(kind, ())
    if kind == "object":
        d.setdefault("membership_ordinal", 1 if d.get("cave_id") else None)
    if kind in ("object", "cave"):
        d.setdefault("bibliography_status", "unknown")
    vals = _values(table, d, nested=nested)
    if kind == "object":
        a = _mapping(d["id_assignment"], "id_assignment")
        if set(a) - set(ASSIGNMENT):
            raise ValueError("Unknown id_assignment fields")
        for key, value in a.items():
            _scalar("id_assignment", key, value)
        vals.update(
            assignment_fields_present=_presence(a),
            assignment_mode=a["method"],
            **{key: a[key] for key in ASSIGNMENT[1:] if key in a},
        )
    rows = [(table, vals)]
    if kind not in ("object", "cave"):
        return rows
    owner = {f"{kind}_id": d["id"]}
    for ordinal, ref in enumerate(_children(d, "external_refs"), 1):
        rows.append(
            (
                f"{kind}_external_refs",
                {**owner, "ordinal": ordinal, **_values("external_refs", ref)},
            )
        )
    for ordinal, citation in enumerate(_children(d, "citations"), 1):
        rows.append(
            (f"{kind}_citations", {**owner, "ordinal": ordinal, **_values("citations", citation)})
        )
    if kind == "cave":
        return rows
    for ordinal, m in enumerate(_children(d, "measurements"), 1):
        if invalid := non_finite_measurement_fields(m):
            raise ValueError(f"MEASUREMENT_NON_FINITE: {m.get('id')}: {', '.join(invalid)}")
        vals = _values("measurements", m, nested=(*COORDINATES, "tags", "citations"))
        # Derived display coordinates do not change a native snapshot on read/write.
        vals["fields_present"] = _presence(
            dict.fromkeys((set(m) - set(COORDINATES)) | {"input_srid", "input_x", "input_y"})
        )
        native_fields = {"input_srid", "input_x", "input_y"}
        if set(m) & native_fields and not native_fields <= set(m):
            raise ValueError("input_srid, input_x and input_y must be supplied together")
        srid = m.get("input_srid", 4326)
        x, y = (m["input_x"], m["input_y"]) if "input_srid" in m else (m["lon"], m["lat"])
        if isinstance(srid, bool) or not isinstance(srid, int) or srid not in (4326, 2180):
            raise ValueError("input_srid must be 4326 or 2180")
        if any(
            isinstance(n, bool) or not isinstance(n, int | float) or not math.isfinite(n)
            for n in (x, y)
        ):
            raise ValueError("Geometry coordinates must be finite numbers")
        rows.append(
            (
                "measurements",
                {
                    **owner,
                    "history_order": ordinal,
                    **vals,
                    "input_geom": f"SRID={srid};POINT({x!r} {y!r})",
                },
            )
        )
        for tag_ordinal, tag in enumerate(_children(m, "tags"), 1):
            if not isinstance(tag, str):
                raise ValueError("tags must contain strings")
            rows.append(
                (
                    "measurement_tags",
                    {**owner, "measurement_id": m["id"], "ordinal": tag_ordinal, "tag": tag},
                )
            )
        for citation_ordinal, citation in enumerate(_children(m, "citations"), 1):
            rows.append(
                (
                    "measurement_citations",
                    {
                        **owner,
                        "measurement_id": m["id"],
                        "ordinal": citation_ordinal,
                        **_values("measurement_citations", citation),
                    },
                )
            )
    b = dict(_mapping(d["best_measurement"], "best_measurement"))
    b.pop("computed_best_measurement_id", None)
    vals = _values("best_policy", b, nested=("measurement_id",))
    _scalar("best_measurement", "measurement_id", b.get("measurement_id"))
    vals["manual_measurement_id"] = b["measurement_id"] if b["mode"] == "manual" else None
    rows.append(("best_policy", {**owner, **vals}))
    for ordinal, att in enumerate(_children(d, "attachments"), 1):
        rows.append(("attachments", {**owner, "ordinal": ordinal, **_values("attachments", att)}))
    return rows


def check_source_fields(kind: str, data: dict) -> None:
    """Canonical files cannot present computed values as editable source facts."""
    if "computed_best_measurement_id" in data or (kind == "cave" and "object_ids" in data):
        raise ValueError("Canonical YAML must not contain computed membership or Best fields")
    if kind == "object":
        b = _mapping(data["best_measurement"], "best_measurement")
        if "computed_best_measurement_id" in b or (
            b.get("mode") == "auto" and "measurement_id" in b
        ):
            raise ValueError("Canonical auto Best must not contain a computed measurement_id")
        for m in _children(data, "measurements"):
            derived = {"x_1992", "y_1992"}
            if any(key in m for key in ("input_srid", "input_x", "input_y")):
                derived.update(("lat", "lon"))
            if derived.intersection(m):
                raise ValueError(
                    f"Measurement {m.get('id')}: derived coordinates are not source fields"
                )
