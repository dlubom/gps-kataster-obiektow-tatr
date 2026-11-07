"""A readable workbook from the artifacts of one validated build."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from math import ceil
from pathlib import Path

from xlsxwriter import Workbook

from gps_kataster_obiektow_tatr.export_data import ExportData, ExportRecord


@dataclass(frozen=True)
class Column:
    key: str
    title: str
    width: int = 22
    number_format: str | None = None


BEST_POINT_COLUMNS = (
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

CAVE_ID_COLUMN = Column("cave_id", "ID jaskini", 15)
SYSTEM_NAME_COLUMN = Column("cave_system_name", "System jaskiniowy", 35)
MORPHOMETRY_COLUMNS = (
    Column("cave_length_m", "Długość jaskini [m]", 20, "General"),
    Column("cave_depth_m", "Głębokość jaskini [m]", 20, "General"),
    Column("cave_denivelation_m", "Deniwelacja jaskini [m]", 20, "General"),
    Column("cave_denivelation_qualifier", "Kwalifikator deniwelacji", 24),
    Column("cave_morphometry_source_ref", "Źródło morfometrii", 42),
)
SYSTEM_COLUMNS = (
    Column("system_cave_id", "ID systemu", 15),
    Column("system_length_m", "Długość systemu [m]", 21, "General"),
    Column("system_depth_m", "Głębokość systemu [m]", 22, "General"),
    Column("system_denivelation_m", "Deniwelacja systemu [m]", 23, "General"),
    Column("system_denivelation_qualifier", "Kwalifikator deniwelacji systemu", 30),
    Column("system_morphometry_source_ref", "Źródło morfometrii systemu", 45),
)
BEST_COLUMNS = (
    *BEST_POINT_COLUMNS,
    CAVE_ID_COLUMN,
    *MORPHOMETRY_COLUMNS,
    SYSTEM_NAME_COLUMN,
    *SYSTEM_COLUMNS,
)

FULL_COLUMNS = (
    *BEST_POINT_COLUMNS[:2],
    Column("selected", "Wybrany do eksportu", 21),
    *BEST_POINT_COLUMNS[2:],
    CAVE_ID_COLUMN,
    Column("cave_name", "Nazwa jaskini", 45),
    SYSTEM_NAME_COLUMN,
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
    *MORPHOMETRY_COLUMNS,
    *SYSTEM_COLUMNS,
)

CAVE_COLUMNS = (
    CAVE_ID_COLUMN,
    Column("cave_name", "Nazwa jaskini", 52),
    SYSTEM_NAME_COLUMN,
    Column("nr_inwent", "Numer inwentarzowy", 23),
    *MORPHOMETRY_COLUMNS,
    *SYSTEM_COLUMNS,
)

SHEET_TEXT = {
    "Best": (
        "Wybrane punkty",
        "Jeden wiersz = jeden wybrany punkt. Szczegóły i uwagi w arkuszu Full. "
        "Pusta dokładność = nieznana.",
    ),
    "Full": (
        "Pełne dane i historia pomiarów",
        "Jeden wiersz = jeden pomiar, także starszy lub odrzucony. "
        "Wybrany do eksportu: Tak/Nie. Pusta dokładność = nieznana.",
    ),
    "Jaskinie": (
        "Jaskinie i pozycje katalogowe",
        "Jeden wiersz = jedna jaskinia lub pozycja katalogowa. Pusta wartość = nieznana.",
    ),
}


def write_excel_export(
    export_data: ExportData,
    *,
    output_path: Path,
    release_version: str | None,
    source_commit: str | None,
) -> Path:
    """Write selected points, preserved measurements and cave records on separate sheets."""
    generated_at = export_data.generated_at
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
            # Best historically consumed the flat CSV's 12-significant-digit numbers.
            # Preserve that workbook contract while using the same in-memory rows.
            _write_sheet(
                book, "Best", BEST_COLUMNS, export_data.selected, source, csv_precision=True
            )
            _write_sheet(book, "Full", FULL_COLUMNS, export_data.history, source)
            _write_sheet(book, "Jaskinie", CAVE_COLUMNS, export_data.caves, source)
        temporary.replace(output_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return output_path


def _write_sheet(
    book: Workbook,
    name: str,
    columns: tuple[Column, ...],
    rows: Sequence[ExportRecord],
    source: str,
    *,
    csv_precision: bool = False,
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
    title, note = SHEET_TEXT[name]
    sheet.write_string(
        1,
        0,
        title,
        book.add_format({**body, "font_size": 15, "bold": True}),
    )
    sheet.write_string(2, 0, source, book.add_format({**body, "font_color": "#596673"}))
    sheet.write_string(3, 0, note, book.add_format(body))
    name_key = columns[1].key
    formats = []
    for index, column in enumerate(columns):
        fmt = book.add_format(
            {
                **body,
                "text_wrap": column.key == name_key,
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
            max(1, ceil(len(line) / 45)) for line in str(record.get(name_key) or "").split("\n")
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
                if csv_precision and isinstance(value, float):
                    value = float(f"{value:.12g}")
                code = sheet.write_number(row_index, column_index, float(value), fmt)
            else:
                code = sheet.write_string(row_index, column_index, str(value), fmt)
            if code != 0:
                raise ValueError(
                    f"Cannot export Excel cell: {name}, {record.get(columns[0].key)}, "
                    f"{column.key} (code {code})"
                )
    sheet.set_landscape()
    sheet.repeat_rows(5)
