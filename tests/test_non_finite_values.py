"""Non-finite measurements must fail before geometry, selection or artifact writes."""

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from export_test_support import accept_source, cli_args, write_sample_data

from gps_kataster_obiektow_tatr.best_measurements_export import export_best_measurements
from gps_kataster_obiektow_tatr.build_db import build_database
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts
from gps_kataster_obiektow_tatr.validator import (
    ValidationSeverity,
    validate_data_dir,
)

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
SOURCE_FIELDS = ("lat", "lon", "input_x", "input_y", *FIELDS[4:])
BAD_VALUES = [float("nan"), float("inf"), float("-inf")]


@pytest.fixture
def canonical_finite_dataset(tmp_path):
    data = write_sample_data(tmp_path / "data")
    path = data / "objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(path.read_text())
    obj["measurements"] = obj["measurements"][:1]
    path.write_text(yaml.safe_dump(obj))
    return data, path, obj


def _snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _reject_json_constant(value):
    raise ValueError(f"Non-standard JSON constant: {value}")


@pytest.mark.parametrize("field", SOURCE_FIELDS)
@pytest.mark.parametrize("value", BAD_VALUES, ids=["nan", "pos-inf", "neg-inf"])
def test_non_finite_measurement_blocks_validation_and_all_artifacts(
    canonical_finite_dataset,
    tmp_path,
    field,
    value,
):
    data_dir, path, obj = canonical_finite_dataset
    if field in ("input_x", "input_y"):
        # EPSG:2180 source, with no redundant/derived coordinate declarations.
        m = obj["measurements"][0]
        m.pop("lat")
        m.pop("lon")
        m.update(input_srid=2180, input_x=563744.25, input_y=152267.23)
        path.write_text(yaml.safe_dump(obj))
    baseline = accept_source(data_dir)
    output = tmp_path / "output"
    result = build_release_artifacts(
        **baseline,
        data_dir=data_dir,
        output_dir=output / "exports",
        generated_at="2026-10-15T00:00:00Z",
    )
    json.loads(result.export_result.geojson_path.read_text(), parse_constant=_reject_json_constant)
    before_output = _snapshot(output)
    assert len(before_output) == 13
    # Corrupt a historical, rejected, non-best measurement: the entire history is checked.
    other = deepcopy(obj["measurements"][0])
    other.update(id="m-002", verification_status="odrzucony")
    other[field] = value
    obj["measurements"].append(other)
    path.write_text(yaml.safe_dump(obj), encoding="utf-8")
    before_data = _snapshot(data_dir)
    issues = validate_data_dir(data_dir)
    assert any(
        i.code == "SQL_CATALOG_INVALID"
        and i.severity == ValidationSeverity.ERROR
        and i.path == path
        and "m-002" in i.description
        and "MEASUREMENT_NON_FINITE" in i.description
        and field in i.description
        for i in issues
    )
    for target in (output, tmp_path / "missing-output"):
        with pytest.raises(ValueError, match=rf"MEASUREMENT_NON_FINITE: m-002: {field}"):
            build_database(**baseline, data_dir=data_dir, output_path=target / "katalog.dump")
        with pytest.raises(ValueError, match=rf"MEASUREMENT_NON_FINITE: m-002: {field}"):
            export_best_measurements(**baseline, data_dir=data_dir, output_dir=target / "exports")
        with pytest.raises(ValueError, match=rf"MEASUREMENT_NON_FINITE: m-002: {field}"):
            build_release_artifacts(
                **baseline,
                data_dir=data_dir,
                output_dir=target / "exports",
            )
    assert _snapshot(output) == before_output
    assert not (tmp_path / "missing-output").exists()
    assert _snapshot(data_dir) == before_data


@pytest.mark.parametrize("value", [None, 0, 12.5])
def test_optional_numbers_preserve_null_zero_and_finite_values(
    canonical_finite_dataset, tmp_path, value
):
    data_dir, path, obj = canonical_finite_dataset
    obj["measurements"][0].update({field: value for field in FIELDS[4:]})
    path.write_text(yaml.safe_dump(obj), encoding="utf-8")
    assert not any(i.severity == ValidationSeverity.ERROR for i in validate_data_dir(data_dir))
    baseline = accept_source(data_dir)
    result = build_release_artifacts(
        **baseline,
        data_dir=data_dir,
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
def test_non_finite_cli_returns_controlled_error_without_writes(
    canonical_finite_dataset, tmp_path, script
):
    data_dir, path, obj = canonical_finite_dataset
    baseline = accept_source(data_dir)
    obj["measurements"][0]["lat"] = float("nan")
    path.write_text(yaml.safe_dump(obj), encoding="utf-8")
    args = [sys.executable, str(REPO_ROOT / "scripts" / script), "--data-dir", str(data_dir)]
    output = tmp_path / "output"
    if script == "build_db.py":
        args += ["--output", str(output / "katalog.dump")]
    elif script == "export_best_measurements.py" or script == "build_release_artifacts.py":
        args += ["--output-dir", str(output / "exports")]
    args += cli_args(baseline)
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    diagnostic = result.stdout + result.stderr
    assert result.returncode == 1, diagnostic
    assert "MEASUREMENT_NON_FINITE" in diagnostic
    if script == "validate.py":
        assert "SQL_CATALOG_INVALID" in diagnostic
    assert str(data_dir) in diagnostic
    assert "Traceback" not in diagnostic
    assert not output.exists()


def test_validator_handles_invalid_latitude(canonical_finite_dataset):
    data_dir, path, obj = canonical_finite_dataset
    obj["measurements"][0]["lat"] = 100
    path.write_text(yaml.safe_dump(obj), encoding="utf-8")
    issues = validate_data_dir(data_dir)
    assert any(
        i.code == "SQL_CATALOG_INVALID"
        and i.path == path
        and "measurements_input_geom_check4" in i.description
        for i in issues
    )


@pytest.mark.parametrize("field", ("lat", "lon", *FIELDS[4:]))
def test_unrepresentable_integer_is_diagnosed_before_float_conversion(
    canonical_finite_dataset, field
):
    data_dir, path, obj = canonical_finite_dataset
    obj["measurements"][0][field] = 10**400
    path.write_text(yaml.safe_dump(obj), encoding="utf-8")
    issues = validate_data_dir(data_dir)
    assert any(
        i.code == "SQL_CATALOG_INVALID"
        and "MEASUREMENT_NON_FINITE" in i.description
        and field in i.description
        for i in issues
    )
