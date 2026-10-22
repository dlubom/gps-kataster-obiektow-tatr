import copy
import importlib.util
import json
from pathlib import Path

import pytest

from gps_kataster_obiektow_tatr import tpn_elevation as elevation
from gps_kataster_obiektow_tatr import tpn_simple as simple
from gps_kataster_obiektow_tatr.tpn_download import LAYERS

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def snapshot():
    layers = {}
    for name in LAYERS:
        attrs = {
            "OBJECTID": 11,
            "GLOBALID": "{source-id}",
            "NAZWA": "Żółta jaskinia",
            "WERYF": "1",
            "UWAGI": None,
            "TATER": "?",
            "NOWE_POLE": ["źródłowe"],
            "CREATED_USER": "editor",
            "CREATED_DATE": 123,
            "LAST_EDITED_USER": "editor",
            "LAST_EDITED_DATE": 456,
        }
        fields = [{"name": key, "type": "esriFieldTypeString"} for key in attrs]
        fields[0]["type"] = "esriFieldTypeOID"
        fields[3]["domain"] = {
            "type": "codedValue",
            "codedValues": [
                {"code": "1", "name": "odnaleziony"},
                {"code": "2", "name": "nieodnaleziony"},
            ],
        }
        layers[name] = {
            "record_count": 1,
            "object_ids": [11],
            "metadata": {"fields": fields},
            "metadata_xml": "<metadata/>",
            "request_urls": ["technical"],
            "feature_set": {
                "spatialReference": {"wkid": 4326},
                "features": [
                    {
                        "attributes": attrs,
                        "geometry": {"x": 20.040162970253178, "y": 49.2516567952702},
                    },
                ],
            },
        }
    return {"schema_version": 1, "layers": layers}


def record(snapshot, layer="jaskinie"):
    return snapshot["layers"][layer]["feature_set"]["features"][0]


def test_simple_preserves_object_data_decodes_codes_and_removes_technical_envelope(snapshot):
    before = copy.deepcopy(snapshot)
    result = simple.simplify_snapshot(snapshot)
    assert set(result) == set(LAYERS)
    for rows in result.values():
        assert rows == [
            {
                "OBJECTID": 11,
                "GLOBALID": "{source-id}",
                "NAZWA": "Żółta jaskinia",
                "WERYF": "odnaleziony",
                "UWAGI": None,
                "TATER": "?",
                "NOWE_POLE": ["źródłowe"],
                "lat": 49.2516567952702,
                "lon": 20.040162970253178,
            }
        ]
    result["jaskinie"][0]["NOWE_POLE"].append("zmiana kopii")
    assert snapshot == before


@pytest.mark.parametrize("value", [None, "99", True])
def test_unknown_domain_codes_and_nulls_are_preserved(snapshot, value):
    record(snapshot)["attributes"]["WERYF"] = value
    assert simple.simplify_snapshot(snapshot)["jaskinie"][0]["WERYF"] == value


@pytest.mark.parametrize("geometry", [None, {"x": None}, {"x": None, "y": None}])
def test_empty_points_keep_record_without_fabricated_coordinates(snapshot, geometry):
    record(snapshot)["geometry"] = geometry
    result = simple.simplify_snapshot(snapshot)["jaskinie"][0]
    assert result["lat"] is None and result["lon"] is None
    assert result["OBJECTID"] == 11


def test_source_z_and_m_are_preserved_without_becoming_nmt_height(snapshot):
    record(snapshot)["geometry"].update(z=1400, m=7)
    result = simple.simplify_snapshot(snapshot)["jaskinie"][0]
    assert result["geometria_dodatkowa"] == {"z": 1400, "m": 7}
    assert "wysokosc_gruntu_nmt_m" not in result


def test_new_attribute_without_metadata_definition_is_kept(snapshot):
    record(snapshot)["attributes"]["PRZYSZLE_POLE"] = {"treść": "bez interpretacji"}
    result = simple.simplify_snapshot(snapshot)
    assert result["jaskinie"][0]["PRZYSZLE_POLE"] == {"treść": "bez interpretacji"}


def test_missing_declared_attribute_is_not_published_as_a_complete_record(snapshot):
    record(snapshot)["attributes"].pop("UWAGI")
    with pytest.raises(ValueError, match="attributes"):
        simple.simplify_snapshot(snapshot)


@pytest.mark.parametrize("change", ["layer", "count", "ids", "crs", "geometry", "collision"])
def test_invalid_snapshot_is_rejected_without_silently_losing_data(snapshot, change):
    if change == "layer":
        snapshot["layers"].pop("leje_krasowe")
    elif change == "count":
        snapshot["layers"]["jaskinie"]["record_count"] = 2
    elif change == "ids":
        snapshot["layers"]["jaskinie"]["object_ids"] = [99]
    elif change == "crs":
        snapshot["layers"]["jaskinie"]["feature_set"]["spatialReference"] = {"wkid": 2180}
    elif change == "geometry":
        record(snapshot)["geometry"]["x"] = float("inf")
    else:
        record(snapshot)["attributes"]["lat"] = "source value"
    with pytest.raises(ValueError):
        simple.simplify_snapshot(snapshot)


def test_nmt_enriches_every_layer_at_exact_source_points_and_retains_evidence(snapshot):
    plain = simple.simplify_snapshot(snapshot)
    before = copy.deepcopy(plain)
    points = []

    def fetch(lat, lon):
        points.append((lat, lon))
        return {
            "elevation_m": 1982.77002,
            "raw_elevation": "1982.770020",
            "point": {"lat": lat, "lon": lon},
            "source": {"model": elevation.MODEL},
        }

    enriched, evidence = simple.enrich_simple(plain, fetch=fetch)
    assert points == [(49.2516567952702, 20.040162970253178)] * 3
    for name in LAYERS:
        assert enriched[name] == [
            {**before[name][0], "wysokosc_gruntu_nmt_m": 1982.77, "status_nmt": "ok"}
        ]
        assert evidence[name][0]["OBJECTID"] == 11
        assert evidence[name][0]["result"]["raw_elevation"] == "1982.770020"
    assert plain == before


def test_no_data_and_missing_points_remain_explicit_nulls(snapshot):
    record(snapshot, "leje_krasowe")["geometry"] = None
    calls = []

    def fetch(lat, lon):
        calls.append((lat, lon))
        raise elevation.ElevationError("NO_DATA: no raster")

    enriched, evidence = simple.enrich_simple(simple.simplify_snapshot(snapshot), fetch=fetch)
    assert len(calls) == 2
    for name in LAYERS:
        row = enriched[name][0]
        assert row["wysokosc_gruntu_nmt_m"] is None
        assert row["status_nmt"] == (
            "brak_wspolrzednych" if name == "leje_krasowe" else "brak_danych"
        )
        assert evidence[name][0]["status"] == row["status_nmt"]


def test_no_data_evidence_is_kept_when_the_reader_supplies_it(snapshot):
    proof = {
        "point": {"lat": 49.2516567952702, "lon": 20.040162970253178},
        "source": {"response_sha256": "no-data-response-hash"},
    }

    def fetch(lat, lon):
        error = elevation.ElevationError("NO_DATA: no raster")
        error.evidence = proof
        raise error

    _, evidence = simple.enrich_simple(simple.simplify_snapshot(snapshot), fetch=fetch)
    assert evidence["jaskinie"][0]["result"] == proof


@pytest.mark.parametrize(
    "message",
    [
        "SOURCE_CHANGED: model",
        "TRANSPORT_ERROR: timeout",
        "API_ERROR: 499",
        "INVALID_RESPONSE: bad",
    ],
)
def test_source_and_service_failures_abort_instead_of_becoming_missing_heights(snapshot, message):
    def fetch(lat, lon):
        raise elevation.ElevationError(message)

    with pytest.raises(elevation.ElevationError, match=message):
        simple.enrich_simple(simple.simplify_snapshot(snapshot), fetch=fetch)


def load_cli():
    spec = importlib.util.spec_from_file_location(
        "tpn_download_cli", ROOT / "scripts/fetch_tpn_data.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_reuses_raw_offline_and_never_overwrites_outputs(snapshot, tmp_path, monkeypatch):
    raw = tmp_path / "raw.json"
    original = json.dumps(snapshot, ensure_ascii=False).encode()
    raw.write_bytes(original)
    output = tmp_path / "simple"
    cli = load_cli()
    monkeypatch.setattr(cli, "fetch_snapshot", lambda **kw: pytest.fail("must reuse input"))
    assert cli.main(["--input", str(raw), "--simple-dir", str(output)]) == 0
    assert json.loads((output / "simple.json").read_text())["jaskinie"][0]["WERYF"] == "odnaleziony"
    assert raw.read_bytes() == original
    assert cli.main(["--input", str(raw), "--simple-dir", str(output)]) == 1
    assert raw.read_bytes() == original


def test_cli_nmt_writes_separate_evidence_and_plain_json(snapshot, tmp_path, monkeypatch):
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps(snapshot))
    output = tmp_path / "simple"
    cli = load_cli()

    class Reader:
        def __init__(self, **kwargs):
            pass

        def fetch(self, lat, lon):
            return {
                "elevation_m": 1234.5678,
                "raw_elevation": "1234.5678",
                "point": {"lat": lat, "lon": lon},
                "source": {"model": elevation.MODEL},
            }

    monkeypatch.setattr(cli, "ElevationClient", Reader)
    assert cli.main(["--input", str(raw), "--simple-dir", str(output), "--with-nmt"]) == 0
    plain = json.loads((output / "simple.json").read_text())
    enriched = json.loads((output / "simple-nmt.json").read_text())
    evidence = json.loads((output / "nmt-evidence.json").read_text())
    assert "wysokosc_gruntu_nmt_m" not in plain["jaskinie"][0]
    assert enriched["jaskinie"][0]["wysokosc_gruntu_nmt_m"] == 1234.57
    assert evidence["records"]["jaskinie"][0]["result"]["raw_elevation"] == "1234.5678"
    assert len(evidence["input_sha256"]) == 64


def test_cli_failed_nmt_never_publishes_enriched_file(snapshot, tmp_path, monkeypatch):
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps(snapshot))
    cli = load_cli()
    output = tmp_path / "simple"

    class Reader:
        def __init__(self, **kwargs):
            pass

        def fetch(self, lat, lon):
            raise elevation.ElevationError("SOURCE_CHANGED: stop")

    monkeypatch.setattr(cli, "ElevationClient", Reader)
    assert cli.main(["--input", str(raw), "--simple-dir", str(output), "--with-nmt"]) == 1
    assert (output / "simple.json").exists()
    assert not (output / "simple-nmt.json").exists()


def test_existing_nmt_evidence_blocks_before_any_api_or_plain_output(
    snapshot, tmp_path, monkeypatch
):
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps(snapshot))
    output = tmp_path / "simple"
    output.mkdir()
    existing = output / "nmt-evidence.json"
    existing.write_text("keep this evidence")
    cli = load_cli()
    monkeypatch.setattr(cli, "ElevationClient", lambda **kw: pytest.fail("must preflight outputs"))
    assert cli.main(["--input", str(raw), "--simple-dir", str(output), "--with-nmt"]) == 1
    assert existing.read_text() == "keep this evidence"
    assert not (output / "simple.json").exists()
