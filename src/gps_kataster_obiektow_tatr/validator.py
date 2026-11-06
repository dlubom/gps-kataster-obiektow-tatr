"""PostgreSQL catalogue validation and external proposal preflight."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

import psycopg
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from gps_kataster_obiektow_tatr.catalog_records import SourceDataset
from gps_kataster_obiektow_tatr.coordinates import (
    DEFAULT_CONSISTENCY_TOLERANCE_M,
)
from gps_kataster_obiektow_tatr.data_loader import (
    DEFAULT_DATA_DIR,
    DataDirectoryError,
    DataKind,
    LoadedDataset,
    LoadedYamlRecord,
    YamlDataLoadError,
    is_canonical_source,
    load_yaml_dataset,
)
from gps_kataster_obiektow_tatr.measurement_values import non_finite_measurement_fields
from gps_kataster_obiektow_tatr.prefix_resolver import (
    PrefixResolution,
)
from gps_kataster_obiektow_tatr.urls import valid_absolute_url

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


class CatalogValidationError(ValueError):
    """Findings that block use of a catalogue or proposal."""

    def __init__(self, issues):
        self.issues = tuple(issues)
        super().__init__(
            "Cannot use invalid catalogue:\n"
            + "\n".join(format_issue(i) for i in self.issues if i.severity == "error")
        )


def validate_data_dir(
    data_dir: Path = DEFAULT_DATA_DIR,
    *,
    repo_root: Path = REPO_ROOT,
    schema_dir: Path = DEFAULT_SCHEMA_DIR,
    prefix_resolver: PrefixResolverLike | None = None,
) -> tuple[ValidationIssue, ...]:
    """Report source/proposal and SQL checks. Git history is a separate required write gate."""
    from gps_kataster_obiektow_tatr.postgres import CatalogLoadError, open_catalog

    try:
        if is_canonical_source(data_dir):
            with open_catalog(data_dir, validate=False) as catalog:
                return validate_catalog(
                    catalog, repo_root=repo_root, prefix_resolver=prefix_resolver
                )
        dataset = load_yaml_dataset(data_dir)
        return validate_proposal(
            dataset,
            data_dir=data_dir,
            repo_root=repo_root,
            schema_dir=schema_dir,
            prefix_resolver=prefix_resolver,
        )
    except DataDirectoryError as exc:
        return (
            ValidationIssue("DATA_DIRECTORY_INVALID", ValidationSeverity.ERROR, exc.path, str(exc)),
        )
    except YamlDataLoadError as exc:
        return (ValidationIssue("YAML_INVALID", ValidationSeverity.ERROR, exc.path, str(exc)),)
    except (CatalogLoadError, psycopg.Error) as exc:
        return (_sql_issue(exc),)


def validate_catalog(catalog, *, repo_root: Path | None = None, prefix_resolver=None):
    """Full checks of the existing SQL state, with no reserialization or second database."""
    return (
        *_validate_file_id_paths(
            ((kind, record_id, path) for (kind, record_id), path in catalog.paths.items()),
            data_dir=catalog.data_dir,
        ),
        *catalog.issues(repo_root=repo_root, prefix_resolver=prefix_resolver),
    )


@contextmanager
def validated_catalog_source(
    data_dir=DEFAULT_DATA_DIR, *, repo_root=REPO_ROOT, prefix_resolver=None
):
    """Check YAML source and existing SQL state; yield its projection once, without Git history."""
    from gps_kataster_obiektow_tatr.postgres import check_snapshot_files, open_catalog

    data_dir = Path(data_dir)
    if not is_canonical_source(data_dir):
        check_snapshot_files(data_dir, canonical=False)
        with validated_proposal(
            load_yaml_dataset(data_dir),
            data_dir=data_dir,
            repo_root=repo_root,
            prefix_resolver=prefix_resolver,
        ) as (catalog, issues):
            yield catalog, catalog.dataset(), issues
        return
    with open_catalog(data_dir, validate=False) as catalog:
        issues = validate_catalog(catalog, repo_root=repo_root, prefix_resolver=prefix_resolver)
        if has_errors(issues):
            raise CatalogValidationError(issues)
        yield catalog, catalog.dataset(), issues


@contextmanager
def history_checked_catalog(data_dir=DEFAULT_DATA_DIR, *, base_ref, history_repo=REPO_ROOT):
    """Build/CLI boundary: checked source, SQL state and actual accepted Git history."""
    from gps_kataster_obiektow_tatr.history import check_history

    with validated_catalog_source(data_dir) as (catalog, projection, issues):
        issues = (
            *issues,
            *check_history(
                base_ref, projection, repo_root=history_repo, connection=catalog.connection
            ),
        )
        if has_errors(issues):
            raise CatalogValidationError(issues)
        yield catalog, projection, issues


def _sql_issue(exc, paths=()):
    path = getattr(exc, "path", None)
    if path is not None:
        path = next((r.path for r in paths if r.path.stem == path.stem), path)
    cause = exc.__cause__ or exc
    constraint = getattr(getattr(cause, "diag", None), "constraint_name", None)
    code = {
        "measurements_pkey": "DUPLICATE_MEASUREMENT_ID",
        "objects_pkey": "DUPLICATE_OBJECT_ID",
        "unique_tpn_globalid": "DUPLICATE_TPN_GLOBALID",
        "objects_cave_id_fkey": "CAVE_REFERENCE_MISSING",
        "best_policy_object_id_manual_measurement_id_fkey": "BEST_MEASUREMENT_MISSING",
        "best_policy_check": "BEST_MEASUREMENT_MANUAL_REASON_REQUIRED",
        "relations_from_object_id_fkey": "RELATION_OBJECT_REFERENCE_MISSING",
        "relations_to_object_id_fkey": "RELATION_OBJECT_REFERENCE_MISSING",
        "attachments_object_id_measurement_id_fkey": "ATTACHMENT_MEASUREMENT_MISSING",
    }.get(constraint, "SQL_CATALOG_INVALID")
    if path is None and cause is not None:
        table = getattr(getattr(cause, "diag", None), "table_name", "")
        matching = [r for r in paths if str(r.kind) + "s" == table]
        if len(matching) == 1:
            path = matching[0].path
    if path is None and len(paths) == 1:
        path = paths[0].path
    return ValidationIssue(code, ValidationSeverity.ERROR, path, str(exc))


def validate_proposal(
    dataset: LoadedDataset,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    repo_root: Path = REPO_ROOT,
    schema_dir: Path = DEFAULT_SCHEMA_DIR,
    prefix_resolver: PrefixResolverLike | None = None,
) -> tuple[ValidationIssue, ...]:
    """Validate a proposal with the same SQL schema used by the final catalogue.

    JSON Schema only protects external shapes before nested values are consumed.
    Membership lists and redundant coordinates are import assertions, never stored authorities.
    """
    try:
        with validated_proposal(
            dataset,
            data_dir=data_dir,
            repo_root=repo_root,
            schema_dir=schema_dir,
            prefix_resolver=prefix_resolver,
        ) as (_, issues):
            return issues
    except CatalogValidationError as exc:
        return exc.issues


@contextmanager
def validated_proposal(
    dataset: LoadedDataset,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    repo_root: Path = REPO_ROOT,
    schema_dir: Path = DEFAULT_SCHEMA_DIR,
    prefix_resolver: PrefixResolverLike | None = None,
):
    """Check legacy/staging assertions, then SQL; retain its connection for history checks."""
    from gps_kataster_obiektow_tatr.postgres import open_proposal

    issues = list(
        _validate_file_id_paths(
            ((r.kind, r.data.get("id"), r.path) for r in dataset.records()), data_dir=data_dir
        )
    )
    issues.extend(validate_records_schema(dataset.records(), schema_dir=schema_dir))
    issues.extend(_validate_duplicate_object_ids(dataset.objects))
    if has_errors(issues):
        raise CatalogValidationError(issues)
    issues.extend(_validate_proposal_membership(dataset))
    for record in dataset.objects:
        issues.extend(validate_auto_best_declaration(record))
    if has_errors(issues):
        raise CatalogValidationError(issues)
    with _validated_sql_proposal(
        dataset,
        open_proposal,
        issues,
        repo_root=repo_root,
        prefix_resolver=prefix_resolver,
        declarations=True,
    ) as result:
        yield result


@contextmanager
def validated_source_proposal(
    source: SourceDataset,
    *,
    data_dir=DEFAULT_DATA_DIR,
    repo_root=REPO_ROOT,
    prefix_resolver=None,
):
    """Check canonical edits and SQL once; never reapply the legacy declaration schema."""
    from gps_kataster_obiektow_tatr.postgres import open_source_proposal

    issues = list(
        _validate_file_id_paths(
            ((r.kind, r.data.get("id"), r.path) for r in source.records()), data_dir=data_dir
        )
    )
    if has_errors(issues):
        raise CatalogValidationError(issues)
    with _validated_sql_proposal(
        source,
        open_source_proposal,
        issues,
        repo_root=repo_root,
        prefix_resolver=prefix_resolver,
    ) as result:
        yield result


@contextmanager
def _validated_sql_proposal(
    dataset,
    opener,
    issues,
    *,
    repo_root,
    prefix_resolver,
    declarations=False,
):
    from contextlib import ExitStack

    from gps_kataster_obiektow_tatr.postgres import CatalogLoadError

    stack = ExitStack()
    try:
        try:
            catalog = stack.enter_context(opener(dataset, validate=False))
            issues.extend(catalog.issues(repo_root=repo_root, prefix_resolver=prefix_resolver))
            if declarations:
                issues.extend(validate_coordinate_declarations(dataset.objects, catalog.connection))
        except (CatalogLoadError, psycopg.Error, ValueError, KeyError, TypeError) as exc:
            issues.append(_sql_issue(exc, dataset.records()))
        if has_errors(issues):
            raise CatalogValidationError(issues)
        yield catalog, tuple(issues)
    finally:
        try:
            stack.close()
        except (CatalogLoadError, psycopg.Error, ValueError, KeyError, TypeError) as exc:
            raise CatalogValidationError((*issues, _sql_issue(exc, dataset.records()))) from exc


def validate_coordinate_declarations(records, connection):
    """Check supplied redundant values on an existing connection, before discarding them."""
    issues = []
    for record in records:
        for m in record.data["measurements"]:
            native = "input_srid" in m
            origin = (
                (m["input_x"], m["input_y"], m["input_srid"])
                if native
                else (m["lon"], m["lat"], 4326)
            )
            for x_key, y_key, srid in (("lon", "lat", 4326), ("y_1992", "x_1992", 2180)):
                if (not native and srid == 4326) or not ({x_key, y_key} & m.keys()):
                    continue
                if not {x_key, y_key} <= m.keys():
                    issues.append(
                        ValidationIssue(
                            "COORDINATE_MISMATCH",
                            ValidationSeverity.ERROR,
                            record.path,
                            f"{m['id']}: incomplete redundant coordinate pair {x_key}/{y_key}",
                        )
                    )
                    continue
                try:
                    with connection.transaction():
                        row = connection.execute(
                            "SELECT ST_Distance("
                            "ST_Transform(ST_SetSRID(ST_MakePoint(%s,%s),%s),2180),"
                            "ST_Transform(ST_SetSRID(ST_MakePoint(%s,%s),%s),2180)) distance",
                            (*origin, m[x_key], m[y_key], srid),
                        ).fetchone()
                except psycopg.Error as exc:
                    issues.append(
                        ValidationIssue(
                            "SQL_CATALOG_INVALID",
                            ValidationSeverity.ERROR,
                            record.path,
                            f"{m['id']}: {exc}",
                        )
                    )
                    continue
                if row["distance"] > DEFAULT_CONSISTENCY_TOLERANCE_M:
                    issues.append(
                        ValidationIssue(
                            "COORDINATE_MISMATCH",
                            ValidationSeverity.ERROR,
                            record.path,
                            f"{m['id']}: redundant source coordinates differ by "
                            f"{row['distance']:.2f} m",
                        )
                    )
    return tuple(issues)


def _validate_proposal_membership(dataset):
    """Reject contradictory legacy/import lists before deriving their ordering."""
    issues = []
    objects = {r.data.get("id"): r for r in dataset.objects}
    caves = {r.data.get("id"): r for r in dataset.caves}
    for c in dataset.caves:
        members = c.data.get("object_ids", [])
        if len(set(members)) != len(members):
            issues.append(
                ValidationIssue(
                    "DUPLICATE_CAVE_OBJECT_ID",
                    ValidationSeverity.ERROR,
                    c.path,
                    f"Cave {c.data.get('id')} lists an object more than once.",
                )
            )
        for oid in members:
            o = objects.get(oid)
            code = (
                "CAVE_OBJECT_REFERENCE_MISSING"
                if o is None
                else "CAVE_OBJECT_MEMBERSHIP_MISMATCH"
                if o.data.get("cave_id") != c.data.get("id")
                else None
            )
            if code:
                issues.append(
                    ValidationIssue(
                        code,
                        ValidationSeverity.ERROR,
                        c.path,
                        f"Cave {c.data.get('id')} lists inconsistent object {oid}.",
                    )
                )
    for o in dataset.objects:
        c = caves.get(o.data.get("cave_id"))
        if c is not None and o.data.get("id") not in c.data.get("object_ids", []):
            issues.append(
                ValidationIssue(
                    "OBJECT_CAVE_MEMBERSHIP_MISSING",
                    ValidationSeverity.ERROR,
                    o.path,
                    f"Object {o.data.get('id')} absent from supplied projection "
                    f"of {c.data.get('id')}.",
                )
            )
    return tuple(issues)


def validate_record_schema(
    record: LoadedYamlRecord, *, schema_dir: Path = DEFAULT_SCHEMA_DIR
) -> tuple[ValidationIssue, ...]:
    """Check a proposal's shape before review actions consume its nested values."""

    return validate_records_schema((record,), schema_dir=schema_dir)


def validate_records_schema(
    records: Sequence[LoadedYamlRecord], *, schema_dir: Path = DEFAULT_SCHEMA_DIR
) -> tuple[ValidationIssue, ...]:
    """Prepare legacy validators once per batch, preserving record/diagnostic order."""
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


def validate_staging_fields(
    record: LoadedYamlRecord, fields: tuple[str, ...], *, measurement_offset: int = 0
):
    """Validate incoming fields, without presenting a canonical target as a legacy record."""
    validator = _load_schema_validators(DEFAULT_SCHEMA_DIR)[record.kind]
    schema = {
        **validator.schema,
        "required": list(fields),
        "properties": {key: validator.schema["properties"][key] for key in fields},
    }
    payload = {key: record.raw_data[key] for key in fields}
    issues = []
    for error in sorted(
        validator.evolve(schema=schema).iter_errors(payload), key=_schema_error_sort_key
    ):
        if len(error.path) > 1 and error.path[0] == "measurements":
            error.path[1] += measurement_offset
        issues.append(
            ValidationIssue(
                "SCHEMA_VALIDATION",
                ValidationSeverity.ERROR,
                record.path,
                _format_schema_error(error),
            )
        )
    if "measurements" in fields:
        issues.extend(
            (*_validate_measurement_identity(record), *_validate_finite_measurements(record))
        )
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
    paths: Iterable[tuple[str, object, Path]],
    *,
    data_dir: Path,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []

    for kind, record_id, path in paths:
        if not isinstance(record_id, str):
            continue
        directory = data_dir / f"{kind}s"
        if kind == DataKind.OBJECT:
            directory /= record_id.split("-", maxsplit=1)[0]
        if (
            path.parent != directory
            or path.suffix not in {".yml", ".yaml", ".sql"}
            or path.stem != record_id
        ):
            issues.append(
                ValidationIssue(
                    code="FILE_ID_MISMATCH",
                    severity=ValidationSeverity.ERROR,
                    path=path,
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


def validate_auto_best_declaration(record):
    """Check a legacy/import reference before removing the cached automatic choice."""
    best = record.data.get("best_measurement")
    if not isinstance(best, dict) or best.get("mode") != "auto":
        return ()
    measurement_id = best.get("measurement_id")
    if isinstance(measurement_id, str) and not any(
        m.get("id") == measurement_id for m in _iter_dicts(record.data.get("measurements"))
    ):
        return (
            ValidationIssue(
                "BEST_MEASUREMENT_MISSING",
                ValidationSeverity.ERROR,
                record.path,
                f"Object {_record_id(record)} best_measurement.measurement_id {measurement_id} "
                "does not exist.",
            ),
        )
    return ()


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


def _validate_attachments(
    attachments: Iterable[dict[str, Any]],
    *,
    paths: dict[tuple[str, str], Path],
    repo_root: Path,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    for attachment in attachments:
        object_id, attachment_id, attachment_path = (
            attachment["object_id"],
            attachment["id"],
            attachment["path"],
        )
        path = paths.get(("object", object_id))
        if _is_url_like(attachment_path):
            if not _valid_http_url(attachment_path):
                issues.append(
                    ValidationIssue(
                        code="ATTACHMENT_URL_INVALID",
                        severity=ValidationSeverity.ERROR,
                        path=path,
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
                    path=path,
                    description=(
                        f"Object {object_id} attachment {attachment_id} path "
                        f"{attachment_path!r} does not exist."
                    ),
                )
            )

    return tuple(issues)


def _records_by_id(records: Sequence[LoadedYamlRecord]) -> dict[str, list[LoadedYamlRecord]]:
    records_by_id: dict[str, list[LoadedYamlRecord]] = {}
    for record in records:
        record_id = record.data.get("id")
        if isinstance(record_id, str):
            records_by_id.setdefault(record_id, []).append(record)
    return records_by_id


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


def _is_url_like(value: str) -> bool:
    return "://" in value


def _valid_http_url(value: str) -> bool:
    return valid_absolute_url(value) and urlparse(value).scheme in {"http", "https"}
