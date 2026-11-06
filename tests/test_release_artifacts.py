import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
from export_test_support import (
    GENERATED_AT,
    KSW_LAT,
    REPO_ROOT,
    accept_source,
    cli_args,
    initialize_source,
)
from export_test_support import (
    excel_records as _excel_records,
)
from export_test_support import (
    valid_cave as _valid_cave,
)
from export_test_support import (
    valid_object as _valid_object,
)
from export_test_support import (
    write_sample_data as _write_sample_data,
)
from export_test_support import (
    write_yaml as _write_yaml,
)
from openpyxl import load_workbook

from gps_kataster_obiektow_tatr.excel_export import write_excel_export
from gps_kataster_obiektow_tatr.export_data import prepare_export_data
from gps_kataster_obiektow_tatr.postgres import read_catalog_projection
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts

BUILD_RELEASE_SCRIPT = REPO_ROOT / "scripts" / "build_release_artifacts.py"


def test_build_release_artifacts_writes_full_expected_set(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    output_dir = tmp_path / "build" / "exports"
    _write_sample_data(data_dir)
    baseline = accept_source(data_dir)

    result = build_release_artifacts(
        **baseline,
        data_dir=data_dir,
        output_dir=output_dir,
        generated_at=GENERATED_AT,
    )

    assert result.artifact_paths == (
        output_dir / "katalog.dump",
        output_dir / "katalog.gpkg",
        output_dir / "best-measurements.geojson",
        output_dir / "best-measurements.csv",
        output_dir / "best-measurements.gpx",
        output_dir / "chocholowska-lejowa-koscieliska.gpx",
        output_dir / "mietusia-sucha-woda.gpx",
        output_dir / "pozostale-pl-sk.gpx",
        output_dir / "best-measurements.shp.zip",
        output_dir / "metadata.json",
        output_dir / "statistics.json",
        output_dir / "statistics.md",
        output_dir / "katalog.xlsx",
    )
    for artifact_path in result.artifact_paths:
        assert artifact_path.exists()

    assert (output_dir / "katalog.dump").read_bytes().startswith(b"PGDMP")
    assert result.export_result.metadata["counts"] == {
        "objects": 1,
        "caves": 1,
        "relations": 0,
        "measurements": 2,
        "validation_warnings": 2,
        "validation_errors": 0,
    }
    statistics = json.loads((output_dir / "statistics.json").read_text())
    assert statistics["selected_points"]["horizontal_accuracy"] == {"known": 1, "unknown": 0}


def test_build_release_artifacts_cli_is_local_dry_run(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    dump_path = tmp_path / "build" / "katalog.dump"
    output_dir = tmp_path / "build" / "exports"
    _write_sample_data(data_dir)
    baseline = accept_source(data_dir)

    result = subprocess.run(
        [
            sys.executable,
            str(BUILD_RELEASE_SCRIPT),
            "--data-dir",
            str(data_dir),
            "--output-dir",
            str(output_dir),
            "--generated-at",
            GENERATED_AT,
            "--release-version",
            "v1.2.3",
            "--source-commit",
            "a" * 40,
            *cli_args(baseline),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    for filename in (
        "best-measurements.geojson",
        "best-measurements.csv",
        "best-measurements.gpx",
        "chocholowska-lejowa-koscieliska.gpx",
        "mietusia-sucha-woda.gpx",
        "pozostale-pl-sk.gpx",
        "best-measurements.shp.zip",
        "katalog.dump",
        "katalog.gpkg",
        "metadata.json",
        "statistics.json",
        "statistics.md",
        "katalog.xlsx",
    ):
        assert (output_dir / filename).exists()
    assert not dump_path.exists()
    assert "release artifacts: 1 objects, 1 caves, 2 measurements" in result.stdout
    statistics = json.loads((output_dir / "statistics.json").read_text())
    assert statistics["release"] == {"version": "v1.2.3", "source_commit": "a" * 40}
    assert statistics["generated_at"] == GENERATED_AT


def test_statistics_count_selected_points_separately_from_history(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    baseline = accept_source(data_dir)
    first = _valid_object()
    first["best_measurement"].update(
        mode="manual", measurement_id="m-001", reason="Confirmed older measurement"
    )
    first["measurements"][0].update(
        verification_status="zweryfikowany",
        horizontal_accuracy_m=0,
        verified_by="tester",
        verified_at="2026-05-16T10:00:00Z",
    )
    first["measurements"][1].update(verification_status="odrzucony", notes="Wrong position")
    _write_yaml(data_dir / "objects/KSW/KSW-0001.yml", first)
    second = _valid_object()
    second["id"] = "KSW-0002"
    second["membership_ordinal"] = 2
    second["external_refs"] = []
    second["category"] = "sztolnia"
    second["measurements"][1]["horizontal_accuracy_m"] = None
    _write_yaml(data_dir / "objects/KSW/KSW-0002.yml", second)
    cave = _valid_cave()
    _write_yaml(data_dir / "caves/C-0001.yml", cave)

    result = build_release_artifacts(
        **baseline,
        data_dir=data_dir,
        output_dir=tmp_path / "exports",
        generated_at=GENERATED_AT,
    )
    statistics = json.loads((result.export_result.output_dir / "statistics.json").read_text())
    assert statistics["release"] == {"version": None, "source_commit": None}
    assert statistics["counts"] == {"objects": 2, "caves": 1, "measurements": 4}
    assert statistics["selected_points"] == {
        "by_category": {"jaskinia_otwor": 1, "sztolnia": 1},
        "by_source": {"PIG": 1, "TPN": 1},
        "by_position_method": {"source_record": 2},
        "by_verification_status": {"nieweryfikowany": 1, "zweryfikowany": 1},
        "horizontal_accuracy": {"known": 1, "unknown": 1},
    }
    assert statistics["measurement_history"] == {
        "by_source": {"PIG": 2, "TPN": 2},
        "by_position_method": {"source_record": 4},
        "by_verification_status": {
            "nieweryfikowany": 2,
            "odrzucony": 1,
            "zweryfikowany": 1,
        },
    }
    report = (result.export_result.output_dir / "statistics.md").read_text()
    assert "| Otwory jaskiń | 1 |" in report
    assert "| Cave entrances | 1 |" in report
    assert "| Jaskynné vchody | 1 |" in report
    assert "| PIG | 1 | 2 |" in report
    assert "| Odrzucone | 0 | 1 |" in report


def test_statistics_use_packaged_method_and_tags_for_each_selected_measurement(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    baseline = accept_source(data_dir)
    cave = _valid_cave()
    cases = [
        ("ustalenie", ["lidar", "gnss_anchor"]),
        ("source_record", ["survey_anchor"]),
        ("siec_pomiarowa", ["gnss_anchor", "survey_anchor"]),
        ("gnss", []),
        ("ustalenie", ["gnss_anchor"]),
        ("ustalenie", ["lidar"]),
        ("source_record", ["lidar", "gnss_anchor"]),
    ]
    for number, (method, tags) in enumerate(cases, start=1):
        obj = _valid_object()
        obj["id"] = f"KSW-{number:04d}"
        obj["membership_ordinal"] = number
        obj["external_refs"] = []
        obj["measurements"][0].update(method=method, tags=tags, source="wlasne")
        obj["best_measurement"].update(
            mode="manual", measurement_id="m-001", reason="Retain the older reviewed point"
        )
        _write_yaml(data_dir / "objects/KSW" / f"{obj['id']}.yml", obj)
    _write_yaml(data_dir / "caves/C-0001.yml", cave)

    result = build_release_artifacts(
        **baseline,
        data_dir=data_dir,
        output_dir=tmp_path / "exports",
        generated_at=GENERATED_AT,
    )
    statistics = json.loads((result.export_result.output_dir / "statistics.json").read_text())
    assert statistics["selected_points"]["by_position_method"] == {
        "lidar_gnss": 1,
        "survey_anchor": 1,
        "siec_pomiarowa": 1,
        "gnss": 1,
        "ustalenie": 2,
        "source_record": 1,
    }
    assert statistics["measurement_history"]["by_position_method"] == {
        "lidar_gnss": 1,
        "survey_anchor": 1,
        "siec_pomiarowa": 1,
        "gnss": 1,
        "ustalenie": 2,
        "source_record": 8,
    }
    report = (result.export_result.output_dir / "statistics.md").read_text()
    assert "| LiDAR dowiązany GNSS | 1 | 1 |" in report
    assert "| GNSS (rodzaj nieudokumentowany) | 1 | 1 |" in report
    assert "| Sieć pomiarowa | 1 | 1 |" in report
    assert "| Punkt dowiązania — pierwotna metoda nieznana | 1 | 1 |" in report
    assert "| GNSS-anchored LiDAR | 1 | 1 |" in report
    assert "| LiDAR naviazaný na GNSS | 1 | 1 |" in report
    assert "| Opracowania własne | 7 | 7 |" in report


def test_export_preparation_rejects_selected_measurement_missing_from_history(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    dataset = read_catalog_projection(data_dir)
    dataset.objects[0].data["best_measurement"]["measurement_id"] = "m-999"
    with pytest.raises(ValueError, match="KSW-0001/m-999"):
        prepare_export_data(dataset, generated_at=GENERATED_AT)


def test_statistics_are_deterministic_and_support_an_empty_catalog(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    initialize_source(data_dir)
    baseline = accept_source(data_dir)
    reports = []
    for name in ("first", "second"):
        output_dir = tmp_path / name
        build_release_artifacts(
            **baseline,
            data_dir=data_dir,
            output_dir=output_dir,
            generated_at=GENERATED_AT,
        )
        reports.append(
            tuple((output_dir / f"statistics.{suffix}").read_bytes() for suffix in ("json", "md"))
        )
    assert reports[0] == reports[1]
    statistics = json.loads(reports[0][0])
    assert statistics["counts"] == {"objects": 0, "caves": 0, "measurements": 0}
    assert statistics["selected_points"]["horizontal_accuracy"] == {"known": 0, "unknown": 0}
    assert statistics["selected_points"]["by_source"] == {}
    assert statistics["selected_points"]["by_position_method"] == {}
    assert statistics["measurement_history"]["by_position_method"] == {}


def test_excel_preserves_best_and_full_history_with_local_measurement_ids(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    baseline = accept_source(data_dir)
    first = _valid_object()
    first["name_local"] = '=HYPERLINK("https://example.invalid", "name")'
    first["notes"] = "Original object notes"
    first["best_measurement"].update(mode="manual", measurement_id="m-001", reason="Older checked")
    first["measurements"][0]["horizontal_accuracy_m"] = 0
    first["measurements"][1].update(verification_status="odrzucony", notes="Rejected location")
    _write_yaml(data_dir / "objects/KSW/KSW-0001.yml", first)
    second = _valid_object()
    second["id"] = "KSW-0002"
    second["membership_ordinal"] = 2
    second["external_refs"] = []
    second["measurements"][1]["horizontal_accuracy_m"] = None
    _write_yaml(data_dir / "objects/KSW/KSW-0002.yml", second)
    cave = _valid_cave()
    _write_yaml(data_dir / "caves/C-0001.yml", cave)
    result = build_release_artifacts(
        **baseline,
        data_dir=data_dir,
        output_dir=tmp_path / "exports",
        generated_at=GENERATED_AT,
        release_version="v1.2.3",
        source_commit="a" * 40,
    )
    path = result.export_result.output_dir / "katalog.xlsx"
    assert path.is_file()
    book = load_workbook(path)
    assert book.sheetnames == ["Best", "Full"]
    best = _excel_records(book["Best"])
    full = _excel_records(book["Full"])
    assert len(best) == 2 and len(full) == 4
    assert [(r["ID obiektu"], r["ID pomiaru"]) for r in best] == [
        ("KSW-0001", "m-001"),
        ("KSW-0002", "m-002"),
    ]
    assert best[0]["Nazwa obiektu"] == first["name_local"]
    assert best[0]["Dokładność pozioma [m]"] == 0
    assert best[1]["Dokładność pozioma [m]"] is None
    assert best[0]["Szerokość WGS84 [°]"] == pytest.approx(KSW_LAT)
    assert best[0]["Data pomiaru"] == datetime(2026, 5, 15)
    assert [r["Wybrany do eksportu"] for r in full] == ["Tak", "Nie", "Nie", "Tak"]
    assert full[0]["Dokładność pozioma [m]"] == 0
    assert full[3]["Dokładność pozioma [m]"] is None
    assert full[1]["Weryfikacja"] == "odrzucony"
    assert full[1]["Uwagi pomiaru"] == "Rejected location"
    assert full[0]["Uwagi obiektu"] == first["notes"]
    assert full[0]["Nazwa jaskini"] == cave["name"]
    assert (
        json.loads(full[0]["Referencje obiektu (JSON)"])[0]["external_id"]
        == first["external_refs"][0]["external_id"]
    )
    assert json.loads(full[0]["Referencje jaskini (JSON)"])[0]["external_id"] == "1094"
    assert full[0]["Nadany prefiks"] == "KSW"
    assert full[0]["Utworzył obiekt"] == "dl"
    assert full[0]["Data źródła"] is None
    for sheet, count in ((book["Best"], 2), (book["Full"], 4)):
        assert sheet.freeze_panes == "C7"
        assert sheet.sheet_view.showGridLines is False
        table = next(iter(sheet.tables.values()))
        assert table.ref.endswith(str(count + 6))
        assert table.autoFilter is not None
        assert not sheet.merged_cells.ranges
        assert all(cell.data_type != "f" for row in sheet for cell in row)
    assert "v1.2.3" in book.properties.description
    assert "a" * 40 in book.properties.description
    book.close()


@pytest.mark.parametrize(
    ("source_date", "expected"),
    [
        ("0001-01-01", "0001-01-01"),
        ("1895-06-15", "1895-06-15"),
        ("1899-12-31", "1899-12-31"),
        ("1900-01-01", datetime(1900, 1, 1)),
        ("1900-01-02", datetime(1900, 1, 2)),
        ("1900-02-28", datetime(1900, 2, 28)),
        ("1900-03-01", datetime(1900, 3, 1)),
        ("2024-02-29", datetime(2024, 2, 29)),
        ("9999-12-31", datetime(9999, 12, 31)),
    ],
)
def test_excel_preserves_dates_across_1900_boundary(
    tmp_path: Path, source_date: str, expected: str | datetime
) -> None:
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    baseline = accept_source(data_dir)
    obj = _valid_object()
    for measurement in obj["measurements"]:
        measurement.update(observed_date=source_date, source_date=source_date)
    _write_yaml(data_dir / "objects/KSW/KSW-0001.yml", obj)

    result = build_release_artifacts(
        **baseline,
        data_dir=data_dir,
        output_dir=tmp_path / "exports",
        generated_at=GENERATED_AT,
    )

    book = load_workbook(result.excel_path)
    try:
        best = _excel_records(book["Best"])
        full = _excel_records(book["Full"])
        assert [row["Data pomiaru"] for row in best] == [expected]
        assert [row["Data pomiaru"] for row in full] == [expected, expected]
        assert [row["Data źródła"] for row in full] == [expected, expected]
    finally:
        book.close()


def test_excel_empty_catalog_has_headers_without_fake_records(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    initialize_source(data_dir)
    baseline = accept_source(data_dir)
    build_release_artifacts(
        **baseline,
        data_dir=data_dir,
        output_dir=tmp_path / "exports",
        generated_at=GENERATED_AT,
    )
    path = tmp_path / "exports/katalog.xlsx"
    assert path.is_file()
    book = load_workbook(path)
    assert book.sheetnames == ["Best", "Full"]
    assert all(sheet.max_row == 6 for sheet in book)
    assert all(sheet["A6"].value == "ID obiektu" for sheet in book)
    book.close()


def test_excel_rejects_text_truncation_without_replacing_existing_workbook(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    baseline = accept_source(data_dir)
    result = build_release_artifacts(
        **baseline,
        data_dir=data_dir,
        output_dir=tmp_path / "exports",
        generated_at=GENERATED_AT,
    )
    before = result.excel_path.read_bytes()
    dataset = read_catalog_projection(data_dir)
    dataset.objects[0].data["name_local"] = "x" * 32768
    with pytest.raises(ValueError, match="Cannot export Excel cell: Best"):
        write_excel_export(
            prepare_export_data(dataset, generated_at=GENERATED_AT),
            output_path=result.excel_path,
            release_version=None,
            source_commit=None,
        )
    assert result.excel_path.read_bytes() == before
    assert not result.excel_path.with_suffix(".xlsx.tmp").exists()


def test_cli_artifact_list_drives_release_workflow_without_publishing(tmp_path):
    """A wildcard, split pathname or stale second list would send wrong files to gh."""
    import os

    import yaml

    data = _write_sample_data(tmp_path / "data")
    baseline = accept_source(data)
    output = tmp_path / "exports with spaces\nand newline"
    output.mkdir()
    (output / "stale.zip").write_bytes(b"do not upload")
    command = [
        sys.executable,
        str(BUILD_RELEASE_SCRIPT),
        "--data-dir",
        str(data),
        "--output-dir",
        str(output),
        "--generated-at",
        GENERATED_AT,
        "--artifact-list",
        *cli_args(baseline),
    ]
    blocked = subprocess.run(command, capture_output=True, check=False)
    assert blocked.returncode == 1
    assert blocked.stdout == b""
    assert b"unmanaged entries" in blocked.stderr
    assert {p.name: p.read_bytes() for p in output.iterdir()} == {"stale.zip": b"do not upload"}
    (output / "stale.zip").unlink()
    result = subprocess.run(command, capture_output=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    filenames = (
        "katalog.dump",
        "katalog.gpkg",
        "best-measurements.geojson",
        "best-measurements.csv",
        "best-measurements.gpx",
        "chocholowska-lejowa-koscieliska.gpx",
        "mietusia-sucha-woda.gpx",
        "pozostale-pl-sk.gpx",
        "best-measurements.shp.zip",
        "metadata.json",
        "statistics.json",
        "statistics.md",
        "katalog.xlsx",
    )
    assets = [str(output / name) for name in filenames]
    assert result.stderr == b""
    assert result.stdout == b"".join(os.fsencode(p) + b"\0" for p in assets)
    assert set(p.name for p in output.iterdir()) == set(filenames)
    # Run the workflow build in a fresh directory, adapting only its installed uv runner.
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/release.yml").read_text())
    steps = workflow["jobs"]["release"]["steps"]
    build = next(s for s in steps if s["name"] == "Build release artifacts")
    runner = (
        'uv() { shift 4; "$U10_PYTHON" "$U10_BUILDER" "$@" '
        '--data-dir "$U10_DATA" --output-dir "$U10_OUTPUT" '
        '--history-repo "$U10_HISTORY"; }\n'
    )
    env = {
        **os.environ,
        "U10_PYTHON": sys.executable,
        "U10_BUILDER": str(BUILD_RELEASE_SCRIPT),
        "U10_DATA": str(data),
        "U10_OUTPUT": str(output),
        "U10_HISTORY": str(baseline["history_repo"]),
        "HISTORY_BASE_SHA": baseline["base_ref"],
        "GITHUB_REF_NAME": "v1.2.3",
        "GITHUB_SHA": "a" * 40,
    }
    completed = subprocess.run(
        ["bash", "-e", "-c", runner + build["run"]],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert (tmp_path / "build/release-artifacts.list").read_bytes() == result.stdout
    (output / "stale.zip").write_bytes(b"even a later extra must not be uploaded")
    publish = next(s for s in steps if s["name"] == "Publish GitHub Release")
    script = publish["run"].replace("${{ steps.version.outputs.VERSION }}", "v1.2.3")
    capture = tmp_path / "gh-arguments"
    completed = subprocess.run(
        ["bash", "-e", "-c", 'gh() { printf "%s\\0" "$@" > "$GH_CAPTURE"; }\n' + script],
        cwd=tmp_path,
        env={**os.environ, "GH_CAPTURE": str(capture)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    expected = [
        "release",
        "create",
        "v1.2.3",
        *assets,
        "--title",
        "v1.2.3",
        "--notes-file",
        "release_notes.md",
    ]
    assert capture.read_bytes() == b"".join(os.fsencode(p) + b"\0" for p in expected)

    previous = {p.name: p.read_bytes() for p in output.iterdir()}
    (data / "publications/.gitkeep").unlink()
    (data / "publications").rmdir()
    failed = subprocess.run(
        ["bash", "-e", "-c", runner + build["run"]],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode == 1
    assert "required data directory" in failed.stderr
    assert {p.name: p.read_bytes() for p in output.iterdir()} == previous
