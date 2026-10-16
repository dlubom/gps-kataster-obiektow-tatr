"""A readable Best/Full workbook from the artifacts of one validated build."""

from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime
from math import ceil
from pathlib import Path
from typing import Any

from xlsxwriter import Workbook


@dataclass(frozen=True)
class Column:
    key: str
    title: str
    width: int = 22
    number_format: str | None = None


BEST_COLUMNS = (
    Column("object_id", "ID obiektu", 15),
    Column("name_local", "Nazwa obiektu", 52),
    Column("category", "Rodzaj obiektu", 22),
    Column("lat", "Szerokość WGS84 [°]", 22, "0.00000000"),
    Column("lon", "Długość WGS84 [°]", 22, "0.00000000"),
    Column("elevation_m", "Wysokość [m]", 17, "0.00"),
    Column("source", "Źródło pomiaru", 18),
    Column("verification_status", "Weryfikacja", 22),
    Column("horizontal_accuracy_m", "Dokładność pozioma [m]", 22, "0.00"),
    Column("observed_date", "Data pomiaru", 16, "yyyy-mm-dd"),
    Column("nr_inwent", "Numer inwentarzowy", 23),
    Column("measurement_id", "ID pomiaru", 15),
    Column("source_ref", "Odniesienie do źródła", 50),
)

FULL_COLUMNS = (
    *BEST_COLUMNS[:2],
    Column("selected", "Wybrany do eksportu", 21),
    *BEST_COLUMNS[2:],
    Column("cave_id", "ID jaskini", 15),
    Column("cave_name", "Nazwa jaskini", 45),
    Column("cave_system_name", "System jaskiniowy", 35),
    Column("x_1992", "X PL-1992 [m]", 20, "0.000"),
    Column("y_1992", "Y PL-1992 [m]", 20, "0.000"),
    Column("vertical_accuracy_m", "Dokładność pionowa [m]", 22, "0.00"),
    Column("elevation_datum", "Układ wysokości", 22),
    Column("elevation_source", "Źródło wysokości", 22),
    Column("source_date", "Data źródła", 16, "yyyy-mm-dd"),
    Column("observed_at", "Czas pomiaru (ISO 8601)", 30),
    Column("method", "Metoda pomiaru", 22),
    Column("device", "Urządzenie", 25),
    Column("tags_json", "Tagi pomiaru (JSON)", 30),
    Column("verified_by", "Zweryfikował", 24),
    Column("verified_at", "Czas weryfikacji (ISO 8601)", 30),
    Column("measurement_notes", "Uwagi pomiaru", 70),
    Column("object_notes", "Uwagi obiektu", 70),
    Column("cave_notes", "Uwagi jaskini", 70),
    Column("pig_id", "ID PIG", 20),
    Column("pig_url", "Link PIG", 55),
    Column("tpn_globalid", "GLOBALID TPN", 42),
    Column("object_external_refs", "Referencje obiektu (JSON)", 70),
    Column("cave_external_refs", "Referencje jaskini (JSON)", 70),
    Column("attachments", "Załączniki obiektu (JSON)", 70),
    Column("relations", "Relacje obiektu (JSON)", 70),
    Column("schema_version", "Wersja schematu obiektu", 22, "0"),
    Column("id_assignment_method", "Sposób nadania ID", 22),
    Column("assigned_from_measurement_id", "Pomiar użyty do nadania ID", 25),
    Column("assigned_prefix", "Nadany prefiks", 18),
    Column("prefix_override_reason", "Powód nadpisania prefiksu", 50),
    Column("best_mode", "Tryb wyboru punktu", 20),
    Column("best_measurement_id", "ID wybranego pomiaru", 22),
    Column("computed_best_measurement_id", "ID sugerowanego pomiaru", 24),
    Column("best_reason", "Uzasadnienie wyboru", 60),
    Column("best_updated_at", "Czas wyboru (ISO 8601)", 30),
    Column("best_updated_by", "Wybrał pomiar", 24),
    Column("object_created_at", "Utworzono obiekt (ISO 8601)", 30),
    Column("object_created_by", "Utworzył obiekt", 24),
    Column("object_updated_at", "Zmieniono obiekt (ISO 8601)", 30),
    Column("object_updated_by", "Zmienił obiekt", 24),
    Column("measurement_created_at", "Zapisano pomiar (ISO 8601)", 30),
    Column("measurement_created_by", "Zapisał pomiar", 24),
)


def write_excel_export(
    *,
    csv_path: Path,
    sqlite_path: Path,
    output_path: Path,
    generated_at: str,
    release_version: str | None,
    source_commit: str | None,
) -> Path:
    """Write one row per selected point in Best, one per preserved measurement in Full."""
    with csv_path.open(encoding="utf-8", newline="") as stream:
        selected = list(csv.DictReader(stream))
    full = _full_records(sqlite_path, selected)
    temporary = output_path.with_name(output_path.name + ".tmp")
    try:
        with Workbook(temporary) as book:
            book.set_properties(
                {
                    "title": "GPS Kataster Obiektów Tatr",
                    "author": "GPS Kataster Obiektów Tatr",
                    "created": datetime.fromisoformat(generated_at.replace("Z", "+00:00")),
                    "comments": f"{release_version or 'Podgląd lokalny'}; {source_commit or '—'}; "
                    f"{generated_at}; CC BY 4.0",
                }
            )
            source = f"Paczka: {release_version or 'podgląd lokalny'}; wygenerowano {generated_at}"
            _write_sheet(book, "Best", BEST_COLUMNS, selected, source)
            _write_sheet(book, "Full", FULL_COLUMNS, full, source)
        temporary.replace(output_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return output_path


def _full_records(sqlite_path: Path, selected: list[dict[str, str]]) -> list[dict[str, Any]]:
    best_by_id = {row["object_id"]: row for row in selected}
    with closing(sqlite3.connect(f"{sqlite_path.resolve().as_uri()}?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        objects = {row["id"]: dict(row) for row in db.execute("SELECT * FROM objects ORDER BY id")}
        caves = {row["id"]: dict(row) for row in db.execute("SELECT * FROM caves ORDER BY id")}
        best = {
            row["object_id"]: dict(row) for row in db.execute("SELECT * FROM best_measurements")
        }
        object_refs = _group_records(db, "object_external_refs", "object_id")
        cave_refs = _group_records(db, "cave_external_refs", "cave_id")
        attachments = _group_records(db, "attachments", "object_id")
        relations: dict[str, list[dict[str, Any]]] = {}
        for row in db.execute("SELECT * FROM relations ORDER BY id"):
            for object_id in {row["from_object_id"], row["to_object_id"]}:
                relations.setdefault(object_id, []).append(dict(row))
        records = []
        for measurement in db.execute("SELECT * FROM measurements ORDER BY object_id, id"):
            object_id = measurement["object_id"]
            obj = objects[object_id]
            cave = caves.get(obj["cave_id"], {})
            choice = best[object_id]
            record = {
                **best_by_id[object_id],
                **obj,
                **dict(measurement),
                "object_id": object_id,
                "measurement_id": measurement["id"],
                "selected": "Tak" if measurement["id"] == choice["measurement_id"] else "Nie",
                "cave_name": cave.get("name"),
                "cave_system_name": cave.get("system_name"),
                "measurement_notes": measurement["notes"],
                "object_notes": obj["notes"],
                "cave_notes": cave.get("notes"),
                "object_external_refs": _json(object_refs.get(object_id, [])),
                "cave_external_refs": _json(cave_refs.get(obj["cave_id"], [])),
                "attachments": _json(attachments.get(object_id, [])),
                "relations": _json(relations.get(object_id, [])),
                "best_updated_at": choice["updated_at"],
                "best_updated_by": choice["updated_by"],
            }
            for prefix, data, fields in (
                ("object", obj, ("created_at", "created_by", "updated_at", "updated_by")),
                ("measurement", measurement, ("created_at", "created_by")),
            ):
                record.update({f"{prefix}_{key}": data[key] for key in fields})
            records.append(record)
    return records


def _group_records(db: sqlite3.Connection, table: str, owner: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    # Table/owner names are constants supplied by this module, never input data.
    for row in db.execute(f"SELECT * FROM {table} ORDER BY {owner}, rowid"):
        grouped.setdefault(row[owner], []).append(
            {key: value for key, value in dict(row).items() if key not in (owner, "rowid")}
        )
    return grouped


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _write_sheet(
    book: Workbook, name: str, columns: tuple[Column, ...], rows: list[dict], source: str
) -> None:
    sheet = book.add_worksheet(name)
    sheet.hide_gridlines(2)
    sheet.freeze_panes(6, 2)
    sheet.set_tab_color("#24476A" if name == "Best" else "#7A8997")
    body = {"font_name": "Arial", "font_size": 11, "valign": "vcenter"}
    header = book.add_format(
        {
            **body,
            "bold": True,
            "font_color": "#FFFFFF",
            "bg_color": "#24476A",
            "text_wrap": True,
            "align": "center",
            "bottom": 1,
            "bottom_color": "#FFFFFF",
        }
    )
    sheet.write_string(
        1,
        0,
        "Wybrane punkty" if name == "Best" else "Pełne dane i historia pomiarów",
        book.add_format({**body, "font_size": 15, "bold": True}),
    )
    sheet.write_string(2, 0, source, book.add_format({**body, "font_color": "#596673"}))
    note = "Jeden wiersz = jeden wybrany punkt. Szczegóły i uwagi w arkuszu Full."
    if name == "Full":
        note = (
            "Jeden wiersz = jeden pomiar, także starszy lub odrzucony. "
            "Wybrany do eksportu: Tak/Nie."
        )
    sheet.write_string(3, 0, note + " Pusta dokładność = nieznana.", book.add_format(body))
    formats = []
    for index, column in enumerate(columns):
        fmt = book.add_format(
            {
                **body,
                "text_wrap": column.key == "name_local",
                **({"num_format": column.number_format} if column.number_format else {}),
            }
        )
        formats.append(fmt)
        sheet.set_column(index, index, column.width, fmt)
        sheet.write_string(5, index, column.title, header)
    sheet.set_row(5, 42)
    if rows:
        sheet.add_table(
            5,
            0,
            len(rows) + 5,
            len(columns) - 1,
            {
                "name": name + "Data",
                "style": "Table Style Medium 2",
                "columns": [{"header": col.title, "header_format": header} for col in columns],
            },
        )
    else:
        sheet.autofilter(5, 0, 5, len(columns) - 1)
    for row_index, record in enumerate(rows, start=6):
        name_lines = sum(
            max(1, ceil(len(line) / 45)) for line in str(record.get("name_local") or "").split("\n")
        )
        sheet.set_row(row_index, min(409, max(24, name_lines * 16)))
        for column_index, column in enumerate(columns):
            value = record.get(column.key)
            if value is None or value == "":
                continue
            fmt = formats[column_index]
            if column.number_format == "yyyy-mm-dd":
                day = date.fromisoformat(str(value))
                if day < date(1900, 1, 1):
                    code = sheet.write_string(row_index, column_index, day.isoformat(), fmt)
                else:
                    # A date avoids XlsxWriter's time-only adjustment for 1900-01-01.
                    code = sheet.write_datetime(row_index, column_index, day, fmt)
            elif column.number_format:
                code = sheet.write_number(row_index, column_index, float(value), fmt)
            else:
                code = sheet.write_string(row_index, column_index, str(value), fmt)
            if code != 0:
                raise ValueError(
                    f"Cannot export Excel cell: {name}, {record.get('object_id')}, "
                    f"{column.key} (code {code})"
                )
    sheet.set_landscape()
    sheet.repeat_rows(5)
