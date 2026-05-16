import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from gps_kataster_obiektow_tatr.source_profile import (
    profile_sources,
    render_markdown_report,
    write_report_files,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE_SOURCES_PATH = REPO_ROOT / "scripts" / "profile_sources.py"

spec = importlib.util.spec_from_file_location("profile_sources_script", PROFILE_SOURCES_PATH)
assert spec is not None
assert spec.loader is not None
profile_sources_script = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = profile_sources_script
spec.loader.exec_module(profile_sources_script)


def test_profiles_missing_values_duplicates_and_coordinate_ranges(tmp_path: Path) -> None:
    pig_csv = tmp_path / "pig.csv"
    tpn_csv = tmp_path / "tpn.csv"
    _write_text(
        pig_csv,
        "\n".join(
            [
                "ID,Nazwa,Nr inw.,X 1992,Y 1992,B,L,Link",
                '1,Jaskinia A,T.A-01,"150000,5","560000,0","49,20","19,90",https://example/1',
                '2,Jaskinia B,T.A-01,bad,"561000,0",,20.0,',
                '2,Jaskinia C,,"151000","562000","49,30","20,10",https://example/2',
            ]
        ),
    )
    _write_text(
        tpn_csv,
        "\n".join(
            [
                "NR_INWENT,NAZWA,GLOBALID,Z,X1992,Y1992",
                'T.A-01,Jaskinia A,{gid-1},"1200,5","150001","560001"',
                'T.A-01,Jaskinia A bis,{gid-2},,not-a-number,"560002"',
                ",Bez inwentarza,{gid-2},1210,150003,560003",
            ]
        ),
    )

    report = profile_sources(pig_csv=pig_csv, tpn_csv=tpn_csv)

    pig_profile = report.profiles[0]
    assert pig_profile.record_count == 3
    assert pig_profile.column_count == 8
    assert pig_profile.key_missing_counts["Nr inw."] == 1
    assert pig_profile.key_missing_counts["B"] == 1
    assert pig_profile.duplicates["ID"].duplicate_group_count == 1
    assert pig_profile.duplicates["ID"].duplicated_record_count == 2
    assert pig_profile.duplicates["Nr inw."].examples[0].row_numbers == (1, 2)
    assert pig_profile.coordinate_ranges["X 1992"].numeric_count == 2
    assert pig_profile.coordinate_ranges["X 1992"].non_numeric_count == 1
    assert pig_profile.coordinate_ranges["B"].minimum == 49.2
    assert pig_profile.coordinate_ranges["B"].maximum == 49.3

    tpn_profile = report.profiles[1]
    assert tpn_profile.key_missing_counts["NR_INWENT"] == 1
    assert tpn_profile.duplicates["GLOBALID"].examples[0].value == "{gid-2}"
    assert tpn_profile.coordinate_ranges["X1992"].non_numeric_count == 1
    assert tpn_profile.coordinate_ranges["Z"].missing_count == 1


def test_writes_json_and_markdown_reports(tmp_path: Path) -> None:
    pig_csv, tpn_csv = _write_minimal_source_csvs(tmp_path)
    report = profile_sources(pig_csv=pig_csv, tpn_csv=tpn_csv)

    json_path, markdown_path = write_report_files(
        report,
        output_dir=tmp_path / "reports",
        generated_at="2026-05-16T00:00:00Z",
    )

    json_data = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")

    assert json_data["generated_at"] == "2026-05-16T00:00:00Z"
    assert json_data["profiles"][0]["source"] == "PIG"
    assert json_data["profiles"][1]["source"] == "TPN"
    assert "# Source Profile" in markdown
    assert "This report does not create final YAML" in markdown
    assert "| PIG |" in markdown


def test_markdown_report_mentions_missing_expected_columns(tmp_path: Path) -> None:
    pig_csv = tmp_path / "pig.csv"
    tpn_csv = tmp_path / "tpn.csv"
    _write_text(pig_csv, "ID,Nazwa\n1,Jaskinia A\n")
    _write_text(tpn_csv, "GLOBALID,NAZWA\n{gid-1},Jaskinia A\n")

    markdown = render_markdown_report(
        profile_sources(pig_csv=pig_csv, tpn_csv=tpn_csv),
        generated_at="2026-05-16T00:00:00Z",
    )

    assert "Missing expected columns" in markdown
    assert "`Nr inw.`" in markdown
    assert "`NR_INWENT`" in markdown


def test_cli_writes_reports_without_final_yaml(tmp_path: Path) -> None:
    pig_csv, tpn_csv = _write_minimal_source_csvs(tmp_path)
    output_dir = tmp_path / "build" / "reports"

    result = subprocess.run(
        [
            sys.executable,
            str(PROFILE_SOURCES_PATH),
            "--pig-csv",
            str(pig_csv),
            "--tpn-csv",
            str(tpn_csv),
            "--output-dir",
            str(output_dir),
            "--generated-at",
            "2026-05-16T00:00:00Z",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert (output_dir / "source-profile.json").exists()
    assert (output_dir / "source-profile.md").exists()
    assert "PIG: 1 records" in result.stdout
    assert not (tmp_path / "data" / "objects").exists()
    assert not (tmp_path / "data" / "caves").exists()


def _write_minimal_source_csvs(tmp_path: Path) -> tuple[Path, Path]:
    pig_csv = tmp_path / "pig.csv"
    tpn_csv = tmp_path / "tpn.csv"
    _write_text(
        pig_csv,
        "\n".join(
            [
                "ID,Nazwa,Nr inw.,X 1992,Y 1992,B,L,Link",
                '1,Jaskinia A,T.A-01,"150000,5","560000,0","49,20","19,90",https://example/1',
            ]
        ),
    )
    _write_text(
        tpn_csv,
        "\n".join(
            [
                "NR_INWENT,NAZWA,GLOBALID,Z,X1992,Y1992",
                'T.A-01,Jaskinia A,{gid-1},"1200,5","150001","560001"',
            ]
        ),
    )
    return pig_csv, tpn_csv


def _write_text(path: Path, content: str) -> None:
    path.write_text(content + "\n", encoding="utf-8")
