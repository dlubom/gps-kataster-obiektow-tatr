"""Build reviewable staging proposals from the PIG source export."""

from __future__ import annotations

import csv
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from xml.etree import ElementTree

from gps_kataster_obiektow_tatr.coordinates import (
    DEFAULT_CONSISTENCY_TOLERANCE_M,
    coordinate_consistency_error_m,
)
from gps_kataster_obiektow_tatr.data_loader import DEFAULT_DATA_DIR
from gps_kataster_obiektow_tatr.prefix_resolver import (
    PrefixResolution,
    PrefixResolutionStatus,
    default_prefix_resolver,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_PIG_SOURCE = REPO_ROOT / "pig_otwory_jaskin_.xlsx.-.Export.csv"
DEFAULT_PIG_STAGING_DIR = REPO_ROOT / "build" / "staging" / "pig"
DEFAULT_IMPORT_AUTHOR = "importer:pig"
DEFAULT_XLSX_SHEET_NAME = "Export"

_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS = {"main": _MAIN_NS, "rel": _REL_NS}


@dataclass(frozen=True, slots=True)
class SourceTable:
    """A rectangular source table loaded from CSV or XLSX."""

    columns: tuple[str, ...]
    rows: tuple[dict[str, str], ...]


@dataclass(frozen=True, slots=True)
class PigPoint:
    """Parsed point fields from one PIG row."""

    lat: float
    lon: float
    x_1992: float
    y_1992: float
    elevation_m: float | None
    observed_date: str
    source_date: str | None


@dataclass(frozen=True, slots=True)
class PigStagingIssue:
    """A non-fatal importer finding for operator review."""

    code: str
    severity: str
    record_number: int | None
    pig_id: str | None
    description: str


@dataclass(frozen=True, slots=True)
class PigStagingRow:
    """Compact per-row summary used by the Markdown staging report."""

    record_number: int
    pig_id: str
    nr_inwent: str
    name: str
    cave_id: str
    object_id: str | None
    status: str


@dataclass(frozen=True, slots=True)
class PigStagingReport:
    """Complete PIG staging import result."""

    source_path: Path
    generated_at: str
    record_count: int
    proposed_caves: tuple[dict[str, Any], ...]
    proposed_objects: tuple[dict[str, Any], ...]
    rows: tuple[PigStagingRow, ...]
    issues: tuple[PigStagingIssue, ...]


class PrefixResolverLike(Protocol):
    """Minimal prefix resolver interface used by the staging importer."""

    def resolve(self, *, lat: float, lon: float) -> PrefixResolution:
        """Resolve a WGS84 coordinate to a staging object prefix."""


def build_pig_staging(
    source_path: Path = DEFAULT_PIG_SOURCE,
    *,
    generated_at: str,
    data_dir: Path = DEFAULT_DATA_DIR,
    prefix_resolver: PrefixResolverLike | None = None,
) -> PigStagingReport:
    """Build PIG cave/object proposals without writing final YAML."""

    table = read_source_table(source_path)
    resolver = prefix_resolver or default_prefix_resolver()
    cave_number = _max_existing_cave_number(data_dir / "caves")
    object_numbers: dict[str, int] = {}
    proposed_caves: list[dict[str, Any]] = []
    proposed_objects: list[dict[str, Any]] = []
    staging_rows: list[PigStagingRow] = []
    issues: list[PigStagingIssue] = []

    for record_number, row in enumerate(table.rows, start=1):
        cave_number += 1
        cave_id = f"C-{cave_number:04d}"
        pig_id = _clean_value(row.get("ID"))
        nr_inwent = _clean_value(row.get("Nr inw."))
        name = _clean_value(row.get("Nazwa")) or f"PIG row {record_number}"
        link = _clean_value(row.get("Link"))

        cave = _build_cave_proposal(
            row=row,
            cave_id=cave_id,
            name=name,
            generated_at=generated_at,
        )
        point = _parse_pig_point(
            row,
            record_number=record_number,
            pig_id=pig_id,
            generated_at=generated_at,
            issues=issues,
        )

        object_id: str | None = None
        if point is not None:
            object_id = _try_build_object_proposal(
                point=point,
                record_number=record_number,
                pig_id=pig_id,
                data_dir=data_dir,
                object_numbers=object_numbers,
                resolver=resolver,
                issues=issues,
            )
            if object_id is not None:
                cave["object_ids"] = [object_id]
                proposed_objects.append(
                    _build_object_proposal(
                        object_id=object_id,
                        cave_id=cave_id,
                        name=name,
                        point=point,
                        pig_id=pig_id,
                        link=link,
                        generated_at=generated_at,
                    )
                )

        proposed_caves.append(cave)
        staging_rows.append(
            PigStagingRow(
                record_number=record_number,
                pig_id=pig_id,
                nr_inwent=nr_inwent,
                name=name,
                cave_id=cave_id,
                object_id=object_id,
                status="object_proposed" if object_id is not None else "cave_only",
            )
        )

    return PigStagingReport(
        source_path=source_path,
        generated_at=generated_at,
        record_count=len(table.rows),
        proposed_caves=tuple(proposed_caves),
        proposed_objects=tuple(proposed_objects),
        rows=tuple(staging_rows),
        issues=tuple(issues),
    )


def read_source_table(path: Path, *, sheet_name: str = DEFAULT_XLSX_SHEET_NAME) -> SourceTable:
    """Read a PIG source table from CSV or XLSX."""

    if path.suffix.lower() == ".xlsx":
        return _read_xlsx_table(path, sheet_name=sheet_name)
    return _read_csv_table(path)


def write_staging_files(report: PigStagingReport, *, output_dir: Path) -> tuple[Path, Path]:
    """Write machine-readable and human-readable PIG staging reports."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "pig-staging.json"
    markdown_path = output_dir / "pig-staging.md"

    json_path.write_text(
        json.dumps(_report_to_json_data(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown_report(report), encoding="utf-8")

    return json_path, markdown_path


def render_markdown_report(report: PigStagingReport) -> str:
    """Render a concise Markdown summary of the staging import."""

    lines = [
        "# PIG Staging Import",
        "",
        f"Generated: `{report.generated_at}`",
        f"Source: `{report.source_path}`",
        "",
        "Scope: staging proposals only. This report does not write final YAML under `data/`.",
        "",
        "## Summary",
        "",
        "| Records | Proposed caves | Proposed objects | Cave-only rows | Issues |",
        "|---:|---:|---:|---:|---:|",
        (
            f"| {report.record_count} | {len(report.proposed_caves)} | "
            f"{len(report.proposed_objects)} | "
            f"{report.record_count - len(report.proposed_objects)} | {len(report.issues)} |"
        ),
        "",
        "## Mapping Rules",
        "",
        "- PIG `ID`, PIG `Link` and `Nr inw.` stay on `Jaskinia.external_refs`.",
        "- PIG measurements use `source: PIG` and `verification_status: nieweryfikowany`.",
        "- Proposed objects are staging candidates and require operator review before final YAML.",
        "",
        "## Rows",
        "",
        "| Row | Cave | Object | PIG ID | Nr inw. | Name | Status |",
        "|---:|---|---|---|---|---|---|",
    ]

    for row in report.rows:
        lines.append(
            "| "
            f"{row.record_number} | "
            f"`{row.cave_id}` | "
            f"{_markdown_code_or_dash(row.object_id)} | "
            f"{_markdown_text(row.pig_id)} | "
            f"{_markdown_text(row.nr_inwent)} | "
            f"{_markdown_text(row.name)} | "
            f"`{row.status}` |"
        )

    if report.issues:
        lines.extend(
            [
                "",
                "## Issues",
                "",
                "| Severity | Code | Row | PIG ID | Description |",
                "|---|---|---:|---|---|",
            ]
        )
        for issue in report.issues:
            lines.append(
                "| "
                f"`{issue.severity}` | "
                f"`{issue.code}` | "
                f"{issue.record_number or '-'} | "
                f"{_markdown_text(issue.pig_id or '')} | "
                f"{_markdown_text(issue.description)} |"
            )

    return "\n".join(lines) + "\n"


def _build_cave_proposal(
    *,
    row: dict[str, str],
    cave_id: str,
    name: str,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": cave_id,
        "name": name,
        "system_name": None,
        "external_refs": _pig_cave_external_refs(row),
        "object_ids": [],
        "notes": _pig_cave_notes(row),
        "created_at": generated_at,
        "created_by": DEFAULT_IMPORT_AUTHOR,
        "updated_at": generated_at,
        "updated_by": DEFAULT_IMPORT_AUTHOR,
    }


def _try_build_object_proposal(
    *,
    point: PigPoint,
    record_number: int,
    pig_id: str,
    data_dir: Path,
    object_numbers: dict[str, int],
    resolver: PrefixResolverLike,
    issues: list[PigStagingIssue],
) -> str | None:
    coordinate_error = coordinate_consistency_error_m(
        lat=point.lat,
        lon=point.lon,
        x_1992=point.x_1992,
        y_1992=point.y_1992,
    )
    if coordinate_error > DEFAULT_CONSISTENCY_TOLERANCE_M:
        issues.append(
            PigStagingIssue(
                code="PIG_COORDINATE_MISMATCH",
                severity="warning",
                record_number=record_number,
                pig_id=pig_id or None,
                description=(
                    "PIG WGS84 and PL-1992 coordinates differ by "
                    f"{coordinate_error:.2f} m; object proposal skipped."
                ),
            )
        )
        return None

    resolution = resolver.resolve(lat=point.lat, lon=point.lon)
    if resolution.status == PrefixResolutionStatus.ERROR or resolution.prefix is None:
        issues.append(
            PigStagingIssue(
                code=resolution.code or "PIG_PREFIX_RESOLUTION_ERROR",
                severity="warning",
                record_number=record_number,
                pig_id=pig_id or None,
                description=(resolution.message or "Prefix resolution failed.")
                + " Object proposal skipped.",
            )
        )
        return None

    if resolution.status == PrefixResolutionStatus.WARNING:
        issues.append(
            PigStagingIssue(
                code=resolution.code or "PIG_PREFIX_RESOLUTION_WARNING",
                severity="warning",
                record_number=record_number,
                pig_id=pig_id or None,
                description=(resolution.message or "Prefix resolution requires review."),
            )
        )

    prefix = resolution.prefix
    object_numbers.setdefault(prefix, _max_existing_object_number(data_dir / "objects", prefix))
    object_numbers[prefix] += 1
    return f"{prefix}-{object_numbers[prefix]:04d}"


def _build_object_proposal(
    *,
    object_id: str,
    cave_id: str,
    name: str,
    point: PigPoint,
    pig_id: str,
    link: str,
    generated_at: str,
) -> dict[str, Any]:
    prefix = object_id.split("-", maxsplit=1)[0]
    measurement = _build_pig_measurement(
        point=point,
        pig_id=pig_id,
        link=link,
        generated_at=generated_at,
    )
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
        "external_refs": [],
        "measurements": [measurement],
        "best_measurement": {
            "mode": "auto",
            "measurement_id": "m-001",
            "reason": None,
            "updated_at": generated_at,
            "updated_by": DEFAULT_IMPORT_AUTHOR,
        },
        "attachments": [],
        "notes": "Staging proposal from PIG; requires operator review before final YAML.",
        "created_at": generated_at,
        "created_by": DEFAULT_IMPORT_AUTHOR,
        "updated_at": generated_at,
        "updated_by": DEFAULT_IMPORT_AUTHOR,
    }


def _build_pig_measurement(
    *,
    point: PigPoint,
    pig_id: str,
    link: str,
    generated_at: str,
) -> dict[str, Any]:
    notes = "PIG source-record measurement imported into staging; not field-verified."
    if link:
        notes += f" Source: {link}"

    return {
        "id": "m-001",
        "lat": point.lat,
        "lon": point.lon,
        "x_1992": point.x_1992,
        "y_1992": point.y_1992,
        "elevation_m": point.elevation_m,
        "elevation_datum": "unknown",
        "elevation_source": "source_record",
        "horizontal_accuracy_m": None,
        "vertical_accuracy_m": None,
        "source": "PIG",
        "source_ref": f"PIG:{pig_id}" if pig_id else None,
        "observed_date": point.observed_date,
        "source_date": point.source_date,
        "method": "source_record",
        "device": None,
        "tags": ["pig", "staging"],
        "verification_status": "nieweryfikowany",
        "verified_by": None,
        "verified_at": None,
        "notes": notes,
        "created_at": generated_at,
        "created_by": DEFAULT_IMPORT_AUTHOR,
    }


def _parse_pig_point(
    row: dict[str, str],
    *,
    record_number: int,
    pig_id: str,
    generated_at: str,
    issues: list[PigStagingIssue],
) -> PigPoint | None:
    lat = _parse_decimal(row.get("B"))
    lon = _parse_decimal(row.get("L"))
    x_1992 = _parse_decimal(row.get("X 1992"))
    y_1992 = _parse_decimal(row.get("Y 1992"))

    if lat is None or lon is None or x_1992 is None or y_1992 is None:
        issues.append(
            PigStagingIssue(
                code="PIG_POINT_COORDINATES_INVALID",
                severity="warning",
                record_number=record_number,
                pig_id=pig_id or None,
                description="Missing or invalid coordinate fields; object proposal skipped.",
            )
        )
        return None

    source_date = _parse_source_year_date(row.get("Stan na rok"))
    if source_date is None:
        source_date = _date_part(generated_at)
        issues.append(
            PigStagingIssue(
                code="PIG_SOURCE_YEAR_INVALID",
                severity="warning",
                record_number=record_number,
                pig_id=pig_id or None,
                description="Missing or invalid 'Stan na rok'; generated date used.",
            )
        )

    return PigPoint(
        lat=lat,
        lon=lon,
        x_1992=x_1992,
        y_1992=y_1992,
        elevation_m=_parse_decimal(row.get("H (wg PIG)")),
        observed_date=source_date,
        source_date=source_date,
    )


def _pig_cave_external_refs(row: dict[str, str]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    nr_inwent = _clean_value(row.get("Nr inw."))
    pig_id = _clean_value(row.get("ID"))
    link = _clean_value(row.get("Link"))

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

    if pig_id:
        ref: dict[str, Any] = {
            "system": "PIG",
            "ref_type": "catalog_id",
            "external_id": pig_id,
            "scope": "cave",
            "notes": "PIG catalog record identifier.",
        }
        if link:
            ref["url"] = link
        refs.append(ref)

    if link:
        refs.append(
            {
                "system": "PIG",
                "ref_type": "url",
                "external_id": link,
                "url": link,
                "scope": "cave",
                "notes": "PIG catalog record link.",
            }
        )

    return refs


def _pig_cave_notes(row: dict[str, str]) -> str | None:
    parts: list[str] = []
    aliases = _clean_value(row.get("Inne nazwy"))
    sector = _clean_value(row.get("Sektor (nazwa)"))
    source_year = _clean_value(row.get("Stan na rok"))
    morphometry = _format_morphometry(row)

    if aliases:
        parts.append(f"PIG aliases: {aliases}")
    if sector:
        parts.append(f"PIG sector: {sector}")
    if morphometry:
        parts.append(morphometry)
    if source_year:
        parts.append(f"PIG source state year: {source_year}")

    return "\n".join(parts) if parts else None


def _format_morphometry(row: dict[str, str]) -> str | None:
    values = {
        "length_m": _clean_value(row.get("Długość [m]")),
        "depth_m": _clean_value(row.get("Głębokość [m]")),
        "denivelation_m": _clean_value(row.get("Deniwelacja [m]")),
    }
    present = {key: value for key, value in values.items() if value}
    if not present:
        return None
    return "PIG morphometry: " + ", ".join(f"{key}={value}" for key, value in present.items())


def _read_csv_table(path: Path) -> SourceTable:
    with path.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        columns = tuple(reader.fieldnames or ())
        rows = tuple(
            {key: _clean_value(value) for key, value in row.items() if key is not None}
            for row in reader
        )
    return SourceTable(columns=columns, rows=rows)


def _read_xlsx_table(path: Path, *, sheet_name: str) -> SourceTable:
    with zipfile.ZipFile(path) as workbook:
        shared_strings = _read_shared_strings(workbook)
        sheet_path = _resolve_sheet_path(workbook, sheet_name=sheet_name)
        root = ElementTree.fromstring(workbook.read(sheet_path))

    raw_rows: list[list[str]] = []
    for row_element in root.findall(".//main:sheetData/main:row", _NS):
        values_by_index: dict[int, str] = {}
        for position, cell in enumerate(row_element.findall("main:c", _NS)):
            cell_ref = cell.attrib.get("r")
            column_index = _column_index_from_cell_ref(cell_ref) if cell_ref else position
            values_by_index[column_index] = _xlsx_cell_text(cell, shared_strings)
        if values_by_index:
            max_index = max(values_by_index)
            raw_rows.append([values_by_index.get(index, "") for index in range(max_index + 1)])

    if not raw_rows:
        return SourceTable(columns=(), rows=())

    columns = tuple(_clean_value(value) for value in raw_rows[0])
    rows = []
    for raw_row in raw_rows[1:]:
        row = {
            column: _clean_value(raw_row[index]) if index < len(raw_row) else ""
            for index, column in enumerate(columns)
            if column
        }
        if any(value for value in row.values()):
            rows.append(row)

    return SourceTable(columns=columns, rows=tuple(rows))


def _read_shared_strings(workbook: zipfile.ZipFile) -> tuple[str, ...]:
    try:
        root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
    except KeyError:
        return ()

    values: list[str] = []
    for item in root.findall("main:si", _NS):
        values.append("".join(text.text or "" for text in item.findall(".//main:t", _NS)))
    return tuple(values)


def _resolve_sheet_path(workbook: zipfile.ZipFile, *, sheet_name: str) -> str:
    workbook_root = ElementTree.fromstring(workbook.read("xl/workbook.xml"))
    relationships = _read_workbook_relationships(workbook)
    selected_rel_id: str | None = None
    fallback_rel_id: str | None = None

    for sheet in workbook_root.findall(".//main:sheets/main:sheet", _NS):
        rel_id = sheet.attrib.get(f"{{{_REL_NS}}}id")
        if fallback_rel_id is None:
            fallback_rel_id = rel_id
        if sheet.attrib.get("name") == sheet_name:
            selected_rel_id = rel_id
            break

    rel_id = selected_rel_id or fallback_rel_id
    if rel_id is None or rel_id not in relationships:
        raise ValueError(f"XLSX workbook has no readable sheet named {sheet_name!r}.")

    target = relationships[rel_id]
    if target.startswith("/"):
        return target.lstrip("/")
    if target.startswith("xl/"):
        return target
    return f"xl/{target}"


def _read_workbook_relationships(workbook: zipfile.ZipFile) -> dict[str, str]:
    root = ElementTree.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    relationships: dict[str, str] = {}
    for relationship in root.findall(f"{{{_PACKAGE_REL_NS}}}Relationship"):
        rel_id = relationship.attrib.get("Id")
        target = relationship.attrib.get("Target")
        if rel_id and target:
            relationships[rel_id] = target
    return relationships


def _xlsx_cell_text(cell: ElementTree.Element, shared_strings: tuple[str, ...]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//main:t", _NS))

    value = cell.find("main:v", _NS)
    if value is None or value.text is None:
        return ""

    if cell_type == "s":
        index = int(value.text)
        return shared_strings[index] if index < len(shared_strings) else ""
    return value.text


def _column_index_from_cell_ref(cell_ref: str | None) -> int:
    if not cell_ref:
        return 0
    letters = re.match(r"^[A-Z]+", cell_ref)
    if not letters:
        return 0

    index = 0
    for char in letters.group(0):
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def _report_to_json_data(report: PigStagingReport) -> dict[str, Any]:
    return {
        "generated_at": report.generated_at,
        "source_path": str(report.source_path),
        "record_count": report.record_count,
        "proposed_cave_count": len(report.proposed_caves),
        "proposed_object_count": len(report.proposed_objects),
        "cave_only_count": report.record_count - len(report.proposed_objects),
        "issue_count": len(report.issues),
        "rows": [
            {
                "record_number": row.record_number,
                "pig_id": row.pig_id,
                "nr_inwent": row.nr_inwent,
                "name": row.name,
                "cave_id": row.cave_id,
                "object_id": row.object_id,
                "status": row.status,
            }
            for row in report.rows
        ],
        "issues": [
            {
                "code": issue.code,
                "severity": issue.severity,
                "record_number": issue.record_number,
                "pig_id": issue.pig_id,
                "description": issue.description,
            }
            for issue in report.issues
        ],
        "proposed_caves": list(report.proposed_caves),
        "proposed_objects": list(report.proposed_objects),
    }


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


def _parse_source_year_date(raw_value: str | None) -> str | None:
    text = _clean_value(raw_value)
    if not re.fullmatch(r"\d{4}", text):
        return None
    return f"{int(text):04d}-12-31"


def _date_part(timestamp: str) -> str:
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(UTC).date().isoformat()
    return parsed.date().isoformat()


def _parse_decimal(raw_value: str | None) -> float | None:
    text = _clean_value(raw_value)
    if text == "":
        return None

    text = text.replace("\u00a0", " ").replace(" ", "")
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _clean_value(raw_value: str | None) -> str:
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
