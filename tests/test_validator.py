import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml

from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992
from gps_kataster_obiektow_tatr.data_loader import (
    DataKind,
    LoadedDataset,
    LoadedYamlRecord,
    load_dataset,
)
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts
from gps_kataster_obiektow_tatr.validator import (
    ValidationIssue,
    ValidationSeverity,
    validate_data_dir,
    validate_dataset,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATE_SCRIPT = REPO_ROOT / "scripts" / "validate.py"
KSW_LAT = 49.23459299
KSW_LON = 19.87589498


def test_unhashable_pig_reference_type_reports_schema_error(tmp_path):
    data_dir = tmp_path / "data"
    obj = _valid_object()
    obj["external_refs"] = [{"system": "PIG", "ref_type": [], "external_id": "test"}]
    _write_object(data_dir, obj)
    issues = validate_data_dir(data_dir)
    assert "SCHEMA_VALIDATION" in _codes(issues)
    assert _severities(issues, "SCHEMA_VALIDATION") == {ValidationSeverity.ERROR}


@pytest.mark.parametrize("target", ["object", "cave", "relation"])
def test_in_memory_dataset_validates_all_record_kinds_without_writing(tmp_path, target):
    data_dir = tmp_path / "data"
    _write_object(data_dir, _valid_object())
    dataset = load_dataset(data_dir)
    if target == "object":
        data = deepcopy(dataset.objects[0].raw_data)
        data["measurements"][0]["lat"] = 0
        record = LoadedYamlRecord(DataKind.OBJECT, dataset.objects[0].path, data, data)
        prospective = LoadedDataset((record,), dataset.caves, ())
        expected = "COORDINATE_MISMATCH"
    elif target == "cave":
        data = deepcopy(dataset.caves[0].raw_data)
        data["object_ids"].append("KSW-9999")
        record = LoadedYamlRecord(DataKind.CAVE, dataset.caves[0].path, data, data)
        prospective = LoadedDataset(dataset.objects, (record,), ())
        expected = "CAVE_OBJECT_REFERENCE_MISSING"
    else:
        data = {
            "schema_version": 1,
            "id": "R-0001",
            "relation_type": "sasiad",
            "from_object_id": "KSW-0001",
            "to_object_id": "KSW-9999",
        }
        record = LoadedYamlRecord(DataKind.RELATION, data_dir / "relations/R-0001.yml", data, data)
        prospective = LoadedDataset(dataset.objects, dataset.caves, (record,))
        expected = "RELATION_OBJECT_REFERENCE_MISSING"
    before = {p: p.read_bytes() for p in data_dir.rglob("*") if p.is_file()}
    issues = validate_dataset(prospective, data_dir=data_dir)
    assert any(i.code == expected and i.path == record.path for i in issues)
    assert {p: p.read_bytes() for p in data_dir.rglob("*") if p.is_file()} == before
    assert not any(i.severity == ValidationSeverity.ERROR for i in validate_data_dir(data_dir))


@pytest.mark.parametrize("replacement", ["same", "best-only"])
def test_duplicate_measurements_block_validation_and_release(tmp_path, replacement):
    data_dir = tmp_path / "data"
    obj = _valid_object()
    older = deepcopy(obj["measurements"][0])
    older.update(id="m-002", observed_date="2026-05-14")
    obj["measurements"].append(older)
    _write_object(data_dir, obj)
    path = data_dir / "objects" / "KSW" / "KSW-0001.yml"
    output = tmp_path / "output"
    kwargs = {
        "data_dir": data_dir,
        "sqlite_path": output / "katalog.sqlite",
        "output_dir": output / "exports",
    }
    # A valid two-measurement release is the independent positive control.
    release = build_release_artifacts(**kwargs, generated_at="2026-10-15T00:00:00Z")
    assert release.export_result.metadata["counts"]["measurements"] == 2
    before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    assert len(before) == 7
    history = obj["measurements"] if replacement == "same" else obj["measurements"][:1]
    content = path.read_text(encoding="utf-8") + yaml.safe_dump({"measurements": history})
    path.write_text(content, encoding="utf-8")

    issues = validate_data_dir(data_dir)
    assert len(issues) == 1
    assert issues[0].code == "YAML_INVALID"
    assert issues[0].severity == ValidationSeverity.ERROR
    assert issues[0].path == path
    assert "measurements" in issues[0].description
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), "--data-dir", str(data_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert str(path) in result.stdout + result.stderr
    assert "duplicate key" in result.stdout + result.stderr

    for target in (output, tmp_path / "new-output"):
        with pytest.raises(ValueError, match="duplicate key.*measurements"):
            build_release_artifacts(
                data_dir=data_dir,
                sqlite_path=target / "katalog.sqlite",
                output_dir=target / "exports",
            )
    assert {
        p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()
    } == before
    assert not (tmp_path / "new-output").exists()
    assert path.read_bytes() == content.encode("utf-8")


def test_reports_error_for_duplicate_object_id(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    object_data = _valid_object()
    _write_object(data_dir, object_data)
    _write_yaml(data_dir / "objects" / "KSW" / "KSW-0001-copy.yml", object_data)

    issues = validate_data_dir(data_dir)

    assert _codes(issues) >= {"DUPLICATE_OBJECT_ID"}
    assert _severities(issues, "DUPLICATE_OBJECT_ID") == {ValidationSeverity.ERROR}


def test_reports_error_for_missing_best_measurement() -> None:
    with _validation_tmp_data() as data_dir:
        object_data = _valid_object()
        object_data["best_measurement"]["measurement_id"] = "m-999"
        _write_object(data_dir, object_data)

        issues = validate_data_dir(data_dir)

    assert _codes(issues) >= {"BEST_MEASUREMENT_MISSING"}


def test_reports_error_for_manual_best_without_reason() -> None:
    with _validation_tmp_data() as data_dir:
        object_data = _valid_object()
        object_data["best_measurement"] = {
            "mode": "manual",
            "measurement_id": "m-001",
            "updated_at": "2026-05-15T10:30:00Z",
            "updated_by": "dl",
        }
        _write_object(data_dir, object_data)

        issues = validate_data_dir(data_dir)

    assert _codes(issues) >= {"BEST_MEASUREMENT_MANUAL_REASON_REQUIRED"}


def test_reports_error_for_inconsistent_coordinates() -> None:
    with _validation_tmp_data() as data_dir:
        object_data = _valid_object()
        object_data["measurements"][0]["x_1992"] += 25.0
        _write_object(data_dir, object_data)

        issues = validate_data_dir(data_dir)

    assert _codes(issues) >= {"COORDINATE_MISMATCH"}


def test_reports_requested_warning_rules_without_error(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    object_data = _valid_object()
    object_data.pop("cave_id")
    object_data["external_refs"] = [
        {
            "system": "NR_INWENT",
            "ref_type": "inventory_number",
            "external_id": "T.D-08.07",
            "scope": "object",
        },
        {
            "system": "PIG",
            "ref_type": "catalog_id",
            "external_id": "1094",
            "scope": "object",
        },
    ]
    object_data["measurements"][0]["horizontal_accuracy_m"] = None
    object_data["measurements"][0]["source_ref"] = None
    _write_object(data_dir, object_data)

    issues = validate_data_dir(data_dir)

    assert _codes(issues) >= {
        "MISSING_HORIZONTAL_ACCURACY",
        "MISSING_SOURCE_REF",
        "CAVE_ID_MISSING_FOR_CAVE_OPENING",
        "NR_INWENT_ON_OBJECT_REFERENCE",
        "PIG_CATALOG_REFERENCE_ON_OBJECT",
    }
    assert all(issue.severity == ValidationSeverity.WARNING for issue in issues)


def test_validate_script_exits_zero_for_warnings_and_nonzero_for_errors(tmp_path: Path) -> None:
    warnings_data_dir = tmp_path / "warnings" / "data"
    warnings_object = _valid_object()
    warnings_object.pop("cave_id")
    _write_object(warnings_data_dir, warnings_object)

    warning_result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), "--data-dir", str(warnings_data_dir)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert warning_result.returncode == 0
    assert "CAVE_ID_MISSING_FOR_CAVE_OPENING" in warning_result.stdout

    errors_data_dir = tmp_path / "errors" / "data"
    errors_object = _valid_object()
    errors_object["best_measurement"]["measurement_id"] = "m-999"
    _write_object(errors_data_dir, errors_object)

    error_result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), "--data-dir", str(errors_data_dir)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert error_result.returncode == 1
    assert "BEST_MEASUREMENT_MISSING" in error_result.stdout


def test_reports_warning_for_auto_best_measurement_mismatch() -> None:
    with _validation_tmp_data() as data_dir:
        object_data = _valid_object()
        object_data["measurements"] = [
            _measurement_variant("m-001", source="PIG", observed_date="2026-05-16"),
            _measurement_variant("m-002", source="TPN", observed_date="2026-05-15"),
        ]
        object_data["best_measurement"]["measurement_id"] = "m-001"
        _write_object(data_dir, object_data)

        issues = validate_data_dir(data_dir)

    assert _codes(issues) >= {"BEST_MEASUREMENT_AUTO_MISMATCH"}
    assert _severities(issues, "BEST_MEASUREMENT_AUTO_MISMATCH") == {ValidationSeverity.WARNING}


def test_manual_best_measurement_is_not_checked_against_auto_algorithm() -> None:
    with _validation_tmp_data() as data_dir:
        object_data = _valid_object()
        object_data["measurements"] = [
            _measurement_variant("m-001", source="PIG", observed_date="2026-05-16"),
            _measurement_variant("m-002", source="TPN", observed_date="2026-05-15"),
        ]
        object_data["best_measurement"] = {
            "mode": "manual",
            "measurement_id": "m-001",
            "reason": "Operator utrzymuje starszy pomiar PIG do czasu rozstrzygniecia TPN.",
            "updated_at": "2026-05-15T10:30:00Z",
            "updated_by": "dl",
        }
        _write_object(data_dir, object_data)

        issues = validate_data_dir(data_dir)

    assert "BEST_MEASUREMENT_AUTO_MISMATCH" not in _codes(issues)


def test_reports_warning_when_auto_best_measurement_uses_rejected_fallback() -> None:
    with _validation_tmp_data() as data_dir:
        object_data = _valid_object()
        object_data["measurements"] = [
            _measurement_variant(
                "m-001",
                source="TPN",
                observed_date="2026-05-15",
                status="odrzucony",
            )
        ]
        object_data["best_measurement"]["measurement_id"] = "m-001"
        _write_object(data_dir, object_data)

        issues = validate_data_dir(data_dir)

    assert _codes(issues) >= {"BEST_MEASUREMENT_REJECTED_FALLBACK"}
    assert _severities(issues, "BEST_MEASUREMENT_REJECTED_FALLBACK") == {ValidationSeverity.WARNING}


class _validation_tmp_data:
    def __enter__(self) -> Path:
        from tempfile import TemporaryDirectory

        self._tmp_dir = TemporaryDirectory()
        self.data_dir = Path(self._tmp_dir.name) / "data"
        return self.data_dir

    def __exit__(self, *args: object) -> None:
        self._tmp_dir.cleanup()


def _valid_object() -> dict[str, Any]:
    measurement = _valid_measurement()
    return {
        "schema_version": 1,
        "id": "KSW-0001",
        "category": "jaskinia_otwor",
        "name_local": "Jaskinia testowa - otwor glowny",
        "cave_id": "C-0001",
        "id_assignment": {
            "method": "auto",
            "assigned_from_measurement_id": "m-001",
            "assigned_prefix": "KSW",
            "prefix_override_reason": None,
        },
        "external_refs": [],
        "measurements": [measurement],
        "best_measurement": {
            "mode": "auto",
            "measurement_id": "m-001",
            "reason": None,
            "updated_at": "2026-05-15T10:30:00Z",
            "updated_by": "dl",
        },
        "attachments": [],
        "notes": None,
        "created_at": "2026-05-15T10:00:00Z",
        "created_by": "dl",
        "updated_at": "2026-05-15T10:30:00Z",
        "updated_by": "dl",
    }


def _valid_measurement() -> dict[str, Any]:
    pl_1992 = wgs84_to_1992(lat=KSW_LAT, lon=KSW_LON)
    return {
        "id": "m-001",
        "lat": KSW_LAT,
        "lon": KSW_LON,
        "x_1992": pl_1992.x_1992,
        "y_1992": pl_1992.y_1992,
        "elevation_m": 1240.0,
        "elevation_datum": "unknown",
        "elevation_source": "gps",
        "horizontal_accuracy_m": 5.0,
        "vertical_accuracy_m": 8.0,
        "source": "wlasne",
        "source_ref": "teren:2026-05-15:gps",
        "observed_date": "2026-05-15",
        "source_date": None,
        "method": "gps_receiver",
        "device": "Garmin GPSMAP",
        "tags": ["fixture"],
        "verification_status": "zweryfikowany",
        "verified_by": "dl",
        "verified_at": "2026-05-15T10:30:00Z",
        "notes": "Minimalny poprawny pomiar domenowy.",
        "created_at": "2026-05-15T10:00:00Z",
        "created_by": "dl",
    }


def _measurement_variant(
    measurement_id: str,
    *,
    source: str,
    observed_date: str,
    status: str = "nieweryfikowany",
) -> dict[str, Any]:
    measurement = _valid_measurement()
    measurement.update(
        {
            "id": measurement_id,
            "source": source,
            "source_ref": f"{source}:{measurement_id}",
            "observed_at": None,
            "observed_date": observed_date,
            "method": "source_record" if source in {"TPN", "PIG", "geoportal"} else "ustalenie",
            "verification_status": status,
            "verified_by": "dl" if status == "zweryfikowany" else None,
            "verified_at": "2026-05-15T10:30:00Z" if status == "zweryfikowany" else None,
        }
    )
    return measurement


def _valid_cave(object_id: str = "KSW-0001") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": "C-0001",
        "name": "Jaskinia testowa",
        "system_name": None,
        "external_refs": [],
        "object_ids": [object_id],
        "notes": None,
        "created_at": "2026-05-15T10:00:00Z",
        "created_by": "dl",
        "updated_at": "2026-05-15T10:30:00Z",
        "updated_by": "dl",
    }


def _write_object(data_dir: Path, object_data: dict[str, Any]) -> None:
    for name in ("objects", "caves", "relations"):
        (data_dir / name).mkdir(parents=True, exist_ok=True)
    data = deepcopy(object_data)
    object_id = data["id"]
    prefix = object_id.split("-", maxsplit=1)[0]
    _write_yaml(data_dir / "objects" / prefix / f"{object_id}.yml", data)
    if data.get("cave_id") == "C-0001":
        _write_yaml(data_dir / "caves" / "C-0001.yml", _valid_cave(object_id))


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _codes(issues: tuple[ValidationIssue, ...]) -> set[str]:
    return {issue.code for issue in issues}


def _severities(issues: tuple[ValidationIssue, ...], code: str) -> set[ValidationSeverity]:
    return {issue.severity for issue in issues if issue.code == code}
