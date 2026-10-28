"""Non-finite measurements must fail before geometry, selection or artifact writes."""

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from qgis_fixtures import write_jktz_source

from gps_kataster_obiektow_tatr.best_measurement import select_default_best_measurement_id
from gps_kataster_obiektow_tatr.best_measurements_export import (
    BestMeasurementsExportValidationError,
    export_best_measurements,
)
from gps_kataster_obiektow_tatr.build_db import (
    BuildDatabaseValidationError,
    build_sqlite_database,
)
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts
from gps_kataster_obiektow_tatr.validator import ValidationSeverity, validate_data_dir

REPO_ROOT = Path(__file__).resolve().parents[1]
FIELDS = (
    "lat",
    "lon",
    "x_1992",
    "y_1992",
    "elevation_m",
    "horizontal_accuracy_m",
    "vertical_accuracy_m",
)
BAD_VALUES = [float("nan"), float("inf"), float("-inf")]


@pytest.fixture
def finite_dataset(tmp_path, make_data_dir):
    data_dir = make_data_dir(tmp_path / "data")
    obj = yaml.safe_load((REPO_ROOT / "tests/fixtures/valid-object.yml").read_text())
    # Independently known WGS84/PL-1992 pair from the coordinate fixture.
    obj["measurements"][0].update(
        lat=49.23459299,
        lon=19.87589498,
        x_1992=152267.23,
        y_1992=563744.25,
    )
    cave = yaml.safe_load((REPO_ROOT / "tests/fixtures/valid-cave.yml").read_text())
    cave["object_ids"] = [obj["id"]]
    path = data_dir / "objects/KSW/KSW-0001.yml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(obj), encoding="utf-8")
    (data_dir / "caves/C-0001.yml").write_text(yaml.safe_dump(cave), encoding="utf-8")
    return data_dir, path, obj


def _snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _reject_json_constant(value):
    raise ValueError(f"Non-standard JSON constant: {value}")


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("value", BAD_VALUES, ids=["nan", "pos-inf", "neg-inf"])
def test_non_finite_measurement_blocks_validation_and_all_artifacts(
    finite_dataset,
    tmp_path,
    field,
    value,
):
    data_dir, path, obj = finite_dataset
    output = tmp_path / "output"
    result = build_release_artifacts(
        jktz_source_dir=write_jktz_source(tmp_path / "jktz"),
        data_dir=data_dir,
        sqlite_path=output / "katalog.sqlite",
        output_dir=output / "exports",
        generated_at="2026-10-15T00:00:00Z",
    )
    json.loads(result.export_result.geojson_path.read_text(), parse_constant=_reject_json_constant)
    before_output = _snapshot(output)
    assert len(before_output) == 14
    # Corrupt a historical, rejected, non-best measurement: the entire history is checked.
    other = deepcopy(obj["measurements"][0])
    other.update(id="m-002", verification_status="odrzucony")
    other[field] = value
    obj["measurements"].append(other)
    path.write_text(yaml.safe_dump(obj), encoding="utf-8")
    before_data = _snapshot(data_dir)
    issues = validate_data_dir(data_dir)
    assert any(
        i.code == "MEASUREMENT_NON_FINITE"
        and i.severity == ValidationSeverity.ERROR
        and i.path == path
        and field in i.description
        and "m-002" in i.description
        and "KSW-0001" in i.description
        for i in issues
    )
    for target in (output, tmp_path / "missing-output"):
        with pytest.raises(BuildDatabaseValidationError, match="MEASUREMENT_NON_FINITE"):
            build_sqlite_database(data_dir=data_dir, output_path=target / "katalog.sqlite")
        with pytest.raises(BestMeasurementsExportValidationError, match="MEASUREMENT_NON_FINITE"):
            export_best_measurements(data_dir=data_dir, output_dir=target / "exports")
        with pytest.raises(BuildDatabaseValidationError, match="MEASUREMENT_NON_FINITE"):
            build_release_artifacts(
                jktz_source_dir=write_jktz_source(tmp_path / "jktz"),
                data_dir=data_dir,
                sqlite_path=target / "katalog.sqlite",
                output_dir=target / "exports",
            )
    assert _snapshot(output) == before_output
    assert not (tmp_path / "missing-output").exists()
    assert _snapshot(data_dir) == before_data


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("value", BAD_VALUES, ids=["nan", "pos-inf", "neg-inf"])
def test_best_selection_rejects_non_finite_values(finite_dataset, field, value):
    _, _, obj = finite_dataset
    obj["measurements"][0][field] = value
    with pytest.raises(ValueError, match=field):
        select_default_best_measurement_id(iter(obj["measurements"]))


def test_validator_diagnoses_all_bad_fields_before_geometry_and_best(finite_dataset, monkeypatch):
    data_dir, path, obj = finite_dataset
    obj["measurements"][0].update({field: float("nan") for field in FIELDS})
    path.write_text(yaml.safe_dump(obj), encoding="utf-8")

    def unexpected(*args, **kwargs):
        pytest.fail("Invalid measurement reached geometry or best selection")

    monkeypatch.setattr(
        "gps_kataster_obiektow_tatr.validator.coordinate_consistency_error_m", unexpected
    )
    monkeypatch.setattr(
        "gps_kataster_obiektow_tatr.validator.select_default_best_measurement_id", unexpected
    )
    issues = validate_data_dir(data_dir)
    errors = [i for i in issues if i.code == "MEASUREMENT_NON_FINITE"]
    assert len(errors) == 7
    assert all(any(field in i.description for i in errors) for field in FIELDS)


@pytest.mark.parametrize("value", [None, 0, 12.5])
def test_optional_numbers_preserve_null_zero_and_finite_values(finite_dataset, tmp_path, value):
    data_dir, path, obj = finite_dataset
    obj["measurements"][0].update({field: value for field in FIELDS[4:]})
    path.write_text(yaml.safe_dump(obj), encoding="utf-8")
    assert not any(i.severity == ValidationSeverity.ERROR for i in validate_data_dir(data_dir))
    result = build_release_artifacts(
        jktz_source_dir=write_jktz_source(tmp_path / "jktz"),
        data_dir=data_dir,
        sqlite_path=tmp_path / "katalog.sqlite",
        output_dir=tmp_path / "exports",
    )
    data = json.loads(
        result.export_result.geojson_path.read_text(), parse_constant=_reject_json_constant
    )
    properties = data["features"][0]["properties"]
    assert properties["elevation_m"] == value
    assert properties["horizontal_accuracy_m"] == value
    assert properties["vertical_accuracy_m"] == value


@pytest.mark.parametrize(
    "script",
    ["validate.py", "build_db.py", "export_best_measurements.py", "build_release_artifacts.py"],
)
def test_non_finite_cli_returns_controlled_error_without_writes(finite_dataset, tmp_path, script):
    data_dir, path, obj = finite_dataset
    obj["measurements"][0]["x_1992"] = float("nan")
    path.write_text(yaml.safe_dump(obj), encoding="utf-8")
    args = [sys.executable, str(REPO_ROOT / "scripts" / script), "--data-dir", str(data_dir)]
    output = tmp_path / "output"
    if script == "build_db.py":
        args += ["--output", str(output / "katalog.sqlite")]
    elif script == "export_best_measurements.py":
        args += ["--output-dir", str(output / "exports")]
    elif script == "build_release_artifacts.py":
        args += [
            "--sqlite-output",
            str(output / "katalog.sqlite"),
            "--output-dir",
            str(output / "exports"),
        ]
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    diagnostic = result.stdout + result.stderr
    assert result.returncode == 1, diagnostic
    assert "MEASUREMENT_NON_FINITE" in diagnostic and "x_1992" in diagnostic
    assert "m-001" in diagnostic and str(path) in diagnostic
    assert "Traceback" not in diagnostic
    assert not output.exists()


def test_validator_handles_non_finite_projection_result(finite_dataset):
    data_dir, path, obj = finite_dataset
    obj["measurements"][0]["lat"] = 100
    path.write_text(yaml.safe_dump(obj), encoding="utf-8")
    issues = validate_data_dir(data_dir)
    assert any(
        i.code == "COORDINATE_TRANSFORM_INVALID" and "m-001" in i.description for i in issues
    )


@pytest.mark.parametrize("field", FIELDS)
def test_unrepresentable_integer_is_diagnosed_before_float_conversion(finite_dataset, field):
    data_dir, path, obj = finite_dataset
    obj["measurements"][0][field] = 10**400
    path.write_text(yaml.safe_dump(obj), encoding="utf-8")
    issues = validate_data_dir(data_dir)
    assert any(i.code == "MEASUREMENT_NON_FINITE" and field in i.description for i in issues)
    with pytest.raises(ValueError, match=field):
        select_default_best_measurement_id(obj["measurements"])
