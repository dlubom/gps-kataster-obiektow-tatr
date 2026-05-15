"""Local data validator for source-of-truth YAML records."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from itertools import combinations
from math import inf
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from gps_kataster_obiektow_tatr.coordinates import (
    DEFAULT_CONSISTENCY_TOLERANCE_M,
    coordinate_consistency_error_m,
    wgs84_to_1992,
)
from gps_kataster_obiektow_tatr.data_loader import (
    DEFAULT_DATA_DIR,
    DataKind,
    LoadedDataset,
    LoadedYamlRecord,
    YamlDataLoadError,
    load_dataset,
)
from gps_kataster_obiektow_tatr.prefix_resolver import (
    PrefixResolution,
    PrefixResolutionStatus,
    default_prefix_resolver,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_DIR = REPO_ROOT / "schema"
FAR_MEASUREMENT_DISTANCE_M = 100.0


class ValidationSeverity(StrEnum):
    """Validation issue severity used by local and CI reports."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A single validation finding with stable reporting fields."""

    code: str
    severity: ValidationSeverity
    path: Path | None
    description: str


class PrefixResolverLike(Protocol):
    """Minimal prefix resolver interface used by validation."""

    def resolve(self, *, lat: float, lon: float) -> PrefixResolution:
        """Resolve a WGS84 coordinate to a prefix/spatial status."""


def validate_data_dir(
    data_dir: Path = DEFAULT_DATA_DIR,
    *,
    repo_root: Path = REPO_ROOT,
    schema_dir: Path = DEFAULT_SCHEMA_DIR,
    prefix_resolver: PrefixResolverLike | None = None,
) -> tuple[ValidationIssue, ...]:
    """Load and validate a data directory."""

    try:
        dataset = load_dataset(data_dir)
    except YamlDataLoadError as exc:
        return (
            ValidationIssue(
                code="YAML_INVALID",
                severity=ValidationSeverity.ERROR,
                path=exc.path,
                description=str(exc),
            ),
        )

    return validate_dataset(
        dataset,
        data_dir=data_dir,
        repo_root=repo_root,
        schema_dir=schema_dir,
        prefix_resolver=prefix_resolver,
    )


def validate_dataset(
    dataset: LoadedDataset,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    repo_root: Path = REPO_ROOT,
    schema_dir: Path = DEFAULT_SCHEMA_DIR,
    prefix_resolver: PrefixResolverLike | None = None,
) -> tuple[ValidationIssue, ...]:
    """Validate an already-loaded dataset and return all issues."""

    resolver = prefix_resolver or default_prefix_resolver()
    validators = _load_schema_validators(schema_dir)
    issues: list[ValidationIssue] = []

    issues.extend(_validate_schema(dataset.records(), validators))
    issues.extend(_validate_file_id_paths(dataset.records(), data_dir=data_dir))
    issues.extend(_validate_duplicate_object_ids(dataset.objects))
    issues.extend(_validate_cross_references(dataset))
    issues.extend(_validate_object_records(dataset.objects, resolver=resolver, repo_root=repo_root))
    issues.extend(_validate_duplicate_tpn_globalids(dataset.objects))

    return tuple(issues)


def format_issue(issue: ValidationIssue) -> str:
    """Format an issue as deterministic tab-separated report output."""

    path = str(issue.path) if issue.path is not None else "<dataset>"
    return f"{issue.code}\t{issue.severity.value}\t{path}\t{issue.description}"


def has_errors(issues: Iterable[ValidationIssue]) -> bool:
    """Return whether any issue is an error."""

    return any(issue.severity == ValidationSeverity.ERROR for issue in issues)


def exit_code_for_issues(issues: Iterable[ValidationIssue]) -> int:
    """Return the validator process exit code for a set of issues."""

    return 1 if has_errors(issues) else 0


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


def _validate_file_id_paths(
    records: Sequence[LoadedYamlRecord],
    *,
    data_dir: Path,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []

    for record in records:
        record_id = record.data.get("id")
        if not isinstance(record_id, str):
            continue

        if not _record_path_matches_id(record, record_id=record_id, data_dir=data_dir):
            issues.append(
                ValidationIssue(
                    code="FILE_ID_MISMATCH",
                    severity=ValidationSeverity.ERROR,
                    path=record.path,
                    description=f"File path does not match record id {record_id}.",
                )
            )

    return tuple(issues)


def _validate_duplicate_object_ids(
    object_records: Sequence[LoadedYamlRecord],
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []

    for object_id, records in _records_by_id(object_records).items():
        if len(records) <= 1:
            continue
        paths = ", ".join(str(record.path) for record in records)
        for record in records:
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_OBJECT_ID",
                    severity=ValidationSeverity.ERROR,
                    path=record.path,
                    description=f"Obiekt.id {object_id} is duplicated in: {paths}.",
                )
            )

    return tuple(issues)


def _validate_cross_references(dataset: LoadedDataset) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    object_ids = set(_records_by_id(dataset.objects))
    cave_ids = set(_records_by_id(dataset.caves))

    for object_record in dataset.objects:
        object_id = _record_id(object_record)
        cave_id = object_record.data.get("cave_id")
        if isinstance(cave_id, str) and cave_id not in cave_ids:
            issues.append(
                ValidationIssue(
                    code="CAVE_REFERENCE_MISSING",
                    severity=ValidationSeverity.ERROR,
                    path=object_record.path,
                    description=f"Object {object_id} references missing cave_id {cave_id}.",
                )
            )

        measurement_ids = _measurement_ids(object_record)
        best_measurement = object_record.data.get("best_measurement")
        if isinstance(best_measurement, dict):
            measurement_id = best_measurement.get("measurement_id")
            if isinstance(measurement_id, str) and measurement_id not in measurement_ids:
                issues.append(
                    ValidationIssue(
                        code="BEST_MEASUREMENT_MISSING",
                        severity=ValidationSeverity.ERROR,
                        path=object_record.path,
                        description=(
                            f"Object {object_id} best_measurement.measurement_id "
                            f"{measurement_id} does not exist."
                        ),
                    )
                )

            if best_measurement.get("mode") == "manual" and not best_measurement.get("reason"):
                issues.append(
                    ValidationIssue(
                        code="BEST_MEASUREMENT_MANUAL_REASON_REQUIRED",
                        severity=ValidationSeverity.ERROR,
                        path=object_record.path,
                        description=f"Object {object_id} manual best_measurement requires reason.",
                    )
                )

        for attachment in _iter_dicts(object_record.data.get("attachments")):
            measurement_id = attachment.get("measurement_id")
            if isinstance(measurement_id, str) and measurement_id not in measurement_ids:
                issues.append(
                    ValidationIssue(
                        code="ATTACHMENT_MEASUREMENT_MISSING",
                        severity=ValidationSeverity.ERROR,
                        path=object_record.path,
                        description=(
                            f"Object {object_id} attachment references missing "
                            f"measurement_id {measurement_id}."
                        ),
                    )
                )

    for cave_record in dataset.caves:
        cave_id = _record_id(cave_record)
        for object_id in _iter_strings(cave_record.data.get("object_ids")):
            if object_id not in object_ids:
                issues.append(
                    ValidationIssue(
                        code="CAVE_OBJECT_REFERENCE_MISSING",
                        severity=ValidationSeverity.ERROR,
                        path=cave_record.path,
                        description=f"Cave {cave_id} references missing object_id {object_id}.",
                    )
                )

    for relation_record in dataset.relations:
        relation_id = _record_id(relation_record)
        for field_name in ("from_object_id", "to_object_id"):
            object_id = relation_record.data.get(field_name)
            if isinstance(object_id, str) and object_id not in object_ids:
                issues.append(
                    ValidationIssue(
                        code="RELATION_OBJECT_REFERENCE_MISSING",
                        severity=ValidationSeverity.ERROR,
                        path=relation_record.path,
                        description=(
                            f"Relation {relation_id} {field_name} references missing "
                            f"object_id {object_id}."
                        ),
                    )
                )

    return tuple(issues)


def _validate_object_records(
    object_records: Sequence[LoadedYamlRecord],
    *,
    resolver: PrefixResolverLike,
    repo_root: Path,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []

    for object_record in object_records:
        issues.extend(_validate_object_domain_warnings(object_record))
        issues.extend(_validate_object_attachments(object_record, repo_root=repo_root))
        issues.extend(_validate_object_measurements(object_record, resolver=resolver))
        issues.extend(_validate_best_measurement_auto(object_record))

    return tuple(issues)


def _validate_object_domain_warnings(
    object_record: LoadedYamlRecord,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    object_id = _record_id(object_record)

    if object_record.data.get("category") == "jaskinia_otwor" and not object_record.data.get(
        "cave_id"
    ):
        issues.append(
            ValidationIssue(
                code="CAVE_ID_MISSING_FOR_CAVE_OPENING",
                severity=ValidationSeverity.WARNING,
                path=object_record.path,
                description=f"Object {object_id} is category jaskinia_otwor without cave_id.",
            )
        )

    for external_ref in _iter_dicts(object_record.data.get("external_refs")):
        system = external_ref.get("system")
        ref_type = external_ref.get("ref_type")

        if system == "NR_INWENT":
            issues.append(
                ValidationIssue(
                    code="NR_INWENT_ON_OBJECT_REFERENCE",
                    severity=ValidationSeverity.WARNING,
                    path=object_record.path,
                    description=(
                        f"Object {object_id} has NR_INWENT in Obiekt.external_refs; "
                        "inventory numbers belong on Jaskinia.external_refs in V1."
                    ),
                )
            )

        if system == "PIG" and ref_type in {"catalog_id", "url"}:
            issues.append(
                ValidationIssue(
                    code="PIG_CATALOG_REFERENCE_ON_OBJECT",
                    severity=ValidationSeverity.WARNING,
                    path=object_record.path,
                    description=(
                        f"Object {object_id} has PIG catalog reference in Obiekt.external_refs; "
                        "PIG catalog references belong on Jaskinia.external_refs in V1."
                    ),
                )
            )

    return tuple(issues)


def _validate_object_attachments(
    object_record: LoadedYamlRecord,
    *,
    repo_root: Path,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    object_id = _record_id(object_record)

    for attachment in _iter_dicts(object_record.data.get("attachments")):
        attachment_id = attachment.get("id", "<unknown>")
        attachment_path = attachment.get("path")
        if not isinstance(attachment_path, str):
            continue

        if _is_url_like(attachment_path):
            if not _valid_http_url(attachment_path):
                issues.append(
                    ValidationIssue(
                        code="ATTACHMENT_URL_INVALID",
                        severity=ValidationSeverity.ERROR,
                        path=object_record.path,
                        description=(
                            f"Object {object_id} attachment {attachment_id} has invalid URL "
                            f"{attachment_path!r}."
                        ),
                    )
                )
            continue

        local_path = Path(attachment_path)
        if not local_path.is_absolute():
            local_path = repo_root / local_path
        if not local_path.exists():
            issues.append(
                ValidationIssue(
                    code="ATTACHMENT_PATH_MISSING",
                    severity=ValidationSeverity.ERROR,
                    path=object_record.path,
                    description=(
                        f"Object {object_id} attachment {attachment_id} path "
                        f"{attachment_path!r} does not exist."
                    ),
                )
            )

    return tuple(issues)


def _validate_object_measurements(
    object_record: LoadedYamlRecord,
    *,
    resolver: PrefixResolverLike,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    object_id = _record_id(object_record)
    measurement_points: list[tuple[str, float, float]] = []

    for measurement in _iter_dicts(object_record.data.get("measurements")):
        measurement_id = _measurement_id(measurement)
        if measurement.get("horizontal_accuracy_m") is None:
            issues.append(
                ValidationIssue(
                    code="MISSING_HORIZONTAL_ACCURACY",
                    severity=ValidationSeverity.WARNING,
                    path=object_record.path,
                    description=(
                        f"Object {object_id} measurement {measurement_id} has no "
                        "horizontal_accuracy_m."
                    ),
                )
            )

        if not measurement.get("source_ref"):
            issues.append(
                ValidationIssue(
                    code="MISSING_SOURCE_REF",
                    severity=ValidationSeverity.WARNING,
                    path=object_record.path,
                    description=(
                        f"Object {object_id} measurement {measurement_id} has no source_ref."
                    ),
                )
            )

        coordinate_values = _measurement_coordinate_values(measurement)
        if coordinate_values is None:
            continue

        lat, lon, x_1992, y_1992 = coordinate_values
        coordinate_error = coordinate_consistency_error_m(
            lat=lat,
            lon=lon,
            x_1992=x_1992,
            y_1992=y_1992,
        )
        if coordinate_error > DEFAULT_CONSISTENCY_TOLERANCE_M:
            issues.append(
                ValidationIssue(
                    code="COORDINATE_MISMATCH",
                    severity=ValidationSeverity.ERROR,
                    path=object_record.path,
                    description=(
                        f"Object {object_id} measurement {measurement_id} WGS84 and PL-1992 "
                        f"differ by {coordinate_error:.2f} m."
                    ),
                )
            )

        resolution = resolver.resolve(lat=lat, lon=lon)
        if resolution.status == PrefixResolutionStatus.ERROR:
            issues.append(
                ValidationIssue(
                    code="MEASUREMENT_OUTSIDE_PL_SK",
                    severity=ValidationSeverity.ERROR,
                    path=object_record.path,
                    description=(
                        f"Object {object_id} measurement {measurement_id} is outside Poland "
                        "and Slovakia fallback boundaries."
                    ),
                )
            )
        elif resolution.status == PrefixResolutionStatus.WARNING:
            issues.append(
                ValidationIssue(
                    code="MEASUREMENT_OUTSIDE_VALLEYS",
                    severity=ValidationSeverity.WARNING,
                    path=object_record.path,
                    description=(
                        f"Object {object_id} measurement {measurement_id} is inside Poland or "
                        "Slovakia but outside configured Tatra valley polygons."
                    ),
                )
            )

        measurement_points.append((measurement_id, lat, lon))

    issues.extend(_validate_prefix_matches_best_measurement(object_record, resolver=resolver))
    issues.extend(_validate_measurement_distances(object_record, measurement_points))

    return tuple(issues)


def _validate_prefix_matches_best_measurement(
    object_record: LoadedYamlRecord,
    *,
    resolver: PrefixResolverLike,
) -> tuple[ValidationIssue, ...]:
    object_id = _record_id(object_record)
    object_prefix = object_id.split("-", maxsplit=1)[0] if "-" in object_id else None
    if not object_prefix:
        return ()

    best_measurement = object_record.data.get("best_measurement")
    if not isinstance(best_measurement, dict):
        return ()

    best_measurement_id = best_measurement.get("measurement_id")
    if not isinstance(best_measurement_id, str):
        return ()

    measurement = _measurement_by_id(object_record, best_measurement_id)
    if measurement is None:
        return ()

    coordinate_values = _measurement_coordinate_values(measurement)
    if coordinate_values is None:
        return ()

    lat, lon, _x_1992, _y_1992 = coordinate_values
    resolution = resolver.resolve(lat=lat, lon=lon)
    if resolution.prefix is None or resolution.prefix == object_prefix:
        return ()

    return (
        ValidationIssue(
            code="OBJECT_PREFIX_MISMATCH",
            severity=ValidationSeverity.WARNING,
            path=object_record.path,
            description=(
                f"Object {object_id} prefix {object_prefix} differs from best measurement "
                f"resolved prefix {resolution.prefix}."
            ),
        ),
    )


def _validate_measurement_distances(
    object_record: LoadedYamlRecord,
    measurement_points: Sequence[tuple[str, float, float]],
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    object_id = _record_id(object_record)

    for left, right in combinations(measurement_points, 2):
        left_id, left_lat, left_lon = left
        right_id, right_lat, right_lon = right
        left_1992 = wgs84_to_1992(lat=left_lat, lon=left_lon)
        right_1992 = wgs84_to_1992(lat=right_lat, lon=right_lon)
        distance = (
            (left_1992.x_1992 - right_1992.x_1992) ** 2
            + (left_1992.y_1992 - right_1992.y_1992) ** 2
        ) ** 0.5

        if distance > FAR_MEASUREMENT_DISTANCE_M:
            issues.append(
                ValidationIssue(
                    code="MEASUREMENT_DISTANCE_OUTLIER",
                    severity=ValidationSeverity.WARNING,
                    path=object_record.path,
                    description=(
                        f"Object {object_id} measurements {left_id} and {right_id} are "
                        f"{distance:.1f} m apart."
                    ),
                )
            )

    return tuple(issues)


def _validate_best_measurement_auto(
    object_record: LoadedYamlRecord,
) -> tuple[ValidationIssue, ...]:
    object_id = _record_id(object_record)
    best_measurement = object_record.data.get("best_measurement")
    if not isinstance(best_measurement, dict) or best_measurement.get("mode") != "auto":
        return ()

    measurement_id = best_measurement.get("measurement_id")
    computed_measurement_id = _default_best_measurement_id(object_record)
    if computed_measurement_id is None or measurement_id == computed_measurement_id:
        return ()

    return (
        ValidationIssue(
            code="BEST_MEASUREMENT_AUTO_MISMATCH",
            severity=ValidationSeverity.WARNING,
            path=object_record.path,
            description=(
                f"Object {object_id} auto best_measurement points to {measurement_id}, "
                f"but default priority selects {computed_measurement_id}."
            ),
        ),
    )


def _validate_duplicate_tpn_globalids(
    object_records: Sequence[LoadedYamlRecord],
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    refs_by_external_id: dict[str, list[LoadedYamlRecord]] = {}

    for object_record in object_records:
        for external_ref in _iter_dicts(object_record.data.get("external_refs")):
            if (
                external_ref.get("system") == "TPN"
                and external_ref.get("ref_type") == "source_globalid"
                and isinstance(external_ref.get("external_id"), str)
            ):
                refs_by_external_id.setdefault(external_ref["external_id"], []).append(
                    object_record
                )

    for external_id, records in refs_by_external_id.items():
        if len(records) <= 1:
            continue
        paths = ", ".join(str(record.path) for record in records)
        for record in records:
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_TPN_GLOBALID",
                    severity=ValidationSeverity.ERROR,
                    path=record.path,
                    description=f"TPN GLOBALID {external_id} appears in multiple objects: {paths}.",
                )
            )

    return tuple(issues)


def _default_best_measurement_id(object_record: LoadedYamlRecord) -> str | None:
    measurements = list(_iter_dicts(object_record.data.get("measurements")))
    if not measurements:
        return None

    for priority in range(6):
        priority_measurements = [
            measurement
            for measurement in measurements
            if _measurement_priority(measurement) == priority
            and isinstance(measurement.get("id"), str)
        ]
        if priority_measurements:
            return _best_measurement_within_priority(priority_measurements)["id"]

    return None


def _measurement_priority(measurement: dict[str, Any]) -> int:
    source = measurement.get("source")
    status = measurement.get("verification_status")
    is_rejected = status == "odrzucony"

    if source == "wlasne" and status == "zweryfikowany":
        return 0
    if source == "TPN" and not is_rejected:
        return 1
    if source == "wlasne" and not is_rejected:
        return 2
    if source == "PIG" and not is_rejected:
        return 3
    if not is_rejected:
        return 4
    return 5


def _best_measurement_within_priority(measurements: Sequence[dict[str, Any]]) -> dict[str, Any]:
    latest_observed = max(
        _measurement_observed_sort_value(measurement) for measurement in measurements
    )
    latest_measurements = [
        measurement
        for measurement in measurements
        if _measurement_observed_sort_value(measurement) == latest_observed
    ]
    return min(
        latest_measurements,
        key=lambda measurement: (
            _measurement_accuracy_sort_value(measurement),
            str(measurement.get("id", "")),
        ),
    )


def _measurement_observed_sort_value(measurement: dict[str, Any]) -> str:
    observed_at = measurement.get("observed_at")
    if isinstance(observed_at, str):
        return observed_at
    observed_date = measurement.get("observed_date")
    if isinstance(observed_date, str):
        return observed_date
    return ""


def _measurement_accuracy_sort_value(measurement: dict[str, Any]) -> float:
    accuracy = measurement.get("horizontal_accuracy_m")
    if isinstance(accuracy, int | float):
        return float(accuracy)
    return inf


def _record_path_matches_id(
    record: LoadedYamlRecord,
    *,
    record_id: str,
    data_dir: Path,
) -> bool:
    try:
        relative_path = record.path.relative_to(data_dir)
    except ValueError:
        return False

    suffix_ok = relative_path.suffix in {".yml", ".yaml"}
    if not suffix_ok or relative_path.stem != record_id:
        return False

    if record.kind == DataKind.OBJECT:
        prefix = record_id.split("-", maxsplit=1)[0]
        return relative_path.parts == ("objects", prefix, relative_path.name)
    if record.kind == DataKind.CAVE:
        return relative_path.parts == ("caves", relative_path.name)
    if record.kind == DataKind.RELATION:
        return relative_path.parts == ("relations", relative_path.name)
    return False


def _records_by_id(records: Sequence[LoadedYamlRecord]) -> dict[str, list[LoadedYamlRecord]]:
    records_by_id: dict[str, list[LoadedYamlRecord]] = {}
    for record in records:
        record_id = record.data.get("id")
        if isinstance(record_id, str):
            records_by_id.setdefault(record_id, []).append(record)
    return records_by_id


def _measurement_ids(object_record: LoadedYamlRecord) -> set[str]:
    return {
        measurement["id"]
        for measurement in _iter_dicts(object_record.data.get("measurements"))
        if isinstance(measurement.get("id"), str)
    }


def _measurement_by_id(
    object_record: LoadedYamlRecord,
    measurement_id: str,
) -> dict[str, Any] | None:
    for measurement in _iter_dicts(object_record.data.get("measurements")):
        if measurement.get("id") == measurement_id:
            return measurement
    return None


def _measurement_coordinate_values(
    measurement: dict[str, Any],
) -> tuple[float, float, float, float] | None:
    lat = measurement.get("lat")
    lon = measurement.get("lon")
    x_1992 = measurement.get("x_1992")
    y_1992 = measurement.get("y_1992")
    if not all(_is_number(value) for value in (lat, lon, x_1992, y_1992)):
        return None
    return (float(lat), float(lon), float(x_1992), float(y_1992))


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


def _iter_strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_url_like(value: str) -> bool:
    return "://" in value


def _valid_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
