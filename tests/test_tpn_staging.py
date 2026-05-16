import csv
import importlib.util
import json
import subprocess
import sys
import zipfile
from html import escape
from pathlib import Path

from gps_kataster_obiektow_tatr.prefix_resolver import (
    PrefixResolution,
    PrefixResolutionArea,
    PrefixResolutionStatus,
)
from gps_kataster_obiektow_tatr.tpn_staging import (
    build_tpn_staging,
    write_staging_files,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
IMPORT_TPN_PATH = REPO_ROOT / "scripts" / "importers" / "import_tpn.py"

spec = importlib.util.spec_from_file_location("import_tpn_script", IMPORT_TPN_PATH)
assert spec is not None
assert spec.loader is not None
import_tpn_script = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = import_tpn_script
spec.loader.exec_module(import_tpn_script)


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


def test_csv_staging_matches_pig_by_nr_and_creates_tpn_measurement_update(
    tmp_path: Path,
) -> None:
    tpn_csv = tmp_path / "tpn.csv"
    pig_staging = tmp_path / "pig-staging.json"
    globalid = "{D7C052E6-D584-4320-B886-367312D2219F}"
    _write_tpn_csv(
        tpn_csv,
        [
            _tpn_row(
                nr_inwent="T.F-09.33",
                name="Szczelina pod Gankowa II",
                globalid=globalid,
                x_1992="152267,23",
                y_1992="563744,25",
            )
        ],
    )
    _write_pig_staging(
        pig_staging,
        object_id="KSW-0001",
        cave_id="C-0001",
        nr_inwent="T.F-09.33",
        name="Szczelina pod Gankowa II",
        x_1992=152267.23,
        y_1992=563744.25,
    )

    report = build_tpn_staging(
        tpn_csv,
        generated_at="2026-05-16T09:00:00Z",
        data_dir=tmp_path / "data",
        pig_staging_path=pig_staging,
        prefix_resolver=StubResolver(),
    )

    update = report.matched_measurements[0]
    measurement = update["measurement"]

    assert report.rows[0].status == "matched"
    assert report.rows[0].match_strategy == "nr_inwent"
    assert update["target_object_id"] == "KSW-0001"
    assert update["target_cave_id"] == "C-0001"
    assert update["object_external_refs"] == [
        {
            "system": "TPN",
            "ref_type": "source_globalid",
            "external_id": globalid,
            "scope": "object",
            "notes": "TPN GLOBALID belongs to the object/source feature.",
        }
    ]
    assert update["cave_external_refs"][0]["external_id"] == "T.F-09.33"
    assert measurement["id"] == "m-002"
    assert measurement["source"] == "TPN"
    assert measurement["source_ref"] == f"TPN:{globalid}"
    assert measurement["verification_status"] == "nieweryfikowany"
    assert report.proposed_caves == ()
    assert report.proposed_objects == ()


def test_new_tpn_row_creates_object_globalid_and_cave_nr_ref(tmp_path: Path) -> None:
    tpn_csv = tmp_path / "tpn.csv"
    globalid = "{38626571-CAA6-4317-8900-D61A995020E9}"
    _write_tpn_csv(
        tpn_csv,
        [
            _tpn_row(
                nr_inwent="T.D-13.05",
                name="Nyza pod Brzozka",
                globalid=globalid,
                x_1992="154416,50",
                y_1992="567679,48",
            )
        ],
    )

    report = build_tpn_staging(
        tpn_csv,
        generated_at="2026-05-16T09:00:00Z",
        data_dir=tmp_path / "data",
        pig_staging_path=None,
        prefix_resolver=StubResolver(),
    )

    cave = report.proposed_caves[0]
    obj = report.proposed_objects[0]
    measurement = obj["measurements"][0]

    assert report.rows[0].status == "new"
    assert cave["id"] == "C-0001"
    assert cave["object_ids"] == ["KSW-0001"]
    assert cave["external_refs"][0]["system"] == "NR_INWENT"
    assert cave["external_refs"][0]["external_id"] == "T.D-13.05"
    assert obj["external_refs"][0]["system"] == "TPN"
    assert obj["external_refs"][0]["external_id"] == globalid
    assert measurement["source"] == "TPN"
    assert measurement["horizontal_accuracy_m"] is None


def test_new_tpn_sztolnia_row_keeps_sztolnia_category(tmp_path: Path) -> None:
    tpn_csv = tmp_path / "tpn.csv"
    _write_tpn_csv(
        tpn_csv,
        [
            _tpn_row(
                nr_inwent="",
                name="Sztolnia w Dolinie Białego nr 1",
                globalid="{0606A079-D986-44F9-BC11-22BE576A107E}",
                x_1992="156532,54",
                y_1992="569519,71",
                geneza="sztolnia",
            )
        ],
    )

    report = build_tpn_staging(
        tpn_csv,
        generated_at="2026-05-16T09:00:00Z",
        data_dir=tmp_path / "data",
        pig_staging_path=None,
        prefix_resolver=StubResolver(prefix="BIA"),
    )

    assert report.proposed_objects[0]["category"] == "sztolnia"


def test_duplicate_nr_without_name_distance_resolution_is_unresolved(tmp_path: Path) -> None:
    tpn_csv = tmp_path / "tpn.csv"
    pig_staging = tmp_path / "pig-staging.json"
    _write_tpn_csv(
        tpn_csv,
        [
            _tpn_row(
                nr_inwent="T.D-08.07",
                name="Jaskinia Mrozna",
                globalid="{11111111-1111-1111-1111-111111111111}",
                x_1992="152000,00",
                y_1992="563000,00",
            ),
            _tpn_row(
                nr_inwent="T.D-08.07",
                name="Drugi otwor",
                globalid="{22222222-2222-2222-2222-222222222222}",
                x_1992="152010,00",
                y_1992="563010,00",
            ),
        ],
    )
    _write_pig_staging(
        pig_staging,
        object_id="KSW-0001",
        cave_id="C-0001",
        nr_inwent="T.D-08.07",
        name="Jaskinia Mrozna",
        x_1992=152267.23,
        y_1992=563744.25,
    )

    report = build_tpn_staging(
        tpn_csv,
        generated_at="2026-05-16T09:00:00Z",
        data_dir=tmp_path / "data",
        pig_staging_path=pig_staging,
        prefix_resolver=StubResolver(),
    )

    assert {row.status for row in report.rows} == {"unresolved"}
    assert {issue.code for issue in report.issues} == {"TPN_NR_INWENT_AMBIGUOUS"}
    assert report.matched_measurements == ()
    assert report.proposed_objects == ()


def test_xlsx_source_is_readable_for_tpn_staging(tmp_path: Path) -> None:
    tpn_xlsx = tmp_path / "tpn.xlsx"
    _write_xlsx(
        tpn_xlsx,
        [
            _tpn_header(),
            _tpn_row(
                nr_inwent="T.D-13.05",
                name="Nyza pod Brzozka",
                globalid="{38626571-CAA6-4317-8900-D61A995020E9}",
                x_1992="154416,50",
                y_1992="567679,48",
            ),
        ],
    )

    report = build_tpn_staging(
        tpn_xlsx,
        generated_at="2026-05-16T09:00:00Z",
        data_dir=tmp_path / "data",
        pig_staging_path=None,
        prefix_resolver=StubResolver(),
    )

    assert report.record_count == 1
    assert report.rows[0].status == "new"
    assert report.proposed_objects[0]["external_refs"][0]["system"] == "TPN"


def test_writes_json_and_markdown_staging_without_final_yaml(tmp_path: Path) -> None:
    tpn_csv = tmp_path / "tpn.csv"
    _write_tpn_csv(
        tpn_csv,
        [
            _tpn_row(
                nr_inwent="T.D-13.05",
                name="Nyza pod Brzozka",
                globalid="{38626571-CAA6-4317-8900-D61A995020E9}",
                x_1992="154416,50",
                y_1992="567679,48",
            ),
            _tpn_row(
                nr_inwent="T.E-08.04",
                name="Bad coordinates",
                globalid="{BADBADBAD-BAD0-BAD0-BAD0-BADBADBADBAD}",
                x_1992="bad",
                y_1992="567679,48",
            ),
        ],
    )
    report = build_tpn_staging(
        tpn_csv,
        generated_at="2026-05-16T09:00:00Z",
        data_dir=tmp_path / "data",
        pig_staging_path=None,
        prefix_resolver=StubResolver(),
    )

    json_path, markdown_path = write_staging_files(report, output_dir=tmp_path / "build")

    json_data = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")

    assert json_data["new_count"] == 1
    assert json_data["rejected_count"] == 1
    assert json_data["proposed_objects"][0]["external_refs"][0]["system"] == "TPN"
    assert "# TPN Staging Import" in markdown
    assert "This report does not write final YAML" in markdown
    assert not (tmp_path / "data" / "objects").exists()
    assert not (tmp_path / "data" / "caves").exists()


def test_cli_writes_staging_artifacts_without_final_yaml(tmp_path: Path) -> None:
    tpn_csv = tmp_path / "tpn.csv"
    output_dir = tmp_path / "build" / "staging" / "tpn"
    data_dir = tmp_path / "data"
    _write_tpn_csv(
        tpn_csv,
        [
            _tpn_row(
                nr_inwent="T.D-13.05",
                name="Nyza pod Brzozka",
                globalid="{38626571-CAA6-4317-8900-D61A995020E9}",
                x_1992="154416,50",
                y_1992="567679,48",
            )
        ],
    )

    result = subprocess.run(
        [
            sys.executable,
            str(IMPORT_TPN_PATH),
            "--tpn-source",
            str(tpn_csv),
            "--data-dir",
            str(data_dir),
            "--output-dir",
            str(output_dir),
            "--generated-at",
            "2026-05-16T09:00:00Z",
            "--no-pig-staging",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert (output_dir / "tpn-staging.json").exists()
    assert (output_dir / "tpn-staging.md").exists()
    assert "TPN staging: 1 records, 0 matched, 1 new, 0 unresolved" in result.stdout
    assert not (data_dir / "objects").exists()
    assert not (data_dir / "caves").exists()


def _tpn_header() -> list[str]:
    return [
        "NR_INWENT",
        "NAZWA",
        "DLUGOSC",
        "GLEBOKOSC",
        "PRZEWYZSZE",
        "DENIWELACJ",
        "SYSTEM",
        "OTWÓR",
        "OPIS",
        "WER_LOK",
        "UWAGI",
        "WERYF",
        "GENEZA",
        "FIELD",
        "CREATED_US",
        "CREATED_DA",
        "LAST_EDITE",
        "LAST_EDI_1",
        "GLOBALID",
        "TATER",
        "Z",
        "X1992",
        "Y1992",
    ]


def _tpn_row(
    *,
    nr_inwent: str,
    name: str,
    globalid: str,
    x_1992: str,
    y_1992: str,
    geneza: str = "jaskinia",
) -> list[str]:
    return [
        nr_inwent,
        name,
        "3",
        "0",
        "0",
        "1",
        "",
        "",
        "",
        "",
        "",
        "1",
        geneza,
        "0",
        "",
        "",
        "SDE",
        "2022-05-25 00:00:00",
        globalid,
        "",
        "1266,0",
        x_1992,
        y_1992,
    ]


def _write_tpn_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(_tpn_header())
        writer.writerows(rows)


def _write_pig_staging(
    path: Path,
    *,
    object_id: str,
    cave_id: str,
    nr_inwent: str,
    name: str,
    x_1992: float,
    y_1992: float,
) -> None:
    path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "record_number": 1,
                        "pig_id": "1692",
                        "nr_inwent": nr_inwent,
                        "name": name,
                        "cave_id": cave_id,
                        "object_id": object_id,
                        "status": "object_proposed",
                    }
                ],
                "proposed_objects": [
                    {
                        "id": object_id,
                        "name_local": name,
                        "external_refs": [],
                        "measurements": [
                            {
                                "id": "m-001",
                                "x_1992": x_1992,
                                "y_1992": y_1992,
                            }
                        ],
                        "best_measurement": {
                            "mode": "auto",
                            "measurement_id": "m-001",
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


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
