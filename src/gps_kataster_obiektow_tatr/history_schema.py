"""Shape checks only for accepted v1 Git baselines, before history comparison."""

import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from gps_kataster_obiektow_tatr.data_loader import DataKind, LoadedYamlRecord
from gps_kataster_obiektow_tatr.measurement_values import non_finite_measurement_fields
from gps_kataster_obiektow_tatr.validator import ValidationIssue, ValidationSeverity

DEFAULT_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schema"


def validate_legacy_records(
    records: Sequence[LoadedYamlRecord], *, schema_dir: Path = DEFAULT_SCHEMA_DIR
) -> tuple[ValidationIssue, ...]:
    """Check accepted legacy records once per batch, preserving diagnostic order."""
    validators = _load_schema_validators(schema_dir)
    issues = []
    for record in records:
        if record.kind == DataKind.PUBLICATION:
            continue
        issues.extend(_validate_schema((record,), validators))
        if record.kind == DataKind.OBJECT:
            issues.extend(_validate_measurement_identity(record))
            issues.extend(_validate_finite_measurements(record))
    return tuple(issues)


def _load_schema_validators(schema_dir: Path) -> dict[DataKind, Draft202012Validator]:
    schema_paths = {
        DataKind.OBJECT: schema_dir / "object.schema.json",
        DataKind.CAVE: schema_dir / "cave.schema.json",
        DataKind.RELATION: schema_dir / "relation.schema.json",
    }
    validators: dict[DataKind, Draft202012Validator] = {}

    for kind, path in schema_paths.items():
        with path.open(encoding="utf-8") as schema_file:
            schema = json.load(schema_file)
        Draft202012Validator.check_schema(schema)
        validators[kind] = Draft202012Validator(schema, format_checker=FormatChecker())

    return validators


def _validate_schema(
    records: Sequence[LoadedYamlRecord],
    validators: dict[DataKind, Draft202012Validator],
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []

    for record in records:
        if record.raw_data.get("schema_version") != 1:
            issues.append(
                ValidationIssue(
                    code="SCHEMA_VERSION_INVALID",
                    severity=ValidationSeverity.ERROR,
                    path=record.path,
                    description="schema_version must be 1.",
                )
            )

        validator = validators[record.kind]
        for error in sorted(validator.iter_errors(record.raw_data), key=_schema_error_sort_key):
            issues.append(
                ValidationIssue(
                    code="SCHEMA_VALIDATION",
                    severity=ValidationSeverity.ERROR,
                    path=record.path,
                    description=_format_schema_error(error),
                )
            )

    return tuple(issues)


def _validate_measurement_identity(
    object_record: LoadedYamlRecord,
) -> tuple[ValidationIssue, ...]:
    counts = Counter(
        measurement["id"]
        for measurement in _iter_dicts(object_record.data.get("measurements"))
        if isinstance(measurement.get("id"), str)
    )
    return tuple(
        ValidationIssue(
            code="DUPLICATE_MEASUREMENT_ID",
            severity=ValidationSeverity.ERROR,
            path=object_record.path,
            description=(
                f"Object {_record_id(object_record)} measurement.id {measurement_id} "
                f"occurs {count} times; measurement IDs must be unique within an object."
            ),
        )
        for measurement_id, count in counts.items()
        if count > 1
    )


def _validate_finite_measurements(
    object_record: LoadedYamlRecord,
) -> tuple[ValidationIssue, ...]:
    return tuple(
        ValidationIssue(
            code="MEASUREMENT_NON_FINITE",
            severity=ValidationSeverity.ERROR,
            path=object_record.path,
            description=(
                f"Object {_record_id(object_record)} measurement {_measurement_id(measurement)} "
                f"field {field} must be finite."
            ),
        )
        for measurement in _iter_dicts(object_record.data.get("measurements"))
        for field in non_finite_measurement_fields(measurement)
    )


def _schema_error_sort_key(error: ValidationError) -> tuple[str, str]:
    return (".".join(str(path_part) for path_part in error.path), error.message)


def _format_schema_error(error: ValidationError) -> str:
    path = ".".join(str(path_part) for path_part in error.path) or "<root>"
    return f"{path}: {error.message}"


def _record_id(record: LoadedYamlRecord) -> str:
    record_id = record.data.get("id")
    return record_id if isinstance(record_id, str) else "<unknown>"


def _measurement_id(measurement: dict[str, Any]) -> str:
    measurement_id = measurement.get("id")
    return measurement_id if isinstance(measurement_id, str) else "<unknown>"


def _iter_dicts(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, dict))
