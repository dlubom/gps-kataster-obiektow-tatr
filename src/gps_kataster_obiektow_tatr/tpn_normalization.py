"""Versioned TPN source normalization; raw values are retained beside fingerprints."""

from __future__ import annotations

import csv
import io
import json
import math
import unicodedata
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pyproj import Geod

from .coordinates import pl1992_to_wgs84
from .tpn_api import ATTRIBUTES, globalid, parse_json, require, validate_attributes
from .tpn_precision import csv_degrees
from .tpn_snapshot import sha256, verify_snapshot

VERSION = "tpn-sync-v1"
CSV_PATH = Path("data/sources/tpn/tpn_otwory_jaskin.xlsx.-.Export.csv")
TECHNICAL = {
    "OBJECTID",
    "FIELD",
    "CREATED_USER",
    "CREATED_DATE",
    "LAST_EDITED_USER",
    "LAST_EDITED_DATE",
}
METADATA = sorted(set(ATTRIBUTES) - TECHNICAL - {"GLOBALID"})
CSV_ALIASES = {
    "CREATED_US": "CREATED_USER",
    "CREATED_DA": "CREATED_DATE",
    "LAST_EDITE": "LAST_EDITED_USER",
    "LAST_EDI_1": "LAST_EDITED_DATE",
}
CSV_COLUMNS = (
    (set(ATTRIBUTES) - {"OBJECTID"} - set(CSV_ALIASES.values()))
    | set(CSV_ALIASES)
    | {"Z", "X1992", "Y1992"}
)
GEOD = Geod(ellps="WGS84")


def canonical(value: object) -> bytes:
    """Exact decimal JSON: no exponent, trailing zeros or negative zero.

    Source JSON is parsed with Decimal; float values from the existing YAML
    loader/coordinate projection use their shortest round-trip representation.
    Text normalization belongs to the source adapter, never to raw catalog bytes.
    """
    if value is None or type(value) is bool or isinstance(value, str):
        result = json.dumps(value, ensure_ascii=False)
    elif isinstance(value, (date, datetime)):
        result = json.dumps(value.isoformat())
    elif type(value) in (int, float, Decimal):
        number = Decimal(str(value))
        require(number.is_finite(), "non-finite canonical number")
        result = format(number, "f")
        if "." in result:
            result = result.rstrip("0").rstrip(".")
        if number == 0:
            result = "0"
    elif isinstance(value, (list, tuple)):
        result = "[" + ",".join(canonical(v).decode() for v in value) + "]"
    elif isinstance(value, dict):
        require(all(isinstance(k, str) for k in value), "JSON keys must be text")
        result = (
            "{"
            + ",".join(
                canonical(k).decode() + ":" + canonical(value[k]).decode() for k in sorted(value)
            )
            + "}"
        )
    else:
        raise ValueError(f"unsupported canonical type: {type(value).__name__}")
    return result.encode("utf-8")


def digest(value: object) -> str:
    return sha256(canonical(value))


def text(value: str | None) -> str | None:
    require(value is None or isinstance(value, str), "text must be string/null")
    if value is None:
        return None
    return (
        unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n")).strip()
        or None
    )


def decimal(value: object) -> Decimal | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    require(type(value) in (int, float, str, Decimal), "invalid numeric value")
    try:
        number = Decimal(str(value).strip().replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError("invalid numeric text") from exc
    require(number.is_finite() and math.isfinite(float(number)), "non-finite number")
    return number


def exact_json(raw: bytes) -> dict:
    # Reuse duplicate-key/invalid-constant checks, but do not round source XY.
    parse_json(raw)
    return json.loads(raw, parse_float=Decimal)


def normalize_feature(feature: dict) -> dict:
    require(set(feature) == {"attributes", "geometry"}, "invalid feature")
    attrs, xy = feature["attributes"], feature["geometry"]
    validate_attributes({k: float(v) if isinstance(v, Decimal) else v for k, v in attrs.items()})
    require(isinstance(xy, dict) and set(xy) == {"x", "y"}, "invalid XY")
    for axis, bound in [("x", 180), ("y", 90)]:
        require(type(xy[axis]) in (int, float, Decimal), "invalid XY type")
        require(
            decimal(xy[axis]) is not None and -bound <= decimal(xy[axis]) <= bound,
            "invalid XY range",
        )
    values = {k: text(v) if ATTRIBUTES[k] == "esriFieldTypeString" else v for k, v in attrs.items()}
    return normalized(
        globalid(attrs["GLOBALID"]),
        values,
        {
            "crs": "EPSG:4326",
            "lon": decimal(xy["x"]),
            "lat": decimal(xy["y"]),
            "elevation": "absent",
        },
        feature,
        "api",
        None,
    )


def normalized(
    guid: str, values: dict, location: dict, raw: dict, kind: str, elevation: Decimal | None
) -> dict:
    metadata = {k: values[k] for k in METADATA}
    location_hash = digest({"policy_version": VERSION, "globalid": guid, **location})
    source_time = None
    if kind == "api":
        milliseconds = values["LAST_EDITED_DATE"]
        modified = (
            (datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=milliseconds))
            if milliseconds is not None
            else None
        )
        source_time = {
            "date_basis": "source_modified" if modified is not None else "unavailable",
            "last_edited_ms": milliseconds,
            "source_modified_at": modified.isoformat().replace("+00:00", "Z") if modified else None,
            "source_date": modified.date().isoformat() if modified else None,
            "field_observed_at": None,
        }
    return {
        "source_time": source_time,
        "globalid": guid,
        "kind": kind,
        "metadata": metadata,
        "technical": {k: values.get(k) for k in sorted(TECHNICAL)},
        "location": location,
        "elevation": elevation,
        "raw": raw,
        "revision_hash": digest(
            {
                "policy_version": VERSION,
                "globalid": guid,
                "metadata": metadata,
                "location": location,
            }
        ),
        "location_hash": location_hash,
    }


def read_csv(path: Path) -> dict[str, dict]:
    raw = path.read_bytes()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    require(
        reader.fieldnames is not None
        and len(reader.fieldnames) == len(CSV_COLUMNS)
        and set(reader.fieldnames) == CSV_COLUMNS,
        "CSV schema drift/duplicate header",
    )
    result = {}
    for row in reader:
        require(None not in row and all(v is not None for v in row.values()), "non-rectangular CSV")
        values = {CSV_ALIASES.get(k, k): v for k, v in row.items()}
        guid = globalid(values["GLOBALID"])
        require(guid not in result, "duplicate CSV GLOBALID")
        for key, kind in ATTRIBUTES.items():
            if key in ("OBJECTID", "GLOBALID"):
                continue
            values[key] = (
                text(values[key])
                if kind in ("esriFieldTypeString", "esriFieldTypeDate")
                else decimal(values[key])
            )
        for key in ("CREATED_DATE", "LAST_EDITED_DATE"):
            if values[key] is not None:
                datetime.strptime(values[key], "%Y-%m-%d %H:%M:%S")
        for key, bits in (("WERYF", 16), ("FIELD", 32)):
            value = values[key]
            require(
                value is None
                or (
                    value == value.to_integral_value()
                    and -(2 ** (bits - 1)) <= value < 2 ** (bits - 1)
                ),
                f"invalid CSV integer: {key}",
            )
        x, y = decimal(row["X1992"]), decimal(row["Y1992"])
        require(x is not None and y is not None, "missing CSV XY")
        point = pl1992_to_wgs84(float(x), float(y))
        require(-90 <= point.lat <= 90 and -180 <= point.lon <= 180, "invalid CSV XY")
        result[guid] = normalized(
            guid,
            values,
            {
                "crs": "EPSG:4326",
                "lat": csv_degrees(point.lat),
                "lon": csv_degrees(point.lon),
                "elevation": "absent",
            },
            row,
            "csv",
            decimal(row["Z"]),
        )
    return result


def read_snapshot(path: Path, policy_hash: str) -> tuple[dict, dict[str, dict]]:
    manifest = verify_snapshot(path)
    require(
        manifest["policy_version"] == VERSION and manifest["policy_hash"] == policy_hash,
        "policy migration required",
    )
    result = {}
    for page in manifest["pages"]:
        raw = (path / Path(page["path"]).name).read_bytes()
        expected = next(f["raw_sha256"] for f in manifest["files"] if f["path"] == page["path"])
        require(sha256(raw) == expected, "snapshot changed after verification")
        for feature in exact_json(raw)["features"]:
            item = normalize_feature(feature)
            item["source_time"]["fetched_at"] = manifest["fetched_at"]
            result[item["globalid"]] = item
    return manifest, result


def distance(a: dict, b: dict) -> float:
    return GEOD.inv(float(a["lon"]), float(a["lat"]), float(b["lon"]), float(b["lat"]))[2]


def same_location(a: dict, b: dict) -> bool:
    if a["kind"] == "csv" or b["kind"] == "csv":
        return distance(a["location"], b["location"]) <= 0.1
    return a["location"] == b["location"]
