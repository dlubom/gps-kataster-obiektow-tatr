"""Offline protocol tests: synthetic IDs, pages, errors and disk corruption."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from gps_kataster_obiektow_tatr.tpn_api import ENDPOINT, SnapshotError
from gps_kataster_obiektow_tatr.tpn_snapshot import fetch_snapshot, verify_snapshot

FIXTURES = Path(__file__).parent / "fixtures" / "tpn_api"
REPO = Path(__file__).resolve().parents[1]


def encoded(value):
    return json.dumps(value, ensure_ascii=False).encode()


class API:
    def __init__(self):
        self.layer = json.loads((FIXTURES / "layer.json").read_bytes())
        self.pages = {n: json.loads((FIXTURES / f"page-{n}.json").read_bytes()) for n in [0, 2]}
        self.calls = []
        self.ids = [[9, 1, 4], [4, 9, 1]]
        self.counts = [3, 3]
        self.mutate = lambda label, data: data

    def __call__(self, endpoint, params):
        self.calls.append((endpoint, params.copy()))
        if endpoint == ENDPOINT:
            label, data = "layer", self.layer
        elif params.get("returnCountOnly"):
            label, data = "count", {"count": self.counts.pop(0)}
        elif params.get("returnIdsOnly"):
            label, data = "ids", {"objectIdFieldName": "OBJECTID", "objectIds": self.ids.pop(0)}
        else:
            assert endpoint == ENDPOINT + "/query"
            assert params["outFields"] == "*"
            assert params["returnGeometry"] is True
            assert params["outSR"] == 4326
            assert params["orderByFields"] == "OBJECTID"
            assert params["resultRecordCount"] <= self.layer["maxRecordCount"]
            label, data = "page", self.pages[params["resultOffset"]]
        return encoded(self.mutate(label, copy.deepcopy(data)))


@pytest.fixture
def repo(tmp_path):
    policy = tmp_path / "docs/asdlc/tpn_sync_contract.md"
    policy.parent.mkdir(parents=True)
    policy.write_bytes((REPO / "docs/asdlc/tpn_sync_contract.md").read_bytes())
    return tmp_path


def fetch(repo, api=None, **kwargs):
    return fetch_snapshot(repo, "test-snapshot", transport=api or API(), attempts=1, **kwargs)


def test_complete_snapshot_replays_raw_bytes_and_preserves_null_zero_text(repo):
    api = API()
    path = fetch(repo, api)
    manifest = verify_snapshot(path)
    assert manifest["checks"] == {
        "count_before": 3,
        "count_after": 3,
        "ids_before": [1, 4, 9],
        "ids_after": [1, 4, 9],
        "feature_count": 3,
        "unique_globalid_count": 3,
        "complete": True,
        "consistency_limit": "count_and_ids_not_transactional_attributes",
    }
    assert [p["result_offset"] for p in manifest["pages"]] == [0, 2]
    assert manifest["query"]["resultRecordCount"] == 2
    page = path / "page-0.json"
    assert page.read_bytes() == encoded(api.pages[0])
    attrs = json.loads(page.read_bytes())["features"][0]["attributes"]
    assert attrs["LAST_EDITED_DATE"] == 0 and attrs["CREATED_DATE"] is None
    assert attrs["WER_LOK"] == "opis źródła" and attrs["DLUGOSC"] == 0
    for item in manifest["files"]:
        assert hashlib.sha256((repo / item["path"]).read_bytes()).hexdigest() == item["raw_sha256"]
    assert not (repo / "data/objects").exists()


@pytest.mark.parametrize(
    "fault",
    [
        "count",
        "ids_changed",
        "ids_duplicate",
        "ids_missing",
        "duplicate_page",
        "missing_page",
        "empty_page",
        "false_end",
        "true_end",
        "bad_guid",
        "duplicate_guid",
        "missing_field",
        "extra_field",
        "bad_type",
        "bad_date",
        "nan",
        "null_geometry",
        "bad_crs",
        "bad_xy",
        "geometry_z",
        "schema",
        "layer",
        "arcgis",
    ],
)
def test_incomplete_or_invalid_source_never_publishes(repo, fault):
    api = API()
    attrs = api.pages[0]["features"][0]["attributes"]
    if fault == "count":
        api.counts[1] = 4
    elif fault == "ids_changed":
        api.ids[1] = [1, 4, 10]
    elif fault == "ids_duplicate":
        api.ids[0] = [1, 1, 9]
    elif fault == "ids_missing":
        api.ids[0] = [1, 4]
    elif fault == "duplicate_page":
        api.pages[2]["features"] = api.pages[0]["features"][:1]
    elif fault == "missing_page":
        api.pages[0]["features"].pop()
    elif fault == "empty_page":
        api.pages[0]["features"] = []
    elif fault == "false_end":
        api.pages[0]["exceededTransferLimit"] = False
    elif fault == "true_end":
        api.pages[2]["exceededTransferLimit"] = True
    elif fault == "bad_guid":
        attrs["GLOBALID"] = "bad"
    elif fault == "duplicate_guid":
        api.pages[2]["features"][0]["attributes"]["GLOBALID"] = attrs["GLOBALID"].lower()
    elif fault == "missing_field":
        del attrs["UWAGI"]
    elif fault == "extra_field":
        attrs["new"] = "value"
    elif fault == "bad_type":
        attrs["WERYF"] = True
    elif fault == "bad_date":
        attrs["LAST_EDITED_DATE"] = "yesterday"
    elif fault == "nan":
        attrs["DLUGOSC"] = float("nan")
    elif fault == "null_geometry":
        api.pages[0]["features"][0]["geometry"] = None
    elif fault == "bad_crs":
        api.pages[0]["spatialReference"]["wkid"] = 2180
    elif fault == "bad_xy":
        api.pages[0]["features"][0]["geometry"]["x"] = 181
    elif fault == "geometry_z":
        api.pages[0]["features"][0]["geometry"]["z"] = 1000
    elif fault == "schema":
        api.layer["fields"][0]["type"] = "esriFieldTypeString"
    elif fault == "layer":
        api.layer["name"] = "Other"
    elif fault == "arcgis":
        api.mutate = lambda label, data: {"error": {"code": 500}}
    with pytest.raises(SnapshotError):
        fetch(repo, api)
    assert not (repo / "data/sources/tpn/snapshots/test-snapshot").exists()


def test_repeated_write_cannot_change_existing_evidence(repo):
    path = fetch(repo)
    before = {p.name: p.read_bytes() for p in path.iterdir()}
    with pytest.raises(SnapshotError, match="exists"):
        fetch(repo)
    assert before == {p.name: p.read_bytes() for p in path.iterdir()}


@pytest.mark.parametrize(
    "fault", ["bytes", "summary", "extra", "missing", "path", "version", "symlink"]
)
def test_offline_reader_rejects_tampering(repo, fault):
    path = fetch(repo)
    manifest_path = path / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    if fault == "bytes":
        (path / "page-0.json").chmod(0o644)
        (path / "page-0.json").write_bytes(b"{}")
    elif fault == "summary":
        manifest["checks"]["feature_count"] = 999
    elif fault == "extra":
        (path / "unexpected.json").write_bytes(b"{}")
    elif fault == "missing":
        (path / "ids-before.json").unlink()
    elif fault == "path":
        manifest["files"][0]["path"] = "../../outside"
    elif fault == "version":
        manifest["format_version"] = 2
    elif fault == "symlink":
        identical = repo / "identical-page.json"
        identical.write_bytes((path / "page-0.json").read_bytes())
        (path / "page-0.json").unlink()
        (path / "page-0.json").symlink_to(identical)
    manifest_path.chmod(0o644)
    manifest_path.write_bytes(encoded(manifest))
    with pytest.raises(SnapshotError):
        verify_snapshot(path)


def test_retry_restarts_at_schema_and_discards_first_attempt(repo):
    first, second = API(), API()
    first.counts[1] = 4
    active = first
    schema_reads = 0

    def transport(endpoint, params):
        nonlocal active, schema_reads
        if endpoint == ENDPOINT:
            schema_reads += 1
            if schema_reads == 3:
                active = second
        return active(endpoint, params)

    path = fetch_snapshot(repo, "retry", transport=transport, attempts=2)
    assert verify_snapshot(path)["checks"]["count_after"] == 3
    assert schema_reads == 4
    assert len(first.calls) == len(second.calls) == 8


def test_retry_is_bounded_and_no_final_directory(repo):
    calls = []

    def broken(endpoint, params):
        calls.append(endpoint)
        raise OSError("connection reset")

    with pytest.raises(SnapshotError, match="after 3 attempt"):
        fetch_snapshot(repo, "retry", transport=broken, attempts=3)
    assert len(calls) == 3
    assert not (repo / "data/sources/tpn/snapshots/retry").exists()


def test_short_pages_continue_by_actual_count_and_absent_flag_ends(repo):
    api = API()
    api.pages[1] = copy.deepcopy(api.pages[0])
    api.pages[1]["features"] = api.pages[0]["features"][1:]
    api.pages[0]["features"] = api.pages[0]["features"][:1]
    del api.pages[2]["exceededTransferLimit"]
    manifest = verify_snapshot(fetch(repo, api))
    assert [p["result_offset"] for p in manifest["pages"]] == [0, 1, 2]


def test_empty_layer_is_a_complete_empty_snapshot(repo):
    api = API()
    api.ids = [[], []]
    api.counts = [0, 0]
    api.pages[0]["features"] = []
    api.pages[0]["exceededTransferLimit"] = False
    assert verify_snapshot(fetch(repo, api))["checks"]["feature_count"] == 0


@pytest.mark.parametrize(
    "payload", [b"{", b"[]", b'{"count":3,"count":3}', b'{"x":1e999}', b"\xff"]
)
def test_invalid_json_fails_closed(repo, payload):
    with pytest.raises(SnapshotError):
        fetch(repo, lambda endpoint, params: payload)
    assert not (repo / "data/sources/tpn/snapshots/test-snapshot").exists()


@pytest.mark.parametrize(
    "kind",
    [
        "schema_after",
        "unknown_schema",
        "missing_schema",
        "page_schema",
        "bool_count",
        "bool_id",
        "flag_type",
        "date_range",
        "inf_xy",
        "duplicate_schema",
        "null_guid",
        "partial_ids",
    ],
)
def test_additional_protocol_guards(repo, kind):
    api = API()
    attrs = api.pages[0]["features"][0]["attributes"]
    if kind == "schema_after":
        calls = 0

        def change(label, data):
            nonlocal calls
            if label == "layer":
                calls += 1
                if calls == 2:
                    data["fields"][1]["alias"] = "changed"
            return data

        api.mutate = change
    elif kind == "unknown_schema":
        api.layer["fields"].append({"name": "NEW", "type": "esriFieldTypeString"})
    elif kind == "missing_schema":
        api.layer["fields"].pop()
    elif kind == "page_schema":
        api.pages[0]["fields"].pop()
    elif kind == "bool_count":
        api.counts[0] = True
    elif kind == "bool_id":
        api.ids[0][0] = True
    elif kind == "flag_type":
        api.pages[0]["exceededTransferLimit"] = 1
    elif kind == "date_range":
        attrs["LAST_EDITED_DATE"] = 10**30
    elif kind == "inf_xy":
        api.pages[0]["features"][0]["geometry"]["y"] = float("inf")
    elif kind == "duplicate_schema":
        api.layer["fields"].append(api.layer["fields"][0])
    elif kind == "null_guid":
        attrs["GLOBALID"] = None
    elif kind == "partial_ids":
        api.mutate = lambda label, data: (
            {**data, "exceededTransferLimit": True} if label == "ids" else data
        )
    with pytest.raises(SnapshotError):
        fetch(repo, api)


def test_rehashed_false_manifest_summary_still_fails(repo):
    from gps_kataster_obiektow_tatr.tpn_snapshot import snapshot_hash

    path = fetch(repo)
    manifest_path = path / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["checks"]["unique_globalid_count"] = 2
    manifest["snapshot_hash"] = snapshot_hash(manifest)
    manifest_path.chmod(0o644)
    manifest_path.write_bytes(encoded(manifest))
    with pytest.raises(SnapshotError, match="manifest does not match"):
        verify_snapshot(path)


@pytest.mark.parametrize("stage", ["write", "readback", "publish"])
def test_io_failure_does_not_publish_manifest_or_touch_prior_snapshot(repo, monkeypatch, stage):
    import gps_kataster_obiektow_tatr.tpn_snapshot as module

    prior = fetch(repo)
    before = {p.name: p.read_bytes() for p in prior.iterdir()}
    if stage == "publish":
        real_link = module.os.link

        def link(source, target):
            if Path(target).name == "manifest.json":
                raise OSError("disk failure")
            return real_link(source, target)

        monkeypatch.setattr(module.os, "link", link)
    else:
        real_write = module.write_bytes

        def write(path, content):
            if path.name == "page-2.json":
                if stage == "write":
                    raise OSError("disk full")
                return real_write(path, b"{}")
            return real_write(path, content)

        monkeypatch.setattr(module, "write_bytes", write)
    with pytest.raises(SnapshotError):
        fetch_snapshot(repo, "failed", transport=API(), attempts=1)
    assert not (prior.parent / "failed").exists()
    assert not list(prior.parent.glob(".partial-*"))
    assert before == {p.name: p.read_bytes() for p in prior.iterdir()}


def test_concurrent_destination_is_never_overwritten(repo, monkeypatch):
    import gps_kataster_obiektow_tatr.tpn_snapshot as module

    original = module.publish

    def publish(parent, snapshot_id, raw, manifest):
        target = parent / snapshot_id
        target.mkdir()
        (target / "other-writer").write_text("preserve")
        return original(parent, snapshot_id, raw, manifest)

    monkeypatch.setattr(module, "publish", publish)
    with pytest.raises(SnapshotError):
        fetch(repo)
    target = repo / "data/sources/tpn/snapshots/test-snapshot"
    assert [p.name for p in target.iterdir()] == ["other-writer"]
    assert (target / "other-writer").read_text() == "preserve"


@pytest.mark.parametrize("snapshot_id", ["../escape", "/absolute", "", ".", "a/b"])
def test_unsafe_snapshot_id_rejected(repo, snapshot_id):
    with pytest.raises(SnapshotError):
        fetch_snapshot(repo, snapshot_id, transport=API())
    assert not (repo / "data").exists()


def test_symlink_output_parent_rejected(repo, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / "data").symlink_to(outside, target_is_directory=True)
    with pytest.raises(SnapshotError, match="symlink"):
        fetch(repo)
    assert not list(outside.iterdir())


def test_http_transport_parameters_timeout_and_status(monkeypatch):
    import gps_kataster_obiektow_tatr.tpn_api as module

    class Response:
        status = 200
        url = ENDPOINT + "?f=json"
        headers = {"Content-Length": "2"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, limit):
            assert limit == 64 * 1024 * 1024 + 1
            return b"{}"

    response = Response()

    def open_request(request, timeout):
        assert "returnGeometry=true" in request.full_url
        assert "outFields=%2A" in request.full_url
        assert timeout == 30
        return response

    monkeypatch.setattr(module, "urlopen", open_request)
    params = {"returnGeometry": True, "outFields": "*"}
    assert module.http_get(ENDPOINT, params) == b"{}"
    response.status = 503
    with pytest.raises(SnapshotError, match="HTTP status"):
        module.http_get(ENDPOINT, params)
    response.status = 200
    response.headers["Content-Length"] = "99"
    with pytest.raises(SnapshotError, match="incomplete"):
        module.http_get(ENDPOINT, params)
    response.url = "https://example.org/other"
    with pytest.raises(SnapshotError, match="redirect"):
        module.http_get(ENDPOINT, params)


def test_http_errors_and_timeout_are_snapshot_errors(monkeypatch):
    from urllib.error import HTTPError, URLError

    import gps_kataster_obiektow_tatr.tpn_api as module

    for error in [
        HTTPError(ENDPOINT, 503, "down", {}, None),
        URLError("DNS"),
        TimeoutError("timeout"),
    ]:

        def fail(*args, error=error, **kwargs):
            raise error

        monkeypatch.setattr(module, "urlopen", fail)
        with pytest.raises(SnapshotError, match="HTTP read failed"):
            module.http_get(ENDPOINT, {})


def test_cli_fetch_and_verify_offline(repo, monkeypatch, capsys):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "snapshot_cli", REPO / "scripts/fetch_tpn_snapshot.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(
        cli,
        "fetch_snapshot",
        lambda root, sid, size, attempts: fetch_snapshot(
            root, sid, size, attempts, transport=API()
        ),
    )
    assert (
        cli.main(["fetch", "--repo-root", str(repo), "--snapshot-id", "cli", "--attempts", "1"])
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["feature_count"] == 3
    assert cli.main(["verify", result["path"]]) == 0
    assert json.loads(capsys.readouterr().out)["snapshot_hash"] == result["snapshot_hash"]
    assert cli.main(["verify", str(repo / "missing")]) == 1
    assert "TPN_SNAPSHOT_INVALID" in capsys.readouterr().err


def test_checked_in_live_evidence_replays_without_network():
    path = REPO / "data/sources/tpn/snapshots/pbi-096-live-20261019"
    manifest = verify_snapshot(path)
    assert manifest["checks"]["complete"] is True
    assert manifest["query"]["outFields"] == "*"
    # No historical count/hash is an acceptance target for a new acquisition.
    assert manifest["checks"]["feature_count"] == len(manifest["checks"]["ids_before"])


@pytest.mark.parametrize(
    "field,value", [("hasZ", 0), ("hasM", 0.0), ("wkid", 4326.0), ("latestWkid", 4326.0)]
)
def test_metadata_flags_and_crs_have_strict_json_types(repo, field, value):
    api = API()
    if field in ("hasZ", "hasM"):
        api.layer[field] = value
    else:
        api.pages[0]["spatialReference"][field] = value
    with pytest.raises(SnapshotError):
        fetch(repo, api)


def test_duplicate_json_key_and_arcgis_error_cannot_hide_in_valid_response(repo):
    api = API()
    layer = encoded(api.layer)
    duplicate = layer.replace(b'"id": 6', b'"id": 6, "id": 6')
    assert duplicate != layer
    with pytest.raises(SnapshotError, match="duplicate JSON key"):
        fetch(repo, lambda endpoint, params: duplicate)
    api.mutate = lambda label, data: {**data, "error": {"code": 500}}
    with pytest.raises(SnapshotError, match="ArcGIS error"):
        fetch(repo, api)
