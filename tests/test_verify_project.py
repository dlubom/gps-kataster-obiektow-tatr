import importlib.util
import json
import sqlite3
import struct
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import yaml
from test_release_artifacts import _valid_cave, _valid_object, _write_yaml

from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts

ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-09-05T12:00:00Z"


@pytest.fixture
def runner():
    spec = importlib.util.spec_from_file_location(
        "verify_project", ROOT / "scripts/verify_project.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shared_verification_entrypoint_exists() -> None:
    assert (ROOT / "scripts" / "verify_project.py").is_file()


@pytest.fixture
def catalog(tmp_path):
    data = tmp_path / "data"
    cave = _valid_cave()
    for index in range(1, 4):
        obj = _valid_object()
        obj["id"] = f"KSW-{index:04}"
        obj["external_refs"] = []
        # Distinct positions make selecting a historical measurement observable.
        for number, measurement in enumerate(obj["measurements"]):
            measurement["lat"] += index * 0.00001 + number * 0.0001
            point = wgs84_to_1992(lat=measurement["lat"], lon=measurement["lon"])
            measurement["x_1992"], measurement["y_1992"] = point.x_1992, point.y_1992
        if index == 2:
            obj["best_measurement"].update(
                mode="manual", measurement_id="m-001", reason="Fixture selection"
            )
            cave["object_ids"].append(obj["id"])
        if index == 3:
            obj["cave_id"] = None
            obj["category"] = "ponor"
            obj["measurements"][1]["elevation_m"] = None
        _write_yaml(data / "objects" / "KSW" / f"{obj['id']}.yml", obj)
    _write_yaml(data / "caves" / "C-0001.yml", cave)
    cave.update(id="C-0002", object_ids=[])
    _write_yaml(data / "caves" / "C-0002.yml", cave)
    _write_yaml(
        data / "relations" / "R-0001.yml",
        {
            "schema_version": 1,
            "id": "R-0001",
            "from_object_id": "KSW-0001",
            "to_object_id": "KSW-0002",
            "relation_type": "sasiad",
            "notes": None,
        },
    )
    return data


@pytest.fixture
def artifacts(catalog, tmp_path):
    run = tmp_path / "artifacts"
    build_release_artifacts(
        data_dir=catalog,
        sqlite_path=run / "katalog.sqlite",
        output_dir=run / "exports",
        generated_at=GENERATED_AT,
    )
    return catalog, run


def test_readback_all_formats_manual_auto_membership_and_nullable_values(runner, artifacts):
    data, run = artifacts
    before = runner.data_hash(data)
    result = runner.readback_artifacts(data, run, GENERATED_AT)
    assert result["counts"] == {
        "objects": 3,
        "caves": 2,
        "measurements": 6,
        "relations": 1,
        "validation_errors": 0,
        "validation_warnings": 0,
    }
    assert len(result["artifact_sha256"]) == 7
    assert runner.data_hash(data) == before


@pytest.mark.parametrize(
    "name",
    [
        "katalog.sqlite",
        "exports/metadata.json",
        "exports/best-measurements.csv",
        "exports/best-measurements.geojson",
        "exports/best-measurements.gpx",
        "exports/best-measurements.shp.zip",
        "exports/katalog.sqlite.zip",
    ],
)
def test_missing_fresh_artifact_fails(runner, artifacts, name):
    data, run = artifacts
    (run / name).unlink()
    with pytest.raises(runner.VerificationError, match="Missing fresh artifact"):
        runner.readback_artifacts(data, run, GENERATED_AT)


def rewrite_zip(path, change):
    with zipfile.ZipFile(path) as archive:
        contents = {name: archive.read(name) for name in archive.namelist()}
    change(contents)
    with zipfile.ZipFile(path, "w") as archive:
        for name, payload in contents.items():
            archive.writestr(name, payload)


@pytest.mark.parametrize(
    "corruption",
    [
        "csv_id",
        "csv_duplicate",
        "csv_measurement",
        "geojson_axes",
        "geojson_measurement",
        "gpx_axes",
        "gpx_measurement",
        "metadata_count",
        "metadata_time",
        "sqlite_best",
        "sqlite_coordinates",
        "sqlite_wkt",
        "sqlite_cave",
        "sqlite_reverse",
        "sqlite_relation",
        "sqlite_fk",
        "sqlite_integrity",
        "zip_contents",
        "zip_crc",
        "shp_axes",
        "shx_offset",
        "dbf_utf8",
    ],
)
def test_readback_detects_corrupt_artifact(runner, artifacts, corruption):
    data, run = artifacts
    exports = run / "exports"
    if corruption.startswith("csv_"):
        path = exports / "best-measurements.csv"
        text = path.read_text()
        if corruption == "csv_id":
            text = text.replace("KSW-0001", "KSW-9999")
        elif corruption == "csv_duplicate":
            text = text.replace("KSW-0002", "KSW-0001")
        else:
            text = text.replace("m-002", "m-999")
        path.write_text(text)
    elif corruption.startswith("geojson_"):
        path = exports / "best-measurements.geojson"
        value = json.loads(path.read_text())
        if corruption == "geojson_axes":
            value["features"][0]["geometry"]["coordinates"].reverse()
        else:
            value["features"][1]["properties"]["measurement_id"] = "m-002"
        path.write_text(json.dumps(value))
    elif corruption.startswith("gpx_"):
        path = exports / "best-measurements.gpx"
        tree = ET.parse(path)
        waypoint = tree.getroot().find(runner.GPX_NS + "wpt")
        if corruption == "gpx_axes":
            waypoint.attrib["lat"], waypoint.attrib["lon"] = (
                waypoint.attrib["lon"],
                waypoint.attrib["lat"],
            )
        else:
            desc = waypoint.find(runner.GPX_NS + "desc")
            desc.text = desc.text.replace("measurement m-002", "measurement m-001")
        tree.write(path)
    elif corruption.startswith("metadata_"):
        path = exports / "metadata.json"
        value = json.loads(path.read_text())
        if corruption == "metadata_count":
            value["counts"]["objects"] += 1
        else:
            value["generated_at"] = "2020-01-01T00:00:00Z"
        path.write_text(json.dumps(value))
    elif corruption.startswith("sqlite_"):
        if corruption == "sqlite_integrity":
            (run / "katalog.sqlite").write_bytes(b"broken")
        else:
            commands = {
                "sqlite_best": (
                    "UPDATE best_measurements SET measurement_id='m-002' WHERE object_id='KSW-0002'"
                ),
                "sqlite_coordinates": "UPDATE objects SET best_lat=best_lon",
                "sqlite_wkt": "UPDATE measurements SET geom_1992=geom_wgs84",
                "sqlite_cave": "UPDATE objects SET cave_id='C-0002' WHERE id='KSW-0001'",
                "sqlite_reverse": "UPDATE caves SET object_ids_json='[]' WHERE id='C-0001'",
                "sqlite_relation": "UPDATE relations SET to_object_id='KSW-0003'",
                "sqlite_fk": "UPDATE objects SET cave_id='C-9999' WHERE id='KSW-0001'",
            }
            with sqlite3.connect(run / "katalog.sqlite") as db:
                db.execute(commands[corruption])
    elif corruption == "zip_contents":
        rewrite_zip(
            exports / "katalog.sqlite.zip", lambda c: c.update({"katalog.sqlite": b"old database"})
        )
    elif corruption == "zip_crc":
        # Store a member without compression, then alter its payload, preserving its old CRC.
        path = exports / "katalog.sqlite.zip"
        rewrite_zip(path, lambda c: None)
        payload = bytearray(path.read_bytes())
        offset = payload.index(b"SQLite format 3")
        payload[offset] ^= 1
        path.write_bytes(payload)
    elif corruption == "shx_offset":

        def change(contents):
            payload = bytearray(contents["best-measurements.shx"])
            struct.pack_into(">i", payload, 100, 1000000)
            contents["best-measurements.shx"] = bytes(payload)

        rewrite_zip(exports / "best-measurements.shp.zip", change)
    elif corruption == "shp_axes":

        def change(contents):
            payload = bytearray(contents["best-measurements.shp"])
            x, y = struct.unpack_from("<dd", payload, 112)
            struct.pack_into("<dd", payload, 112, y, x)
            contents["best-measurements.shp"] = bytes(payload)

        rewrite_zip(exports / "best-measurements.shp.zip", change)
    else:

        def change(contents):
            payload = bytearray(contents["best-measurements.dbf"])
            header_length = struct.unpack_from("<H", payload, 8)[0]
            # Corrupt a name field, leaving the object ID intact.
            payload[header_length + 42] = 0xFF
            contents["best-measurements.dbf"] = bytes(payload)

        rewrite_zip(exports / "best-measurements.shp.zip", change)
    with pytest.raises(
        (
            runner.VerificationError,
            sqlite3.DatabaseError,
            UnicodeDecodeError,
            zipfile.BadZipFile,
            struct.error,
        )
    ):
        runner.readback_artifacts(data, run, GENERATED_AT)


@pytest.mark.parametrize("direction", ["object", "cave"])
def test_readback_checks_both_source_membership_directions(runner, artifacts, direction):
    data, run = artifacts
    if direction == "object":
        path = data / "objects" / "KSW" / "KSW-0001.yml"
        obj = yaml.safe_load(path.read_text())
        obj["cave_id"] = "C-0002"
    else:
        path = data / "caves" / "C-0002.yml"
        obj = yaml.safe_load(path.read_text())
        obj["object_ids"] = ["KSW-0001"]
    _write_yaml(path, obj)
    with pytest.raises(runner.VerificationError, match="link"):
        runner.readback_artifacts(data, run, GENERATED_AT)


@pytest.fixture
def repo(catalog):
    root = catalog.parent
    (root / ".gitignore").write_text("build/\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--allow-empty",
            "-qm",
            "fixture",
        ],
        cwd=root,
        check=True,
    )
    return root


def fake_executor(runner, monkeypatch, *, failing=None, build=True):
    calls = []

    def execute(command, cwd, log_path):
        name = log_path.stem
        calls.append(name)
        log_path.write_text(f"fixture command: {name}\n")
        if name == failing:
            return 23
        if name == "build" and build:
            build_release_artifacts(
                data_dir=cwd / "data",
                sqlite_path=log_path.parent / "katalog.sqlite",
                output_dir=log_path.parent / "exports",
                generated_at=command[-1],
            )
        return 0

    monkeypatch.setattr(runner, "execute", execute)
    return calls


@pytest.mark.parametrize(
    "stage",
    ["uv-version", "git-version", "format", "lint", "tests", "validate", "build", "readback"],
)
def test_stage_failure_is_reported_and_never_masked(runner, repo, monkeypatch, stage):
    calls = fake_executor(runner, monkeypatch, failing=stage)
    if stage == "readback":

        def fail(*args):
            raise runner.VerificationError("forced readback failure")

        monkeypatch.setattr(runner, "readback_artifacts", fail)
    code, path = runner.verify_project(repo)
    report = json.loads(path.read_text())
    assert code != 0
    assert report["exit_code"] == code
    assert report["stages"][-1]["name"] == stage
    assert report["stages"][-1]["exit_code"] != 0
    assert calls == [s["name"] for s in report["stages"] if s["name"] != "readback"]
    assert report["immutability_exit_code"] == 0


def test_runner_records_identity_commands_versions_and_fresh_build(runner, repo, monkeypatch):
    calls = fake_executor(runner, monkeypatch)
    code, path = runner.verify_project(repo)
    report = json.loads(path.read_text())
    assert code == 0
    assert calls == ["uv-version", "git-version", "format", "lint", "tests", "validate", "build"]
    assert report["python"]
    assert report["packages"]["pytest"]
    assert len(report["source_before"]["base_sha"]) == 40
    assert len(report["source_before"]["tree_sha256"]) == 64
    assert report["source_before"] == report["source_after"]
    assert report["data_before_sha256"] == report["data_after_sha256"]
    assert report["readback"]["counts"]["objects"] == 3
    assert all(s["command"] and s["exit_code"] == 0 for s in report["stages"])
    # A successful command that produces nothing cannot reuse the preceding successful run.
    fake_executor(runner, monkeypatch, build=False)
    second_code, second_path = runner.verify_project(repo)
    assert second_code != 0
    assert second_path.parent != path.parent
    assert "Missing fresh artifact" in json.loads(second_path.read_text())["error"]


@pytest.mark.parametrize("target", ["data", "code"])
def test_runner_rejects_changed_source_even_when_commands_pass(runner, repo, monkeypatch, target):
    fake_executor(runner, monkeypatch)
    original = runner.execute

    def execute(command, cwd, log_path):
        result = original(command, cwd, log_path)
        if log_path.stem == "tests":
            path = repo / "data" / "new-source.txt" if target == "data" else repo / "new-code.py"
            path.write_text("changed")
        return result

    monkeypatch.setattr(runner, "execute", execute)
    code, path = runner.verify_project(repo)
    report = json.loads(path.read_text())
    assert code != 0
    assert report["immutability_exit_code"] == 1
    assert "changed during verification" in report["immutability_error"]


def test_hash_tracks_untracked_paths_bytes_modes_and_excludes_reports(runner, repo):
    before = runner.tree_identity(repo)
    (repo / "build").mkdir()
    (repo / "build" / "report.json").write_text("ignored")
    assert runner.tree_identity(repo) == before
    path = repo / "script.py"
    path.write_text("one")
    first = runner.tree_identity(repo)
    assert first["tree_sha256"] != before["tree_sha256"]
    path.write_text("two")
    second = runner.tree_identity(repo)
    assert first["tree_sha256"] != second["tree_sha256"]
    path.chmod(0o755)
    assert runner.tree_identity(repo)["tree_sha256"] != second["tree_sha256"]
    path.rename(repo / "renamed.py")
    assert runner.tree_identity(repo)["tree_sha256"] != second["tree_sha256"]


def test_execute_retains_real_exit_code_and_both_streams(runner, tmp_path):
    log = tmp_path / "stage.log"
    code = runner.execute(
        [
            sys.executable,
            "-c",
            "import sys; print('out'); print('err', file=sys.stderr); sys.exit(17)",
        ],
        tmp_path,
        log,
    )
    assert code == 17
    assert "out" in log.read_text() and "err" in log.read_text()
    assert runner.execute([str(tmp_path / "missing-executable")], tmp_path, log) == 127
    assert "FileNotFoundError" in log.read_text()


def test_main_propagates_gate_failure(runner, monkeypatch):
    monkeypatch.setattr(runner, "verify_project", lambda: (23, Path("report.json")))
    assert runner.main([]) == 1
