"""Read a ground elevation from the reviewed public TPN raster service."""

from __future__ import annotations

import hashlib
import json
import math
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from http.client import HTTPException
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SERVICE_URL = "https://gis.tpn.pl/server/rest/services/Topografia___wysoko%C5%9Bci_MIL1/MapServer"
ITEM_ID = "6750310b9d3e4e24a888b8d1ee32ef81"
METADATA_URL = (
    f"https://gis.tpn.pl/portal/sharing/rest/content/items/{ITEM_ID}/info/metadata/metadata.xml"
)
MODEL = "nmt_05m_mggp_2019"
LEGEND_URL = f"{SERVICE_URL}/legend?f=json"
DATA_DESCRIPTION_URL = "https://geoportaltatry.pl/informacje_o_usludze/topografia.pdf"


class ElevationError(ValueError):
    """An input, transport, source-contract or elevation-response failure."""


def _read(url: str, timeout: float) -> bytes:
    request = Request(url, headers={"User-Agent": "gps-kataster-tpn-elevation/1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read(2_000_001)
    except (OSError, URLError, HTTPException) as exc:
        raise ElevationError(f"TRANSPORT_ERROR: {exc}") from exc
    if len(data) > 2_000_000:
        raise ElevationError("INVALID_RESPONSE: response exceeds 2 MB")
    return data


def _json(data: bytes) -> dict:
    try:
        result = json.loads(data)
    except (ValueError, UnicodeError) as exc:
        raise ElevationError("INVALID_RESPONSE: expected JSON") from exc
    if not isinstance(result, dict):
        raise ElevationError("INVALID_RESPONSE: expected a JSON object")
    if "error" in result:
        error = result["error"]
        code = error.get("code", "unknown") if isinstance(error, dict) else "unknown"
        raise ElevationError(f"API_ERROR: ArcGIS code {code}")
    return result


def _check_metadata(data: bytes) -> None:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ElevationError("INVALID_RESPONSE: expected metadata XML") from exc
    code = root.find(".//refSysInfo/RefSystem/refSysID/identCode")
    sizes = [root.findtext(f".//rastinfo/{axis}", "") for axis in ("rastxsz", "rastysz")]
    try:
        grid_matches = all(float(value.replace(",", ".")) == 0.5 for value in sizes)
    except ValueError:
        grid_matches = False
    if (
        root.findtext(".//itemName") != MODEL
        or not grid_matches
        or root.findtext(".//rastinfo/rastband") != "1"
        or code is None
        or code.get("code") != "2178"
        or root.findtext(".//refSysInfo/RefSystem/refSysID/idCodeSpace") != "EPSG"
    ):
        raise ElevationError("SOURCE_CHANGED: review the model, grid, bands and CRS metadata")


def _check_legend(payload: dict) -> str:
    layers = payload.get("layers")
    matches = (
        [
            layer
            for layer in layers
            if isinstance(layer, dict)
            and type(layer.get("layerId")) is int
            and layer["layerId"] == 0
        ]
        if isinstance(layers, list)
        else []
    )
    if (
        len(matches) != 1
        or matches[0].get("layerName") != "Topografia - wysokości"
        or matches[0].get("layerType") != "Raster Layer"
    ):
        raise ElevationError("SOURCE_CHANGED: expected the reviewed raster layer 0 legend")
    groups = matches[0].get("legendGroups")
    if (
        not isinstance(groups, list)
        or len(groups) != 1
        or not isinstance(groups[0], dict)
        or groups[0].get("heading") != "m n.p.m."
    ):
        raise ElevationError("SOURCE_CHANGED: review the publisher's elevation reference label")
    return groups[0]["heading"]


def _pixel_value(payload: dict) -> str:
    results = payload.get("results")
    if results == []:
        raise ElevationError("NO_DATA: no TPN raster data at this point")
    if not isinstance(results, list) or len(results) != 1:
        raise ElevationError("INVALID_RESPONSE: expected one raster result")
    result = results[0]
    if not isinstance(result, dict) or type(result.get("layerId")) is not int:
        raise ElevationError("INVALID_RESPONSE: missing raster layer ID")
    attributes = result.get("attributes")
    if result["layerId"] != 0 or not isinstance(attributes, dict):
        raise ElevationError("INVALID_RESPONSE: unexpected raster layer or attributes")
    value = attributes.get("Stretch.Pixel Value")
    if not isinstance(value, str):
        raise ElevationError("INVALID_RESPONSE: missing numeric raster value")
    if value.strip().lower().replace(" ", "") == "nodata":
        raise ElevationError("NO_DATA: TPN raster returned NoData")
    try:
        valid = math.isfinite(float(value))
    except ValueError:
        valid = False
    if not valid:
        raise ElevationError("INVALID_RESPONSE: raster value must be a finite number")
    return value


def fetch_elevation(lat: float, lon: float, *, timeout: float = 20.0) -> dict:
    """Return one raster value with provenance; never write catalog data.

    The publisher labels elevations as metres above sea level. Its exact
    vertical datum, accuracy and resampling algorithm remain undocumented.
    """
    for name, value, low, high in (
        ("lat", lat, -90, 90),
        ("lon", lon, -180, 180),
        ("timeout", timeout, 0, math.inf),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, (float, int))
            or not math.isfinite(value)
            or not low <= value <= high
            or (name == "timeout" and value == 0)
        ):
            raise ElevationError(f"INVALID_INPUT: invalid {name}")

    service = _json(_read(f"{SERVICE_URL}?f=json", timeout))
    if service.get("serviceItemId") != ITEM_ID:
        raise ElevationError("SOURCE_CHANGED: service no longer identifies the reviewed source")
    layers = service.get("layers")
    if not isinstance(layers, list):
        raise ElevationError("SOURCE_CHANGED: missing raster layer definitions")
    matches = [
        layer
        for layer in layers
        if isinstance(layer, dict) and type(layer.get("id")) is int and layer["id"] == 0
    ]
    if (
        len(matches) != 1
        or matches[0].get("type") != "Raster Layer"
        or matches[0].get("name") != "Topografia - wysokości"
    ):
        raise ElevationError("SOURCE_CHANGED: review layer 0 identity and raster type")
    metadata = _read(METADATA_URL, timeout)
    _check_metadata(metadata)
    legend = _read(LEGEND_URL, timeout)
    reference_label = _check_legend(_json(legend))

    # Explicit point semantics and tiny map extent avoid a screen-pixel search.
    params = {
        "f": "json",
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "sr": "4326",
        "layers": "all:0",
        "tolerance": "0",
        "mapExtent": f"{lon - 0.00001},{lat - 0.00001},{lon + 0.00001},{lat + 0.00001}",
        "imageDisplay": "1000,1000,96",
        "returnGeometry": "false",
    }
    identify_url = f"{SERVICE_URL}/identify?{urlencode(params)}"
    response = _read(identify_url, timeout)
    raw_value = _pixel_value(_json(response))
    return {
        "format_version": 1,
        "point": {"lat": lat, "lon": lon, "crs": "EPSG:4326"},
        "surface": "ground",
        "elevation_m": float(raw_value),
        "raw_elevation": raw_value,
        "elevation_reference": "sea_level",
        "elevation_datum": "unknown",
        "vertical_accuracy_m": "unknown",
        "retrieved_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source": {
            "provider": "TPN",
            "model": MODEL,
            "model_year_in_name": 2019,
            "data_date": "2019-10-14/2019-10-15",
            "data_date_source_url": DATA_DESCRIPTION_URL,
            "latestness": "unconfirmed",
            "grid_resolution_m": 0.5,
            "horizontal_crs": "EPSG:2178",
            "resampling": "unknown",
            "service_url": SERVICE_URL,
            "layer_id": 0,
            "metadata_url": METADATA_URL,
            "metadata_sha256": hashlib.sha256(metadata).hexdigest(),
            "elevation_reference_label": reference_label,
            "legend_url": LEGEND_URL,
            "legend_sha256": hashlib.sha256(legend).hexdigest(),
            "identify_url": identify_url,
            "response_sha256": hashlib.sha256(response).hexdigest(),
        },
    }
