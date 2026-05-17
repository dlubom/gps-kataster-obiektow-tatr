import zipfile
from pathlib import Path

from gps_kataster_obiektow_tatr.source_table import read_source_table

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def test_reads_csv_with_utf8_bom_and_trims_values(tmp_path: Path) -> None:
    csv_path = tmp_path / "source.csv"
    csv_path.write_text("\ufeffID,Name,Note\n 1 , Cave A , \n", encoding="utf-8")

    table = read_source_table(csv_path)

    assert table.columns == ("ID", "Name", "Note")
    assert table.rows == ({"ID": "1", "Name": "Cave A", "Note": ""},)


def test_reads_sparse_xlsx_rows_shared_strings_and_inline_strings(tmp_path: Path) -> None:
    xlsx_path = tmp_path / "source.xlsx"
    _write_xlsx(
        xlsx_path,
        sheet_name="Export",
        relationship_target="worksheets/sheet1.xml",
        sheet_xml=f"""
        <worksheet xmlns="{MAIN_NS}">
          <sheetData>
            <row r="1">
              <c r="A1" t="s"><v>0</v></c>
              <c r="C1" t="inlineStr"><is><t>Name</t></is></c>
            </row>
            <row r="2">
              <c r="A2"><v>1</v></c>
              <c r="C2" t="s"><v>1</v></c>
            </row>
            <row r="3">
              <c r="B3"><v>ignored because its header is blank</v></c>
            </row>
          </sheetData>
        </worksheet>
        """,
    )

    table = read_source_table(xlsx_path)

    assert table.columns == ("ID", "", "Name")
    assert table.rows == ({"ID": "1", "Name": "Cave A"},)


def test_xlsx_reader_uses_first_sheet_when_requested_sheet_is_missing(
    tmp_path: Path,
) -> None:
    xlsx_path = tmp_path / "fallback.xlsx"
    _write_xlsx(
        xlsx_path,
        sheet_name="Other",
        relationship_target="/xl/worksheets/sheet1.xml",
        sheet_xml=f"""
        <worksheet xmlns="{MAIN_NS}">
          <sheetData>
            <row r="1"><c r="A1" t="inlineStr"><is><t>ID</t></is></c></row>
            <row r="2"><c r="A2"><v>42</v></c></row>
          </sheetData>
        </worksheet>
        """,
    )

    table = read_source_table(xlsx_path, sheet_name="Export")

    assert table.columns == ("ID",)
    assert table.rows == ({"ID": "42"},)


def test_xlsx_reader_returns_empty_table_for_empty_sheet(tmp_path: Path) -> None:
    xlsx_path = tmp_path / "empty.xlsx"
    _write_xlsx(
        xlsx_path,
        sheet_name="Export",
        relationship_target="xl/worksheets/sheet1.xml",
        sheet_xml=f"""
        <worksheet xmlns="{MAIN_NS}">
          <sheetData />
        </worksheet>
        """,
        shared_strings=False,
    )

    table = read_source_table(xlsx_path)

    assert table.columns == ()
    assert table.rows == ()


def test_xlsx_reader_rejects_workbook_without_readable_sheet(tmp_path: Path) -> None:
    xlsx_path = tmp_path / "bad.xlsx"
    with zipfile.ZipFile(xlsx_path, "w") as workbook:
        workbook.writestr(
            "xl/workbook.xml",
            f"""
            <workbook xmlns="{MAIN_NS}" xmlns:r="{REL_NS}">
              <sheets><sheet name="Export" sheetId="1" r:id="rId1" /></sheets>
            </workbook>
            """,
        )
        workbook.writestr(
            "xl/_rels/workbook.xml.rels",
            f"""<Relationships xmlns="{PACKAGE_REL_NS}" />""",
        )

    try:
        read_source_table(xlsx_path)
    except ValueError as exc:
        assert "no readable sheet named 'Export'" in str(exc)
    else:
        raise AssertionError("Expected ValueError for workbook without readable sheet")


def _write_xlsx(
    path: Path,
    *,
    sheet_name: str,
    relationship_target: str,
    sheet_xml: str,
    shared_strings: bool = True,
) -> None:
    with zipfile.ZipFile(path, "w") as workbook:
        workbook.writestr(
            "xl/workbook.xml",
            f"""
            <workbook xmlns="{MAIN_NS}" xmlns:r="{REL_NS}">
              <sheets><sheet name="{sheet_name}" sheetId="1" r:id="rId1" /></sheets>
            </workbook>
            """,
        )
        workbook.writestr(
            "xl/_rels/workbook.xml.rels",
            f"""
            <Relationships xmlns="{PACKAGE_REL_NS}">
              <Relationship Id="rId1" Target="{relationship_target}" />
            </Relationships>
            """,
        )
        if shared_strings:
            workbook.writestr(
                "xl/sharedStrings.xml",
                f"""
                <sst xmlns="{MAIN_NS}">
                  <si><t>ID</t></si>
                  <si><t>Cave A</t></si>
                </sst>
                """,
            )
        workbook.writestr("xl/worksheets/sheet1.xml", sheet_xml)
