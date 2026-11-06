"""Legacy declarations must be validated before normalization."""

import pytest
from export_test_support import write_yaml
from test_legacy_migration import legacy_source

from gps_kataster_obiektow_tatr.data_loader import load_yaml_dataset
from gps_kataster_obiektow_tatr.validator import has_errors, validate_proposal, validated_proposal


def native(measurement, srid):
    measurement.update(
        input_srid=srid,
        input_x=measurement["lon"] if srid == 4326 else measurement["y_1992"],
        input_y=measurement["lat"] if srid == 4326 else measurement["x_1992"],
    )


@pytest.mark.parametrize("srid", [4326, 2180])
@pytest.mark.parametrize("damage", ["wgs", "projected", "partial-wgs", "partial-projected"])
def test_native_geometry_checks_every_supplied_coordinate_declaration(tmp_path, srid, damage):
    data, obj, _ = legacy_source(tmp_path)
    m = obj["measurements"][0]
    native(m, srid)
    if damage == "wgs":
        m["lat"] += 0.01
    elif damage == "projected":
        m["x_1992"] += 100
    else:
        m.pop("lon" if damage == "partial-wgs" else "y_1992")
    path = data / "objects/KSW/KSW-0001.yml"
    write_yaml(path, obj)
    issues = validate_proposal(load_yaml_dataset(data), data_dir=data)
    assert any(i.code == "COORDINATE_MISMATCH" and i.path == path for i in issues), issues


@pytest.mark.parametrize("srid", [4326, 2180])
@pytest.mark.parametrize("declarations", ["none", "wgs", "projected", "both"])
def test_valid_native_declarations_preserve_geometry_and_auto_choice(tmp_path, srid, declarations):
    data, obj, _ = legacy_source(tmp_path)
    m = obj["measurements"][0]
    native(m, srid)
    expected = (m["input_x"], m["input_y"])
    if declarations in ("none", "projected"):
        m.pop("lat")
        m.pop("lon")
    if declarations in ("none", "wgs"):
        m.pop("x_1992")
        m.pop("y_1992")
    # Valid stale auto cache is a reference, not a manual selection.
    obj["best_measurement"]["measurement_id"] = "m-001"
    write_yaml(data / "objects/KSW/KSW-0001.yml", obj)
    with validated_proposal(load_yaml_dataset(data), data_dir=data) as (catalog, issues):
        assert not has_errors(issues)
        projection = catalog.dataset().objects[0].data
        assert projection["best_measurement"]["measurement_id"] == "m-002"
        assert (
            projection["measurements"][0]["input_x"],
            projection["measurements"][0]["input_y"],
        ) == expected


def test_missing_legacy_auto_best_is_rejected_before_normalization(tmp_path):
    data, obj, _ = legacy_source(tmp_path)
    obj["best_measurement"]["measurement_id"] = "m-999"
    path = data / "objects/KSW/KSW-0001.yml"
    write_yaml(path, obj)
    issues = validate_proposal(load_yaml_dataset(data), data_dir=data)
    assert any(i.code == "BEST_MEASUREMENT_MISSING" and i.path == path for i in issues), issues
