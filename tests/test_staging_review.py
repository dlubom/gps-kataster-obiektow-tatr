import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml

from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992
from gps_kataster_obiektow_tatr.staging_review import (
    ReviewDecisionError,
    ReviewSeverity,
    StagingReports,
    apply_review_decisions,
    load_review_decisions,
    load_staging_reports,
    render_review_markdown,
    write_review_report_files,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
APPLY_REVIEW_PATH = REPO_ROOT / "scripts" / "importers" / "apply_review.py"
VALIDATE_SCRIPT = REPO_ROOT / "scripts" / "validate.py"
KSW_LAT = 49.23459299
KSW_LON = 19.87589498
TPN_GLOBALID = "{38626571-CAA6-4317-8900-D61A995020E9}"


def test_apply_review_directly_materializes_pig_and_tpn_decisions(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"

    result = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:00:00Z",
            "reviewed_by": "dl",
            "decisions": [
                {"action": "create_cave", "source": "PIG", "record_number": 1},
                {"action": "create_object", "source": "PIG", "record_number": 1},
                {"action": "add_measurement", "source": "TPN", "record_number": 1},
            ],
        },
        staging_reports=StagingReports(pig=_pig_staging(), tpn=_tpn_staging()),
        data_dir=data_dir,
    )

    object_path = data_dir / "objects" / "KSW" / "KSW-0001.yml"
    cave_path = data_dir / "caves" / "C-0001.yml"
    object_data = _read_yaml(object_path)
    cave_data = _read_yaml(cave_path)

    assert result.has_errors is False
    assert result.written_paths == (cave_path, object_path)
    assert [decision.status for decision in result.applied_decisions] == [
        "materialized",
        "materialized",
        "materialized",
    ]
    assert [measurement["id"] for measurement in object_data["measurements"]] == [
        "m-001",
        "m-002",
    ]
    assert object_data["best_measurement"] == {
        "mode": "auto",
        "measurement_id": "m-002",
        "reason": None,
        "updated_at": "2026-05-16T10:00:00Z",
        "updated_by": "dl",
    }
    assert object_data["measurements"][0]["tags"] == ["pig"]
    assert object_data["measurements"][1]["tags"] == ["tpn"]
    assert object_data["external_refs"] == [
        {
            "system": "TPN",
            "ref_type": "source_globalid",
            "external_id": TPN_GLOBALID,
            "scope": "object",
            "notes": "TPN GLOBALID belongs to the object/source feature.",
        }
    ]
    assert cave_data["external_refs"] == [
        _nr_inwent_ref(),
        {
            "system": "PIG",
            "ref_type": "catalog_id",
            "external_id": "1692",
            "url": "https://jaskiniepolski.pgi.gov.pl/Details/Information/1692",
            "scope": "cave",
            "notes": "PIG catalog record identifier.",
        },
    ]


def test_write_review_report_files_serializes_decisions_issues_and_paths(tmp_path: Path) -> None:
    result = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:15:00Z",
            "reviewed_by": "dl",
            "decisions": [
                {"action": "unresolved", "source": "TPN", "record_number": 3},
            ],
        },
        staging_reports=StagingReports(tpn=_tpn_review_only_staging()),
        data_dir=tmp_path / "data",
        write=False,
    )

    json_path, markdown_path = write_review_report_files(result, output_dir=tmp_path / "review")
    json_data = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")

    assert json_data["has_errors"] is False
    assert json_data["decision_count"] == 1
    assert json_data["issue_count"] == 1
    assert json_data["decisions"][0]["description"] == "No reason provided."
    assert json_data["issues"][0]["code"] == "DECISION_REASON_MISSING"
    assert "| `warning` | `DECISION_REASON_MISSING` |" in markdown
    assert "No reason provided." in markdown


def test_load_review_decisions_rejects_invalid_yaml_and_non_mapping(tmp_path: Path) -> None:
    invalid_yaml = tmp_path / "invalid.yml"
    invalid_yaml.write_text("decisions: [\n", encoding="utf-8")
    non_mapping = tmp_path / "non-mapping.yml"
    non_mapping.write_text("- action: reject\n", encoding="utf-8")

    with pytest.raises(ReviewDecisionError, match="invalid YAML"):
        load_review_decisions(invalid_yaml)
    with pytest.raises(ReviewDecisionError, match="decision file must be a mapping"):
        load_review_decisions(non_mapping)


def test_load_staging_reports_handles_missing_paths_and_rejects_non_objects(
    tmp_path: Path,
) -> None:
    bad_json = tmp_path / "bad-staging.json"
    bad_json.write_text("[]\n", encoding="utf-8")

    assert load_staging_reports(pig_staging_path=None, tpn_staging_path=tmp_path / "missing") == (
        StagingReports()
    )
    with pytest.raises(ReviewDecisionError, match="staging report must be a JSON object"):
        load_staging_reports(pig_staging_path=bad_json, tpn_staging_path=None)


def test_cli_applies_sample_decisions_and_final_yaml_passes_validate_py(
    tmp_path: Path,
) -> None:
    pig_staging_path = tmp_path / "pig-staging.json"
    tpn_staging_path = tmp_path / "tpn-staging.json"
    decisions_path = tmp_path / "decisions.yml"
    data_dir = tmp_path / "data"
    review_dir = tmp_path / "build" / "review"
    _write_json(pig_staging_path, _pig_staging())
    _write_json(tpn_staging_path, _tpn_staging())
    _write_yaml(
        decisions_path,
        {
            "reviewed_at": "2026-05-16T10:00:00Z",
            "reviewed_by": "dl",
            "decisions": [
                {"action": "create_cave", "source": "PIG", "record_number": 1},
                {"action": "create_object", "source": "PIG", "record_number": 1},
                {"action": "add_measurement", "source": "TPN", "record_number": 1},
            ],
        },
    )

    result = subprocess.run(
        [
            sys.executable,
            str(APPLY_REVIEW_PATH),
            "--decisions",
            str(decisions_path),
            "--data-dir",
            str(data_dir),
            "--pig-staging",
            str(pig_staging_path),
            "--tpn-staging",
            str(tpn_staging_path),
            "--output-dir",
            str(review_dir),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    validation = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), "--data-dir", str(data_dir)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    object_data = _read_yaml(data_dir / "objects" / "KSW" / "KSW-0001.yml")
    cave_data = _read_yaml(data_dir / "caves" / "C-0001.yml")
    report = json.loads((review_dir / "staging-review.json").read_text(encoding="utf-8"))

    assert "staging review: 3 decisions, 2 final YAML files" in result.stdout
    assert validation.returncode == 0, validation.stdout + validation.stderr
    assert [measurement["id"] for measurement in object_data["measurements"]] == [
        "m-001",
        "m-002",
    ]
    assert object_data["notes"] == "Imported from PIG source record after operator review."
    assert object_data["measurements"][0]["tags"] == ["pig"]
    assert (
        object_data["measurements"][0]["notes"]
        == "PIG source-record measurement imported after operator review; not field-verified."
    )
    assert object_data["measurements"][1]["tags"] == ["tpn"]
    assert (
        object_data["measurements"][1]["notes"]
        == "TPN source-record measurement imported after operator review; not field-verified."
    )
    assert object_data["best_measurement"]["measurement_id"] == "m-002"
    assert object_data["external_refs"][0]["external_id"] == TPN_GLOBALID
    assert cave_data["object_ids"] == ["KSW-0001"]
    assert report["has_errors"] is False
    assert report["decision_count"] == 3


def test_link_reject_and_unresolved_decisions_are_reported(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _write_yaml(data_dir / "objects" / "KSW" / "KSW-0001.yml", _object_data(cave_id=None))
    _write_yaml(data_dir / "caves" / "C-0001.yml", _cave_data(object_ids=[]))

    result = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:15:00Z",
            "reviewed_by": "dl",
            "decisions": [
                {"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"},
                {
                    "action": "reject",
                    "source": "TPN",
                    "record_number": 2,
                    "reason": "Duplicated source row.",
                },
                {
                    "action": "unresolved",
                    "source": "TPN",
                    "record_number": 3,
                    "reason": "Needs field review.",
                },
            ],
        },
        staging_reports=StagingReports(tpn=_tpn_review_only_staging()),
        data_dir=data_dir,
    )

    object_data = _read_yaml(data_dir / "objects" / "KSW" / "KSW-0001.yml")
    cave_data = _read_yaml(data_dir / "caves" / "C-0001.yml")
    markdown = render_review_markdown(result)

    assert result.has_errors is False
    assert result.issues == ()
    assert object_data["cave_id"] == "C-0001"
    assert cave_data["object_ids"] == ["KSW-0001"]
    assert [decision.status for decision in result.applied_decisions] == [
        "materialized",
        "skipped",
        "skipped",
    ]
    assert "Duplicated source row." in markdown
    assert "Needs field review." in markdown


def test_invalid_decision_blocks_all_final_yaml_writes(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    result = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:30:00Z",
            "reviewed_by": "dl",
            "decisions": [
                {"action": "create_cave", "source": "PIG", "record_number": 1},
                {"action": "create_object", "source": "PIG", "record_number": 99},
            ],
        },
        staging_reports=StagingReports(pig=_pig_staging()),
        data_dir=data_dir,
    )

    assert result.has_errors is True
    assert result.written_paths == ()
    assert not (data_dir / "caves" / "C-0001.yml").exists()


def test_invalid_decision_shapes_and_non_materialized_warnings_are_reported(
    tmp_path: Path,
) -> None:
    invalid_list = apply_review_decisions(
        {"reviewed_at": "2026-05-16T10:30:00Z", "reviewed_by": "dl", "decisions": "bad"},
        staging_reports=StagingReports(),
        data_dir=tmp_path / "data-invalid-list",
    )
    mixed = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:31:00Z",
            "reviewed_by": "dl",
            "decisions": [
                None,
                {"action": "unknown"},
                {"action": "reject", "source": "bad", "record_number": 0},
                {"action": "reject", "source": "TPN", "record_number": 2},
            ],
        },
        staging_reports=StagingReports(tpn=_tpn_review_only_staging()),
        data_dir=tmp_path / "data-mixed",
        write=False,
    )

    assert _issue_codes(invalid_list) == ["DECISIONS_INVALID"]
    assert _issue_codes(mixed) == [
        "DECISION_INVALID",
        "DECISION_ACTION_INVALID",
        "DECISION_SOURCE_INVALID",
        "DECISION_RECORD_INVALID",
        "DECISION_REASON_MISSING",
    ]
    assert mixed.issues[-1].severity == ReviewSeverity.WARNING
    assert mixed.applied_decisions[0].description == "No reason provided."


def test_duplicate_create_decisions_report_existing_final_records(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _write_yaml(data_dir / "objects" / "KSW" / "KSW-0001.yml", _object_data(cave_id="C-0001"))
    _write_yaml(data_dir / "caves" / "C-0001.yml", _cave_data(object_ids=["KSW-0001"]))

    result = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:32:00Z",
            "reviewed_by": "dl",
            "decisions": [
                {"action": "create_cave", "source": "PIG", "record_number": 1},
                {"action": "create_object", "source": "PIG", "record_number": 1},
            ],
        },
        staging_reports=StagingReports(pig=_pig_staging()),
        data_dir=data_dir,
        write=False,
    )

    assert _issue_codes(result) == ["CAVE_ALREADY_EXISTS", "OBJECT_ALREADY_EXISTS"]
    assert result.applied_decisions == ()


def test_add_measurement_reports_blocking_edge_cases(tmp_path: Path) -> None:
    unsupported_source = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:33:00Z",
            "reviewed_by": "dl",
            "decisions": [{"action": "add_measurement", "source": "PIG", "record_number": 1}],
        },
        staging_reports=StagingReports(pig=_pig_staging()),
        data_dir=tmp_path / "data-unsupported",
        write=False,
    )
    missing_update = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:34:00Z",
            "reviewed_by": "dl",
            "decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 2}],
        },
        staging_reports=StagingReports(tpn=_tpn_review_only_staging()),
        data_dir=tmp_path / "data-missing-update",
        write=False,
    )
    target_missing = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:35:00Z",
            "reviewed_by": "dl",
            "decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}],
        },
        staging_reports=StagingReports(tpn=_tpn_staging()),
        data_dir=tmp_path / "data-target-missing",
        write=False,
    )

    invalid_measurement_dir = tmp_path / "data-invalid-measurement"
    _write_yaml(
        invalid_measurement_dir / "objects" / "KSW" / "KSW-0001.yml",
        _object_data(cave_id="C-0001"),
    )
    invalid_tpn = deepcopy(_tpn_staging())
    invalid_tpn["matched_measurements"][0]["measurement"] = None
    invalid_measurement = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:36:00Z",
            "reviewed_by": "dl",
            "decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}],
        },
        staging_reports=StagingReports(tpn=invalid_tpn),
        data_dir=invalid_measurement_dir,
        write=False,
    )

    duplicate_dir = tmp_path / "data-duplicate-measurement"
    _write_yaml(
        duplicate_dir / "objects" / "KSW" / "KSW-0001.yml",
        _object_data(
            cave_id="C-0001", measurement=_measurement("m-002", source="TPN", source_ref="")
        ),
    )
    duplicate = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:37:00Z",
            "reviewed_by": "dl",
            "decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}],
        },
        staging_reports=StagingReports(tpn=_tpn_staging()),
        data_dir=duplicate_dir,
        write=False,
    )

    assert _issue_codes(unsupported_source) == ["MEASUREMENT_SOURCE_UNSUPPORTED"]
    assert _issue_codes(missing_update) == ["STAGING_MEASUREMENT_UPDATE_MISSING"]
    assert _issue_codes(target_missing) == ["TARGET_OBJECT_MISSING"]
    assert _issue_codes(invalid_measurement) == ["STAGING_MEASUREMENT_INVALID"]
    assert _issue_codes(duplicate) == ["MEASUREMENT_ALREADY_EXISTS"]


def _pig_staging() -> dict[str, Any]:
    cave = _cave_data(
        object_ids=["KSW-0001"],
        external_refs=[
            _nr_inwent_ref(),
            {
                "system": "PIG",
                "ref_type": "catalog_id",
                "external_id": "1692",
                "url": "https://jaskiniepolski.pgi.gov.pl/Details/Information/1692",
                "scope": "cave",
                "notes": "PIG catalog record identifier.",
            },
        ],
        created_by="importer:pig",
    )
    obj = _object_data(
        cave_id="C-0001",
        created_by="importer:pig",
        measurement=_measurement("m-001", source="PIG", source_ref="PIG:1692"),
        notes="Staging proposal from PIG; requires operator review before final YAML.",
    )
    return {
        "generated_at": "2026-05-16T08:00:00Z",
        "rows": [
            {
                "record_number": 1,
                "pig_id": "1692",
                "nr_inwent": "T.F-09.33",
                "name": "Szczelina pod Gankowa II",
                "cave_id": "C-0001",
                "object_id": "KSW-0001",
                "status": "object_proposed",
            }
        ],
        "proposed_caves": [cave],
        "proposed_objects": [obj],
    }


def _tpn_staging() -> dict[str, Any]:
    measurement = _measurement("m-002", source="TPN", source_ref=f"TPN:{TPN_GLOBALID}")
    return {
        "generated_at": "2026-05-16T09:00:00Z",
        "rows": [
            {
                "record_number": 1,
                "globalid": TPN_GLOBALID,
                "nr_inwent": "T.F-09.33",
                "name": "Szczelina pod Gankowa II",
                "status": "matched",
                "cave_id": "C-0001",
                "object_id": "KSW-0001",
                "match_strategy": "nr_inwent",
                "distance_m": 0.0,
            }
        ],
        "matched_measurements": [
            {
                "status": "matched",
                "record_number": 1,
                "target_object_id": "KSW-0001",
                "target_cave_id": "C-0001",
                "object_external_refs": [
                    {
                        "system": "TPN",
                        "ref_type": "source_globalid",
                        "external_id": TPN_GLOBALID,
                        "scope": "object",
                        "notes": "TPN GLOBALID belongs to the object/source feature.",
                    }
                ],
                "cave_external_refs": [_nr_inwent_ref()],
                "measurement": measurement,
            }
        ],
        "proposed_caves": [],
        "proposed_objects": [],
    }


def _tpn_review_only_staging() -> dict[str, Any]:
    return {
        "rows": [
            {"record_number": 2, "status": "rejected"},
            {"record_number": 3, "status": "unresolved"},
        ],
        "matched_measurements": [],
        "proposed_caves": [],
        "proposed_objects": [],
    }


def _object_data(
    *,
    cave_id: str | None,
    created_by: str = "dl",
    measurement: dict[str, Any] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    measurement_data = measurement or _measurement(
        "m-001",
        source="wlasne",
        source_ref="teren:2026-05-15:gps",
        horizontal_accuracy_m=5.0,
    )
    return {
        "schema_version": 1,
        "id": "KSW-0001",
        "category": "jaskinia_otwor",
        "name_local": "Szczelina pod Gankowa II",
        "cave_id": cave_id,
        "id_assignment": {
            "method": "auto",
            "assigned_from_measurement_id": "m-001",
            "assigned_prefix": "KSW",
            "prefix_override_reason": None,
        },
        "external_refs": [],
        "measurements": [measurement_data],
        "best_measurement": {
            "mode": "auto",
            "measurement_id": "m-001",
            "reason": None,
            "updated_at": "2026-05-16T08:00:00Z",
            "updated_by": created_by,
        },
        "attachments": [],
        "notes": notes,
        "created_at": "2026-05-16T08:00:00Z",
        "created_by": created_by,
        "updated_at": "2026-05-16T08:00:00Z",
        "updated_by": created_by,
    }


def _cave_data(
    *,
    object_ids: list[str],
    external_refs: list[dict[str, Any]] | None = None,
    created_by: str = "dl",
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": "C-0001",
        "name": "Szczelina pod Gankowa II",
        "system_name": None,
        "external_refs": external_refs or [],
        "object_ids": object_ids,
        "notes": None,
        "created_at": "2026-05-16T08:00:00Z",
        "created_by": created_by,
        "updated_at": "2026-05-16T08:00:00Z",
        "updated_by": created_by,
    }


def _measurement(
    measurement_id: str,
    *,
    source: str,
    source_ref: str,
    horizontal_accuracy_m: float | None = None,
) -> dict[str, Any]:
    pl_1992 = wgs84_to_1992(lat=KSW_LAT, lon=KSW_LON)
    return {
        "id": measurement_id,
        "lat": KSW_LAT,
        "lon": KSW_LON,
        "x_1992": pl_1992.x_1992,
        "y_1992": pl_1992.y_1992,
        "elevation_m": 1266.0,
        "elevation_datum": "unknown",
        "elevation_source": "source_record" if source in {"PIG", "TPN"} else "gps",
        "horizontal_accuracy_m": horizontal_accuracy_m,
        "vertical_accuracy_m": None,
        "source": source,
        "source_ref": source_ref,
        "observed_date": "2026-05-16",
        "source_date": "2026-05-16",
        "method": "source_record" if source in {"PIG", "TPN"} else "gps_receiver",
        "device": None,
        "tags": [source.lower(), "staging"] if source in {"PIG", "TPN"} else [source.lower()],
        "verification_status": "nieweryfikowany",
        "verified_by": None,
        "verified_at": None,
        "notes": (
            f"{source} source-record measurement imported into staging; not field-verified."
            if source in {"PIG", "TPN"}
            else f"{source} review fixture measurement."
        ),
        "created_at": "2026-05-16T08:00:00Z",
        "created_by": f"importer:{source.lower()}",
    }


def _nr_inwent_ref() -> dict[str, Any]:
    return {
        "system": "NR_INWENT",
        "ref_type": "inventory_number",
        "external_id": "T.F-09.33",
        "scope": "cave",
        "notes": "Inventory number belongs to the cave/catalog entry, not the object.",
    }


def _issue_codes(result: Any) -> list[str]:
    return [issue.code for issue in result.issues]


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data
