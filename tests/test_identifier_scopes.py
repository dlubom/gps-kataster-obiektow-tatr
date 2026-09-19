"""Domain ID collisions must fail before SQLite or export writes."""

import json
import sqlite3
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts
from gps_kataster_obiektow_tatr.validator import ValidationSeverity, has_errors, validate_data_dir

REPO_ROOT = Path(__file__).resolve().parents[1]
SCOPES = {
    "object": ("DUPLICATE_OBJECT_ID", "KSW-0001"),
    "cave": ("DUPLICATE_CAVE_ID", "C-0001"),
    "relation": ("DUPLICATE_RELATION_ID", "R-0001"),
    "measurement": ("DUPLICATE_MEASUREMENT_ID", "m-001"),
    "attachment": ("DUPLICATE_ATTACHMENT_ID", "a-001"),
}
ARTIFACTS = (
    "katalog.sqlite",
    "katalog.sqlite.zip",
    "metadata.json",
    "best-measurements.geojson",
    "best-measurements.csv",
    "best-measurements.gpx",
    "best-measurements.shp.zip",
)


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _sample(data_dir):
    obj = yaml.safe_load((REPO_ROOT / "tests/fixtures/valid-object.yml").read_text())
    coords = wgs84_to_1992(lat=49.23459299, lon=19.87589498)
    obj["measurements"][0].update(
        lat=49.23459299,
        lon=19.87589498,
        x_1992=coords.x_1992,
        y_1992=coords.y_1992,
        source_ref="field:1",
    )
    obj["attachments"] = [
        {
            "id": "a-001",
            "kind": "zdjecie",
            "path": "https://example.org/photo.jpg",
            "measurement_id": "m-001",
            "created_at": "2026-05-15T10:00:00Z",
            "created_by": "dl",
        }
    ]
    cave = yaml.safe_load((REPO_ROOT / "tests/fixtures/valid-cave.yml").read_text())
    cave["object_ids"] = ["KSW-0001", "KSW-0002"]
    other = deepcopy(obj)
    other["id"] = "KSW-0002"
    relation = {
        "schema_version": 1,
        "id": "R-0001",
        "from_object_id": "KSW-0001",
        "to_object_id": "KSW-0002",
        "relation_type": "sasiad",
    }
    paths = {
        "object": data_dir / "objects/KSW/KSW-0001.yml",
        "cave": data_dir / "caves/C-0001.yml",
        "relation": data_dir / "relations/R-0001.yml",
    }
    for kind, record in [("object", obj), ("cave", cave), ("relation", relation)]:
        _write(paths[kind], record)
    _write(data_dir / "objects/KSW/KSW-0002.yaml", other)
    return paths


def _duplicate(paths, scope, different):
    path = paths.get(scope, paths["object"])
    record = yaml.safe_load(path.read_text())
    if scope in {"measurement", "attachment"}:
        field = f"{scope}s"
        duplicate = deepcopy(record[field][0])
        if different:
            duplicate["elevation_m" if scope == "measurement" else "path"] = (
                1300 if scope == "measurement" else "https://example.org/other.jpg"
            )
        record[field].append(duplicate)
        _write(path, record)
        return [path]
    if different:
        record["notes"] = "Different record sharing the same ID."
    duplicate_path = path.with_suffix(".yaml")
    _write(duplicate_path, record)
    return [path, duplicate_path]


def _snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("different", [False, True])
def test_duplicate_ids_are_domain_errors(tmp_path, scope, different):
    data_dir = tmp_path / "data"
    paths = _sample(data_dir)
    affected = _duplicate(paths, scope, different)
    before = _snapshot(data_dir)
    issues = validate_data_dir(data_dir)
    code, identifier = SCOPES[scope]
    errors = [issue for issue in issues if issue.severity == ValidationSeverity.ERROR]
    expected_codes = {code}
    if scope == "attachment" and not different:
        # Existing uniqueItems also rejects identical items.
        expected_codes.add("SCHEMA_VALIDATION")
    assert {issue.code for issue in errors} == expected_codes
    errors = [issue for issue in errors if issue.code == code]
    assert {issue.path for issue in errors} == set(affected)
    for issue in errors:
        assert identifier in issue.description
        if scope in {"measurement", "attachment"}:
            assert "KSW-0001" in issue.description
        else:
            assert all(str(path) in issue.description for path in affected)
    assert _snapshot(data_dir) == before


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize(
    "command",
    [
        "validate.py",
        "build_db.py",
        "export_best_measurements.py",
        "build_release_artifacts.py",
    ],
)
def test_cli_duplicate_ids_preserve_artifacts(tmp_path, scope, existing, command):
    data_dir = tmp_path / "data"
    paths = _sample(data_dir)
    _duplicate(paths, scope, different=True)
    output = tmp_path / "build"
    if existing:
        output.mkdir()
        for name in ARTIFACTS:
            (output / name).write_bytes(f"existing: {name}".encode())
    before = _snapshot(tmp_path)
    args = ["--data-dir", str(data_dir)]
    if command == "build_db.py":
        args += ["--output", str(output / "katalog.sqlite")]
    elif command == "export_best_measurements.py":
        args += ["--output-dir", str(output)]
    elif command == "build_release_artifacts.py":
        args += ["--output-dir", str(output), "--sqlite-output", str(output / "katalog.sqlite")]
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / command), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    diagnostic = result.stdout + result.stderr
    assert result.returncode == 1, diagnostic
    assert SCOPES[scope][0] in diagnostic
    assert "Traceback" not in diagnostic
    assert _snapshot(tmp_path) == before


def test_local_ids_can_repeat_in_different_objects_and_build(tmp_path):
    data_dir = tmp_path / "data"
    _sample(data_dir)
    assert not has_errors(validate_data_dir(data_dir))
    before = _snapshot(data_dir)
    result = build_release_artifacts(
        data_dir=data_dir,
        sqlite_path=tmp_path / "build/katalog.sqlite",
        output_dir=tmp_path / "build",
        generated_at="2026-09-18T12:00:00Z",
    )
    assert len(result.artifact_paths) == 7
    with sqlite3.connect(result.sqlite_result.sqlite_path) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        for table, identifier in [("measurements", "m-001"), ("attachments", "a-001")]:
            assert conn.execute(
                f"SELECT object_id, id FROM {table} ORDER BY object_id"
            ).fetchall() == [
                ("KSW-0001", identifier),
                ("KSW-0002", identifier),
            ]
        assert conn.execute("SELECT id FROM relations").fetchall() == [("R-0001",)]
    geojson = json.loads(result.export_result.geojson_path.read_text())
    assert len(geojson["features"]) == 2
    assert _snapshot(data_dir) == before


@pytest.mark.parametrize("scope", ["object", "cave", "relation"])
def test_global_duplicate_after_unique_record_is_still_reported(tmp_path, scope):
    data_dir = tmp_path / "data"
    paths = _sample(data_dir)
    unique = yaml.safe_load(paths[scope].read_text())
    unique["id"] = unique["id"][:-1] + "0"
    if scope == "cave":
        unique["object_ids"] = []
    elif scope == "object":
        cave = yaml.safe_load(paths["cave"].read_text())
        cave["object_ids"].append(unique["id"])
        _write(paths["cave"], cave)
    _write(paths[scope].with_name(f"{unique['id']}.yml"), unique)
    affected = _duplicate(paths, scope, different=True)
    errors = [i for i in validate_data_dir(data_dir) if i.severity == ValidationSeverity.ERROR]
    assert {i.code for i in errors} == {SCOPES[scope][0]}
    assert {i.path for i in errors} == set(affected)


@pytest.mark.parametrize("scope", ["measurement", "attachment"])
def test_invalid_local_id_does_not_hide_later_duplicates(tmp_path, scope):
    data_dir = tmp_path / "data"
    paths = _sample(data_dir)
    _duplicate(paths, scope, different=True)
    obj = yaml.safe_load(paths["object"].read_text())
    malformed = deepcopy(obj[f"{scope}s"][0])
    malformed["id"] = []
    obj[f"{scope}s"].insert(0, malformed)
    _write(paths["object"], obj)
    errors = [i for i in validate_data_dir(data_dir) if i.severity == ValidationSeverity.ERROR]
    assert {i.code for i in errors} == {"SCHEMA_VALIDATION", SCOPES[scope][0]}
    assert {i.path for i in errors} == {paths["object"]}
