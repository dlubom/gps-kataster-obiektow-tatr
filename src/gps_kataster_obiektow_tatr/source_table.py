"""Read rectangular source tables from CSV and simple XLSX exports."""

from __future__ import annotations

import csv
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

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


def read_source_table(path: Path, *, sheet_name: str = DEFAULT_XLSX_SHEET_NAME) -> SourceTable:
    """Read a source table from CSV or XLSX."""

    if path.suffix.lower() == ".xlsx":
        return _read_xlsx_table(path, sheet_name=sheet_name)
    return _read_csv_table(path)


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


def _clean_value(raw_value: str | None) -> str:
    if raw_value is None:
        return ""
    return str(raw_value).strip()
