"""Validate canonical YAML and PostgreSQL state before accepted-history checks."""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

import psycopg

from gps_kataster_obiektow_tatr.data_loader import (
    DEFAULT_DATA_DIR,
    DataDirectoryError,
    DataKind,
    YamlDataLoadError,
)
from gps_kataster_obiektow_tatr.prefix_resolver import (
    PrefixResolution,
)
from gps_kataster_obiektow_tatr.urls import valid_absolute_url

REPO_ROOT = Path(__file__).resolve().parents[2]


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
    """Findings that block use of a catalogue."""

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
    prefix_resolver: PrefixResolverLike | None = None,
) -> tuple[ValidationIssue, ...]:
    """Report canonical source and SQL checks; Git history is a separate build gate."""
    from gps_kataster_obiektow_tatr.postgres import CatalogLoadError, open_catalog

    try:
        with open_catalog(data_dir, validate=False) as catalog:
            return validate_catalog(catalog, repo_root=repo_root, prefix_resolver=prefix_resolver)
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
    from gps_kataster_obiektow_tatr.postgres import open_catalog

    data_dir = Path(data_dir)
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


def _sql_issue(exc):
    path = getattr(exc, "path", None)
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
    return ValidationIssue(code, ValidationSeverity.ERROR, path, str(exc))


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


def _is_url_like(value: str) -> bool:
    return "://" in value


def _valid_http_url(value: str) -> bool:
    return valid_absolute_url(value) and urlparse(value).scheme in {"http", "https"}
