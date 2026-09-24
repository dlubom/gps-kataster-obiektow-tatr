import csv
import importlib.util
import json
import subprocess
import sys
import zipfile
from copy import deepcopy
from dataclasses import asdict, replace
from html import escape
from pathlib import Path

import pytest
import yaml

from gps_kataster_obiektow_tatr.coordinates import pl1992_to_wgs84, wgs84_to_1992
from gps_kataster_obiektow_tatr.prefix_resolver import (
    PrefixResolution,
    PrefixResolutionArea,
    PrefixResolutionStatus,
)
from gps_kataster_obiektow_tatr.staging_review import (
    StagingReports,
    apply_review_decisions,
    load_staging_reports,
)
from gps_kataster_obiektow_tatr.tpn_staging import (
    TpnStagingReport,
    _Candidate,
    _deduplicate_candidates,
    _pig_measurement_ids,
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


def _unresolved_report(tmp_path: Path, *, x: str = "152000", y: str = "563000") -> TpnStagingReport:
    source = tmp_path / "ambiguous.csv"
    pig = tmp_path / "pig.json"
    _write_pig_staging(
        pig,
        object_id="KSW-0001",
        cave_id="C-0001",
        nr_inwent="T.D-08.07",
        name="Known opening",
        x_1992=152267.23,
        y_1992=563744.25,
    )
    rows = [
        _tpn_row(
            nr_inwent="T.D-08.07",
            name=f"Niejednoznaczna nyża {number}",
            globalid=f"{{UNRESOLVED-{number}}}",
            x_1992=x,
            y_1992=y,
        )
        for number in (1, 2)
    ]
    rows[0][_tpn_header().index("OTWÓR")] = "Otwór południowy"
    _write_tpn_csv(source, rows)
    return build_tpn_staging(
        source,
        generated_at="2026-09-24T10:00:00Z",
        data_dir=tmp_path / "data",
        pig_staging_path=pig,
    )


def test_unresolved_payload_survives_json_round_trip_without_final_data(tmp_path: Path) -> None:
    report = _unresolved_report(tmp_path)
    json_path, _ = write_staging_files(report, output_dir=tmp_path / "staging")
    loaded = load_staging_reports(pig_staging_path=None, tpn_staging_path=json_path).tpn
    assert loaded is not None
    assert loaded["format_version"] == 2
    assert loaded["source_path"] == str(tmp_path / "ambiguous.csv")
    assert loaded["generated_at"] == "2026-09-24T10:00:00Z"
    assert loaded["record_count"] == loaded["unresolved_count"] == 2
    assert loaded["matched_count"] == loaded["new_count"] == loaded["rejected_count"] == 0
    assert (
        loaded["matched_measurements"]
        == loaded["proposed_caves"]
        == loaded["proposed_objects"]
        == []
    )
    expected_wgs84 = pl1992_to_wgs84(x_1992=152000, y_1992=563000)
    for number, row in enumerate(loaded["rows"], start=1):
        assert row["record_number"] == number
        assert row["globalid"] == f"{{UNRESOLVED-{number}}}"
        assert row["nr_inwent"] == "T.D-08.07"
        assert row["name"] == f"Niejednoznaczna nyża {number}"
        assert row["status"] == "unresolved"
        assert (
            row["object_id"] is row["cave_id"] is row["match_strategy"] is row["distance_m"] is None
        )
        payload = row["payload"]
        assert payload == report.rows[number - 1].payload
        assert payload["category"] == "jaskinia_otwor"
        measurement = payload["measurement"]
        assert "id" not in measurement
        assert measurement["source"] == "TPN"
        assert measurement["source_ref"] == f"TPN:{{UNRESOLVED-{number}}}"
        assert measurement["observed_date"] == measurement["source_date"] == "2022-05-25"
        assert (measurement["lat"], measurement["lon"]) == (expected_wgs84.lat, expected_wgs84.lon)
        assert (measurement["x_1992"], measurement["y_1992"], measurement["elevation_m"]) == (
            152000,
            563000,
            1266,
        )
        assert measurement["verification_status"] == "nieweryfikowany"
        assert measurement["created_at"] == loaded["generated_at"]
        assert measurement["created_by"] == "importer:tpn"
        assert payload["object_external_refs"][0]["external_id"] == row["globalid"]
        assert payload["object_external_refs"][0]["scope"] == "object"
        assert payload["cave_external_refs"][0]["external_id"] == row["nr_inwent"]
        assert payload["cave_external_refs"][0]["scope"] == "cave"
        assert "TPN length: 3" in payload["cave_notes"]
    assert "Otwór południowy" in loaded["rows"][0]["payload"]["object_notes"]
    assert not (tmp_path / "data").exists()


@pytest.mark.parametrize("x", ["bad", "", "NaN", "Infinity"])
def test_unresolved_invalid_coordinates_have_no_payload(tmp_path: Path, x: str) -> None:
    report = _unresolved_report(tmp_path, x=x)
    json_path, _ = write_staging_files(report, output_dir=tmp_path / "staging")
    data = json.loads(json_path.read_text())
    assert data["rejected_count"] == 2
    assert all(row["status"] == "rejected" and "payload" not in row for row in data["rows"])
    assert {issue.code for issue in report.issues} == {"TPN_POINT_COORDINATES_INVALID"}
    assert not (tmp_path / "data").exists()


@pytest.mark.parametrize(
    ("lat", "lon", "status", "issue_code"),
    [
        (48.8566, 2.3522, "rejected", "POINT_OUTSIDE_PL_SK"),
        (52.2297, 21.0122, "unresolved", "POINT_OUTSIDE_VALLEYS"),
    ],
)
def test_unresolved_payload_respects_geographic_boundary(
    tmp_path: Path, lat: float, lon: float, status: str, issue_code: str
) -> None:
    point = wgs84_to_1992(lat=lat, lon=lon)
    report = _unresolved_report(tmp_path, x=str(point.x_1992), y=str(point.y_1992))
    json_path, _ = write_staging_files(report, output_dir=tmp_path / "staging")
    data = json.loads(json_path.read_text())
    assert len(data["rows"]) == 2
    assert data["issues"] == [asdict(issue) for issue in report.issues]
    assert data["issue_count"] == len(data["issues"])
    assert all(row["status"] == status for row in data["rows"])
    assert all(("payload" in row) == (status == "unresolved") for row in data["rows"])
    assert len(report.issues) == (2 if status == "rejected" else 4)
    for number in (1, 2):
        row_issues = [issue for issue in report.issues if issue.record_number == number]
        assert {issue.code for issue in row_issues} == (
            {issue_code} if status == "rejected" else {issue_code, "TPN_NR_INWENT_AMBIGUOUS"}
        )
        assert all(issue.severity == "warning" for issue in row_issues)
        assert all(issue.globalid == f"{{UNRESOLVED-{number}}}" for issue in row_issues)
        assert all(issue.nr_inwent == "T.D-08.07" for issue in row_issues)
        assert all(issue.description for issue in row_issues)
        if status == "rejected":
            assert row_issues[0].description.endswith(" Row rejected.")
    assert data["matched_measurements"] == data["proposed_caves"] == data["proposed_objects"] == []
    assert not (tmp_path / "data").exists()


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize(
    "action", [None, "reject", "unresolved", "add_measurement", "create_object", "create_cave"]
)
def test_unresolved_payload_does_not_authorize_materialization(
    tmp_path: Path, legacy: bool, action: str | None
) -> None:
    report = _unresolved_report(tmp_path)
    json_path, _ = write_staging_files(report, output_dir=tmp_path / "staging")
    data = json.loads(json_path.read_text())
    if legacy:
        data.pop("format_version", None)
        for row in data["rows"]:
            row.pop("payload", None)
    decisions = (
        []
        if action is None
        else [
            {
                "action": action,
                "source": "TPN",
                "record_number": 1,
                "target_object_id": "KSW-0001",
                "reason": "Pending operator review.",
            }
        ]
    )
    result = apply_review_decisions(
        {"decisions": decisions},
        staging_reports=StagingReports(tpn=data),
        data_dir=tmp_path / "data",
        initialize_data_dir=True,
    )
    assert result.has_errors == (action in {"add_measurement", "create_object", "create_cave"})
    assert result.written_paths == ()
    if action == "add_measurement":
        assert result.issues[0].code == "STAGING_MEASUREMENT_UPDATE_MISSING"
        assert "row 1" in result.issues[0].description
    assert not (tmp_path / "data").exists()


def test_unresolved_payload_keeps_matched_new_and_rejected_contracts(tmp_path: Path) -> None:
    _unresolved_report(tmp_path)
    source = tmp_path / "ambiguous.csv"
    with source.open(newline="") as handle:
        rows = list(csv.reader(handle))[1:]
    rows[0][_tpn_header().index("NAZWA")] = "Sztolnia niejednoznaczna"
    rows.extend(
        [
            _tpn_row(
                nr_inwent="T.D-08.07",
                name="Known opening",
                globalid="{MATCHED}",
                x_1992="152267.23",
                y_1992="563744.25",
            ),
            _tpn_row(
                nr_inwent="T.D-00.01",
                name="New opening",
                globalid="{NEW}",
                x_1992="154416.50",
                y_1992="567679.48",
            ),
            _tpn_row(
                nr_inwent="T.D-08.07",
                name="Bad opening",
                globalid="{BAD}",
                x_1992="bad",
                y_1992="563000",
            ),
        ]
    )
    _write_tpn_csv(source, rows)
    report = build_tpn_staging(
        source,
        generated_at="2026-09-24T10:00:00Z",
        data_dir=tmp_path / "data",
        pig_staging_path=tmp_path / "pig.json",
        prefix_resolver=StubResolver(),
    )
    json_path, _ = write_staging_files(report, output_dir=tmp_path / "staging")
    data = json.loads(json_path.read_text())
    assert [row["status"] for row in data["rows"]] == [
        "unresolved",
        "unresolved",
        "matched",
        "new",
        "rejected",
    ]
    assert all("payload" not in row for row in data["rows"][2:])
    assert data["rows"][0]["payload"]["category"] == "sztolnia"
    assert data["rows"][2]["cave_id"] == "C-0001"
    assert data["rows"][3]["cave_id"] == "C-0002"
    assert data["matched_measurements"][0]["target_object_id"] == "KSW-0001"
    assert data["matched_measurements"][0]["measurement"]["id"] == "m-002"
    assert data["proposed_objects"][0]["id"] == "KSW-0002"
    assert data["proposed_objects"][0]["measurements"][0]["id"] == "m-001"
    assert data["proposed_caves"][0]["id"] == "C-0002"
    assert not (tmp_path / "data").exists()


def test_two_matches_to_one_object_get_distinct_proposed_measurement_ids(tmp_path: Path) -> None:
    source = tmp_path / "tpn.csv"
    data_dir = tmp_path / "data"
    _write_final_pig_candidate(data_dir)
    _write_tpn_csv(
        source,
        [
            _tpn_row(
                nr_inwent="T.F-09.33",
                name="Szczelina pod Gankowa II",
                globalid="{TPN-A}",
                x_1992="152267,23",
                y_1992="563744,25",
            ),
            _tpn_row(
                nr_inwent="T.F-09.33",
                name="Szczelina pod Gankowa II",
                globalid="{TPN-B}",
                x_1992="152267,23",
                y_1992="563744,25",
            ),
        ],
    )

    report = build_tpn_staging(
        source,
        generated_at="2026-05-16T09:00:00Z",
        data_dir=data_dir,
        pig_staging_path=None,
        prefix_resolver=StubResolver(),
    )

    assert [row.status for row in report.rows] == ["matched", "matched"]
    assert [(row.record_number, row.globalid, row.object_id) for row in report.rows] == [
        (1, "{TPN-A}", "KSW-0001"),
        (2, "{TPN-B}", "KSW-0001"),
    ]
    assert [item["record_number"] for item in report.matched_measurements] == [1, 2]
    assert [item["measurement"]["created_at"] for item in report.matched_measurements] == [
        "2026-05-16T09:00:00Z",
        "2026-05-16T09:00:00Z",
    ]
    assert [item["measurement"]["id"] for item in report.matched_measurements] == ["m-003", "m-004"]


def test_matched_objects_keep_separate_measurement_counters(tmp_path: Path) -> None:
    source = tmp_path / "tpn.csv"
    data_dir = tmp_path / "data"
    _write_final_pig_candidate(data_dir)
    first_object = yaml.safe_load((data_dir / "objects/KSW/KSW-0001.yml").read_text())
    first_cave = yaml.safe_load((data_dir / "caves/C-0001.yml").read_text())
    second_object = deepcopy(first_object)
    second_object.update(id="KSW-0002", cave_id="C-0002", name_local="Other opening")
    second_object["measurements"] = second_object["measurements"][:1]
    second_object["best_measurement"] = {"mode": "auto", "measurement_id": "m-001"}
    second_cave = deepcopy(first_cave)
    second_cave.update(id="C-0002", name="Other opening", object_ids=["KSW-0002"])
    second_cave["external_refs"][0]["external_id"] = "T.F-09.34"
    (data_dir / "objects/KSW/KSW-0002.yml").write_text(yaml.safe_dump(second_object))
    (data_dir / "caves/C-0002.yml").write_text(yaml.safe_dump(second_cave))
    _write_tpn_csv(
        source,
        [
            _tpn_row(
                nr_inwent="T.F-09.33",
                name="Szczelina pod Gankowa II",
                globalid="{TPN-A}",
                x_1992="152267,23",
                y_1992="563744,25",
            ),
            _tpn_row(
                nr_inwent="T.F-09.34",
                name="Other opening",
                globalid="{TPN-B}",
                x_1992="152267,23",
                y_1992="563744,25",
            ),
        ],
    )

    report = build_tpn_staging(
        source,
        generated_at="2026-05-16T09:00:00Z",
        data_dir=data_dir,
        pig_staging_path=None,
        prefix_resolver=StubResolver(),
    )

    assert [item["target_object_id"] for item in report.matched_measurements] == [
        "KSW-0001",
        "KSW-0002",
    ]
    assert [item["measurement"]["id"] for item in report.matched_measurements] == ["m-003", "m-002"]


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
    assert report.rows[0].distance_m == 0.0
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


@pytest.mark.parametrize("with_staging", [False, True])
def test_accepted_pig_object_is_one_final_candidate(tmp_path: Path, with_staging: bool) -> None:
    tpn_csv = tmp_path / "tpn.csv"
    pig_staging = tmp_path / "pig-staging.json"
    data_dir = tmp_path / "data"
    _write_tpn_csv(
        tpn_csv,
        [
            _tpn_row(
                nr_inwent="T.F-09.33",
                name="Szczelina pod Gankowa II",
                globalid="{D7C052E6-D584-4320-B886-367312D2219F}",
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
    _write_final_pig_candidate(data_dir)

    report = build_tpn_staging(
        tpn_csv,
        generated_at="2026-05-16T09:00:00Z",
        data_dir=data_dir,
        pig_staging_path=pig_staging if with_staging else None,
        prefix_resolver=StubResolver(),
    )

    assert report.rows[0].status == "matched"
    assert report.rows[0].object_id == "KSW-0001"
    assert report.rows[0].match_strategy == "nr_inwent"
    assert report.issues == ()
    assert report.matched_measurements[0]["match"]["source"] == "data_yaml"
    assert report.matched_measurements[0]["measurement"]["id"] == "m-003"


def test_final_candidate_wins_independently_of_source_order() -> None:
    staging = _Candidate(
        source="pig_staging",
        cave_id="C-0001",
        object_id="KSW-0001",
        nr_inwent="T.F-09.33",
        name="Szczelina pod Gankowa II",
        x_1992=152267.23,
        y_1992=563744.25,
        globalids=(),
        next_measurement_id="m-002",
        pig_ids=("1692",),
    )
    final = replace(staging, source="data_yaml", next_measurement_id="m-003")
    other = replace(staging, object_id="KSW-0002", pig_ids=("9999",))

    assert _deduplicate_candidates((final, staging, other)) == (final, other)
    assert _deduplicate_candidates((staging, final, other)) == (final, other)
    assert _deduplicate_candidates((staging, other, final)) == (final, other)
    assert _deduplicate_candidates((staging, staging, other)) == (staging, other)


def test_empty_pig_source_ref_does_not_prove_identity() -> None:
    assert _pig_measurement_ids({"measurements": [{"source_ref": "PIG:"}]}) == ()


def test_conflicting_pig_provenance_for_same_object_id_is_rejected(tmp_path: Path) -> None:
    tpn_csv = tmp_path / "tpn.csv"
    pig_staging = tmp_path / "pig-staging.json"
    data_dir = tmp_path / "data"
    _write_tpn_csv(
        tpn_csv,
        [
            _tpn_row(
                nr_inwent="T.F-09.33",
                name="Szczelina pod Gankowa II",
                globalid="{D7C052E6-D584-4320-B886-367312D2219F}",
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
    data = json.loads(pig_staging.read_text(encoding="utf-8"))
    data["rows"][0]["pig_id"] = "9999"
    data["proposed_objects"][0]["measurements"][0]["source_ref"] = "PIG:9999"
    pig_staging.write_text(json.dumps(data), encoding="utf-8")
    _write_final_pig_candidate(data_dir)

    with pytest.raises(ValueError, match="KSW-0001.*PIG provenance"):
        build_tpn_staging(
            tpn_csv,
            generated_at="2026-05-16T09:00:00Z",
            data_dir=data_dir,
            pig_staging_path=pig_staging,
            prefix_resolver=StubResolver(),
        )


def test_distinct_nearby_pig_objects_remain_ambiguous_in_either_order(tmp_path: Path) -> None:
    tpn_csv = tmp_path / "tpn.csv"
    pig_staging = tmp_path / "pig-staging.json"
    _write_tpn_csv(
        tpn_csv,
        [
            _tpn_row(
                nr_inwent="T.F-09.33",
                name="Szczelina pod Gankowa II",
                globalid="{D7C052E6-D584-4320-B886-367312D2219F}",
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
    data = json.loads(pig_staging.read_text(encoding="utf-8"))
    second_row = {**data["rows"][0], "object_id": "KSW-0002", "cave_id": "C-0002", "pig_id": "9999"}
    second_object = deepcopy(data["proposed_objects"][0])
    second_object["id"] = "KSW-0002"
    second_object["measurements"][0]["x_1992"] += 1
    data["rows"].append(second_row)
    data["proposed_objects"].append(second_object)

    for reverse in (False, True):
        data["rows"] = list(reversed(data["rows"])) if reverse else data["rows"]
        data["proposed_objects"] = (
            list(reversed(data["proposed_objects"])) if reverse else data["proposed_objects"]
        )
        pig_staging.write_text(json.dumps(data), encoding="utf-8")
        report = build_tpn_staging(
            tpn_csv,
            generated_at="2026-05-16T09:00:00Z",
            data_dir=tmp_path / "data",
            pig_staging_path=pig_staging,
            prefix_resolver=StubResolver(),
        )
        assert report.rows[0].status == "unresolved"
        assert [issue.code for issue in report.issues] == ["TPN_NR_INWENT_AMBIGUOUS"]
        assert report.matched_measurements == ()


def test_conflicting_staging_rows_for_one_object_id_are_rejected(tmp_path: Path) -> None:
    tpn_csv = tmp_path / "tpn.csv"
    pig_staging = tmp_path / "pig-staging.json"
    _write_tpn_csv(tpn_csv, [])
    _write_pig_staging(
        pig_staging,
        object_id="KSW-0001",
        cave_id="C-0001",
        nr_inwent="T.F-09.33",
        name="Szczelina pod Gankowa II",
        x_1992=152267.23,
        y_1992=563744.25,
    )
    data = json.loads(pig_staging.read_text(encoding="utf-8"))
    data["rows"].append({**data["rows"][0], "pig_id": "9999"})
    pig_staging.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="KSW-0001.*conflicting PIG staging rows"):
        build_tpn_staging(
            tpn_csv,
            generated_at="2026-05-16T09:00:00Z",
            data_dir=tmp_path / "data",
            pig_staging_path=pig_staging,
            prefix_resolver=StubResolver(),
        )


def test_cave_only_pig_row_does_not_hide_following_object_candidate(tmp_path: Path) -> None:
    tpn_csv = tmp_path / "tpn.csv"
    pig_staging = tmp_path / "pig-staging.json"
    _write_tpn_csv(
        tpn_csv,
        [
            _tpn_row(
                nr_inwent="T.F-09.33",
                name="Szczelina pod Gankowa II",
                globalid="{D7C052E6-D584-4320-B886-367312D2219F}",
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
    data = json.loads(pig_staging.read_text(encoding="utf-8"))
    data["rows"].insert(0, {"object_id": None, "cave_id": "C-0002"})
    orphan = deepcopy(data["proposed_objects"][0])
    orphan["id"] = "KSW-9999"
    data["proposed_objects"].insert(0, orphan)
    pig_staging.write_text(json.dumps(data), encoding="utf-8")

    report = build_tpn_staging(
        tpn_csv,
        generated_at="2026-05-16T09:00:00Z",
        data_dir=tmp_path / "data",
        pig_staging_path=pig_staging,
        prefix_resolver=StubResolver(),
    )
    assert report.rows[0].status == "matched"
    assert report.rows[0].object_id == "KSW-0001"


def test_staging_row_and_measurement_must_agree_on_pig_identity(tmp_path: Path) -> None:
    tpn_csv = tmp_path / "tpn.csv"
    pig_staging = tmp_path / "pig-staging.json"
    _write_tpn_csv(tpn_csv, [])
    _write_pig_staging(
        pig_staging,
        object_id="KSW-0001",
        cave_id="C-0001",
        nr_inwent="T.F-09.33",
        name="Szczelina pod Gankowa II",
        x_1992=152267.23,
        y_1992=563744.25,
    )
    data = json.loads(pig_staging.read_text(encoding="utf-8"))
    data["proposed_objects"][0]["measurements"][0]["source_ref"] = "PIG:9999"
    pig_staging.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="KSW-0001.*conflicting PIG provenance"):
        build_tpn_staging(
            tpn_csv,
            generated_at="2026-05-16T09:00:00Z",
            data_dir=tmp_path / "data",
            pig_staging_path=pig_staging,
            prefix_resolver=StubResolver(),
        )


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


def _write_final_pig_candidate(data_dir: Path) -> None:
    object_path = data_dir / "objects" / "KSW" / "KSW-0001.yml"
    cave_path = data_dir / "caves" / "C-0001.yml"
    object_path.parent.mkdir(parents=True)
    cave_path.parent.mkdir(parents=True)
    object_path.write_text(
        yaml.safe_dump(
            {
                "id": "KSW-0001",
                "cave_id": "C-0001",
                "name_local": "Szczelina pod Gankowa II",
                "measurements": [
                    {
                        "id": "m-001",
                        "source": "PIG",
                        "source_ref": "PIG:1692",
                        "x_1992": 152267.23,
                        "y_1992": 563744.25,
                    },
                    {"id": "m-002", "source": "own", "x_1992": 152267.23, "y_1992": 563744.25},
                ],
                "best_measurement": {"mode": "manual", "measurement_id": "m-002"},
            }
        ),
        encoding="utf-8",
    )
    cave_path.write_text(
        yaml.safe_dump(
            {
                "id": "C-0001",
                "name": "Szczelina pod Gankowa II",
                "object_ids": ["KSW-0001"],
                "external_refs": [
                    {"system": "NR_INWENT", "external_id": "T.F-09.33"},
                    {"system": "PIG", "ref_type": "catalog_id", "external_id": "1692"},
                ],
            }
        ),
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
