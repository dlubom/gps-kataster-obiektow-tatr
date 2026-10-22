import copy
import importlib.util
import io
import json
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

import pytest

from gps_kataster_obiektow_tatr import tpn_download as download

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def api(monkeypatch):
    state = {"ids": [3, 1, 2], "count": 3, "after_ids": None, "page": None, "xml": b"<metadata/>"}
    calls = []
    id_reads = {}
    metadata = {
        "name": "Źródło TPN",
        "maxRecordCount": 2,
        "geometryType": "esriGeometryPoint",
        "fields": [
            {"name": "OBJECTID", "type": "esriFieldTypeOID"},
            {"name": "NOWE_POLE", "type": "esriFieldTypeString", "alias": "Nowe pole"},
            {"name": "WERYF", "domain": {"codedValues": [{"code": "1", "name": "odnaleziony"}]}},
        ],
        "hasAttachments": False,
        "relationships": [],
    }
    state["metadata"] = metadata

    def open_url(request, *, timeout):
        assert timeout == 30
        url = request.full_url
        calls.append(url)
        parsed = urlparse(url)
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        if parsed.path.endswith("/metadata"):
            return io.BytesIO(state["xml"])
        if not parsed.path.endswith("/query"):
            result = state["metadata"]
        elif params.get("returnCountOnly") == "true":
            result = {"count": state["count"]}
        elif params.get("returnIdsOnly") == "true":
            n = id_reads.get(parsed.path, 0)
            id_reads[parsed.path] = n + 1
            ids = state["after_ids"] if n and state["after_ids"] is not None else state["ids"]
            result = {"objectIdFieldName": "OBJECTID", "objectIds": ids}
        else:
            assert params["outFields"] == "*"
            assert params["outSR"] == "4326"
            assert params["returnGeometry"] == "true"
            assert params["returnZ"] == "true" and params["returnM"] == "true"
            assert "geometryPrecision" not in params
            ids = [int(v) for v in params["objectIds"].split(",")] if "objectIds" in params else []
            assert len(ids) <= 2
            result = {
                "spatialReference": {"wkid": 4326},
                "geometryType": "esriGeometryPoint",
                "fields": copy.deepcopy(metadata["fields"]),
                "features": [
                    {
                        "attributes": {
                            "OBJECTID": oid,
                            "NOWE_POLE": "Żółta jaskinia",
                            "WERYF": None,
                            "CREATED_DATE": 1234567890000,
                            "GLOBALID": "shared-across-layers",
                        },
                        "geometry": {"x": 19 + oid / 100, "y": 49.2},
                    }
                    for oid in reversed(ids)
                ],
            }
            if state["page"]:
                state["page"](result)
        if isinstance(result, Exception):
            raise result
        return io.BytesIO(json.dumps(result).encode())

    monkeypatch.setattr(download, "urlopen", open_url)
    state["calls"] = calls
    return state


def test_all_layers_and_batches_preserve_source_information(api):
    snapshot = download.fetch_snapshot()
    assert snapshot["schema_version"] == 1
    assert snapshot["started_at"].endswith("Z") and snapshot["finished_at"].endswith("Z")
    assert set(snapshot["layers"]) == {"jaskinie", "leje_krasowe", "sztolnie_kopalnie"}
    for name, layer in snapshot["layers"].items():
        assert layer["source_url"] == download.LAYERS[name]
        assert layer["metadata"] == api["metadata"]
        assert layer["metadata_xml"] == "<metadata/>"
        assert layer["object_ids"] == [1, 2, 3]
        assert layer["record_count"] == 3
        features = layer["feature_set"]["features"]
        assert [f["attributes"]["OBJECTID"] for f in features] == [1, 2, 3]
        assert features[0]["attributes"]["NOWE_POLE"] == "Żółta jaskinia"
        assert features[0]["attributes"]["WERYF"] is None
        assert features[0]["attributes"]["CREATED_DATE"] == 1234567890000
        assert features[0]["geometry"] == {"x": 19.01, "y": 49.2}
        assert layer["request_urls"]


def test_shape_field_is_returned_as_geometry_not_an_attribute(api):
    api["metadata"]["fields"].append({"name": "SHAPE", "type": "esriFieldTypeGeometry"})
    snapshot = download.fetch_snapshot()
    for layer in snapshot["layers"].values():
        assert layer["metadata"]["fields"][-1]["name"] == "SHAPE"
        assert "SHAPE" not in layer["feature_set"]["features"][0]["attributes"]
        assert layer["feature_set"]["features"][0]["geometry"]["x"] == 19.01


@pytest.mark.parametrize("change", ["drop", "duplicate", "wrong_id", "limit", "crs", "field"])
def test_incomplete_or_mislabelled_page_fails(api, change):
    def mutate(page):
        if change == "drop":
            page["features"].pop()
        elif change == "duplicate":
            page["features"].append(page["features"][0])
        elif change == "wrong_id":
            page["features"][0]["attributes"]["OBJECTID"] = 99
        elif change == "limit":
            page["exceededTransferLimit"] = True
        elif change == "crs":
            page["spatialReference"]["wkid"] = 3857
        else:
            del page["features"][0]["attributes"]["NOWE_POLE"]

    api["page"] = mutate
    with pytest.raises(download.DownloadError):
        download.fetch_snapshot()


@pytest.mark.parametrize("ids,count", [([1, 1, 3], 3), ([1, 2], 3), ([True], 1), (["1"], 1)])
def test_invalid_id_inventory_is_rejected(api, ids, count):
    api.update(ids=ids, count=count)
    with pytest.raises(download.DownloadError):
        download.fetch_snapshot()


def test_same_count_with_changed_ids_is_rejected(api):
    api["after_ids"] = [1, 2, 99]
    with pytest.raises(download.DownloadError, match="changed"):
        download.fetch_snapshot()


def test_empty_layers_and_null_geometry_remain_source_data(api):
    api.update(ids=[], count=0)
    assert all(
        layer["feature_set"]["features"] == []
        for layer in download.fetch_snapshot()["layers"].values()
    )
    api.update(ids=[1], count=1)
    api["page"] = lambda page: page["features"][0].update(geometry=None)
    assert all(
        layer["feature_set"]["features"][0]["geometry"] is None
        for layer in download.fetch_snapshot()["layers"].values()
    )


@pytest.mark.parametrize(
    "payload", [{"error": {"code": 499}}, [], {"fields": []}, URLError("offline")]
)
def test_bad_metadata_and_api_errors_fail(api, payload):
    api["metadata"] = payload
    with pytest.raises(download.DownloadError):
        download.fetch_snapshot()


@pytest.mark.parametrize(
    "xml", [b"<broken", b"<html><body>login</body></html>", b'{"error":{"code":499}}']
)
def test_non_metadata_xml_fails(api, xml):
    api["xml"] = xml
    with pytest.raises(download.DownloadError):
        download.fetch_snapshot()


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True])
def test_invalid_timeout_does_not_call_network(api, timeout):
    with pytest.raises(download.DownloadError):
        download.fetch_snapshot(timeout=timeout)
    assert api["calls"] == []


def test_pretty_utf8_write_and_existing_file_protection(api, tmp_path):
    snapshot = download.fetch_snapshot()
    output = tmp_path / "nested" / "tpn.json"
    download.write_snapshot(output, snapshot)
    original = output.read_bytes()
    assert b'\n  "schema_version": 1,' in original and "Żółta" in original.decode()
    assert json.loads(original) == snapshot
    with pytest.raises(FileExistsError):
        download.write_snapshot(output, snapshot)
    assert output.read_bytes() == original
    assert list(output.parent.iterdir()) == [output]


def test_failed_serialization_or_publication_leaves_no_partial_file(monkeypatch, tmp_path):
    output = tmp_path / "tpn.json"
    with pytest.raises(ValueError):
        download.write_snapshot(output, {"bad": float("nan")})
    assert list(tmp_path.iterdir()) == []

    def fail(*args, **kwargs):
        raise OSError("disk failure")

    monkeypatch.setattr(download.os, "link", fail)
    with pytest.raises(OSError, match="disk failure"):
        download.write_snapshot(output, {"ok": True})
    assert list(tmp_path.iterdir()) == []


def test_file_created_during_publication_is_never_replaced(monkeypatch, tmp_path):
    output = tmp_path / "tpn.json"
    original_link = download.os.link

    def race(source, target):
        target.write_text("other process")
        return original_link(source, target)

    monkeypatch.setattr(download.os, "link", race)
    with pytest.raises(FileExistsError):
        download.write_snapshot(output, {"new": True})
    assert output.read_text() == "other process"
    assert list(tmp_path.iterdir()) == [output]


def test_cli_default_output_uses_repo_local_api_directory(api, tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "fetch_tpn_data", ROOT / "scripts/fetch_tpn_data.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    assert cli.main([]) == 0
    files = list((tmp_path / "data/sources/tpn/api").glob("tpn-*.json"))
    assert len(files) == 1
    assert len(json.loads(files[0].read_text())["layers"]) == 3


def test_cli_and_output_protection(api, tmp_path, capsys, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "fetch_tpn_data", ROOT / "scripts/fetch_tpn_data.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    output = tmp_path / "tpn.json"
    assert cli.main(["--output", str(output)]) == 0
    assert json.loads(output.read_text())["layers"]["jaskinie"]["record_count"] == 3
    capsys.readouterr()
    api["calls"].clear()
    assert cli.main(["--output", str(output)]) == 1
    assert api["calls"] == []
    assert "already exists" in capsys.readouterr().err
    api["metadata"] = {"error": {"code": 499}}
    assert cli.main(["--output", str(tmp_path / "failure.json")]) == 1
    assert not (tmp_path / "failure.json").exists()
    assert "499" in capsys.readouterr().err
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path)
    api["metadata"] = {"error": {"code": 499}}
    assert cli.main([]) == 1
    assert not (tmp_path / "data").exists()
