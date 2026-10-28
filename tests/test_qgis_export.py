import hashlib
import importlib
import json
import sqlite3
import xml.etree.ElementTree as ET
import zipfile
from copy import deepcopy

import pytest
from qgis_fixtures import write_jktz_source
from test_release_artifacts import _valid_cave, _valid_object, _write_yaml

from gps_kataster_obiektow_tatr.best_measurements_export import export_best_measurements
from gps_kataster_obiektow_tatr.build_db import build_sqlite_database

STAMP = "2026-10-28T10:00:00Z"


@pytest.fixture
def qgis_inputs(tmp_path):
    data = tmp_path / "data"
    (data / "relations").mkdir(parents=True)
    obj = _valid_object()
    obj["name_local"] = "A <b> & ' cave"
    obj["best_measurement"].update(mode="manual", measurement_id="m-001", reason="Older choice")
    obj["measurements"][0].update(horizontal_accuracy_m=0, notes='<img src="bad"> source text')
    obj["measurements"][1].update(
        verification_status="odrzucony",
        lat=49.23469299,
        lon=19.87599498,
        x_1992=152278.4273821069,
        y_1992=563751.398684218,
        horizontal_accuracy_m=None,
        notes="Rejected old location",
    )
    coincident = deepcopy(obj["measurements"][0])
    coincident.update(id="m-003", source="wlasne")
    obj["measurements"].append(coincident)
    _write_yaml(data / "objects/KSW/KSW-0001.yml", obj)
    second = deepcopy(obj)
    second["id"] = "KSW-0002"
    second["external_refs"] = []
    second["name_local"] = None
    second["measurements"] = [deepcopy(obj["measurements"][0])]
    second["measurements"][0].update(verification_status="odrzucony", horizontal_accuracy_m=None)
    _write_yaml(data / "objects/KSW/KSW-0002.yml", second)
    cave = _valid_cave()
    cave["object_ids"].append("KSW-0002")
    _write_yaml(data / "caves/C-0001.yml", cave)
    sqlite_path = tmp_path / "katalog.sqlite"
    build_sqlite_database(data_dir=data, output_path=sqlite_path, generated_at=STAMP)
    exported = export_best_measurements(
        data_dir=data, output_dir=tmp_path / "best", generated_at=STAMP
    )
    return {
        "sqlite_path": sqlite_path,
        "best_geojson_path": exported.geojson_path,
        "jktz_source_dir": write_jktz_source(tmp_path / "jktz"),
        "generated_at": STAMP,
        "release_version": "v1.2.3",
        "source_commit": "a" * 40,
    }


def build(inputs, output):
    module = importlib.import_module("gps_kataster_obiektow_tatr.qgis_export")
    assert module.write_qgis_export(**inputs, output_path=output) == output
    with zipfile.ZipFile(output) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def features(members, role):
    manifest = json.loads(members["manifest.json"])
    layer = next(layer for layer in manifest["layers"] if layer["role"] == role)
    return json.loads(members[layer["path"]])["features"]


def ids(rows):
    return [(f["properties"]["object_id"], f["properties"]["measurement_id"]) for f in rows]


def test_qgis_points_keep_complete_disjoint_history_and_authoritative_manual_best(
    qgis_inputs, tmp_path
):
    members = build(qgis_inputs, tmp_path / "qgis.zip")
    assert ids(features(members, "best")) == [("KSW-0001", "m-001"), ("KSW-0002", "m-001")]
    assert ids(features(members, "other")) == [("KSW-0001", "m-003")]
    assert ids(features(members, "rejected")) == [("KSW-0001", "m-002")]
    assert ids(features(members, "full")) == [
        ("KSW-0001", "m-001"),
        ("KSW-0001", "m-002"),
        ("KSW-0001", "m-003"),
        ("KSW-0002", "m-001"),
    ]
    best = features(members, "best")
    assert best[0]["geometry"]["coordinates"] == [19.87589498, 49.23459299]
    assert best[0]["properties"]["horizontal_accuracy_m"] == 0
    assert best[1]["properties"]["horizontal_accuracy_m"] is None
    assert best[0]["properties"]["name_local"] == "A <b> & ' cave"
    assert best[0]["properties"]["measurement_notes"] == '<img src="bad"> source text'
    assert best[0]["properties"]["best_reason"] == "Older choice"
    assert best[1]["properties"]["verification_status"] == "odrzucony"
    assert best[1]["properties"]["display_name"] == "KSW-0002"
    assert best[0]["properties"]["display_name_html"] == "A &lt;b&gt; &amp; &#x27; cave"


def test_qgis_difference_lines_measure_projected_separation_and_skip_coincident_readings(
    qgis_inputs, tmp_path
):
    members = build(qgis_inputs, tmp_path / "qgis.zip")
    lines = features(members, "differences")
    assert len(lines) == 1
    line = lines[0]
    assert line["geometry"] == {
        "type": "LineString",
        "coordinates": [[19.87599498, 49.23469299], [19.87589498, 49.23459299]],
    }
    assert line["properties"]["object_id"] == "KSW-0001"
    assert line["properties"]["measurement_id"] == "m-002"
    assert line["properties"]["best_measurement_id"] == "m-001"
    assert line["properties"]["distance_m"] == pytest.approx(13.2853, abs=0.001)


def test_qgis_project_opens_with_best_only_and_a_single_selected_tpn_basemap(qgis_inputs, tmp_path):
    members = build(qgis_inputs, tmp_path / "qgis.zip")
    manifest = json.loads(members["manifest.json"])
    project = ET.fromstring(members["kataster.qgs"])
    nodes = {n.attrib["id"]: n for n in project.findall(".//layer-tree-layer")}
    for layer in manifest["layers"]:
        assert nodes[layer["id"]].attrib["checked"] == (
            "Qt::Checked" if layer["role"] == "best" else "Qt::Unchecked"
        )
    models = [layer for layer in manifest["layers"] if layer["role"] == "jktz"]
    assert [m["model"] for m in models] == ["Alpha", "Beta"]
    assert all(
        n.attrib["checked"] == "Qt::Unchecked"
        for n in nodes.values()
        if n.attrib["id"].startswith("jktz_")
    )
    basemaps = manifest["basemaps"]
    assert [m["id"] for m in basemaps] == [
        "tpn_rgb_2020",
        "tpn_rgb_2018",
        "tpn_nmt_image",
        "tpn_nmpt_image",
        "osm_basemap",
    ]
    assert nodes["tpn_rgb_2020"].attrib["checked"] == "Qt::Checked"
    assert nodes["osm_basemap"].attrib["checked"] == "Qt::Checked"
    for basemap in basemaps[:-1]:
        native = next(
            layer
            for layer in project.findall("./projectlayers/maplayer")
            if layer.findtext("id") == basemap["id"]
        )
        assert native.attrib["hasScaleBasedVisibilityFlag"] == "1"
        assert float(native.attrib["minScale"]) == 25000
    assert len(project.findall(".//Bookmarks/Bookmark")) >= 2
    assert {n.attrib["name"] for n in project.findall(".//text-style/families/family")} >= {
        "Arial",
        "DejaVu Sans",
        "Noto Sans",
        "Liberation Sans",
    }
    assert not project.findall(".//pythonCode")
    assert not project.findall(".//actionsetting/action")


def test_qgis_archive_is_portable_reproducible_and_records_both_sources(qgis_inputs, tmp_path):
    first, second = tmp_path / "first/qgis.zip", tmp_path / "elsewhere/qgis.zip"
    members = build(qgis_inputs, first)
    build(qgis_inputs, second)
    assert first.read_bytes() == second.read_bytes()
    assert str(tmp_path).encode() not in members["kataster.qgs"]
    manifest = json.loads(members["manifest.json"])
    assert manifest["gps"]["version"] == "v1.2.3"
    assert manifest["gps"]["source_commit"] == "a" * 40
    assert (
        manifest["gps"]["sqlite_sha256"]
        == hashlib.sha256(qgis_inputs["sqlite_path"].read_bytes()).hexdigest()
    )
    assert manifest["jktz"]["version"] == "v9.8.7"
    assert manifest["generated_at"] == STAMP
    assert manifest["counts"] == {
        "best": 2,
        "other": 1,
        "rejected": 1,
        "full": 4,
        "differences": 1,
        "jktz_models": 2,
        "jktz_legs": 2,
    }
    with zipfile.ZipFile(qgis_inputs["jktz_source_dir"] / "JKTZ.zip") as source:
        assert members["jktz/Alpha.shp"] == source.read("exports/caves/Alpha.shp")
        assert members["jktz/LICENCE"] == source.read("LICENCE")
    for name, digest in manifest["sha256"].items():
        assert hashlib.sha256(members[name]).hexdigest() == digest


def test_qgis_ids_are_long_enough_to_survive_native_loading(qgis_inputs, tmp_path):
    # QGIS regenerates short IDs, leaving the saved tree without its intended layers.
    members = build(qgis_inputs, tmp_path / "qgis.zip")
    project = ET.fromstring(members["kataster.qgs"])
    assert all(len(node.text) >= 10 for node in project.findall("./projectlayers/maplayer/id"))


def test_qgis_enables_project_projection_before_reading_its_crs(qgis_inputs, tmp_path):
    # Both supported versions ignore projectCrs if ProjectionsEnabled is absent/false.
    members = build(qgis_inputs, tmp_path / "qgis.zip")
    project = ET.fromstring(members["kataster.qgs"])
    assert project.findtext("./properties/SpatialRefSys/ProjectionsEnabled") == "1"


@pytest.mark.parametrize("corrupt", ["missing-best", "changed-best-geometry", "jktz"])
def test_invalid_input_preserves_previous_qgis_asset(qgis_inputs, tmp_path, corrupt):
    output = tmp_path / "qgis.zip"
    output.write_bytes(b"previous accepted asset")
    if corrupt == "missing-best":
        with sqlite3.connect(qgis_inputs["sqlite_path"]) as db:
            db.execute(
                "UPDATE best_measurements SET measurement_id='m-missing' WHERE object_id='KSW-0001'"
            )
    elif corrupt == "changed-best-geometry":
        data = json.loads(qgis_inputs["best_geojson_path"].read_text())
        data["features"][0]["geometry"]["coordinates"][0] += 0.1
        qgis_inputs["best_geojson_path"].write_text(json.dumps(data))
    else:
        (qgis_inputs["jktz_source_dir"] / "JKTZ.zip").write_bytes(b"bad source")
    with pytest.raises(ValueError):
        build(qgis_inputs, output)
    assert output.read_bytes() == b"previous accepted asset"


def test_qgis_supports_a_legal_empty_catalog(tmp_path, make_data_dir):
    data = make_data_dir(tmp_path / "empty")
    database = tmp_path / "empty.sqlite"
    build_sqlite_database(data_dir=data, output_path=database, generated_at=STAMP)
    best = export_best_measurements(data_dir=data, output_dir=tmp_path / "best", generated_at=STAMP)
    members = build(
        {
            "sqlite_path": database,
            "best_geojson_path": best.geojson_path,
            "jktz_source_dir": write_jktz_source(tmp_path / "jktz"),
            "generated_at": STAMP,
            "release_version": None,
            "source_commit": None,
        },
        tmp_path / "qgis.zip",
    )
    for role in ("full", "best", "other", "rejected", "differences"):
        assert features(members, role) == []
