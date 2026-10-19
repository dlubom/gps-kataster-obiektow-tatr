"""Read-only public TPN ArcGIS protocol; raw responses remain unmodified."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from http.client import HTTPException
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import UUID

ENDPOINT = "https://gis.tpn.pl/server/rest/services/Topografia___wektor_MIL1/MapServer/6"
FIELDS = {
    "OBJECTID": "esriFieldTypeOID",
    "GLOBALID": "esriFieldTypeGlobalID",
    "SHAPE": "esriFieldTypeGeometry",
    **dict.fromkeys(
        [
            "NR_INWENT",
            "NAZWA",
            "SYSTEM",
            "OTWÓR",
            "OPIS",
            "WER_LOK",
            "UWAGI",
            "GENEZA",
            "CREATED_USER",
            "LAST_EDITED_USER",
            "TATER",
        ],
        "esriFieldTypeString",
    ),
    **dict.fromkeys(["DLUGOSC", "GLEBOKOSC", "PRZEWYZSZE", "DENIWELACJ"], "esriFieldTypeDouble"),
    "WERYF": "esriFieldTypeSmallInteger",
    "FIELD": "esriFieldTypeInteger",
    "CREATED_DATE": "esriFieldTypeDate",
    "LAST_EDITED_DATE": "esriFieldTypeDate",
}
ATTRIBUTES = {k: v for k, v in FIELDS.items() if k != "SHAPE"}
CONSISTENCY_LIMIT = "count_and_ids_not_transactional_attributes"
Transport = Callable[[str, dict], bytes]


class SnapshotError(ValueError):
    """No complete, validated snapshot can be published/consumed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SnapshotError(message)


def parse_json(raw: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def number(value):
        result = float(value)
        require(math.isfinite(result), "non-finite JSON number")
        return result

    def constant(value):
        raise SnapshotError(f"invalid JSON constant: {value}")

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_float=number,
            parse_constant=constant,
        )
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise SnapshotError(f"invalid JSON: {exc}") from exc
    require(isinstance(value, dict), "response must be a JSON object")
    require("error" not in value, f"ArcGIS error: {value.get('error')}")
    return value


def http_get(endpoint: str, params: dict) -> bytes:
    """One bounded GET; retries belong to the whole acquisition, not a page."""
    query = {k: str(v).lower() if isinstance(v, bool) else v for k, v in params.items()}
    request = Request(
        endpoint + "?" + urlencode(query),
        headers={
            "User-Agent": "gps-kataster-tpn-snapshot/1",
            "Accept": "application/json",
            "Cache-Control": "no-cache",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            require(response.status == 200, f"HTTP status {response.status}")
            require(response.url.split("?")[0] == endpoint, "unexpected HTTP redirect")
            raw = response.read(64 * 1024 * 1024 + 1)
            require(len(raw) <= 64 * 1024 * 1024, "HTTP response exceeds 64 MiB")
            length = response.headers.get("Content-Length")
            require(
                length is None or (length.isdecimal() and int(length) == len(raw)),
                "incomplete HTTP response",
            )
            return raw
    except (OSError, URLError, HTTPException) as exc:
        raise SnapshotError(f"HTTP read failed: {exc}") from exc


def field_types(value: object) -> dict:
    require(isinstance(value, list), "missing field declarations")
    fields = {}
    for field in value:
        require(isinstance(field, dict), "invalid field declaration")
        name, kind = field.get("name"), field.get("type")
        require(isinstance(name, str) and isinstance(kind, str), "invalid field name/type")
        require(name not in fields, f"duplicate field declaration: {name}")
        fields[name] = kind
    return fields


def integer(value: object, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def validate_layer(layer: dict) -> int:
    require(
        type(layer.get("id")) is int
        and layer["id"] == 6
        and layer.get("name") == "Jaskinie"
        and layer.get("type") == "Feature Layer"
        and layer.get("geometryType") == "esriGeometryPoint",
        "unexpected layer identity",
    )
    require(field_types(layer.get("fields")) == FIELDS, "layer schema drift")
    require(
        all(layer.get(key) is None or layer.get(key) is False for key in ("hasZ", "hasM")),
        "unsupported Z/M geometry",
    )
    capabilities = layer.get("advancedQueryCapabilities")
    require(
        isinstance(capabilities, dict)
        and capabilities.get("supportsPagination") is True
        and capabilities.get("supportsOrderBy") is True,
        "pagination/order unsupported",
    )
    limit = layer.get("maxRecordCount")
    require(integer(limit, 1), "invalid layer maxRecordCount")
    return limit


def transfer_limit(response: dict) -> bool:
    value = response.get("exceededTransferLimit", False)
    require(type(value) is bool, "invalid exceededTransferLimit")
    return value


def count_value(response: dict) -> int:
    value = response.get("count")
    require(integer(value) and not transfer_limit(response), "invalid/incomplete count")
    return value


def id_values(response: dict) -> list[int]:
    require(response.get("objectIdFieldName") == "OBJECTID", "unexpected ID field")
    ids = response.get("objectIds")
    require(isinstance(ids, list) and all(integer(x, 1) for x in ids), "invalid ID list")
    require(len(ids) == len(set(ids)) and not transfer_limit(response), "duplicate/incomplete IDs")
    return sorted(ids)


def globalid(value: object) -> str:
    require(isinstance(value, str), "GLOBALID must be text")
    value = value.strip()
    if value.startswith("{") and value.endswith("}"):
        value = value[1:-1]
    require(
        re.fullmatch(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}", value) is not None,
        "invalid GLOBALID",
    )
    return str(UUID(value))


def validate_attributes(attrs: object) -> tuple[int, str]:
    require(
        isinstance(attrs, dict) and attrs.keys() == ATTRIBUTES.keys(),
        "missing/unknown attribute field",
    )
    for name, kind in ATTRIBUTES.items():
        value = attrs[name]
        if name == "OBJECTID":
            require(integer(value, 1), "invalid OBJECTID")
        elif name == "GLOBALID":
            globalid(value)
        elif value is None:
            continue
        elif kind == "esriFieldTypeString":
            require(isinstance(value, str), f"invalid string: {name}")
        elif kind == "esriFieldTypeDouble":
            require(type(value) in (int, float) and math.isfinite(value), f"invalid number: {name}")
        elif kind == "esriFieldTypeDate":
            require(type(value) is int, f"invalid date type: {name}")
            try:
                datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=value)
            except OverflowError as exc:
                raise SnapshotError(f"invalid date range: {name}") from exc
        else:
            bits = 16 if kind == "esriFieldTypeSmallInteger" else 32
            require(
                type(value) is int and -(2 ** (bits - 1)) <= value < 2 ** (bits - 1),
                f"invalid integer: {name}",
            )
    return attrs["OBJECTID"], globalid(attrs["GLOBALID"])


def validate_page(page: dict) -> tuple[list[int], list[str], bool]:
    require(page.get("geometryType") == "esriGeometryPoint", "unexpected page geometry type")
    sr = page.get("spatialReference")
    require(
        isinstance(sr, dict)
        and type(sr.get("wkid")) is int
        and sr.get("wkid") == 4326
        and type(sr.get("latestWkid", 4326)) is int
        and sr.get("latestWkid", 4326) == 4326,
        "page CRS must be EPSG:4326",
    )
    require(field_types(page.get("fields")) == ATTRIBUTES, "page schema drift")
    features = page.get("features")
    require(isinstance(features, list), "missing features")
    ids, guids = [], []
    for feature in features:
        require(
            isinstance(feature, dict) and set(feature) == {"attributes", "geometry"},
            "invalid feature",
        )
        oid, guid = validate_attributes(feature["attributes"])
        geometry = feature["geometry"]
        require(
            isinstance(geometry, dict) and set(geometry) == {"x", "y"}, "invalid point geometry"
        )
        for axis, bound in [("x", 180), ("y", 90)]:
            value = geometry[axis]
            require(
                type(value) in (int, float) and -bound <= value <= bound, f"invalid geometry.{axis}"
            )
        ids.append(oid)
        guids.append(guid)
    require(ids == sorted(set(ids)), "duplicate/unsorted page OBJECTID")
    return ids, guids, transfer_limit(page)


def query_params(page_size: int) -> dict:
    return {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": True,
        "outSR": 4326,
        "orderByFields": "OBJECTID",
        "resultOffset": 0,
        "resultRecordCount": page_size,
        "f": "json",
    }


def acquire(transport: Transport, page_size: int) -> dict[str, bytes]:
    """Collect one attempt; all validation is also replayed by the disk reader."""
    raw = {}

    def get(name, params, layer=False):
        raw[name] = transport(ENDPOINT if layer else ENDPOINT + "/query", params)
        return parse_json(raw[name])

    layer = get("layer.json", {"f": "json"}, layer=True)
    limit = min(page_size, validate_layer(layer))
    count = count_value(
        get("count-before.json", {"where": "1=1", "returnCountOnly": True, "f": "json"})
    )
    ids = id_values(get("ids-before.json", {"where": "1=1", "returnIdsOnly": True, "f": "json"}))
    require(count == len(ids), "count/IDs disagree before acquisition")
    offset = 0
    while True:
        page = get(f"page-{offset}.json", {**query_params(limit), "resultOffset": offset})
        page_ids, _, more = validate_page(page)
        require(len(page_ids) <= limit, "page exceeds requested limit")
        require(
            page_ids == ids[offset : offset + len(page_ids)], "page IDs disagree with full ID list"
        )
        offset += len(page_ids)
        require(offset <= count, "page total exceeds count")
        if not more:
            require(offset == count, "premature end of pages")
            break
        require(page_ids and offset < count, "pagination makes no progress or exceeds count")
    get("count-after.json", {"where": "1=1", "returnCountOnly": True, "f": "json"})
    get("ids-after.json", {"where": "1=1", "returnIdsOnly": True, "f": "json"})
    get("layer-after.json", {"f": "json"}, layer=True)
    return raw


def summarize(raw: dict[str, bytes], prefix: str, page_size: int) -> tuple[dict, list[dict]]:
    """Independently recheck the saved protocol transcript and derive its summaries."""
    parsed = {name: parse_json(value) for name, value in raw.items() if name != "policy.md"}
    layer = parsed["layer.json"]
    limit = validate_layer(layer)
    validate_layer(parsed["layer-after.json"])
    require(layer == parsed["layer-after.json"], "layer changed during acquisition")
    require(integer(page_size, 1) and page_size <= limit, "invalid requested page size")
    before, after = (count_value(parsed[f"count-{side}.json"]) for side in ["before", "after"])
    ids_before, ids_after = (id_values(parsed[f"ids-{side}.json"]) for side in ["before", "after"])
    require(
        before == after == len(ids_before) == len(ids_after) and ids_before == ids_after,
        "source count/IDs changed during acquisition",
    )
    pages, ids, guids = [], [], []
    offset = 0
    while True:
        name = f"page-{offset}.json"
        require(name in parsed, f"missing page: {name}")
        page_ids, page_guids, more = validate_page(parsed[name])
        require(len(page_ids) <= page_size, "page exceeds requested limit")
        require(
            page_ids == ids_before[offset : offset + len(page_ids)], "page ID sequence mismatch"
        )
        pages.append(
            {
                "path": f"{prefix}/{name}",
                "result_offset": offset,
                "count": len(page_ids),
                "object_ids": page_ids,
                "exceeded_transfer_limit": more,
            }
        )
        ids.extend(page_ids)
        guids.extend(page_guids)
        offset += len(page_ids)
        require(offset <= before, "page count overflow")
        if not more:
            break
        require(page_ids and offset < before, "pagination makes no progress or exceeds count")
    require(ids == ids_before, "incomplete page ID set")
    require(len(guids) == len(set(guids)), "duplicate GLOBALID")
    expected = {
        "layer.json",
        "layer-after.json",
        "count-before.json",
        "count-after.json",
        "ids-before.json",
        "ids-after.json",
        "policy.md",
    }
    expected.update(p["path"].rsplit("/", 1)[1] for p in pages)
    require(set(raw) == expected, "missing/extra transcript files")
    return (
        {
            "count_before": before,
            "count_after": after,
            "ids_before": ids_before,
            "ids_after": ids_after,
            "feature_count": len(ids),
            "unique_globalid_count": len(set(guids)),
            "complete": True,
            "consistency_limit": CONSISTENCY_LIMIT,
        },
        pages,
    )
