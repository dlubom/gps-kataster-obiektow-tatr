import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml

from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992
from gps_kataster_obiektow_tatr.validator import (
    ValidationIssue,
    ValidationSeverity,
    validate_data_dir,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATE_SCRIPT = REPO_ROOT / "scripts" / "validate.py"
KSW_LAT = 49.23459299
KSW_LON = 19.87589498


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


@pytest.mark.parametrize(
    ("assignment_field", "invalid_value", "expected_code"),
    [
        ("assigned_from_measurement_id", "m-999", "ID_ASSIGNMENT_MEASUREMENT_MISSING"),
        ("assigned_prefix", "ABC", "ID_ASSIGNMENT_PREFIX_MISMATCH"),
    ],
)
def test_id_assignment_rejects_missing_measurement_or_wrong_durable_prefix(
    tmp_path: Path, assignment_field: str, invalid_value: str, expected_code: str
) -> None:
    data_dir = tmp_path / "data"
    object_data = _valid_object()
    object_data["id_assignment"][assignment_field] = invalid_value
    _write_object(data_dir, object_data)

    issues = validate_data_dir(data_dir)

    errors = [issue for issue in issues if issue.severity == ValidationSeverity.ERROR]
    assert {issue.code for issue in errors} == {expected_code}
    assert errors[0].path == data_dir / "objects/KSW/KSW-0001.yml"
    assert "KSW-0001" in errors[0].description
    assert invalid_value in errors[0].description


def test_id_assignment_measurement_must_belong_to_same_object(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    first = _valid_object()
    first["id_assignment"]["assigned_from_measurement_id"] = "m-999"
    _write_object(data_dir, first)
    second = _valid_object()
    second["id"] = "KSW-0002"
    second["category"] = "inne"
    second["cave_id"] = None
    second["measurements"][0]["id"] = "m-999"
    second["id_assignment"]["assigned_from_measurement_id"] = "m-999"
    second["best_measurement"]["measurement_id"] = "m-999"
    _write_object(data_dir, second)

    issues = validate_data_dir(data_dir)

    assignment_errors = [
        issue for issue in issues if issue.code == "ID_ASSIGNMENT_MEASUREMENT_MISSING"
    ]
    assert len(assignment_errors) == 1
    assert assignment_errors[0].path == data_dir / "objects/KSW/KSW-0001.yml"


@pytest.mark.parametrize("invalid_field", ["assigned_from_measurement_id", "assigned_prefix"])
@pytest.mark.parametrize(
    "command", ["build_db.py", "export_best_measurements.py", "build_release_artifacts.py"]
)
@pytest.mark.parametrize("existing_output", [False, True])
def test_id_assignment_error_blocks_artifact_writes(
    tmp_path: Path, invalid_field: str, command: str, existing_output: bool
) -> None:
    data_dir = tmp_path / "data"
    object_data = _valid_object()
    object_data["id_assignment"][invalid_field] = (
        "m-999" if invalid_field == "assigned_from_measurement_id" else "ABC"
    )
    _write_object(data_dir, object_data)
    output_dir = tmp_path / "build"
    if existing_output:
        output_dir.mkdir()
        for name in ("katalog.sqlite", "metadata.json", "best-measurements.geojson"):
            (output_dir / name).write_bytes(f"old {name}".encode())
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    args = ["--data-dir", str(data_dir)]
    if command == "build_db.py":
        args.extend(["--output", str(output_dir / "katalog.sqlite")])
    elif command == "export_best_measurements.py":
        args.extend(["--output-dir", str(output_dir)])
    else:
        args.extend(
            ["--sqlite-output", str(output_dir / "katalog.sqlite"), "--output-dir", str(output_dir)]
        )

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / command), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "ID_ASSIGNMENT_" in result.stdout + result.stderr
    assert "Traceback" not in result.stdout + result.stderr
    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_historical_id_assignment_remains_valid_after_best_measurement_changes(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    object_data = _valid_object()
    object_data["measurements"] = [
        _measurement_variant("m-001", source="PIG", observed_date="2010-12-31"),
        _measurement_variant("m-002", source="TPN", observed_date="2022-05-25"),
    ]
    later = object_data["measurements"][1]
    later["lat"], later["lon"] = 49.24292969, 19.80613095  # CHZ
    coordinates = wgs84_to_1992(lat=later["lat"], lon=later["lon"])
    later["x_1992"], later["y_1992"] = coordinates.x_1992, coordinates.y_1992
    object_data["best_measurement"]["measurement_id"] = "m-002"
    _write_object(data_dir, object_data)

    issues = validate_data_dir(data_dir)

    assert not [issue for issue in issues if issue.severity == ValidationSeverity.ERROR]
    assert "OBJECT_PREFIX_MISMATCH" in _codes(issues)


def test_manual_id_assignment_with_reason_remains_valid(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    object_data = _valid_object()
    object_data["id_assignment"]["method"] = "manual"
    object_data["id_assignment"]["prefix_override_reason"] = "Decyzja operatora przy nadaniu ID."
    object_data["best_measurement"]["mode"] = "manual"
    object_data["best_measurement"]["reason"] = "Zachowano pomiar terenowy."
    _write_object(data_dir, object_data)

    issues = validate_data_dir(data_dir)

    assert not [issue for issue in issues if issue.severity == ValidationSeverity.ERROR]


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
