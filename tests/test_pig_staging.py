import importlib.util
import json
import subprocess
import sys
import zipfile
from html import escape
from pathlib import Path

from gps_kataster_obiektow_tatr.pig_staging import (
    build_pig_staging,
    read_source_table,
    write_staging_files,
)
from gps_kataster_obiektow_tatr.prefix_resolver import (
    PrefixResolution,
    PrefixResolutionArea,
    PrefixResolutionStatus,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
IMPORT_PIG_PATH = REPO_ROOT / "scripts" / "importers" / "import_pig.py"

spec = importlib.util.spec_from_file_location("import_pig_script", IMPORT_PIG_PATH)
assert spec is not None
assert spec.loader is not None
import_pig_script = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = import_pig_script
spec.loader.exec_module(import_pig_script)


class StubResolver:
    def __init__(self, prefix: str = "KSW") -> None:
        self.prefix = prefix

    def resolve(self, *, lat: float, lon: float) -> PrefixResolution:
        return PrefixResolution(
            status=PrefixResolutionStatus.OK,
            area=PrefixResolutionArea.VALLEY,
            prefix=self.prefix,
            code=None,
            message=None,
            x_1992=152267.23,
            y_1992=563744.25,
            valley_name="Dolina Koscieliska - Wschod",
        )


def test_csv_staging_keeps_pig_refs_on_cave_and_pig_measurement_low_priority(
    tmp_path: Path,
) -> None:
    pig_csv = tmp_path / "pig.csv"
    _write_text(
        pig_csv,
        "\n".join(
            [
                _pig_header(),
                _pig_row(
                    pig_id="1692",
                    name="Szczelina pod Gankowa II",
                    nr_inwent="T.F-09.33",
                    x_1992="152267,23",
                    y_1992="563744,25",
                    lat="49,23459299",
                    lon="19,87589498",
                    source_year="2010",
                ),
            ]
        ),
    )

    report = build_pig_staging(
        pig_csv,
        generated_at="2026-05-16T08:00:00Z",
        data_dir=tmp_path / "data",
        prefix_resolver=StubResolver(),
    )

    cave = report.proposed_caves[0]
    obj = report.proposed_objects[0]
    measurement = obj["measurements"][0]

    assert cave["id"] == "C-0001"
    assert cave["object_ids"] == ["KSW-0001"]
    assert {
        (ref["system"], ref["ref_type"], ref["external_id"]) for ref in cave["external_refs"]
    } == {
        ("NR_INWENT", "inventory_number", "T.F-09.33"),
        ("PIG", "catalog_id", "1692"),
        ("PIG", "url", "https://jaskiniepolski.pgi.gov.pl/Details/Information/1692"),
    }
    assert obj["external_refs"] == []
    assert obj["best_measurement"]["mode"] == "auto"
    assert measurement["source"] == "PIG"
    assert measurement["verification_status"] == "nieweryfikowany"
    assert measurement["source_ref"] == "PIG:1692"
    assert measurement["horizontal_accuracy_m"] is None
    assert measurement["observed_date"] == "2010-12-31"
    assert report.issues == ()


def test_coordinate_mismatch_keeps_cave_but_skips_object(tmp_path: Path) -> None:
    pig_csv = tmp_path / "pig.csv"
    _write_text(
        pig_csv,
        "\n".join(
            [
                _pig_header(),
                _pig_row(
                    pig_id="1692",
                    name="Szczelina pod Gankowa II",
                    nr_inwent="T.F-09.33",
                    x_1992="1",
                    y_1992="2",
                    lat="49,23459299",
                    lon="19,87589498",
                    source_year="2010",
                ),
            ]
        ),
    )

    report = build_pig_staging(
        pig_csv,
        generated_at="2026-05-16T08:00:00Z",
        data_dir=tmp_path / "data",
        prefix_resolver=StubResolver(),
    )

    assert len(report.proposed_caves) == 1
    assert report.proposed_caves[0]["object_ids"] == []
    assert report.proposed_objects == ()
    assert report.rows[0].status == "cave_only"
    assert report.issues[0].code == "PIG_COORDINATE_MISMATCH"


def test_xlsx_source_is_readable_for_staging(tmp_path: Path) -> None:
    pig_xlsx = tmp_path / "pig.xlsx"
    _write_xlsx(
        pig_xlsx,
        [
            _pig_header().split(","),
            [
                "1692",
                "Szczelina pod Gankowa II",
                "",
                "T.F-09.33",
                "152267,23",
                "563744,25",
                "1266",
                "49,23459299",
                "19,87589498",
                "D. Koscieliska - Wsch.",
                "3",
                "0,7",
                "1",
                "2010",
                "https://jaskiniepolski.pgi.gov.pl/Details/Information/1692",
            ],
        ],
    )

    table = read_source_table(pig_xlsx)
    report = build_pig_staging(
        pig_xlsx,
        generated_at="2026-05-16T08:00:00Z",
        data_dir=tmp_path / "data",
        prefix_resolver=StubResolver(),
    )

    assert table.columns[:4] == ("ID", "Nazwa", "Inne nazwy", "Nr inw.")
    assert report.record_count == 1
    assert report.proposed_caves[0]["external_refs"][1]["external_id"] == "1692"
    assert report.proposed_objects[0]["id"] == "KSW-0001"


def test_writes_json_and_markdown_staging_without_final_yaml(tmp_path: Path) -> None:
    pig_csv = tmp_path / "pig.csv"
    _write_text(
        pig_csv,
        "\n".join(
            [
                _pig_header(),
                _pig_row(
                    pig_id="1692",
                    name="Szczelina pod Gankowa II",
                    nr_inwent="T.F-09.33",
                    x_1992="152267,23",
                    y_1992="563744,25",
                    lat="49,23459299",
                    lon="19,87589498",
                    source_year="2010",
                ),
            ]
        ),
    )
    report = build_pig_staging(
        pig_csv,
        generated_at="2026-05-16T08:00:00Z",
        data_dir=tmp_path / "data",
        prefix_resolver=StubResolver(),
    )

    json_path, markdown_path = write_staging_files(report, output_dir=tmp_path / "build")

    json_data = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")

    assert json_data["proposed_cave_count"] == 1
    assert json_data["proposed_object_count"] == 1
    assert json_data["proposed_caves"][0]["external_refs"][0]["system"] == "NR_INWENT"
    assert "# PIG Staging Import" in markdown
    assert "This report does not write final YAML" in markdown
    assert not (tmp_path / "data" / "objects").exists()
    assert not (tmp_path / "data" / "caves").exists()


def test_cli_writes_staging_artifacts_without_final_yaml(tmp_path: Path) -> None:
    pig_csv = tmp_path / "pig.csv"
    output_dir = tmp_path / "build" / "staging" / "pig"
    data_dir = tmp_path / "data"
    _write_text(
        pig_csv,
        "\n".join(
            [
                _pig_header(),
                _pig_row(
                    pig_id="1692",
                    name="Szczelina pod Gankowa II",
                    nr_inwent="T.F-09.33",
                    x_1992="152267,23",
                    y_1992="563744,25",
                    lat="49,23459299",
                    lon="19,87589498",
                    source_year="2010",
                ),
            ]
        ),
    )

    result = subprocess.run(
        [
            sys.executable,
            str(IMPORT_PIG_PATH),
            "--pig-source",
            str(pig_csv),
            "--data-dir",
            str(data_dir),
            "--output-dir",
            str(output_dir),
            "--generated-at",
            "2026-05-16T08:00:00Z",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert (output_dir / "pig-staging.json").exists()
    assert (output_dir / "pig-staging.md").exists()
    assert "PIG staging: 1 records, 1 cave proposals, 1 object proposals" in result.stdout
    assert not (data_dir / "objects").exists()
    assert not (data_dir / "caves").exists()


def _pig_header() -> str:
    return (
        "ID,Nazwa,Inne nazwy,Nr inw.,X 1992,Y 1992,H (wg PIG),B,L,Sektor (nazwa),"
        "Długość [m],Głębokość [m],Deniwelacja [m],Stan na rok,Link"
    )


def _pig_row(
    *,
    pig_id: str,
    name: str,
    nr_inwent: str,
    x_1992: str,
    y_1992: str,
    lat: str,
    lon: str,
    source_year: str,
) -> str:
    link = f"https://jaskiniepolski.pgi.gov.pl/Details/Information/{pig_id}"
    return (
        f'{pig_id},{name},,{nr_inwent},"{x_1992}","{y_1992}",1266,'
        f'"{lat}","{lon}",D. Koscieliska - Wsch.,3,"0,7",1,{source_year},{link}'
    )


def _write_text(path: Path, content: str) -> None:
    path.write_text(content + "\n", encoding="utf-8")


def _write_xlsx(path: Path, rows: list[list[str]]) -> None:
    with zipfile.ZipFile(path, "w") as workbook:
        workbook.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" '
                'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/xl/workbook.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                '<Override PartName="/xl/worksheets/sheet1.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                "</Types>"
            ),
        )
        workbook.writestr(
            "_rels/.rels",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
                'officeDocument" '
                'Target="xl/workbook.xml"/>'
                "</Relationships>"
            ),
        )
        workbook.writestr(
            "xl/workbook.xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets><sheet name="Export" sheetId="1" r:id="rId1"/></sheets>'
                "</workbook>"
            ),
        )
        workbook.writestr(
            "xl/_rels/workbook.xml.rels",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
                'worksheet" '
                'Target="worksheets/sheet1.xml"/>'
                "</Relationships>"
            ),
        )
        workbook.writestr("xl/worksheets/sheet1.xml", _worksheet_xml(rows))


def _worksheet_xml(rows: list[list[str]]) -> str:
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row):
            cell_ref = f"{_column_name(column_index)}{row_index}"
            cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(row_xml)}</sheetData>"
        "</worksheet>"
    )


def _column_name(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name
