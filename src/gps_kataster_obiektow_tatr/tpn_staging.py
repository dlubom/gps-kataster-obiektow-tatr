"""Build reviewable staging proposals from the TPN source export."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from math import hypot
from pathlib import Path
from typing import Any, Protocol

from gps_kataster_obiektow_tatr.coordinates import pl1992_to_wgs84
from gps_kataster_obiektow_tatr.data_loader import DEFAULT_DATA_DIR, load_dataset
from gps_kataster_obiektow_tatr.prefix_resolver import (
    PrefixResolution,
    PrefixResolutionStatus,
    default_prefix_resolver,
)
from gps_kataster_obiektow_tatr.source_table import read_source_table

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_TPN_SOURCE = REPO_ROOT / "tpn_otwory_jaskin.xlsx.-.Export.csv"
DEFAULT_TPN_STAGING_DIR = REPO_ROOT / "build" / "staging" / "tpn"
DEFAULT_PIG_STAGING_PATH = REPO_ROOT / "build" / "staging" / "pig" / "pig-staging.json"
DEFAULT_IMPORT_AUTHOR = "importer:tpn"
DEFAULT_DUPLICATE_RADIUS_M = 25.0


@dataclass(frozen=True, slots=True)
class TpnPoint:
    """Parsed point fields from one TPN row."""

    lat: float
    lon: float
    x_1992: float
    y_1992: float
    elevation_m: float | None
    observed_date: str
    source_date: str | None


@dataclass(frozen=True, slots=True)
class TpnStagingIssue:
    """A non-fatal importer finding for operator review."""

    code: str
    severity: str
    record_number: int | None
    globalid: str | None
    nr_inwent: str | None
    description: str


@dataclass(frozen=True, slots=True)
class TpnStagingRow:
    """Compact per-row summary used by the Markdown staging report."""

    record_number: int
    globalid: str
    nr_inwent: str
    name: str
    status: str
    cave_id: str | None
    object_id: str | None
    match_strategy: str | None
    distance_m: float | None


@dataclass(frozen=True, slots=True)
class TpnStagingReport:
    """Complete TPN staging import result."""

    source_path: Path
    generated_at: str
    record_count: int
    matched_measurements: tuple[dict[str, Any], ...]
    proposed_caves: tuple[dict[str, Any], ...]
    proposed_objects: tuple[dict[str, Any], ...]
    rows: tuple[TpnStagingRow, ...]
    issues: tuple[TpnStagingIssue, ...]


@dataclass(frozen=True, slots=True)
class _Candidate:
    source: str
    cave_id: str | None
    object_id: str
    nr_inwent: str | None
    name: str
    x_1992: float | None
    y_1992: float | None
    globalids: tuple[str, ...]
    next_measurement_id: str


@dataclass(frozen=True, slots=True)
class _Match:
    candidate: _Candidate
    strategy: str
    distance_m: float | None


@dataclass(frozen=True, slots=True)
class _MatchOutcome:
    status: str
    match: _Match | None = None
    issue_code: str | None = None
    issue_description: str | None = None


class PrefixResolverLike(Protocol):
    """Minimal prefix resolver interface used by the staging importer."""

    def resolve(self, *, lat: float, lon: float) -> PrefixResolution:
        """Resolve a WGS84 coordinate to a staging object prefix."""


def build_tpn_staging(
    source_path: Path = DEFAULT_TPN_SOURCE,
    *,
    generated_at: str,
    data_dir: Path = DEFAULT_DATA_DIR,
    pig_staging_path: Path | None = DEFAULT_PIG_STAGING_PATH,
    prefix_resolver: PrefixResolverLike | None = None,
    duplicate_radius_m: float = DEFAULT_DUPLICATE_RADIUS_M,
) -> TpnStagingReport:
    """Build TPN measurement/object proposals without writing final YAML."""

    table = read_source_table(source_path)
    candidates = (
        *_load_existing_candidates(data_dir),
        *_load_pig_staging_candidates(pig_staging_path),
    )
    resolver = prefix_resolver or default_prefix_resolver()
    source_nr_counts = _source_nr_counts(table.rows)
    cave_number = _seed_cave_number(data_dir, candidates)
    object_numbers = _seed_object_numbers(data_dir, candidates)

    matched_measurements: list[dict[str, Any]] = []
    proposed_caves: list[dict[str, Any]] = []
    proposed_objects: list[dict[str, Any]] = []
    staging_rows: list[TpnStagingRow] = []
    issues: list[TpnStagingIssue] = []

    for record_number, row in enumerate(table.rows, start=1):
        globalid = _clean_value(row.get("GLOBALID"))
        nr_inwent = _clean_value(row.get("NR_INWENT"))
        name = _clean_value(row.get("NAZWA")) or f"TPN row {record_number}"
        point = _parse_tpn_point(
            row,
            record_number=record_number,
            globalid=globalid,
            nr_inwent=nr_inwent,
            generated_at=generated_at,
            issues=issues,
        )

        if not globalid:
            issues.append(
                TpnStagingIssue(
                    code="TPN_GLOBALID_MISSING",
                    severity="warning",
                    record_number=record_number,
                    globalid=None,
                    nr_inwent=nr_inwent or None,
                    description="Missing GLOBALID; TPN measurement proposal rejected.",
                )
            )
            staging_rows.append(
                _row_summary(
                    record_number=record_number,
                    globalid=globalid,
                    nr_inwent=nr_inwent,
                    name=name,
                    status="rejected",
                )
            )
            continue

        if point is None:
            staging_rows.append(
                _row_summary(
                    record_number=record_number,
                    globalid=globalid,
                    nr_inwent=nr_inwent,
                    name=name,
                    status="rejected",
                )
            )
            continue

        outcome = _match_tpn_row(
            candidates=candidates,
            globalid=globalid,
            nr_inwent=nr_inwent,
            name=name,
            point=point,
            source_nr_count=source_nr_counts.get(nr_inwent, 0),
            duplicate_radius_m=duplicate_radius_m,
        )
        if outcome.status == "unresolved":
            issues.append(
                TpnStagingIssue(
                    code=outcome.issue_code or "TPN_MATCH_UNRESOLVED",
                    severity="warning",
                    record_number=record_number,
                    globalid=globalid,
                    nr_inwent=nr_inwent or None,
                    description=outcome.issue_description or "TPN row requires operator review.",
                )
            )
            staging_rows.append(
                _row_summary(
                    record_number=record_number,
                    globalid=globalid,
                    nr_inwent=nr_inwent,
                    name=name,
                    status="unresolved",
                )
            )
            continue

        if outcome.match is not None:
            match = outcome.match
            if match.distance_m is not None and match.distance_m > duplicate_radius_m:
                issues.append(
                    TpnStagingIssue(
                        code="TPN_MATCH_DISTANCE_REVIEW",
                        severity="warning",
                        record_number=record_number,
                        globalid=globalid,
                        nr_inwent=nr_inwent or None,
                        description=(
                            f"Matched by {match.strategy}, but TPN point is "
                            f"{match.distance_m:.2f} m from the candidate."
                        ),
                    )
                )
            matched_measurements.append(
                _build_measurement_update(
                    row=row,
                    point=point,
                    match=match,
                    globalid=globalid,
                    nr_inwent=nr_inwent,
                    generated_at=generated_at,
                )
            )
            staging_rows.append(
                _row_summary(
                    record_number=record_number,
                    globalid=globalid,
                    nr_inwent=nr_inwent,
                    name=name,
                    status="matched",
                    cave_id=match.candidate.cave_id,
                    object_id=match.candidate.object_id,
                    match_strategy=match.strategy,
                    distance_m=match.distance_m,
                )
            )
            continue

        new_ids = _try_build_new_ids(
            point=point,
            record_number=record_number,
            globalid=globalid,
            nr_inwent=nr_inwent,
            data_dir=data_dir,
            object_numbers=object_numbers,
            resolver=resolver,
            issues=issues,
        )
        if new_ids is None:
            staging_rows.append(
                _row_summary(
                    record_number=record_number,
                    globalid=globalid,
                    nr_inwent=nr_inwent,
                    name=name,
                    status="rejected",
                )
            )
            continue

        cave_number += 1
        cave_id = f"C-{cave_number:04d}"
        object_id = new_ids
        proposed_caves.append(
            _build_cave_proposal(
                row=row,
                cave_id=cave_id,
                object_id=object_id,
                name=name,
                generated_at=generated_at,
            )
        )
        proposed_objects.append(
            _build_object_proposal(
                row=row,
                object_id=object_id,
                cave_id=cave_id,
                name=name,
                point=point,
                globalid=globalid,
                generated_at=generated_at,
            )
        )
        staging_rows.append(
            _row_summary(
                record_number=record_number,
                globalid=globalid,
                nr_inwent=nr_inwent,
                name=name,
                status="new",
                cave_id=cave_id,
                object_id=object_id,
            )
        )

    return TpnStagingReport(
        source_path=source_path,
        generated_at=generated_at,
        record_count=len(table.rows),
        matched_measurements=tuple(matched_measurements),
        proposed_caves=tuple(proposed_caves),
        proposed_objects=tuple(proposed_objects),
        rows=tuple(staging_rows),
        issues=tuple(issues),
    )


def write_staging_files(report: TpnStagingReport, *, output_dir: Path) -> tuple[Path, Path]:
    """Write machine-readable and human-readable TPN staging reports."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "tpn-staging.json"
    markdown_path = output_dir / "tpn-staging.md"

    json_path.write_text(
        json.dumps(_report_to_json_data(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown_report(report), encoding="utf-8")

    return json_path, markdown_path


def render_markdown_report(report: TpnStagingReport) -> str:
    """Render a concise Markdown summary of the staging import."""

    counts = _status_counts(report.rows)
    lines = [
        "# TPN Staging Import",
        "",
        f"Generated: `{report.generated_at}`",
        f"Source: `{report.source_path}`",
        "",
        "Scope: staging proposals only. This report does not write final YAML under `data/`.",
        "",
        "## Summary",
        "",
        "| Records | Matched | New | Unresolved | Rejected | Issues |",
        "|---:|---:|---:|---:|---:|---:|",
        (
            f"| {report.record_count} | {counts['matched']} | {counts['new']} | "
            f"{counts['unresolved']} | {counts['rejected']} | {len(report.issues)} |"
        ),
        "",
        "## Mapping Rules",
        "",
        "- TPN `GLOBALID` is proposed as `Obiekt.external_refs`.",
        "- TPN `NR_INWENT` is proposed as `Jaskinia.external_refs`.",
        "- Matched rows propose measurement additions; new rows propose staging caves and objects.",
        "",
        "## Rows",
        "",
        "| Row | Status | Cave | Object | Match | Distance m | GLOBALID | NR_INWENT | Name |",
        "|---:|---|---|---|---|---:|---|---|---|",
    ]

    for row in report.rows:
        distance = "-" if row.distance_m is None else f"{row.distance_m:.2f}"
        lines.append(
            "| "
            f"{row.record_number} | "
            f"`{row.status}` | "
            f"{_markdown_code_or_dash(row.cave_id)} | "
            f"{_markdown_code_or_dash(row.object_id)} | "
            f"{_markdown_code_or_dash(row.match_strategy)} | "
            f"{distance} | "
            f"{_markdown_text(row.globalid)} | "
            f"{_markdown_text(row.nr_inwent)} | "
            f"{_markdown_text(row.name)} |"
        )

    if report.issues:
        lines.extend(
            [
                "",
                "## Issues",
                "",
                "| Severity | Code | Row | GLOBALID | NR_INWENT | Description |",
                "|---|---|---:|---|---|---|",
            ]
        )
        for issue in report.issues:
            lines.append(
                "| "
                f"`{issue.severity}` | "
                f"`{issue.code}` | "
                f"{issue.record_number or '-'} | "
                f"{_markdown_text(issue.globalid or '')} | "
                f"{_markdown_text(issue.nr_inwent or '')} | "
                f"{_markdown_text(issue.description)} |"
            )

    return "\n".join(lines) + "\n"


def _parse_tpn_point(
    row: dict[str, str],
    *,
    record_number: int,
    globalid: str,
    nr_inwent: str,
    generated_at: str,
    issues: list[TpnStagingIssue],
) -> TpnPoint | None:
    x_1992 = _parse_decimal(row.get("X1992"))
    y_1992 = _parse_decimal(row.get("Y1992"))

    if x_1992 is None or y_1992 is None:
        issues.append(
            TpnStagingIssue(
                code="TPN_POINT_COORDINATES_INVALID",
                severity="warning",
                record_number=record_number,
                globalid=globalid or None,
                nr_inwent=nr_inwent or None,
                description="Missing or invalid PL-1992 coordinates; row rejected.",
            )
        )
        return None

    source_date = _parse_source_date(row) or _date_part(generated_at)
    wgs84 = pl1992_to_wgs84(x_1992=x_1992, y_1992=y_1992)
    return TpnPoint(
        lat=wgs84.lat,
        lon=wgs84.lon,
        x_1992=x_1992,
        y_1992=y_1992,
        elevation_m=_parse_decimal(row.get("Z")),
        observed_date=source_date,
        source_date=source_date,
    )


def _match_tpn_row(
    *,
    candidates: tuple[_Candidate, ...],
    globalid: str,
    nr_inwent: str,
    name: str,
    point: TpnPoint,
    source_nr_count: int,
    duplicate_radius_m: float,
) -> _MatchOutcome:
    by_globalid = [candidate for candidate in candidates if globalid in candidate.globalids]
    if by_globalid:
        return _unique_candidate_outcome(
            candidates=by_globalid,
            strategy="globalid",
            point=point,
            issue_code="TPN_GLOBALID_AMBIGUOUS",
            issue_description="GLOBALID matches more than one candidate.",
        )

    by_nr = [
        candidate for candidate in candidates if candidate.nr_inwent == nr_inwent and nr_inwent
    ]
    if by_nr:
        if source_nr_count > 1:
            by_name_and_distance = [
                candidate
                for candidate in by_nr
                if _names_equal(candidate.name, name)
                and _candidate_distance_m(candidate, point) is not None
                and _candidate_distance_m(candidate, point) <= duplicate_radius_m
            ]
            if len(by_name_and_distance) == 1:
                return _matched_outcome(by_name_and_distance[0], "nr_inwent_name_distance", point)
            return _MatchOutcome(
                status="unresolved",
                issue_code="TPN_NR_INWENT_AMBIGUOUS",
                issue_description=(
                    "TPN source contains multiple rows with this NR_INWENT; "
                    "name and distance did not resolve one object."
                ),
            )
        return _choose_candidate_by_distance_or_name(
            candidates=by_nr,
            strategy="nr_inwent",
            point=point,
            name=name,
            duplicate_radius_m=duplicate_radius_m,
            issue_code="TPN_NR_INWENT_AMBIGUOUS",
            issue_description="NR_INWENT matches more than one candidate.",
        )

    by_name_and_distance = [
        candidate
        for candidate in candidates
        if _names_equal(candidate.name, name)
        and _candidate_distance_m(candidate, point) is not None
        and _candidate_distance_m(candidate, point) <= duplicate_radius_m
    ]
    if by_name_and_distance:
        return _choose_candidate_by_distance_or_name(
            candidates=by_name_and_distance,
            strategy="name_distance",
            point=point,
            name=name,
            duplicate_radius_m=duplicate_radius_m,
            issue_code="TPN_NAME_DISTANCE_AMBIGUOUS",
            issue_description="Name and distance match more than one candidate.",
        )

    return _MatchOutcome(status="new")


def _unique_candidate_outcome(
    *,
    candidates: list[_Candidate],
    strategy: str,
    point: TpnPoint,
    issue_code: str,
    issue_description: str,
) -> _MatchOutcome:
    if len(candidates) == 1:
        return _matched_outcome(candidates[0], strategy, point)
    return _MatchOutcome(
        status="unresolved",
        issue_code=issue_code,
        issue_description=issue_description,
    )


def _choose_candidate_by_distance_or_name(
    *,
    candidates: list[_Candidate],
    strategy: str,
    point: TpnPoint,
    name: str,
    duplicate_radius_m: float,
    issue_code: str,
    issue_description: str,
) -> _MatchOutcome:
    if len(candidates) == 1:
        return _matched_outcome(candidates[0], strategy, point)

    close = [
        candidate
        for candidate in candidates
        if _candidate_distance_m(candidate, point) is not None
        and _candidate_distance_m(candidate, point) <= duplicate_radius_m
    ]
    close_name_matches = [candidate for candidate in close if _names_equal(candidate.name, name)]
    if len(close_name_matches) == 1:
        return _matched_outcome(close_name_matches[0], f"{strategy}_name_distance", point)
    if len(close) == 1:
        return _matched_outcome(close[0], f"{strategy}_distance", point)

    return _MatchOutcome(
        status="unresolved",
        issue_code=issue_code,
        issue_description=issue_description,
    )


def _matched_outcome(candidate: _Candidate, strategy: str, point: TpnPoint) -> _MatchOutcome:
    return _MatchOutcome(
        status="matched",
        match=_Match(
            candidate=candidate,
            strategy=strategy,
            distance_m=_candidate_distance_m(candidate, point),
        ),
    )


def _try_build_new_ids(
    *,
    point: TpnPoint,
    record_number: int,
    globalid: str,
    nr_inwent: str,
    data_dir: Path,
    object_numbers: dict[str, int],
    resolver: PrefixResolverLike,
    issues: list[TpnStagingIssue],
) -> str | None:
    resolution = resolver.resolve(lat=point.lat, lon=point.lon)
    if resolution.status == PrefixResolutionStatus.ERROR or resolution.prefix is None:
        issues.append(
            TpnStagingIssue(
                code=resolution.code or "TPN_PREFIX_RESOLUTION_ERROR",
                severity="warning",
                record_number=record_number,
                globalid=globalid or None,
                nr_inwent=nr_inwent or None,
                description=(resolution.message or "Prefix resolution failed.") + " Row rejected.",
            )
        )
        return None

    if resolution.status == PrefixResolutionStatus.WARNING:
        issues.append(
            TpnStagingIssue(
                code=resolution.code or "TPN_PREFIX_RESOLUTION_WARNING",
                severity="warning",
                record_number=record_number,
                globalid=globalid or None,
                nr_inwent=nr_inwent or None,
                description=(resolution.message or "Prefix resolution requires review."),
            )
        )

    prefix = resolution.prefix
    object_numbers.setdefault(prefix, _max_existing_object_number(data_dir / "objects", prefix))
    object_numbers[prefix] += 1
    return f"{prefix}-{object_numbers[prefix]:04d}"


def _build_measurement_update(
    *,
    row: dict[str, str],
    point: TpnPoint,
    match: _Match,
    globalid: str,
    nr_inwent: str,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "status": "matched",
        "target_object_id": match.candidate.object_id,
        "target_cave_id": match.candidate.cave_id,
        "match": {
            "source": match.candidate.source,
            "strategy": match.strategy,
            "distance_m": match.distance_m,
        },
        "object_external_refs": [_tpn_object_external_ref(globalid)],
        "cave_external_refs": _tpn_cave_external_refs(row),
        "measurement": _build_tpn_measurement(
            measurement_id=match.candidate.next_measurement_id,
            point=point,
            globalid=globalid,
            generated_at=generated_at,
        ),
        "notes": (
            "Staging measurement update from TPN; requires operator review before final YAML."
        ),
        "nr_inwent": nr_inwent,
    }


def _build_cave_proposal(
    *,
    row: dict[str, str],
    cave_id: str,
    object_id: str,
    name: str,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": cave_id,
        "name": name,
        "system_name": None,
        "external_refs": _tpn_cave_external_refs(row),
        "object_ids": [object_id],
        "notes": _tpn_cave_notes(row),
        "created_at": generated_at,
        "created_by": DEFAULT_IMPORT_AUTHOR,
        "updated_at": generated_at,
        "updated_by": DEFAULT_IMPORT_AUTHOR,
    }


def _build_object_proposal(
    *,
    row: dict[str, str],
    object_id: str,
    cave_id: str,
    name: str,
    point: TpnPoint,
    globalid: str,
    generated_at: str,
) -> dict[str, Any]:
    prefix = object_id.split("-", maxsplit=1)[0]
    return {
        "schema_version": 1,
        "id": object_id,
        "category": "jaskinia_otwor",
        "name_local": name,
        "cave_id": cave_id,
        "id_assignment": {
            "method": "auto",
            "assigned_from_measurement_id": "m-001",
            "assigned_prefix": prefix,
            "prefix_override_reason": None,
        },
        "external_refs": [_tpn_object_external_ref(globalid)],
        "measurements": [
            _build_tpn_measurement(
                measurement_id="m-001",
                point=point,
                globalid=globalid,
                generated_at=generated_at,
            )
        ],
        "best_measurement": {
            "mode": "auto",
            "measurement_id": "m-001",
            "reason": None,
            "updated_at": generated_at,
            "updated_by": DEFAULT_IMPORT_AUTHOR,
        },
        "attachments": [],
        "notes": _tpn_object_notes(row),
        "created_at": generated_at,
        "created_by": DEFAULT_IMPORT_AUTHOR,
        "updated_at": generated_at,
        "updated_by": DEFAULT_IMPORT_AUTHOR,
    }


def _build_tpn_measurement(
    *,
    measurement_id: str,
    point: TpnPoint,
    globalid: str,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "id": measurement_id,
        "lat": point.lat,
        "lon": point.lon,
        "x_1992": point.x_1992,
        "y_1992": point.y_1992,
        "elevation_m": point.elevation_m,
        "elevation_datum": "unknown",
        "elevation_source": "source_record",
        "horizontal_accuracy_m": None,
        "vertical_accuracy_m": None,
        "source": "TPN",
        "source_ref": f"TPN:{globalid}",
        "observed_date": point.observed_date,
        "source_date": point.source_date,
        "method": "source_record",
        "device": None,
        "tags": ["tpn", "staging"],
        "verification_status": "nieweryfikowany",
        "verified_by": None,
        "verified_at": None,
        "notes": "TPN source-record measurement imported into staging; not field-verified.",
        "created_at": generated_at,
        "created_by": DEFAULT_IMPORT_AUTHOR,
    }


def _tpn_object_external_ref(globalid: str) -> dict[str, Any]:
    return {
        "system": "TPN",
        "ref_type": "source_globalid",
        "external_id": globalid,
        "scope": "object",
        "notes": "TPN GLOBALID belongs to the object/source feature.",
    }


def _tpn_cave_external_refs(row: dict[str, str]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    nr_inwent = _clean_value(row.get("NR_INWENT"))
    if nr_inwent:
        refs.append(
            {
                "system": "NR_INWENT",
                "ref_type": "inventory_number",
                "external_id": nr_inwent,
                "scope": "cave",
                "notes": "Inventory number belongs to the cave/catalog entry, not the object.",
            }
        )
    return refs


def _tpn_cave_notes(row: dict[str, str]) -> str | None:
    parts: list[str] = []
    for label, column in (
        ("TPN length", "DLUGOSC"),
        ("TPN depth", "GLEBOKOSC"),
        ("TPN denivelation", "DENIWELACJ"),
        ("TPN verification/location note", "WER_LOK"),
        ("TPN notes", "UWAGI"),
    ):
        value = _clean_value(row.get(column))
        if value:
            parts.append(f"{label}: {value}")
    return "\n".join(parts) if parts else None


def _tpn_object_notes(row: dict[str, str]) -> str:
    otwor = _clean_value(row.get("OTWÓR"))
    note = "Staging proposal from TPN; requires operator review before final YAML."
    if otwor:
        note += f"\nTPN opening: {otwor}"
    return note


def _load_existing_candidates(data_dir: Path) -> tuple[_Candidate, ...]:
    dataset = load_dataset(data_dir)
    caves_by_id = {_clean_value(record.data.get("id")): record.data for record in dataset.caves}
    cave_id_by_object_id: dict[str, str] = {}
    for cave_id, cave in caves_by_id.items():
        for object_id in cave.get("object_ids", []):
            if isinstance(object_id, str):
                cave_id_by_object_id.setdefault(object_id, cave_id)

    candidates: list[_Candidate] = []
    for record in dataset.objects:
        data = record.data
        object_id = _clean_value(data.get("id"))
        if not object_id:
            continue
        cave_id = _clean_value(data.get("cave_id")) or cave_id_by_object_id.get(object_id)
        cave = caves_by_id.get(cave_id or "")
        measurement = _candidate_measurement(data)
        candidates.append(
            _Candidate(
                source="data_yaml",
                cave_id=cave_id,
                object_id=object_id,
                nr_inwent=_first_external_ref_id(cave, system="NR_INWENT"),
                name=_clean_value(data.get("name_local"))
                or _clean_value(cave.get("name") if cave else ""),
                x_1992=_parse_decimal(measurement.get("x_1992") if measurement else None),
                y_1992=_parse_decimal(measurement.get("y_1992") if measurement else None),
                globalids=tuple(_external_ref_ids(data, system="TPN")),
                next_measurement_id=_next_measurement_id(data.get("measurements", [])),
            )
        )

    return tuple(candidates)


def _load_pig_staging_candidates(pig_staging_path: Path | None) -> tuple[_Candidate, ...]:
    if pig_staging_path is None or not pig_staging_path.exists():
        return ()

    data = json.loads(pig_staging_path.read_text(encoding="utf-8"))
    rows_by_object_id = {
        _clean_value(row.get("object_id")): row
        for row in data.get("rows", [])
        if _clean_value(row.get("object_id"))
    }
    candidates: list[_Candidate] = []
    for proposed_object in data.get("proposed_objects", []):
        object_id = _clean_value(proposed_object.get("id"))
        row = rows_by_object_id.get(object_id)
        if not object_id or row is None:
            continue
        measurement = _candidate_measurement(proposed_object)
        candidates.append(
            _Candidate(
                source="pig_staging",
                cave_id=_clean_value(row.get("cave_id")) or None,
                object_id=object_id,
                nr_inwent=_clean_value(row.get("nr_inwent")) or None,
                name=_clean_value(row.get("name"))
                or _clean_value(proposed_object.get("name_local")),
                x_1992=_parse_decimal(measurement.get("x_1992") if measurement else None),
                y_1992=_parse_decimal(measurement.get("y_1992") if measurement else None),
                globalids=tuple(_external_ref_ids(proposed_object, system="TPN")),
                next_measurement_id=_next_measurement_id(proposed_object.get("measurements", [])),
            )
        )
    return tuple(candidates)


def _candidate_measurement(data: dict[str, Any]) -> dict[str, Any] | None:
    measurements = data.get("measurements")
    if not isinstance(measurements, list):
        return None

    best_measurement = data.get("best_measurement")
    best_measurement_id = (
        best_measurement.get("measurement_id") if isinstance(best_measurement, dict) else None
    )
    if best_measurement_id:
        for measurement in measurements:
            if isinstance(measurement, dict) and measurement.get("id") == best_measurement_id:
                return measurement

    for measurement in measurements:
        if isinstance(measurement, dict):
            return measurement
    return None


def _external_ref_ids(data: dict[str, Any] | None, *, system: str) -> list[str]:
    if not isinstance(data, dict):
        return []
    refs = data.get("external_refs")
    if not isinstance(refs, list):
        return []
    return [
        _clean_value(ref.get("external_id"))
        for ref in refs
        if isinstance(ref, dict)
        and ref.get("system") == system
        and _clean_value(ref.get("external_id"))
    ]


def _first_external_ref_id(data: dict[str, Any] | None, *, system: str) -> str | None:
    refs = _external_ref_ids(data, system=system)
    return refs[0] if refs else None


def _source_nr_counts(rows: tuple[dict[str, str], ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        nr_inwent = _clean_value(row.get("NR_INWENT"))
        if nr_inwent:
            counts[nr_inwent] = counts.get(nr_inwent, 0) + 1
    return counts


def _seed_cave_number(data_dir: Path, candidates: tuple[_Candidate, ...]) -> int:
    cave_number = _max_existing_cave_number(data_dir / "caves")
    for candidate in candidates:
        if candidate.cave_id:
            cave_number = max(cave_number, _parse_prefixed_number(candidate.cave_id, prefix="C"))
    return cave_number


def _seed_object_numbers(
    data_dir: Path,
    candidates: tuple[_Candidate, ...],
) -> dict[str, int]:
    numbers: dict[str, int] = {}
    for candidate in candidates:
        parsed = _parse_object_id(candidate.object_id)
        if parsed is None:
            continue
        prefix, number = parsed
        numbers[prefix] = max(
            numbers.get(prefix, 0),
            _max_existing_object_number(data_dir / "objects", prefix),
            number,
        )
    return numbers


def _report_to_json_data(report: TpnStagingReport) -> dict[str, Any]:
    counts = _status_counts(report.rows)
    return {
        "generated_at": report.generated_at,
        "source_path": str(report.source_path),
        "record_count": report.record_count,
        "matched_count": counts["matched"],
        "new_count": counts["new"],
        "unresolved_count": counts["unresolved"],
        "rejected_count": counts["rejected"],
        "issue_count": len(report.issues),
        "rows": [
            {
                "record_number": row.record_number,
                "globalid": row.globalid,
                "nr_inwent": row.nr_inwent,
                "name": row.name,
                "status": row.status,
                "cave_id": row.cave_id,
                "object_id": row.object_id,
                "match_strategy": row.match_strategy,
                "distance_m": row.distance_m,
            }
            for row in report.rows
        ],
        "issues": [
            {
                "code": issue.code,
                "severity": issue.severity,
                "record_number": issue.record_number,
                "globalid": issue.globalid,
                "nr_inwent": issue.nr_inwent,
                "description": issue.description,
            }
            for issue in report.issues
        ],
        "matched_measurements": list(report.matched_measurements),
        "proposed_caves": list(report.proposed_caves),
        "proposed_objects": list(report.proposed_objects),
    }


def _row_summary(
    *,
    record_number: int,
    globalid: str,
    nr_inwent: str,
    name: str,
    status: str,
    cave_id: str | None = None,
    object_id: str | None = None,
    match_strategy: str | None = None,
    distance_m: float | None = None,
) -> TpnStagingRow:
    return TpnStagingRow(
        record_number=record_number,
        globalid=globalid,
        nr_inwent=nr_inwent,
        name=name,
        status=status,
        cave_id=cave_id,
        object_id=object_id,
        match_strategy=match_strategy,
        distance_m=distance_m,
    )


def _status_counts(rows: tuple[TpnStagingRow, ...]) -> dict[str, int]:
    counts = {"matched": 0, "new": 0, "unresolved": 0, "rejected": 0}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    return counts


def _candidate_distance_m(candidate: _Candidate, point: TpnPoint) -> float | None:
    if candidate.x_1992 is None or candidate.y_1992 is None:
        return None
    return hypot(candidate.x_1992 - point.x_1992, candidate.y_1992 - point.y_1992)


def _names_equal(left: str, right: str) -> bool:
    return bool(_normalize_name(left)) and _normalize_name(left) == _normalize_name(right)


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", _clean_value(value).lower())
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def _parse_source_date(row: dict[str, str]) -> str | None:
    for column in ("LAST_EDI_1", "CREATED_DA"):
        parsed = _parse_date(_clean_value(row.get(column)))
        if parsed is not None:
            return parsed
    return None


def _parse_date(raw_value: str) -> str | None:
    text = _clean_value(raw_value)
    if not text:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _date_part(timestamp: str) -> str:
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(UTC).date().isoformat()
    return parsed.date().isoformat()


def _next_measurement_id(measurements: Any) -> str:
    max_number = 0
    if isinstance(measurements, list):
        for measurement in measurements:
            if not isinstance(measurement, dict):
                continue
            match = re.fullmatch(r"m-(\d+)", _clean_value(measurement.get("id")))
            if match:
                max_number = max(max_number, int(match.group(1)))
    return f"m-{max_number + 1:03d}"


def _max_existing_cave_number(caves_dir: Path) -> int:
    return _max_existing_number(caves_dir, prefix="C")


def _max_existing_object_number(objects_dir: Path, prefix: str) -> int:
    return _max_existing_number(objects_dir / prefix, prefix=prefix)


def _max_existing_number(directory: Path, *, prefix: str) -> int:
    if not directory.exists():
        return 0

    max_number = 0
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)\.ya?ml$")
    for path in directory.iterdir():
        match = pattern.match(path.name)
        if match:
            max_number = max(max_number, int(match.group(1)))
    return max_number


def _parse_object_id(object_id: str) -> tuple[str, int] | None:
    match = re.fullmatch(r"([A-Z]{2,3})-(\d+)", _clean_value(object_id))
    if not match:
        return None
    return match.group(1), int(match.group(2))


def _parse_prefixed_number(value: str, *, prefix: str) -> int:
    match = re.fullmatch(rf"{re.escape(prefix)}-(\d+)", _clean_value(value))
    return int(match.group(1)) if match else 0


def _parse_decimal(raw_value: Any) -> float | None:
    text = _clean_value(raw_value)
    if text == "":
        return None

    text = text.replace("\u00a0", " ").replace(" ", "")
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _clean_value(raw_value: Any) -> str:
    if raw_value is None:
        return ""
    return str(raw_value).strip()


def _markdown_code_or_dash(value: str | None) -> str:
    if not value:
        return "-"
    return f"`{_markdown_text(value)}`"


def _markdown_text(value: str) -> str:
    text = _clean_value(value)
    if not text:
        return "-"
    return text.replace("|", "\\|").replace("\n", "<br>")
