"""Regressions for source content lost by the PBI-065 historical mutations."""

import csv
from copy import deepcopy
from pathlib import Path

import pytest
from test_staging_review import (
    TPN_GLOBALID,
    _cave_data,
    _nr_inwent_ref,
    _object_data,
    _read_yaml,
    _tpn_staging,
    _write_yaml,
)

from gps_kataster_obiektow_tatr.pig_staging import build_pig_staging
from gps_kataster_obiektow_tatr.pig_staging import write_staging_files as write_pig_staging
from gps_kataster_obiektow_tatr.staging_review import (
    StagingReports,
    apply_review_decisions,
    load_staging_reports,
)
from gps_kataster_obiektow_tatr.tpn_staging import build_tpn_staging
from gps_kataster_obiektow_tatr.tpn_staging import write_staging_files as write_tpn_staging
from gps_kataster_obiektow_tatr.validator import has_errors, validate_data_dir

GENERATED_AT = "2026-06-17T23:41:52+02:00"
PIG_LINK = "https://jaskiniepolski.pgi.gov.pl/Details/Information/1692"
PIG_NOTES = (
    "PIG aliases: Nyża Żółta; Schronisko Źródlane\n"
    "PIG sector: Dolina Kościeliska — Wschód\n"
    "PIG morphometry: length_m=123,4, depth_m=-7,8, denivelation_m=9,1"
)
TPN_NOTES = (
    "TPN length: 234,5\nTPN depth: -8,6\nTPN denivelation: 11,2\n"
    "TPN verification/location note: Lokalizacja według opisu źródłowego\n"
    "TPN notes: Dwa otwory; zachować opis ściany północnej"
)


def _write_source(path: Path, row: dict[str, str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)


def _create_pair(data_dir: Path, reports: StagingReports, source: str) -> None:
    result = apply_review_decisions(
        {
            "reviewed_at": "2026-06-18T09:00:00Z",
            "reviewed_by": "dl",
            "decisions": [
                {"action": action, "source": source, "record_number": 1}
                for action in ("create_cave", "create_object")
            ],
        },
        staging_reports=reports,
        data_dir=data_dir,
    )
    assert not result.has_errors, result.issues
    assert set(result.written_paths) == {
        data_dir / "caves/C-0001.yml",
        data_dir / "objects/KSW/KSW-0001.yml",
    }
    assert not has_errors(validate_data_dir(data_dir))


@pytest.mark.parametrize(
    "source_year, generated_at, expected_date",
    [
        ("2014", GENERATED_AT, "2014-12-31"),
        ("", GENERATED_AT, "2026-06-17"),
        ("", "2026-06-17T21:41:52Z", "2026-06-17"),
    ],
)
def test_pig_source_content_survives_import_json_review_and_yaml(
    tmp_path: Path, source_year: str, generated_at: str, expected_date: str
) -> None:
    # Removing alias/sector/morphometry/year or source_date must fail at the public boundary.
    source = tmp_path / "pig.csv"
    _write_source(
        source,
        {
            "ID": "1692",
            "Nazwa": "Nyża z opisem źródłowym",
            "Inne nazwy": "Nyża Żółta; Schronisko Źródlane",
            "Nr inw.": "T.F-09.33",
            "X 1992": "152267,23",
            "Y 1992": "563744,25",
            "H (wg PIG)": "1266,7",
            "B": "49,23459299",
            "L": "19,87589498",
            "Sektor (nazwa)": "Dolina Kościeliska — Wschód",
            "Długość [m]": "123,4",
            "Głębokość [m]": "-7,8",
            "Deniwelacja [m]": "9,1",
            "Stan na rok": source_year,
            "Link": PIG_LINK,
        },
    )
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    report = build_pig_staging(source, generated_at=generated_at, data_dir=data_dir)
    expected_notes = PIG_NOTES + ("\nPIG source state year: 2014" if source_year else "")
    assert report.proposed_caves[0]["notes"] == expected_notes
    assert [issue.code for issue in report.issues] == (
        [] if source_year else ["PIG_SOURCE_YEAR_INVALID"]
    )
    if not source_year:
        issue = report.issues[0]
        assert (issue.severity, issue.record_number, issue.pig_id) == ("warning", 1, "1692")
        assert isinstance(issue.description, str) and "generated date" in issue.description.lower()
    json_path, _ = write_pig_staging(report, output_dir=tmp_path / "staging")
    reports = load_staging_reports(pig_staging_path=json_path, tpn_staging_path=None)
    assert reports.pig is not None
    assert reports.pig["proposed_caves"][0]["notes"] == expected_notes
    proposal = reports.pig["proposed_objects"][0]
    measurement = proposal["measurements"][0]
    assert measurement["observed_date"] == measurement["source_date"] == expected_date
    assert measurement["elevation_m"] == 1266.7
    # Existing operator annotations and a non-staging tag must survive finalization too.
    proposal["notes"] += "\nNotatka operatora: zachować wariant nazwy."
    measurement["notes"] += "\nUwaga pomiaru: wysokość źródłowa."
    measurement["tags"].append("opis_źródłowy")
    before = deepcopy(reports.pig)
    _create_pair(data_dir, reports, "PIG")
    cave = _read_yaml(data_dir / "caves/C-0001.yml")
    obj = _read_yaml(data_dir / "objects/KSW/KSW-0001.yml")
    assert cave["notes"] == expected_notes
    assert obj["notes"] == (
        "Imported from PIG source record after operator review.\n"
        "Notatka operatora: zachować wariant nazwy."
    )
    final_measurement = obj["measurements"][0]
    assert final_measurement["notes"] == (
        "PIG source-record measurement imported after operator review; not field-verified."
        f" Source: {PIG_LINK}\nUwaga pomiaru: wysokość źródłowa."
    )
    assert final_measurement["source"] == "PIG"
    assert final_measurement["source_ref"] == "PIG:1692"
    assert final_measurement["observed_date"] == final_measurement["source_date"] == expected_date
    assert final_measurement["elevation_m"] == 1266.7
    assert final_measurement["tags"] == ["pig", "opis_źródłowy"]
    assert final_measurement["verification_status"] == "nieweryfikowany"
    assert [(r["system"], r["ref_type"], r["external_id"]) for r in cave["external_refs"]] == [
        ("NR_INWENT", "inventory_number", "T.F-09.33"),
        ("PIG", "catalog_id", "1692"),
        ("PIG", "url", PIG_LINK),
    ]
    assert reports.pig == before


def test_tpn_source_notes_and_date_survive_import_json_review_and_yaml(tmp_path: Path) -> None:
    # Dropping any populated TPN cave-note column or the opening suffix must fail.
    source = tmp_path / "tpn.csv"
    _write_source(
        source,
        {
            "NR_INWENT": "T.F-09.33",
            "NAZWA": "Nyża z opisem źródłowym",
            "GLOBALID": TPN_GLOBALID,
            "X1992": "152267,23",
            "Y1992": "563744,25",
            "Z": "1267,8",
            "LAST_EDI_1": "2021-08-09 00:00:00",
            "OTWÓR": "Otwór północny — szczelina",
            "DLUGOSC": "234,5",
            "GLEBOKOSC": "-8,6",
            "DENIWELACJ": "11,2",
            "WER_LOK": "Lokalizacja według opisu źródłowego",
            "UWAGI": "Dwa otwory; zachować opis ściany północnej",
        },
    )
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    report = build_tpn_staging(
        source, generated_at=GENERATED_AT, data_dir=data_dir, pig_staging_path=None
    )
    assert report.proposed_caves[0]["notes"] == TPN_NOTES
    json_path, _ = write_tpn_staging(report, output_dir=tmp_path / "staging")
    reports = load_staging_reports(pig_staging_path=None, tpn_staging_path=json_path)
    assert reports.tpn is not None
    assert reports.tpn["proposed_caves"][0]["notes"] == TPN_NOTES
    measurement = reports.tpn["proposed_objects"][0]["measurements"][0]
    assert measurement["observed_date"] == measurement["source_date"] == "2021-08-09"
    assert measurement["elevation_m"] == 1267.8
    before = deepcopy(reports.tpn)
    _create_pair(data_dir, reports, "TPN")
    cave = _read_yaml(data_dir / "caves/C-0001.yml")
    obj = _read_yaml(data_dir / "objects/KSW/KSW-0001.yml")
    assert cave["notes"] == TPN_NOTES
    assert obj["notes"] == (
        "Imported from TPN source record after operator review.\n"
        "TPN opening: Otwór północny — szczelina"
    )
    final_measurement = obj["measurements"][0]
    assert final_measurement["notes"] == (
        "TPN source-record measurement imported after operator review; not field-verified."
    )
    assert final_measurement["source"] == "TPN"
    assert final_measurement["source_ref"] == f"TPN:{TPN_GLOBALID}"
    assert final_measurement["observed_date"] == final_measurement["source_date"] == "2021-08-09"
    assert final_measurement["elevation_m"] == 1267.8
    assert final_measurement["tags"] == ["tpn"]
    assert final_measurement["verification_status"] == "nieweryfikowany"
    assert cave["external_refs"] == reports.tpn["proposed_caves"][0]["external_refs"]
    assert obj["external_refs"] == reports.tpn["proposed_objects"][0]["external_refs"]
    assert reports.tpn == before


@pytest.mark.parametrize("refs_already_present", [False, True])
def test_review_preserves_distinct_refs_after_duplicates_in_catalog_and_batch(
    tmp_path: Path, refs_already_present: bool
) -> None:
    # continue→break loses a later distinct ref; removing seen.add duplicates within one list.
    data_dir = tmp_path / "data"
    object_path = data_dir / "objects/KSW/KSW-0001.yml"
    cave_path = data_dir / "caves/C-0001.yml"
    report = _tpn_staging()
    first = report["matched_measurements"][0]
    original_ref = deepcopy(first["object_external_refs"][0])
    original_ref["notes"] = "Dotychczasowa notatka referencji; zachować."
    distinct = {
        "system": "inne",
        "ref_type": "other",
        "external_id": "notatnik:otwór-2",
        "scope": "object",
        "notes": "Odrębna legalna referencja po duplikacie.",
    }
    catalog_distinct = {**distinct, "external_id": "notatnik:jaskinia", "scope": "cave"}
    obj = _object_data(cave_id="C-0001", notes="Istniejąca notatka obiektu — źródło terenowe.")
    cave = _cave_data(object_ids=["KSW-0001"])
    cave["notes"] = "Istniejąca notatka jaskini — historia nazw."
    obj["external_refs"] = [original_ref] if refs_already_present else []
    cave["external_refs"] = [_nr_inwent_ref()] if refs_already_present else []
    _write_yaml(object_path, obj)
    _write_yaml(cave_path, cave)
    # Schema uniqueItems rejects byte-identical dictionaries before merging. These legal
    # annotations differ, while the persisted source identity is the same.
    duplicate = {**original_ref, "notes": "Powtórzona tożsamość z inną notatką."}
    inventory_duplicate = {**_nr_inwent_ref(), "notes": "Powtórzony numer źródłowy."}
    first["object_external_refs"] = [deepcopy(original_ref), distinct, duplicate]
    first["cave_external_refs"] = [_nr_inwent_ref(), catalog_distinct, inventory_duplicate]
    second = deepcopy(first)
    second["record_number"] = 2
    next_globalid = "{PBI-065-SECOND}"
    second["measurement"].update(id="m-003", source_ref=f"TPN:{next_globalid}")
    next_ref = {**original_ref, "external_id": next_globalid, "notes": "Drugi rekord źródłowy."}
    second["object_external_refs"] = [deepcopy(original_ref), next_ref, deepcopy(duplicate)]
    report["matched_measurements"].append(second)
    report["rows"].append({**report["rows"][0], "record_number": 2, "globalid": next_globalid})
    before = deepcopy(report)
    result = apply_review_decisions(
        {
            "decisions": [
                {"action": "add_measurement", "source": "TPN", "record_number": number}
                for number in (1, 2)
            ]
        },
        staging_reports=StagingReports(tpn=report),
        data_dir=data_dir,
    )
    assert not result.has_errors, result.issues
    assert set(result.written_paths) == {object_path, cave_path}
    final_obj, final_cave = _read_yaml(object_path), _read_yaml(cave_path)
    assert final_obj["external_refs"] == [original_ref, distinct, next_ref]
    assert final_cave["external_refs"] == [_nr_inwent_ref(), catalog_distinct]
    assert final_obj["notes"] == "Istniejąca notatka obiektu — źródło terenowe."
    assert final_cave["notes"] == "Istniejąca notatka jaskini — historia nazw."
    assert final_obj["measurements"][0] == obj["measurements"][0]
    assert [m["id"] for m in final_obj["measurements"]] == ["m-001", "m-002", "m-003"]
    assert [m["source_ref"] for m in final_obj["measurements"]][1:] == [
        f"TPN:{TPN_GLOBALID}",
        f"TPN:{next_globalid}",
    ]
    assert report == before
    assert not has_errors(validate_data_dir(data_dir))
