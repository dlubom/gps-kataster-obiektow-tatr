import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

import pytest

from gps_kataster_obiektow_tatr import tpn_elevation as elevation

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "tpn_elevation"


@pytest.fixture
def api(monkeypatch):
    responses = {
        "service": (FIXTURES / "service.json").read_bytes(),
        "metadata": (FIXTURES / "metadata.xml").read_bytes(),
        "legend": (FIXTURES / "legend.json").read_bytes(),
        "identify": (FIXTURES / "identify.json").read_bytes(),
    }

    def open_url(request, *, timeout):
        url = request.full_url
        parsed = urlparse(url)
        if parsed.path.endswith("/identify"):
            params = parse_qs(parsed.query)
            assert params["geometry"] == ["19.9816,49.232"]
            assert params["sr"] == ["4326"]
            assert params["layers"] == ["all:0"]
            assert params["tolerance"] == ["0"]
            assert params["returnGeometry"] == ["false"]
            assert params["imageDisplay"] == ["1000,1000,96"]
            xmin, ymin, xmax, ymax = map(float, params["mapExtent"][0].split(","))
            assert xmin < 19.9816 < xmax and ymin < 49.232 < ymax
            assert xmax - xmin < 0.0001 and ymax - ymin < 0.0001
            data = responses["identify"]
        elif parsed.path.endswith("/metadata.xml"):
            data = responses["metadata"]
        elif parsed.path.endswith("/legend"):
            data = responses["legend"]
        else:
            assert parsed.path.endswith("/MapServer")
            data = responses["service"]
        if isinstance(data, Exception):
            raise data
        return io.BytesIO(data)

    monkeypatch.setattr(elevation, "urlopen", open_url)
    return responses


def test_point_read_preserves_value_and_uncertainty(api):
    result = elevation.fetch_elevation(49.232, 19.9816)
    assert result["elevation_m"] == 1982.770020
    assert result["raw_elevation"] == "1982.770020"
    assert result["point"] == {"lat": 49.232, "lon": 19.9816, "crs": "EPSG:4326"}
    assert result["elevation_datum"] == "unknown"
    assert result["elevation_reference"] == "sea_level"
    assert result["vertical_accuracy_m"] == "unknown"
    assert result["surface"] == "ground"
    source = result["source"]
    assert source["model"] == "nmt_05m_mggp_2019"
    assert source["model_year_in_name"] == 2019
    assert source["data_date"] == "2019-10-14/2019-10-15"
    assert (
        source["data_date_source_url"]
        == "https://geoportaltatry.pl/informacje_o_usludze/topografia.pdf"
    )
    assert source["elevation_reference_label"] == "m n.p.m."
    assert source["legend_url"].endswith("/legend?f=json")
    assert len(source["legend_sha256"]) == 64
    assert source["latestness"] == "unconfirmed"
    assert source["grid_resolution_m"] == 0.5
    assert source["horizontal_crs"] == "EPSG:2178"
    assert source["resampling"] == "unknown"
    assert len(source["metadata_sha256"]) == 64
    assert len(source["response_sha256"]) == 64
    assert result["retrieved_at"].endswith("Z")


def test_batch_client_checks_source_once_and_keeps_point_specific_results(monkeypatch):
    calls = []

    def read(url, timeout):
        calls.append(url)
        if "/identify?" in url:
            lat = float(parse_qs(urlparse(url).query)["geometry"][0].split(",")[1])
            return json.dumps(
                {
                    "results": [
                        {
                            "layerId": 0,
                            "attributes": {
                                "Stretch.Pixel Value": str(lat * 10),
                            },
                        }
                    ]
                }
            ).encode()
        name = (
            "metadata.xml"
            if "/metadata.xml" in url
            else ("legend.json" if "/legend?" in url else "service.json")
        )
        return (FIXTURES / name).read_bytes()

    monkeypatch.setattr(elevation, "_read", read)
    client = elevation.ElevationClient(timeout=9)
    first = client.fetch(49.2, 19.9)
    second = client.fetch(49.3, 20.1)
    assert first["elevation_m"] == 492
    assert second["elevation_m"] == 493
    assert second["point"] == {"lat": 49.3, "lon": 20.1, "crs": "EPSG:4326"}
    assert first["source"]["identify_url"] != second["source"]["identify_url"]
    assert len(calls) == 5  # three source checks plus one query per point
    assert first["source"]["response_sha256"] != second["source"]["response_sha256"]


@pytest.mark.parametrize(
    "lat,lon", [(float("nan"), 20), (49, float("inf")), (91, 20), (49, -181), (True, 20)]
)
def test_invalid_coordinates_fail_before_http(monkeypatch, lat, lon):
    def unexpected_http(*args, **kwargs):
        pytest.fail("invalid coordinates must not reach the API")

    monkeypatch.setattr(elevation, "urlopen", unexpected_http)
    with pytest.raises(elevation.ElevationError, match="INVALID_INPUT"):
        elevation.fetch_elevation(lat, lon)


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_invalid_timeout(api, timeout):
    with pytest.raises(elevation.ElevationError, match="INVALID_INPUT"):
        elevation.fetch_elevation(49.232, 19.9816, timeout=timeout)


@pytest.mark.parametrize(
    "payload",
    [
        {"results": []},
        {"results": [{"layerId": 0, "attributes": {"Stretch.Pixel Value": "NoData"}}]},
    ],
)
def test_no_data_is_an_error(api, payload):
    api["identify"] = json.dumps(payload).encode()
    with pytest.raises(elevation.ElevationError, match="NO_DATA"):
        elevation.fetch_elevation(49.232, 19.9816)


def test_no_data_error_retains_point_and_response_provenance(api):
    api["identify"] = b'{"results":[]}'
    with pytest.raises(elevation.ElevationError, match="NO_DATA") as error:
        elevation.ElevationClient().fetch(49.232, 19.9816)
    proof = error.value.evidence
    assert proof["point"] == {"lat": 49.232, "lon": 19.9816, "crs": "EPSG:4326"}
    assert proof["elevation_m"] is None
    assert proof["retrieved_at"].endswith("Z")
    assert proof["source"]["model"] == "nmt_05m_mggp_2019"
    assert len(proof["source"]["response_sha256"]) == 64
    assert "geometry=19.9816%2C49.232" in proof["source"]["identify_url"]


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "1e999", "", "abc", None, True])
def test_invalid_pixel_values_are_not_heights(api, value):
    api["identify"] = json.dumps(
        {"results": [{"layerId": 0, "attributes": {"Stretch.Pixel Value": value}}]}
    ).encode()
    with pytest.raises(elevation.ElevationError, match="INVALID_RESPONSE"):
        elevation.fetch_elevation(49.232, 19.9816)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [],
        {"results": "bad"},
        {"results": [None]},
        {"results": [{"layerId": 1, "attributes": {"Stretch.Pixel Value": "1"}}]},
        {"results": [{"layerId": 0, "attributes": {}}]},
        {"results": [{"layerId": 0}, {"layerId": 0}]},
    ],
)
def test_malformed_or_ambiguous_result_is_rejected(api, payload):
    api["identify"] = json.dumps(payload).encode()
    with pytest.raises(elevation.ElevationError, match="INVALID_RESPONSE"):
        elevation.fetch_elevation(49.232, 19.9816)


@pytest.mark.parametrize("part", ["service", "legend", "identify"])
def test_arcgis_error_even_on_http_200(api, part):
    api[part] = b'{"error":{"code":499,"message":"Token Required"}}'
    with pytest.raises(elevation.ElevationError, match="API_ERROR.*499"):
        elevation.fetch_elevation(49.232, 19.9816)


@pytest.mark.parametrize("part", ["service", "legend", "identify"])
def test_invalid_json(api, part):
    api[part] = b"<html>maintenance</html>"
    with pytest.raises(elevation.ElevationError, match="INVALID_RESPONSE"):
        elevation.fetch_elevation(49.232, 19.9816)


def test_changed_service_item_is_not_labelled_as_old_model(api):
    api["service"] = b'{"serviceItemId":"another-item"}'
    with pytest.raises(elevation.ElevationError, match="SOURCE_CHANGED"):
        elevation.fetch_elevation(49.232, 19.9816)


@pytest.mark.parametrize("change", ["missing", "type", "name", "duplicate", "not-object"])
def test_changed_service_layer_is_not_labelled_as_old_model(api, change):
    service = json.loads(api["service"])
    layer = service["layers"][0]
    if change == "missing":
        service["layers"] = []
    elif change == "type":
        layer["type"] = "Feature Layer"
    elif change == "name":
        layer["name"] = "new-model"
    elif change == "duplicate":
        service["layers"].append(dict(layer))
    else:
        service["layers"] = [None]
    api["service"] = json.dumps(service).encode()
    with pytest.raises(elevation.ElevationError, match="SOURCE_CHANGED"):
        elevation.fetch_elevation(49.232, 19.9816)


def test_crs_authority_must_also_match(api):
    api["metadata"] = api["metadata"].replace(b">EPSG</idCodeSpace>", b">OTHER</idCodeSpace>")
    with pytest.raises(elevation.ElevationError, match="SOURCE_CHANGED"):
        elevation.fetch_elevation(49.232, 19.9816)


@pytest.mark.parametrize(
    "change",
    [
        "missing-layers",
        "wrong-layer",
        "duplicate-layer",
        "missing-groups",
        "empty-groups",
        "wrong-heading",
        "wrong-name",
        "wrong-type",
        "other-layer-heading",
    ],
)
def test_changed_legend_cannot_claim_sea_level(api, change):
    legend = json.loads(api["legend"])
    layer = legend["layers"][0]
    if change == "missing-layers":
        legend.pop("layers")
    elif change == "wrong-layer":
        layer["layerId"] = 1
    elif change == "duplicate-layer":
        legend["layers"].append(dict(layer))
    elif change == "missing-groups":
        layer.pop("legendGroups")
    elif change == "empty-groups":
        layer["legendGroups"] = []
    elif change == "wrong-heading":
        layer["legendGroups"][0]["heading"] = "ellipsoidal m"
    elif change == "wrong-name":
        layer["layerName"] = "Other layer"
    elif change == "wrong-type":
        layer["layerType"] = "Feature Layer"
    else:
        other = dict(layer, layerId=1)
        layer["legendGroups"] = [{"heading": "unknown"}]
        legend["layers"].append(other)
    api["legend"] = json.dumps(legend).encode()
    with pytest.raises(elevation.ElevationError, match="SOURCE_CHANGED"):
        elevation.fetch_elevation(49.232, 19.9816)


@pytest.mark.parametrize(
    "old,new",
    [
        (b"nmt_05m_mggp_2019", b"nmt_2025"),
        (b"0,500000", b"1,000000"),
        (b'code="2178"', b'code="4326"'),
        (b">1</rastband>", b">3</rastband>"),
    ],
)
def test_changed_model_metadata_is_rejected(api, old, new):
    assert old in api["metadata"]
    api["metadata"] = api["metadata"].replace(old, new)
    with pytest.raises(elevation.ElevationError, match="SOURCE_CHANGED"):
        elevation.fetch_elevation(49.232, 19.9816)


def test_invalid_xml(api):
    api["metadata"] = b"<html>"
    with pytest.raises(elevation.ElevationError, match="INVALID_RESPONSE"):
        elevation.fetch_elevation(49.232, 19.9816)


def test_transport_failure(api):
    api["identify"] = URLError("network unavailable")
    with pytest.raises(elevation.ElevationError, match="TRANSPORT_ERROR"):
        elevation.fetch_elevation(49.232, 19.9816)


def load_cli():
    spec = importlib.util.spec_from_file_location(
        "tpn_elevation_cli", ROOT / "scripts/tpn_elevation.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_json(api, capsys):
    assert load_cli().main(["--lat", "49.232", "--lon", "19.9816", "--json"]) == 0
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert result["raw_elevation"] == "1982.770020"
    assert result["elevation_datum"] == "unknown"
    assert result["elevation_reference"] == "sea_level"
    assert output.err == ""


def test_cli_text_explains_unknown_datum(api, capsys):
    assert load_cli().main(["--lat", "49.232", "--lon", "19.9816"]) == 0
    output = capsys.readouterr().out
    assert "1982.77 m" in output
    assert "unknown" in output
    assert "unconfirmed" in output
    assert "1982.77 m n.p.m." in output
    assert "według legendy TPN" in output
    assert "Dokładny układ wysokości: unknown" in output
    assert "2019-10-14/2019-10-15" in output


def test_cli_error_has_no_success_output(api, capsys):
    api["identify"] = b'{"results":[]}'
    assert load_cli().main(["--lat", "49.232", "--lon", "19.9816", "--json"]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "NO_DATA" in output.err


def test_cli_runs_outside_repository(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/tpn_elevation.py"), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--lat" in result.stdout and "--lon" in result.stdout
