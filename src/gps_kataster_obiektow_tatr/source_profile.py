"""Profile source CSV exports before staging imports."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

MAX_DUPLICATE_EXAMPLES = 10
MAX_DUPLICATE_ROW_NUMBERS = 20


@dataclass(frozen=True, slots=True)
class SourceProfileSpec:
    """Configuration describing one external source export."""

    source: str
    key_columns: tuple[str, ...]
    duplicate_columns: tuple[str, ...]
    coordinate_columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DuplicateValueProfile:
    """One duplicate value and its source record numbers."""

    value: str
    count: int
    row_numbers: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class DuplicateColumnProfile:
    """Duplicate summary for a source column."""

    column: str
    duplicate_group_count: int
    duplicated_record_count: int
    duplicate_extra_record_count: int
    examples: tuple[DuplicateValueProfile, ...]


@dataclass(frozen=True, slots=True)
class NumericColumnProfile:
    """Numeric range summary for a coordinate-like source column."""

    column: str
    numeric_count: int
    missing_count: int
    non_numeric_count: int
    minimum: float | None
    maximum: float | None


@dataclass(frozen=True, slots=True)
class SourceCsvProfile:
    """Profile of one CSV source export."""

    source: str
    path: Path
    record_count: int
    column_count: int
    columns: tuple[str, ...]
    missing_columns: tuple[str, ...]
    key_missing_counts: dict[str, int]
    duplicates: dict[str, DuplicateColumnProfile]
    coordinate_ranges: dict[str, NumericColumnProfile]


@dataclass(frozen=True, slots=True)
class SourceProfileReport:
    """Combined source profile report."""

    profiles: tuple[SourceCsvProfile, ...]


PIG_PROFILE_SPEC = SourceProfileSpec(
    source="PIG",
    key_columns=("ID", "Nazwa", "Nr inw.", "X 1992", "Y 1992", "B", "L", "Link"),
    duplicate_columns=("ID", "Nr inw."),
    coordinate_columns=("X 1992", "Y 1992", "B", "L", "H (wg PIG)"),
)

TPN_PROFILE_SPEC = SourceProfileSpec(
    source="TPN",
    key_columns=("GLOBALID", "NR_INWENT", "NAZWA", "X1992", "Y1992", "Z"),
    duplicate_columns=("GLOBALID", "NR_INWENT"),
    coordinate_columns=("X1992", "Y1992", "Z"),
)


def profile_csv_source(path: Path, spec: SourceProfileSpec) -> SourceCsvProfile:
    """Read and profile one CSV source export."""

    columns, rows = _read_csv(path)
    relevant_columns = (*spec.key_columns, *spec.duplicate_columns, *spec.coordinate_columns)
    missing_columns = tuple(
        dict.fromkeys(column for column in relevant_columns if column not in columns)
    )

    return SourceCsvProfile(
        source=spec.source,
        path=path,
        record_count=len(rows),
        column_count=len(columns),
        columns=columns,
        missing_columns=missing_columns,
        key_missing_counts=_profile_key_missing_counts(rows, spec.key_columns),
        duplicates={column: _profile_duplicates(rows, column) for column in spec.duplicate_columns},
        coordinate_ranges={
            column: _profile_numeric_column(rows, column) for column in spec.coordinate_columns
        },
    )


def profile_sources(
    *,
    pig_csv: Path,
    tpn_csv: Path,
) -> SourceProfileReport:
    """Profile the V1 PIG and TPN CSV exports."""

    return SourceProfileReport(
        profiles=(
            profile_csv_source(pig_csv, PIG_PROFILE_SPEC),
            profile_csv_source(tpn_csv, TPN_PROFILE_SPEC),
        )
    )


def write_report_files(
    report: SourceProfileReport,
    *,
    output_dir: Path,
    generated_at: str,
) -> tuple[Path, Path]:
    """Write machine-readable and human-readable source profile reports."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "source-profile.json"
    markdown_path = output_dir / "source-profile.md"

    json_path.write_text(
        json.dumps(
            _report_to_json_data(report, generated_at=generated_at), ensure_ascii=False, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_markdown_report(report, generated_at=generated_at), encoding="utf-8"
    )

    return json_path, markdown_path


def render_markdown_report(report: SourceProfileReport, *, generated_at: str) -> str:
    """Render the source profile as a Markdown report."""

    lines = [
        "# Source Profile",
        "",
        f"Generated: `{generated_at}`",
        "",
        "Scope: PIG and TPN CSV exports only. This report does not create final YAML.",
        "",
        "## Summary",
        "",
        "| Source | File | Records | Columns | Missing expected columns |",
        "|---|---:|---:|---:|---:|",
    ]

    for profile in report.profiles:
        lines.append(
            "| "
            f"{profile.source} | "
            f"`{profile.path}` | "
            f"{profile.record_count} | "
            f"{profile.column_count} | "
            f"{len(profile.missing_columns)} |"
        )

    for profile in report.profiles:
        lines.extend(_render_profile_markdown(profile))

    return "\n".join(lines) + "\n"


def _render_profile_markdown(profile: SourceCsvProfile) -> list[str]:
    lines = [
        "",
        f"## {profile.source}",
        "",
        "Columns:",
        "",
        ", ".join(f"`{column}`" for column in profile.columns),
    ]

    if profile.missing_columns:
        lines.extend(
            [
                "",
                "Missing expected columns:",
                "",
                ", ".join(f"`{column}`" for column in profile.missing_columns),
            ]
        )

    lines.extend(
        [
            "",
            "### Key Missing Values",
            "",
            "| Column | Missing records |",
            "|---|---:|",
        ]
    )
    for column, count in profile.key_missing_counts.items():
        lines.append(f"| `{column}` | {count} |")

    lines.extend(
        [
            "",
            "### Duplicates",
            "",
            (
                "| Column | Duplicate groups | Records in duplicate groups | "
                "Extra records | Examples |"
            ),
            "|---|---:|---:|---:|---|",
        ]
    )
    for duplicate in profile.duplicates.values():
        examples = "; ".join(_format_duplicate_example(example) for example in duplicate.examples)
        lines.append(
            "| "
            f"`{duplicate.column}` | "
            f"{duplicate.duplicate_group_count} | "
            f"{duplicate.duplicated_record_count} | "
            f"{duplicate.duplicate_extra_record_count} | "
            f"{examples or '-'} |"
        )

    lines.extend(
        [
            "",
            "### Coordinate Ranges",
            "",
            "| Column | Numeric | Missing | Non-numeric | Min | Max |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for numeric in profile.coordinate_ranges.values():
        lines.append(
            "| "
            f"`{numeric.column}` | "
            f"{numeric.numeric_count} | "
            f"{numeric.missing_count} | "
            f"{numeric.non_numeric_count} | "
            f"{_format_number(numeric.minimum)} | "
            f"{_format_number(numeric.maximum)} |"
        )

    return lines


def _report_to_json_data(report: SourceProfileReport, *, generated_at: str) -> dict[str, object]:
    return {
        "generated_at": generated_at,
        "profiles": [_profile_to_json_data(profile) for profile in report.profiles],
    }


def _profile_to_json_data(profile: SourceCsvProfile) -> dict[str, object]:
    return {
        "source": profile.source,
        "path": str(profile.path),
        "record_count": profile.record_count,
        "column_count": profile.column_count,
        "columns": list(profile.columns),
        "missing_columns": list(profile.missing_columns),
        "key_missing_counts": profile.key_missing_counts,
        "duplicates": {
            column: _duplicate_to_json_data(duplicate)
            for column, duplicate in profile.duplicates.items()
        },
        "coordinate_ranges": {
            column: _numeric_to_json_data(numeric)
            for column, numeric in profile.coordinate_ranges.items()
        },
    }


def _duplicate_to_json_data(duplicate: DuplicateColumnProfile) -> dict[str, object]:
    return {
        "duplicate_group_count": duplicate.duplicate_group_count,
        "duplicated_record_count": duplicate.duplicated_record_count,
        "duplicate_extra_record_count": duplicate.duplicate_extra_record_count,
        "examples": [
            {
                "value": example.value,
                "count": example.count,
                "row_numbers": list(example.row_numbers),
            }
            for example in duplicate.examples
        ],
    }


def _numeric_to_json_data(numeric: NumericColumnProfile) -> dict[str, object]:
    return {
        "numeric_count": numeric.numeric_count,
        "missing_count": numeric.missing_count,
        "non_numeric_count": numeric.non_numeric_count,
        "minimum": numeric.minimum,
        "maximum": numeric.maximum,
    }


def _read_csv(path: Path) -> tuple[tuple[str, ...], tuple[dict[str, str], ...]]:
    with path.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        columns = tuple(reader.fieldnames or ())
        rows = tuple(
            {key: value or "" for key, value in row.items() if key is not None} for row in reader
        )

    return columns, rows


def _profile_key_missing_counts(
    rows: tuple[dict[str, str], ...],
    columns: tuple[str, ...],
) -> dict[str, int]:
    return {column: sum(1 for row in rows if _is_blank(row.get(column))) for column in columns}


def _profile_duplicates(
    rows: tuple[dict[str, str], ...],
    column: str,
) -> DuplicateColumnProfile:
    value_rows: dict[str, list[int]] = {}

    for row_number, row in enumerate(rows, start=1):
        value = _clean_value(row.get(column))
        if value == "":
            continue
        value_rows.setdefault(value, []).append(row_number)

    duplicate_values = [
        DuplicateValueProfile(
            value=value,
            count=len(row_numbers),
            row_numbers=tuple(row_numbers[:MAX_DUPLICATE_ROW_NUMBERS]),
        )
        for value, row_numbers in value_rows.items()
        if len(row_numbers) > 1
    ]
    duplicate_values.sort(key=lambda duplicate: (-duplicate.count, duplicate.value))

    return DuplicateColumnProfile(
        column=column,
        duplicate_group_count=len(duplicate_values),
        duplicated_record_count=sum(duplicate.count for duplicate in duplicate_values),
        duplicate_extra_record_count=sum(duplicate.count - 1 for duplicate in duplicate_values),
        examples=tuple(duplicate_values[:MAX_DUPLICATE_EXAMPLES]),
    )


def _profile_numeric_column(
    rows: tuple[dict[str, str], ...],
    column: str,
) -> NumericColumnProfile:
    values: list[float] = []
    missing_count = 0
    non_numeric_count = 0

    for row in rows:
        raw_value = row.get(column)
        if _is_blank(raw_value):
            missing_count += 1
            continue

        number = _parse_decimal(raw_value)
        if number is None:
            non_numeric_count += 1
        else:
            values.append(number)

    return NumericColumnProfile(
        column=column,
        numeric_count=len(values),
        missing_count=missing_count,
        non_numeric_count=non_numeric_count,
        minimum=min(values) if values else None,
        maximum=max(values) if values else None,
    )


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


def _is_blank(raw_value: str | None) -> bool:
    return _clean_value(raw_value) == ""


def _clean_value(raw_value: str | None) -> str:
    if raw_value is None:
        return ""
    return str(raw_value).strip()


def _format_number(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.6g}"


def _format_duplicate_example(example: DuplicateValueProfile) -> str:
    rows = _format_row_numbers(example.row_numbers, example.count)
    return f"`{example.value}` ({example.count}x: rows {rows})"


def _format_row_numbers(row_numbers: tuple[int, ...], total_count: int) -> str:
    if not row_numbers:
        return "-"
    suffix = "+" if total_count > len(row_numbers) else ""
    return ", ".join(str(row_number) for row_number in row_numbers) + suffix
