"""Exercise the validated boundary with real YAML and public consumers."""

from copy import deepcopy

import pytest
import yaml
from test_validator import _valid_object, _write_yaml

from gps_kataster_obiektow_tatr.data_loader import load_dataset
from gps_kataster_obiektow_tatr.validator import has_errors, validate_dataset


def _catalog(tmp_path):
    obj = _valid_object()
    obj.pop("cave_id", None)
    for kind in ("objects", "caves", "relations"):
        (tmp_path / kind).mkdir()
    path = tmp_path / "objects" / obj["id"].split("-")[0] / f"{obj['id']}.yml"
    _write_yaml(path, obj)
    return obj, path


def test_consumers_use_validated_raw_representation(tmp_path):
    from gps_kataster_obiektow_tatr.validator import validate_loaded_dataset

    obj, _ = _catalog(tmp_path)
    dataset = load_dataset(tmp_path)
    dataset.objects[0].data["measurements"][0]["lat"] = 0
    validated, issues = validate_loaded_dataset(dataset, data_dir=tmp_path)
    assert not has_errors(issues)
    assert validated.objects[0].data["measurements"] == obj["measurements"]
    assert validated.objects[0].raw_data == obj


@pytest.mark.parametrize("value", ["bad", True, float("nan"), float("inf"), 10**400])
def test_invalid_numbers_block_real_sqlite_and_exports(tmp_path, value):
    from gps_kataster_obiektow_tatr.best_measurements_export import export_best_measurements
    from gps_kataster_obiektow_tatr.build_db import build_sqlite_database

    data = tmp_path / "data"
    data.mkdir()
    obj, path = _catalog(data)
    obj["measurements"][0]["elevation_m"] = value
    _write_yaml(path, obj)
    database = tmp_path / "previous.sqlite"
    database.write_bytes(b"previous database")
    exports = tmp_path / "exports"
    exports.mkdir()
    csv = exports / "best-measurements.csv"
    csv.write_bytes(b"previous export")
    with pytest.raises(ValueError):
        build_sqlite_database(data_dir=data, output_path=database)
    with pytest.raises(ValueError):
        export_best_measurements(data_dir=data, output_dir=exports)
    assert database.read_bytes() == b"previous database"
    assert csv.read_bytes() == b"previous export"


def test_id_assignment_requires_existing_measurement(tmp_path):
    obj, path = _catalog(tmp_path)
    obj["id_assignment"]["assigned_from_measurement_id"] = "m-999"
    _write_yaml(path, obj)
    issues = validate_dataset(load_dataset(tmp_path), data_dir=tmp_path)
    assert "ID_ASSIGNMENT_MEASUREMENT_MISSING" in {i.code for i in issues}


def test_duplicate_attachment_ids_are_rejected(tmp_path):
    obj, path = _catalog(tmp_path)
    attachment = {
        "id": "a-001",
        "kind": "inne",
        "path": "https://example.org/a",
        "created_at": "2026-11-04T00:00:00Z",
        "created_by": "test",
    }
    obj["attachments"] = [attachment, {**attachment, "caption": "different"}]
    _write_yaml(path, obj)
    issues = validate_dataset(load_dataset(tmp_path), data_dir=tmp_path)
    assert "DUPLICATE_ATTACHMENT_ID" in {i.code for i in issues}


def test_duplicate_caves_are_rejected_before_build(tmp_path):
    from pathlib import Path

    _catalog(tmp_path)
    cave = yaml.safe_load((Path(__file__).parent / "fixtures/schema/valid-cave.yml").read_text())
    cave["object_ids"] = []
    _write_yaml(tmp_path / "caves" / f"{cave['id']}.yml", cave)
    _write_yaml(tmp_path / "caves" / f"{cave['id']}.yaml", deepcopy(cave))
    issues = validate_dataset(load_dataset(tmp_path), data_dir=tmp_path)
    assert "DUPLICATE_CAVE_ID" in {i.code for i in issues}


@pytest.mark.parametrize("field", ["name_local", "notes"])
@pytest.mark.parametrize("character", ["\x00", "\x01", "\ud800", "\ufffe"])
def test_unexportable_source_text_is_rejected_before_any_write(tmp_path, field, character):
    from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts

    data = tmp_path / "data"
    data.mkdir()
    obj, path = _catalog(data)
    obj[field] = "source" + character + "text"
    _write_yaml(path, obj)
    issues = validate_dataset(load_dataset(data), data_dir=data)
    assert any(i.code == "SCHEMA_VALIDATION" and field in i.description for i in issues)
    output = tmp_path / "exports"
    output.mkdir()
    sentinel = output / "best-measurements.csv"
    sentinel.write_bytes(b"old export")
    with pytest.raises(ValueError):
        build_release_artifacts(data_dir=data, sqlite_path=tmp_path / "db", output_dir=output)
    assert sentinel.read_bytes() == b"old export"
    assert not (tmp_path / "db").exists()


def test_path_validation_uses_raw_identity_not_stale_normalized_copy(tmp_path):
    _catalog(tmp_path)
    dataset = load_dataset(tmp_path)
    dataset.objects[0].raw_data["id"] = "KSW-9999"
    issues = validate_dataset(dataset, data_dir=tmp_path)
    assert "FILE_ID_MISMATCH" in {i.code for i in issues}
