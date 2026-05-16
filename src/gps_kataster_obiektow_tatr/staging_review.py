"""Apply operator review decisions to staging import proposals."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from gps_kataster_obiektow_tatr.best_measurement import select_default_best_measurement_id
from gps_kataster_obiektow_tatr.data_loader import (
    DEFAULT_DATA_DIR,
    YamlDataLoadError,
    load_dataset,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_PIG_STAGING_PATH = REPO_ROOT / "build" / "staging" / "pig" / "pig-staging.json"
DEFAULT_TPN_STAGING_PATH = REPO_ROOT / "build" / "staging" / "tpn" / "tpn-staging.json"
DEFAULT_REVIEW_OUTPUT_DIR = REPO_ROOT / "build" / "staging" / "review"
DEFAULT_REVIEW_AUTHOR = "operator:staging-review"
_STAGING_PROPOSAL_NOTE_PREFIX = (
    "Staging proposal from {source}; requires operator review before final YAML."
)
_FINAL_PROPOSAL_NOTE_PREFIX = "Imported from {source} source record after operator review."
_STAGING_MEASUREMENT_NOTE_PREFIX = (
    "{source} source-record measurement imported into staging; not field-verified."
)
_FINAL_MEASUREMENT_NOTE_PREFIX = (
    "{source} source-record measurement imported after operator review; not field-verified."
)

_CREATE_CAVE = "create_cave"
_CREATE_OBJECT = "create_object"
_ADD_MEASUREMENT = "add_measurement"
_LINK_CAVE = "link_cave"
_REJECT = "reject"
_UNRESOLVED = "unresolved"

_ACTIONS = {
    _CREATE_CAVE,
    _CREATE_OBJECT,
    _ADD_MEASUREMENT,
    _LINK_CAVE,
    _REJECT,
    _UNRESOLVED,
}


class ReviewSeverity(StrEnum):
    """Severity levels for review-application issues."""

    ERROR = "error"
    WARNING = "warning"


class ReviewDecisionError(ValueError):
    """Raised when the decision or staging input cannot be parsed."""


@dataclass(frozen=True, slots=True)
class ReviewIssue:
    """One issue found while applying operator decisions."""

    code: str
    severity: ReviewSeverity
    decision_index: int | None
    description: str


@dataclass(frozen=True, slots=True)
class AppliedDecision:
    """A normalized decision application entry for reports."""

    decision_index: int
    action: str
    status: str
    source: str | None
    record_number: int | None
    object_id: str | None
    cave_id: str | None
    description: str


@dataclass(frozen=True, slots=True)
class StagingReports:
    """Loaded staging reports available to the review applier."""

    pig: dict[str, Any] | None = None
    tpn: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class StagingReviewResult:
    """Result of applying one operator decision file."""

    reviewed_at: str
    reviewed_by: str
    data_dir: Path
    applied_decisions: tuple[AppliedDecision, ...]
    issues: tuple[ReviewIssue, ...]
    written_paths: tuple[Path, ...]

    @property
    def has_errors(self) -> bool:
        """Return whether any review issue blocks final YAML writes."""

        return any(issue.severity == ReviewSeverity.ERROR for issue in self.issues)


@dataclass(frozen=True, slots=True)
class _StagingIndexes:
    pig_rows_by_record: dict[int, dict[str, Any]]
    pig_caves_by_id: dict[str, dict[str, Any]]
    pig_objects_by_id: dict[str, dict[str, Any]]
    tpn_rows_by_record: dict[int, dict[str, Any]]
    tpn_measurements_by_record: dict[int, dict[str, Any]]
    tpn_caves_by_id: dict[str, dict[str, Any]]
    tpn_objects_by_id: dict[str, dict[str, Any]]


def load_review_decisions(decisions_path: Path) -> dict[str, Any]:
    """Load a YAML operator decision file."""

    try:
        data = yaml.safe_load(decisions_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ReviewDecisionError(f"{decisions_path}: invalid YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise ReviewDecisionError(f"{decisions_path}: decision file must be a mapping")
    return data


def load_staging_reports(
    *,
    pig_staging_path: Path | None = DEFAULT_PIG_STAGING_PATH,
    tpn_staging_path: Path | None = DEFAULT_TPN_STAGING_PATH,
) -> StagingReports:
    """Load optional PIG and TPN staging JSON reports."""

    return StagingReports(
        pig=_load_staging_json(pig_staging_path),
        tpn=_load_staging_json(tpn_staging_path),
    )


def apply_review_decisions(
    decision_data: dict[str, Any],
    *,
    staging_reports: StagingReports,
    data_dir: Path = DEFAULT_DATA_DIR,
    write: bool = True,
) -> StagingReviewResult:
    """Apply operator decisions and optionally write final YAML under ``data_dir``."""

    reviewed_at = _clean_value(decision_data.get("reviewed_at")) or _utc_timestamp()
    reviewed_by = _clean_value(decision_data.get("reviewed_by")) or DEFAULT_REVIEW_AUTHOR
    decisions = decision_data.get("decisions")
    issues: list[ReviewIssue] = []
    applied: list[AppliedDecision] = []

    if not isinstance(decisions, list):
        issues.append(
            ReviewIssue(
                code="DECISIONS_INVALID",
                severity=ReviewSeverity.ERROR,
                decision_index=None,
                description="Decision file must contain a decisions list.",
            )
        )
        return StagingReviewResult(
            reviewed_at=reviewed_at,
            reviewed_by=reviewed_by,
            data_dir=data_dir,
            applied_decisions=(),
            issues=tuple(issues),
            written_paths=(),
        )

    try:
        objects, caves = _load_existing_final_data(data_dir)
    except YamlDataLoadError as exc:
        issues.append(
            ReviewIssue(
                code="FINAL_DATA_INVALID",
                severity=ReviewSeverity.ERROR,
                decision_index=None,
                description=str(exc),
            )
        )
        return StagingReviewResult(
            reviewed_at=reviewed_at,
            reviewed_by=reviewed_by,
            data_dir=data_dir,
            applied_decisions=(),
            issues=tuple(issues),
            written_paths=(),
        )

    indexes = _build_indexes(staging_reports)
    dirty_objects: set[str] = set()
    dirty_caves: set[str] = set()

    for decision_index, decision in enumerate(decisions, start=1):
        if not isinstance(decision, dict):
            issues.append(
                ReviewIssue(
                    code="DECISION_INVALID",
                    severity=ReviewSeverity.ERROR,
                    decision_index=decision_index,
                    description="Decision entry must be a mapping.",
                )
            )
            continue

        action = _clean_value(decision.get("action"))
        if action not in _ACTIONS:
            issues.append(
                ReviewIssue(
                    code="DECISION_ACTION_INVALID",
                    severity=ReviewSeverity.ERROR,
                    decision_index=decision_index,
                    description=f"Unsupported decision action {action!r}.",
                )
            )
            continue

        if action == _CREATE_CAVE:
            _apply_create_cave(
                decision=decision,
                decision_index=decision_index,
                indexes=indexes,
                caves=caves,
                dirty_caves=dirty_caves,
                issues=issues,
                applied=applied,
            )
        elif action == _CREATE_OBJECT:
            _apply_create_object(
                decision=decision,
                decision_index=decision_index,
                indexes=indexes,
                objects=objects,
                dirty_objects=dirty_objects,
                issues=issues,
                applied=applied,
            )
        elif action == _ADD_MEASUREMENT:
            _apply_add_measurement(
                decision=decision,
                decision_index=decision_index,
                indexes=indexes,
                objects=objects,
                caves=caves,
                dirty_objects=dirty_objects,
                dirty_caves=dirty_caves,
                reviewed_at=reviewed_at,
                reviewed_by=reviewed_by,
                issues=issues,
                applied=applied,
            )
        elif action == _LINK_CAVE:
            _apply_link_cave(
                decision=decision,
                decision_index=decision_index,
                objects=objects,
                caves=caves,
                dirty_objects=dirty_objects,
                dirty_caves=dirty_caves,
                reviewed_at=reviewed_at,
                reviewed_by=reviewed_by,
                issues=issues,
                applied=applied,
            )
        elif action in {_REJECT, _UNRESOLVED}:
            _apply_non_materialized_decision(
                decision=decision,
                decision_index=decision_index,
                action=action,
                indexes=indexes,
                issues=issues,
                applied=applied,
            )

    has_errors = any(issue.severity == ReviewSeverity.ERROR for issue in issues)
    written_paths: tuple[Path, ...] = ()
    if write and not has_errors:
        written_paths = _write_dirty_records(
            data_dir=data_dir,
            objects=objects,
            caves=caves,
            dirty_objects=dirty_objects,
            dirty_caves=dirty_caves,
        )

    return StagingReviewResult(
        reviewed_at=reviewed_at,
        reviewed_by=reviewed_by,
        data_dir=data_dir,
        applied_decisions=tuple(applied),
        issues=tuple(issues),
        written_paths=written_paths,
    )


def write_review_report_files(
    result: StagingReviewResult,
    *,
    output_dir: Path = DEFAULT_REVIEW_OUTPUT_DIR,
) -> tuple[Path, Path]:
    """Write machine-readable and Markdown review-application reports."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "staging-review.json"
    markdown_path = output_dir / "staging-review.md"

    json_path.write_text(
        json.dumps(_result_to_json_data(result), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_review_markdown(result), encoding="utf-8")
    return json_path, markdown_path


def render_review_markdown(result: StagingReviewResult) -> str:
    """Render a concise Markdown report from an application result."""

    counts = _applied_status_counts(result.applied_decisions)
    lines = [
        "# Staging Review Decisions",
        "",
        f"Reviewed: `{result.reviewed_at}` by `{result.reviewed_by}`",
        f"Data dir: `{result.data_dir}`",
        "",
        "## Summary",
        "",
        "| Decisions | Materialized | Skipped | Issues | Written YAML |",
        "|---:|---:|---:|---:|---:|",
        (
            f"| {len(result.applied_decisions)} | {counts['materialized']} | "
            f"{counts['skipped']} | {len(result.issues)} | {len(result.written_paths)} |"
        ),
        "",
        "## Decisions",
        "",
        "| # | Action | Status | Source | Row | Cave | Object | Description |",
        "|---:|---|---|---|---:|---|---|---|",
    ]

    for decision in result.applied_decisions:
        lines.append(
            "| "
            f"{decision.decision_index} | "
            f"`{decision.action}` | "
            f"`{decision.status}` | "
            f"{_markdown_code_or_dash(decision.source)} | "
            f"{decision.record_number or '-'} | "
            f"{_markdown_code_or_dash(decision.cave_id)} | "
            f"{_markdown_code_or_dash(decision.object_id)} | "
            f"{_markdown_text(decision.description)} |"
        )

    if result.issues:
        lines.extend(
            [
                "",
                "## Issues",
                "",
                "| Severity | Code | Decision | Description |",
                "|---|---|---:|---|",
            ]
        )
        for issue in result.issues:
            lines.append(
                "| "
                f"`{issue.severity.value}` | "
                f"`{issue.code}` | "
                f"{issue.decision_index or '-'} | "
                f"{_markdown_text(issue.description)} |"
            )

    if result.written_paths:
        lines.extend(["", "## Written YAML", ""])
        lines.extend(f"- `{path}`" for path in result.written_paths)

    return "\n".join(lines) + "\n"


def _apply_create_cave(
    *,
    decision: dict[str, Any],
    decision_index: int,
    indexes: _StagingIndexes,
    caves: dict[str, dict[str, Any]],
    dirty_caves: set[str],
    issues: list[ReviewIssue],
    applied: list[AppliedDecision],
) -> None:
    source, record_number = _decision_source_record(decision, decision_index, issues)
    if source is None or record_number is None:
        return

    proposal = _cave_proposal_for_decision(
        source=source,
        record_number=record_number,
        explicit_cave_id=_clean_value(decision.get("cave_id")) or None,
        indexes=indexes,
    )
    if proposal is None:
        issues.append(
            ReviewIssue(
                code="STAGING_CAVE_PROPOSAL_MISSING",
                severity=ReviewSeverity.ERROR,
                decision_index=decision_index,
                description=f"No cave proposal for {source} row {record_number}.",
            )
        )
        return

    cave_id = _clean_value(proposal.get("id"))
    if cave_id in caves:
        issues.append(
            ReviewIssue(
                code="CAVE_ALREADY_EXISTS",
                severity=ReviewSeverity.ERROR,
                decision_index=decision_index,
                description=f"Cave {cave_id} already exists in final data or earlier decisions.",
            )
        )
        return

    caves[cave_id] = _finalize_staging_record(proposal, source=source)
    dirty_caves.add(cave_id)
    applied.append(
        AppliedDecision(
            decision_index=decision_index,
            action=_CREATE_CAVE,
            status="materialized",
            source=source,
            record_number=record_number,
            object_id=None,
            cave_id=cave_id,
            description=f"Created final cave {cave_id} from staging proposal.",
        )
    )


def _apply_create_object(
    *,
    decision: dict[str, Any],
    decision_index: int,
    indexes: _StagingIndexes,
    objects: dict[str, dict[str, Any]],
    dirty_objects: set[str],
    issues: list[ReviewIssue],
    applied: list[AppliedDecision],
) -> None:
    source, record_number = _decision_source_record(decision, decision_index, issues)
    if source is None or record_number is None:
        return

    proposal = _object_proposal_for_decision(
        source=source,
        record_number=record_number,
        explicit_object_id=_clean_value(decision.get("object_id")) or None,
        indexes=indexes,
    )
    if proposal is None:
        issues.append(
            ReviewIssue(
                code="STAGING_OBJECT_PROPOSAL_MISSING",
                severity=ReviewSeverity.ERROR,
                decision_index=decision_index,
                description=f"No object proposal for {source} row {record_number}.",
            )
        )
        return

    object_id = _clean_value(proposal.get("id"))
    if object_id in objects:
        issues.append(
            ReviewIssue(
                code="OBJECT_ALREADY_EXISTS",
                severity=ReviewSeverity.ERROR,
                decision_index=decision_index,
                description=(
                    f"Object {object_id} already exists in final data or earlier decisions."
                ),
            )
        )
        return

    objects[object_id] = _finalize_staging_record(proposal, source=source)
    dirty_objects.add(object_id)
    applied.append(
        AppliedDecision(
            decision_index=decision_index,
            action=_CREATE_OBJECT,
            status="materialized",
            source=source,
            record_number=record_number,
            object_id=object_id,
            cave_id=_clean_value(proposal.get("cave_id")) or None,
            description=f"Created final object {object_id} from staging proposal.",
        )
    )


def _apply_add_measurement(
    *,
    decision: dict[str, Any],
    decision_index: int,
    indexes: _StagingIndexes,
    objects: dict[str, dict[str, Any]],
    caves: dict[str, dict[str, Any]],
    dirty_objects: set[str],
    dirty_caves: set[str],
    reviewed_at: str,
    reviewed_by: str,
    issues: list[ReviewIssue],
    applied: list[AppliedDecision],
) -> None:
    source, record_number = _decision_source_record(decision, decision_index, issues)
    if source is None or record_number is None:
        return
    if source != "TPN":
        issues.append(
            ReviewIssue(
                code="MEASUREMENT_SOURCE_UNSUPPORTED",
                severity=ReviewSeverity.ERROR,
                decision_index=decision_index,
                description="Only TPN matched measurement updates are supported in V1.",
            )
        )
        return

    update = indexes.tpn_measurements_by_record.get(record_number)
    if update is None:
        issues.append(
            ReviewIssue(
                code="STAGING_MEASUREMENT_UPDATE_MISSING",
                severity=ReviewSeverity.ERROR,
                decision_index=decision_index,
                description=f"No matched TPN measurement update for row {record_number}.",
            )
        )
        return

    object_id = _clean_value(decision.get("target_object_id")) or _clean_value(
        update.get("target_object_id")
    )
    cave_id = _clean_value(decision.get("target_cave_id")) or _clean_value(
        update.get("target_cave_id")
    )
    if object_id not in objects:
        issues.append(
            ReviewIssue(
                code="TARGET_OBJECT_MISSING",
                severity=ReviewSeverity.ERROR,
                decision_index=decision_index,
                description=f"Target object {object_id or '<missing>'} does not exist.",
            )
        )
        return

    object_data = objects[object_id]
    measurement = deepcopy(update.get("measurement"))
    if not isinstance(measurement, dict):
        issues.append(
            ReviewIssue(
                code="STAGING_MEASUREMENT_INVALID",
                severity=ReviewSeverity.ERROR,
                decision_index=decision_index,
                description=f"Matched TPN update for row {record_number} has no measurement.",
            )
        )
        return

    measurement_id = _clean_value(measurement.get("id"))
    existing_measurement_ids = {
        _clean_value(item.get("id"))
        for item in object_data.get("measurements", [])
        if isinstance(item, dict)
    }
    if measurement_id in existing_measurement_ids:
        issues.append(
            ReviewIssue(
                code="MEASUREMENT_ALREADY_EXISTS",
                severity=ReviewSeverity.ERROR,
                decision_index=decision_index,
                description=f"Object {object_id} already has measurement {measurement_id}.",
            )
        )
        return

    object_data.setdefault("measurements", []).append(_finalize_staging_measurement(measurement))
    _append_unique_dicts(
        object_data.setdefault("external_refs", []), update.get("object_external_refs")
    )
    _refresh_auto_best_measurement(object_data, reviewed_at=reviewed_at, reviewed_by=reviewed_by)
    _touch_record(object_data, reviewed_at=reviewed_at, reviewed_by=reviewed_by)
    dirty_objects.add(object_id)

    if cave_id and cave_id in caves:
        cave_data = caves[cave_id]
        _append_unique_dicts(
            cave_data.setdefault("external_refs", []), update.get("cave_external_refs")
        )
        _touch_record(cave_data, reviewed_at=reviewed_at, reviewed_by=reviewed_by)
        dirty_caves.add(cave_id)

    applied.append(
        AppliedDecision(
            decision_index=decision_index,
            action=_ADD_MEASUREMENT,
            status="materialized",
            source=source,
            record_number=record_number,
            object_id=object_id,
            cave_id=cave_id or None,
            description=f"Added measurement {measurement_id} to object {object_id}.",
        )
    )


def _apply_link_cave(
    *,
    decision: dict[str, Any],
    decision_index: int,
    objects: dict[str, dict[str, Any]],
    caves: dict[str, dict[str, Any]],
    dirty_objects: set[str],
    dirty_caves: set[str],
    reviewed_at: str,
    reviewed_by: str,
    issues: list[ReviewIssue],
    applied: list[AppliedDecision],
) -> None:
    object_id = _clean_value(decision.get("object_id"))
    cave_id = _clean_value(decision.get("cave_id"))
    if not object_id or not cave_id:
        issues.append(
            ReviewIssue(
                code="LINK_CAVE_TARGET_MISSING",
                severity=ReviewSeverity.ERROR,
                decision_index=decision_index,
                description="link_cave requires object_id and cave_id.",
            )
        )
        return
    if object_id not in objects:
        issues.append(
            ReviewIssue(
                code="LINK_OBJECT_MISSING",
                severity=ReviewSeverity.ERROR,
                decision_index=decision_index,
                description=f"Object {object_id} does not exist.",
            )
        )
        return
    if cave_id not in caves:
        issues.append(
            ReviewIssue(
                code="LINK_CAVE_MISSING",
                severity=ReviewSeverity.ERROR,
                decision_index=decision_index,
                description=f"Cave {cave_id} does not exist.",
            )
        )
        return

    object_data = objects[object_id]
    cave_data = caves[cave_id]
    object_data["cave_id"] = cave_id
    object_ids = cave_data.setdefault("object_ids", [])
    if object_id not in object_ids:
        object_ids.append(object_id)
    _touch_record(object_data, reviewed_at=reviewed_at, reviewed_by=reviewed_by)
    _touch_record(cave_data, reviewed_at=reviewed_at, reviewed_by=reviewed_by)
    dirty_objects.add(object_id)
    dirty_caves.add(cave_id)
    applied.append(
        AppliedDecision(
            decision_index=decision_index,
            action=_LINK_CAVE,
            status="materialized",
            source=None,
            record_number=None,
            object_id=object_id,
            cave_id=cave_id,
            description=f"Linked object {object_id} with cave {cave_id}.",
        )
    )


def _apply_non_materialized_decision(
    *,
    decision: dict[str, Any],
    decision_index: int,
    action: str,
    indexes: _StagingIndexes,
    issues: list[ReviewIssue],
    applied: list[AppliedDecision],
) -> None:
    source, record_number = _decision_source_record(decision, decision_index, issues)
    if source is None or record_number is None:
        return
    if not _staging_row_exists(source=source, record_number=record_number, indexes=indexes):
        issues.append(
            ReviewIssue(
                code="STAGING_ROW_MISSING",
                severity=ReviewSeverity.ERROR,
                decision_index=decision_index,
                description=f"No {source} staging row {record_number}.",
            )
        )
        return
    reason = _clean_value(decision.get("reason"))
    if not reason:
        issues.append(
            ReviewIssue(
                code="DECISION_REASON_MISSING",
                severity=ReviewSeverity.WARNING,
                decision_index=decision_index,
                description=f"{action} decision for {source} row {record_number} has no reason.",
            )
        )
        reason = "No reason provided."

    applied.append(
        AppliedDecision(
            decision_index=decision_index,
            action=action,
            status="skipped",
            source=source,
            record_number=record_number,
            object_id=None,
            cave_id=None,
            description=reason,
        )
    )


def _decision_source_record(
    decision: dict[str, Any],
    decision_index: int,
    issues: list[ReviewIssue],
) -> tuple[str | None, int | None]:
    source = _clean_value(decision.get("source")).upper()
    record_number = _parse_positive_int(decision.get("record_number"))
    if source not in {"PIG", "TPN"}:
        issues.append(
            ReviewIssue(
                code="DECISION_SOURCE_INVALID",
                severity=ReviewSeverity.ERROR,
                decision_index=decision_index,
                description="Decision source must be PIG or TPN.",
            )
        )
        source = None
    if record_number is None:
        issues.append(
            ReviewIssue(
                code="DECISION_RECORD_INVALID",
                severity=ReviewSeverity.ERROR,
                decision_index=decision_index,
                description="Decision record_number must be a positive integer.",
            )
        )
    return source, record_number


def _cave_proposal_for_decision(
    *,
    source: str,
    record_number: int,
    explicit_cave_id: str | None,
    indexes: _StagingIndexes,
) -> dict[str, Any] | None:
    rows = indexes.pig_rows_by_record if source == "PIG" else indexes.tpn_rows_by_record
    caves = indexes.pig_caves_by_id if source == "PIG" else indexes.tpn_caves_by_id
    cave_id = explicit_cave_id or _clean_value(rows.get(record_number, {}).get("cave_id"))
    return caves.get(cave_id)


def _object_proposal_for_decision(
    *,
    source: str,
    record_number: int,
    explicit_object_id: str | None,
    indexes: _StagingIndexes,
) -> dict[str, Any] | None:
    rows = indexes.pig_rows_by_record if source == "PIG" else indexes.tpn_rows_by_record
    objects = indexes.pig_objects_by_id if source == "PIG" else indexes.tpn_objects_by_id
    object_id = explicit_object_id or _clean_value(rows.get(record_number, {}).get("object_id"))
    return objects.get(object_id)


def _staging_row_exists(
    *,
    source: str,
    record_number: int,
    indexes: _StagingIndexes,
) -> bool:
    rows = indexes.pig_rows_by_record if source == "PIG" else indexes.tpn_rows_by_record
    return record_number in rows


def _load_existing_final_data(
    data_dir: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    dataset = load_dataset(data_dir)
    objects = {
        _clean_value(record.data.get("id")): deepcopy(record.raw_data) for record in dataset.objects
    }
    caves = {
        _clean_value(record.data.get("id")): deepcopy(record.raw_data) for record in dataset.caves
    }
    return objects, caves


def _write_dirty_records(
    *,
    data_dir: Path,
    objects: dict[str, dict[str, Any]],
    caves: dict[str, dict[str, Any]],
    dirty_objects: set[str],
    dirty_caves: set[str],
) -> tuple[Path, ...]:
    paths: list[Path] = []

    for cave_id in sorted(dirty_caves):
        path = data_dir / "caves" / f"{cave_id}.yml"
        _write_yaml(path, caves[cave_id])
        paths.append(path)

    for object_id in sorted(dirty_objects):
        prefix = object_id.split("-", maxsplit=1)[0]
        path = data_dir / "objects" / prefix / f"{object_id}.yml"
        _write_yaml(path, objects[object_id])
        paths.append(path)

    return tuple(paths)


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _load_staging_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ReviewDecisionError(f"{path}: staging report must be a JSON object")
    return data


def _build_indexes(staging_reports: StagingReports) -> _StagingIndexes:
    pig_rows = _rows_by_record(staging_reports.pig)
    tpn_rows = _rows_by_record(staging_reports.tpn)
    return _StagingIndexes(
        pig_rows_by_record=pig_rows,
        pig_caves_by_id=_records_by_id(staging_reports.pig, "proposed_caves"),
        pig_objects_by_id=_records_by_id(staging_reports.pig, "proposed_objects"),
        tpn_rows_by_record=tpn_rows,
        tpn_measurements_by_record=_tpn_measurements_by_record(
            staging_reports.tpn,
            rows_by_record=tpn_rows,
        ),
        tpn_caves_by_id=_records_by_id(staging_reports.tpn, "proposed_caves"),
        tpn_objects_by_id=_records_by_id(staging_reports.tpn, "proposed_objects"),
    )


def _rows_by_record(report: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    if report is None:
        return {}
    rows: dict[int, dict[str, Any]] = {}
    for row in report.get("rows", []):
        if not isinstance(row, dict):
            continue
        record_number = _parse_positive_int(row.get("record_number"))
        if record_number is not None:
            rows[record_number] = row
    return rows


def _records_by_id(report: dict[str, Any] | None, key: str) -> dict[str, dict[str, Any]]:
    if report is None:
        return {}
    records: dict[str, dict[str, Any]] = {}
    for item in report.get(key, []):
        if not isinstance(item, dict):
            continue
        record_id = _clean_value(item.get("id"))
        if record_id:
            records[record_id] = item
    return records


def _tpn_measurements_by_record(
    report: dict[str, Any] | None,
    *,
    rows_by_record: dict[int, dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    if report is None:
        return {}

    by_record: dict[int, dict[str, Any]] = {}
    globalid_to_record: dict[str, int] = {}
    for record_number, row in rows_by_record.items():
        globalid = _clean_value(row.get("globalid"))
        if globalid:
            globalid_to_record[globalid] = record_number

    for update in report.get("matched_measurements", []):
        if not isinstance(update, dict):
            continue
        record_number = _parse_positive_int(update.get("record_number"))
        if record_number is None:
            measurement = update.get("measurement")
            source_ref = measurement.get("source_ref") if isinstance(measurement, dict) else ""
            if isinstance(source_ref, str) and source_ref.startswith("TPN:"):
                record_number = globalid_to_record.get(source_ref.removeprefix("TPN:"))
        if record_number is not None:
            by_record[record_number] = update
    return by_record


def _append_unique_dicts(target: list[Any], additions: Any) -> None:
    if not isinstance(additions, list):
        return
    seen = {_dict_identity(item) for item in target if isinstance(item, dict)}
    for item in additions:
        if not isinstance(item, dict):
            continue
        identity = _dict_identity(item)
        if identity in seen:
            continue
        target.append(deepcopy(item))
        seen.add(identity)


def _finalize_staging_record(data: dict[str, Any], *, source: str) -> dict[str, Any]:
    finalized = deepcopy(data)
    finalized["notes"] = _finalized_note(
        finalized.get("notes"),
        staging_prefix=_STAGING_PROPOSAL_NOTE_PREFIX.format(source=source),
        final_prefix=_FINAL_PROPOSAL_NOTE_PREFIX.format(source=source),
    )
    measurements = finalized.get("measurements")
    if isinstance(measurements, list):
        finalized["measurements"] = [
            _finalize_staging_measurement(measurement)
            if isinstance(measurement, dict)
            else measurement
            for measurement in measurements
        ]
    return finalized


def _finalize_staging_measurement(measurement: dict[str, Any]) -> dict[str, Any]:
    finalized = deepcopy(measurement)
    source = _clean_value(finalized.get("source")).upper()
    tags = finalized.get("tags")
    if isinstance(tags, list):
        finalized["tags"] = [tag for tag in tags if tag != "staging"]
    if source:
        finalized["notes"] = _finalized_note(
            finalized.get("notes"),
            staging_prefix=_STAGING_MEASUREMENT_NOTE_PREFIX.format(source=source),
            final_prefix=_FINAL_MEASUREMENT_NOTE_PREFIX.format(source=source),
        )
    return finalized


def _finalized_note(value: object, *, staging_prefix: str, final_prefix: str) -> object:
    if not isinstance(value, str):
        return value
    if not value.startswith(staging_prefix):
        return value
    return f"{final_prefix}{value.removeprefix(staging_prefix)}"


def _dict_identity(item: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        _clean_value(item.get("system")),
        _clean_value(item.get("ref_type")),
        _clean_value(item.get("external_id")),
        _clean_value(item.get("url")),
    )


def _refresh_auto_best_measurement(
    object_data: dict[str, Any],
    *,
    reviewed_at: str,
    reviewed_by: str,
) -> None:
    best_measurement = object_data.get("best_measurement")
    measurements = object_data.get("measurements")
    if not isinstance(best_measurement, dict) or not isinstance(measurements, list):
        return
    if best_measurement.get("mode") != "auto":
        return
    selected_id = select_default_best_measurement_id(
        [measurement for measurement in measurements if isinstance(measurement, dict)]
    )
    if selected_id is None:
        return
    best_measurement["measurement_id"] = selected_id
    best_measurement["updated_at"] = reviewed_at
    best_measurement["updated_by"] = reviewed_by


def _touch_record(
    data: dict[str, Any],
    *,
    reviewed_at: str,
    reviewed_by: str,
) -> None:
    data["updated_at"] = reviewed_at
    data["updated_by"] = reviewed_by


def _result_to_json_data(result: StagingReviewResult) -> dict[str, Any]:
    return {
        "reviewed_at": result.reviewed_at,
        "reviewed_by": result.reviewed_by,
        "data_dir": str(result.data_dir),
        "decision_count": len(result.applied_decisions),
        "issue_count": len(result.issues),
        "has_errors": result.has_errors,
        "decisions": [
            {
                "decision_index": decision.decision_index,
                "action": decision.action,
                "status": decision.status,
                "source": decision.source,
                "record_number": decision.record_number,
                "object_id": decision.object_id,
                "cave_id": decision.cave_id,
                "description": decision.description,
            }
            for decision in result.applied_decisions
        ],
        "issues": [
            {
                "code": issue.code,
                "severity": issue.severity.value,
                "decision_index": issue.decision_index,
                "description": issue.description,
            }
            for issue in result.issues
        ],
        "written_paths": [str(path) for path in result.written_paths],
    }


def _applied_status_counts(decisions: tuple[AppliedDecision, ...]) -> dict[str, int]:
    counts = {"materialized": 0, "skipped": 0}
    for decision in decisions:
        counts[decision.status] = counts.get(decision.status, 0) + 1
    return counts


def _parse_positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _clean_value(raw_value: Any) -> str:
    if raw_value is None:
        return ""
    return str(raw_value).strip()


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _markdown_code_or_dash(value: str | None) -> str:
    if not value:
        return "-"
    return f"`{_markdown_text(value)}`"


def _markdown_text(value: str) -> str:
    text = _clean_value(value)
    if not text:
        return "-"
    return text.replace("|", "\\|").replace("\n", "<br>")
