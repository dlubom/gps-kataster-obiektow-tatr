"""Download complete source layers from the public TPN ArcGIS service."""

from __future__ import annotations

import json
import math
import os
import tempfile
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from http.client import HTTPException
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://gis.tpn.pl/server/rest/services"
LAYERS = {
    "jaskinie": f"{BASE_URL}/Topografia___wektor_MIL1/MapServer/6",
    "leje_krasowe": f"{BASE_URL}/SIPTPN/Geologia_i_gleby/MapServer/3",
    "sztolnie_kopalnie": f"{BASE_URL}/SIPTPN/Dziedzictwo_kulturowe/MapServer/13",
}


class DownloadError(ValueError):
    """An invalid input, incomplete response or source/transport failure."""


def _read(url: str, timeout: float) -> bytes:
    try:
        request = Request(url, headers={"User-Agent": "gps-kataster-tpn-download/1"})
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except (OSError, HTTPException) as exc:
        raise DownloadError(f"HTTP request failed: {url}: {exc}") from exc


def _json(data: bytes) -> dict:
    try:
        result = json.loads(data)
    except (ValueError, UnicodeError) as exc:
        raise DownloadError("Expected JSON from TPN") from exc
    if not isinstance(result, dict):
        raise DownloadError("Expected a JSON object from TPN")
    if "error" in result:
        raise DownloadError(f"ArcGIS error: {result['error']}")
    return result


def _fetch_layer(url: str, timeout: float) -> dict:
    request_urls = []

    def get(suffix="", **params):
        request_url = f"{url}{suffix}?{urlencode({'f': 'json', **params})}"
        request_urls.append(request_url)
        return _json(_read(request_url, timeout))

    metadata = get()
    fields = metadata.get("fields")
    limit = metadata.get("maxRecordCount")
    if (
        not isinstance(fields, list)
        or not fields
        or any(not isinstance(f, dict) or not isinstance(f.get("name"), str) for f in fields)
        or type(limit) is not int
        or limit <= 0
        or metadata.get("geometryType") != "esriGeometryPoint"
    ):
        raise DownloadError(f"Invalid layer metadata: {url}")
    oid_fields = [f["name"] for f in fields if f.get("type") == "esriFieldTypeOID"]
    if len(oid_fields) != 1:
        raise DownloadError(f"Expected one object ID field: {url}")
    oid_field = oid_fields[0]
    field_names = {f["name"] for f in fields if f.get("type") != "esriFieldTypeGeometry"}
    xml_url = f"{url}/metadata?f=xml"
    request_urls.append(xml_url)
    xml = _read(xml_url, timeout)
    try:
        root = ET.fromstring(xml)
        metadata_xml = xml.decode("utf-8-sig")
    except (ET.ParseError, UnicodeError) as exc:
        raise DownloadError(f"Invalid metadata XML: {xml_url}") from exc
    if root.tag != "metadata":
        raise DownloadError(f"Expected metadata XML: {xml_url}")

    def inventory():
        count = get("/query", where="1=1", returnCountOnly="true").get("count")
        payload = get("/query", where="1=1", returnIdsOnly="true")
        ids = payload.get("objectIds")
        if ids is None and count == 0:
            ids = []
        if (
            type(count) is not int
            or count < 0
            or not isinstance(ids, list)
            or any(type(oid) is not int for oid in ids)
            or len(ids) != count
            or len(set(ids)) != count
            or payload.get("objectIdFieldName") != oid_field
            or payload.get("exceededTransferLimit", False) is not False
        ):
            raise DownloadError(f"Incomplete or invalid ID inventory: {url}")
        return sorted(ids)

    ids = inventory()
    size = min(limit, 500)
    batches = [ids[start : start + size] for start in range(0, len(ids), size)] or [[]]
    feature_set = None
    features = []
    for batch in batches:
        params = {"objectIds": ",".join(map(str, batch))} if batch else {"where": "1=0"}
        page = get(
            "/query",
            **params,
            outFields="*",
            outSR=4326,
            returnGeometry="true",
            returnZ="true",
            returnM="true",
            orderByFields=f"{oid_field} ASC",
        )
        page_features = page.get("features")
        spatial_reference = page.get("spatialReference")
        if (
            not isinstance(page_features, list)
            or page.get("exceededTransferLimit", False) is not False
            or not isinstance(spatial_reference, dict)
            or spatial_reference.get("latestWkid", spatial_reference.get("wkid")) != 4326
        ):
            raise DownloadError(f"Incomplete page or unexpected CRS: {url}")
        page_ids = []
        for feature in page_features:
            attributes = feature.get("attributes") if isinstance(feature, dict) else None
            if (
                not isinstance(attributes, dict)
                or not field_names.issubset(attributes)
                or type(attributes.get(oid_field)) is not int
            ):
                raise DownloadError(f"Incomplete feature attributes: {url}")
            geometry = feature.get("geometry")
            if geometry is not None and (
                not isinstance(geometry, dict)
                or any(
                    type(geometry.get(axis)) not in (int, float)
                    or not math.isfinite(geometry[axis])
                    or not -bound <= geometry[axis] <= bound
                    for axis, bound in (("x", 180), ("y", 90))
                )
            ):
                raise DownloadError(f"Invalid WGS84 point: {url}")
            page_ids.append(attributes[oid_field])
        if sorted(page_ids) != batch:
            raise DownloadError(f"Incomplete or duplicate features in ID batch: {url}")
        if feature_set is None:
            feature_set = {k: v for k, v in page.items() if k != "features"}
        features.extend(page_features)
    if inventory() != ids:
        raise DownloadError(f"Source ID inventory changed during download: {url}")
    features.sort(key=lambda feature: feature["attributes"][oid_field])
    feature_set["features"] = features
    return {
        "source_url": url,
        "metadata": metadata,
        "metadata_xml": metadata_xml,
        "request_urls": request_urls,
        "object_ids": ids,
        "record_count": len(ids),
        "feature_set": feature_set,
    }


def fetch_snapshot(*, timeout: float = 30.0) -> dict:
    """Fetch three independent layers; never read or change the local catalog."""
    if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
        raise DownloadError("Timeout must be a positive finite number")
    started_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    layers = {}
    for name, url in LAYERS.items():
        try:
            layers[name] = _fetch_layer(url, timeout)
        except DownloadError as exc:
            raise DownloadError(f"{name}: {exc}") from exc
    return {
        "schema_version": 1,
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "layers": layers,
    }


def write_snapshot(output: Path, snapshot: dict) -> None:
    """Publish a fully written UTF-8 JSON atomically, without replacing any path."""
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output.parent, prefix=f".{output.name}.", delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(snapshot, handle, ensure_ascii=False, allow_nan=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
