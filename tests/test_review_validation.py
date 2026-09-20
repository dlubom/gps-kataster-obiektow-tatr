"""Review validates input and the complete proposed catalog before any write."""

from copy import deepcopy

import pytest
from test_cave_membership import _sample, _snapshot, _write
from test_staging_review import _pig_staging, _tpn_staging

from gps_kataster_obiektow_tatr.staging_review import StagingReports, apply_review_decisions
from gps_kataster_obiektow_tatr.validator import has_errors, validate_data_dir


def _decisions(*actions):
    return {
        "reviewed_at": "2026-09-19T12:00:00Z",
        "reviewed_by": "reviewer",
        "decisions": [
            {"action": action, "source": "PIG", "record_number": 1} for action in actions
        ],
    }


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize(
    "case", ["object_only", "cave_only", "bad_coordinate", "bad_type", "bad_date"]
)
def test_invalid_proposed_catalog_blocks_all_writes(tmp_path, write, case):
    pig = _pig_staging()
    actions = ["create_object", "create_cave"]
    if case == "object_only":
        actions = ["create_object"]
    elif case == "cave_only":
        actions = ["create_cave"]
    elif case == "bad_coordinate":
        pig["proposed_objects"][0]["measurements"][0]["lat"] = 0
    elif case == "bad_type":
        pig["proposed_objects"][0]["measurements"] = "invalid"
    else:
        pig["proposed_objects"][0]["measurements"][0]["observed_date"] = "bad"
    before = _snapshot(tmp_path)
    original = deepcopy(pig)
    result = apply_review_decisions(
        _decisions(*actions),
        staging_reports=StagingReports(pig=pig),
        data_dir=tmp_path,
        write=write,
    )
    assert result.has_errors
    assert result.written_paths == ()
    assert any(i.severity == "error" and i.description for i in result.issues)
    expected = (
        "STAGING_PROPOSAL_INVALID" if case in {"bad_type", "bad_date"} else "PROPOSED_DATA_INVALID"
    )
    assert result.issues[0].code == expected
    if expected == "STAGING_PROPOSAL_INVALID":
        assert result.issues[0].decision_index == 1
        assert "SCHEMA_VALIDATION" in result.issues[0].description
    else:
        assert result.issues[0].decision_index is None
    assert _snapshot(tmp_path) == before
    assert pig == original


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize(
    "case",
    [
        "schema",
        "duplicate_relation",
        "broken_relation",
        "path",
        "membership",
        "duplicate_measurement",
    ],
)
def test_invalid_input_blocks_review_before_decisions(tmp_path, write, case):
    records = _sample(tmp_path)
    path = tmp_path / "objects/KSW/KSW-0001.yml"
    obj = records["objects/KSW/KSW-0001.yml"]
    if case == "schema":
        obj["id"] = ["bad"]
        _write(path, obj)
    elif case == "duplicate_measurement":
        obj["measurements"].append(deepcopy(obj["measurements"][0]))
        _write(path, obj)
    elif case == "membership":
        records["caves/C-0001.yml"]["object_ids"] = ["KSW-0002"]
        _write(tmp_path / "caves/C-0001.yml", records["caves/C-0001.yml"])
    elif case == "path":
        path.rename(path.with_name("KSW-9999.yaml"))
    else:
        relation = {
            "schema_version": 1,
            "id": "R-0001",
            "from_object_id": "KSW-0001",
            "to_object_id": "KSW-0002",
            "relation_type": "sasiad",
        }
        if case == "broken_relation":
            relation["to_object_id"] = "KSW-9999"
        _write(tmp_path / "relations/R-0001.yml", relation)
        if case == "duplicate_relation":
            _write(tmp_path / "relations/R-0001.yaml", relation)
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        {"decisions": [{"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0002"}]},
        staging_reports=StagingReports(),
        data_dir=tmp_path,
        write=write,
    )
    assert result.has_errors
    assert result.applied_decisions == () and result.written_paths == ()
    assert "FINAL_DATA_INVALID" in {i.code for i in result.issues}
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "actions", [("create_cave", "create_object"), ("create_object", "create_cave")]
)
@pytest.mark.parametrize("source", ["PIG", "TPN"])
def test_valid_pair_checks_final_batch_and_dry_run(tmp_path, actions, source):
    reports = StagingReports(**{source.lower(): _pig_staging()})
    decision = _decisions(*actions)
    for entry in decision["decisions"]:
        entry["source"] = source
    before = _snapshot(tmp_path)
    dry = apply_review_decisions(decision, staging_reports=reports, data_dir=tmp_path, write=False)
    assert not dry.has_errors and dry.written_paths == ()
    assert _snapshot(tmp_path) == before
    result = apply_review_decisions(decision, staging_reports=reports, data_dir=tmp_path)
    assert not result.has_errors
    assert result.issues == dry.issues
    assert len(result.written_paths) == 2
    assert not has_errors(validate_data_dir(tmp_path))


@pytest.mark.parametrize("explicit", [None, "C-0002", "C-0001"])
def test_redirected_measurement_uses_actual_cave(tmp_path, explicit):
    records = _sample(tmp_path)
    obj = records["objects/KSW/KSW-0002.yml"]
    obj["cave_id"] = "C-0002"
    records["caves/C-0001.yml"]["object_ids"] = ["KSW-0001"]
    records["caves/C-0002.yml"]["object_ids"] = ["KSW-0002"]
    for path, data in records.items():
        _write(tmp_path / path, data)
    before = _snapshot(tmp_path)
    decision = {
        "action": "add_measurement",
        "source": "TPN",
        "record_number": 1,
        "target_object_id": "KSW-0002",
    }
    if explicit:
        decision["target_cave_id"] = explicit
    result = apply_review_decisions(
        {"decisions": [decision]},
        staging_reports=StagingReports(tpn=_tpn_staging()),
        data_dir=tmp_path,
    )
    if explicit == "C-0001":
        assert result.has_errors and result.written_paths == ()
        assert [(i.code, i.severity, i.decision_index) for i in result.issues] == [
            ("TARGET_CAVE_MISMATCH", "error", 1)
        ]
        assert result.issues[0].description
        assert _snapshot(tmp_path) == before
    else:
        import yaml

        assert not result.has_errors
        assert result.applied_decisions[0].cave_id == "C-0002"
        assert (tmp_path / "caves/C-0001.yml").read_bytes() == before["caves/C-0001.yml"]
        cave = yaml.safe_load((tmp_path / "caves/C-0002.yml").read_text())
        assert (
            _tpn_staging()["matched_measurements"][0]["cave_external_refs"][0]
            in cave["external_refs"]
        )
        assert not has_errors(validate_data_dir(tmp_path))


@pytest.mark.parametrize(
    "field,value",
    [
        ("measurement", {"id": "m-002", "observed_date": "bad"}),
        ("object_external_refs", "bad"),
        ("object_external_refs", [None]),
        ("cave_external_refs", [None]),
        ("cave_external_refs", [{"system": "bad"}]),
    ],
)
@pytest.mark.parametrize("write", [False, True])
def test_malformed_update_is_reported_without_writes(tmp_path, field, value, write):
    _sample(tmp_path)
    tpn = _tpn_staging()
    tpn["matched_measurements"][0][field] = value
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        {"decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}]},
        staging_reports=StagingReports(tpn=tpn),
        data_dir=tmp_path,
        write=write,
    )
    assert result.has_errors and result.written_paths == ()
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "invalid,code", [(None, "DECISION_INVALID"), ({"action": "bad"}, "DECISION_ACTION_INVALID")]
)
def test_invalid_decision_blocks_otherwise_valid_batch(tmp_path, invalid, code):
    decisions = _decisions("create_cave", "create_object")
    decisions["decisions"].append(invalid)
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        decisions, staging_reports=StagingReports(pig=_pig_staging()), data_dir=tmp_path
    )
    assert result.has_errors and result.written_paths == ()
    assert [(i.code, i.severity, i.decision_index) for i in result.issues] == [(code, "error", 3)]
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("write", [False, True])
def test_unassigned_target_cannot_lose_catalog_references(tmp_path, write):
    records = _sample(tmp_path)
    records["objects/KSW/KSW-0001.yml"]["cave_id"] = None
    records["caves/C-0001.yml"]["object_ids"] = ["KSW-0002"]
    for path, data in records.items():
        _write(tmp_path / path, data)
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        {"decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}]},
        staging_reports=StagingReports(tpn=_tpn_staging()),
        data_dir=tmp_path,
        write=write,
    )
    assert result.has_errors and result.written_paths == ()
    assert result.issues[0].code == "TARGET_CAVE_MISSING"
    assert _snapshot(tmp_path) == before


def test_full_validation_keeps_relations_and_original_paths(tmp_path, monkeypatch):
    from gps_kataster_obiektow_tatr import staging_review

    records = _sample(tmp_path)
    for relative in records:
        path = tmp_path / relative
        path.rename(path.with_suffix(".yaml"))
    relation = {
        "schema_version": 1,
        "id": "R-0001",
        "from_object_id": "KSW-0001",
        "to_object_id": "KSW-0002",
        "relation_type": "sasiad",
    }
    relpath = tmp_path / "relations/R-0001.yaml"
    _write(relpath, relation)
    before = relpath.read_bytes()
    calls = []
    real_validate = staging_review.validate_dataset

    def validate(dataset, **kwargs):
        calls.append(dataset)
        return real_validate(dataset, **kwargs)

    monkeypatch.setattr(staging_review, "validate_dataset", validate)
    result = apply_review_decisions(
        {"decisions": [{"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0002"}]},
        staging_reports=StagingReports(),
        data_dir=tmp_path,
    )
    assert not result.has_errors
    assert len(calls) == 2
    for dataset in calls:
        assert len(dataset.relations) == 1
        assert dataset.relations[0].path == relpath
        assert dataset.relations[0].raw_data == relation
        assert all(record.path.suffix == ".yaml" for record in dataset.records())
    assert calls[0].objects[0].raw_data["cave_id"] == "C-0001"
    assert calls[1].objects[0].raw_data["cave_id"] == "C-0002"
    assert relpath.read_bytes() == before


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("valid", [False, True])
def test_cli_review_validation(tmp_path, dry_run, valid):
    import json
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    staging = tmp_path / "pig.json"
    staging.write_text(json.dumps(_pig_staging()))
    decisions = tmp_path / "decisions.yml"
    _write(
        decisions, _decisions(*(["create_object", "create_cave"] if valid else ["create_object"]))
    )
    data_dir = tmp_path / "data"
    before = _snapshot(data_dir)
    command = [
        sys.executable,
        str(root / "scripts/importers/apply_review.py"),
        "--init-data-dir",
        "--decisions",
        str(decisions),
        "--pig-staging",
        str(staging),
        "--no-tpn-staging",
        "--data-dir",
        str(data_dir),
        "--output-dir",
        str(tmp_path / "report"),
    ]
    if dry_run:
        command.append("--dry-run")
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == (0 if valid else 1), result.stderr
    report = json.loads((tmp_path / "report/staging-review.json").read_text())
    assert report["has_errors"] == (not valid)
    if dry_run or not valid:
        assert _snapshot(data_dir) == before
        assert report["written_paths"] == []
    else:
        assert len(report["written_paths"]) == 2
        assert not has_errors(validate_data_dir(data_dir))
    if not valid:
        assert "CAVE_REFERENCE_MISSING" in report["issues"][0]["description"]
        assert "inspect the report before retrying" in result.stderr


@pytest.mark.parametrize(
    "field", ["rows", "proposed_objects", "proposed_caves", "matched_measurements"]
)
@pytest.mark.parametrize("value", [None, 1, [None]])
@pytest.mark.parametrize("source", ["PIG", "TPN"])
def test_malformed_staging_container_is_reported(tmp_path, field, value, source):
    report = _pig_staging()
    report[field] = value
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        _decisions("create_object", "create_cave"),
        staging_reports=StagingReports(**{source.lower(): report}),
        data_dir=tmp_path,
    )
    assert result.has_errors and result.written_paths == ()
    assert result.issues[0].code == "STAGING_REPORT_INVALID"
    assert result.issues[0].severity == "error"
    assert result.issues[0].decision_index is None
    assert result.applied_decisions == ()
    assert field in result.issues[0].description
    assert _snapshot(tmp_path) == before


def test_schema_invalid_input_cannot_crash_domain_validation(tmp_path):
    records = _sample(tmp_path)
    records["objects/KSW/KSW-0001.yml"]["external_refs"] = [
        {"system": "PIG", "ref_type": [], "external_id": "123"}
    ]
    _write(tmp_path / "objects/KSW/KSW-0001.yml", records["objects/KSW/KSW-0001.yml"])
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        {"decisions": []}, staging_reports=StagingReports(), data_dir=tmp_path
    )
    assert result.has_errors and result.written_paths == ()
    assert "SCHEMA_VALIDATION" in result.issues[0].description
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("late_link", [False, True])
def test_catalog_references_follow_completed_batch(tmp_path, late_link):
    decisions = _decisions("create_object")
    decisions["decisions"] += [
        {"action": "add_measurement", "source": "TPN", "record_number": 1},
        {"action": "create_cave", "source": "PIG", "record_number": 1},
    ]
    if late_link:
        from test_staging_review import _cave_data

        _write(tmp_path / "caves/C-0002.yml", {**_cave_data(object_ids=[]), "id": "C-0002"})
        decisions["decisions"].append(
            {"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0002"}
        )
    reports = StagingReports(pig=_pig_staging(), tpn=_tpn_staging())
    before = _snapshot(tmp_path)
    dry = apply_review_decisions(decisions, staging_reports=reports, data_dir=tmp_path, write=False)
    assert not dry.has_errors and dry.written_paths == ()
    assert _snapshot(tmp_path) == before
    result = apply_review_decisions(decisions, staging_reports=reports, data_dir=tmp_path)
    assert not result.has_errors
    import yaml

    target = "C-0002" if late_link else "C-0001"
    assert result.applied_decisions[1].cave_id == target
    cave = yaml.safe_load((tmp_path / f"caves/{target}.yml").read_text())
    assert (
        _tpn_staging()["matched_measurements"][0]["cave_external_refs"][0] in cave["external_refs"]
    )
    assert not has_errors(validate_data_dir(tmp_path))


@pytest.mark.parametrize("action", ["create_object", "create_cave"])
def test_standalone_unassigned_object_or_empty_cave_is_valid(tmp_path, action):
    pig = _pig_staging()
    pig["proposed_objects"][0]["cave_id"] = None
    pig["proposed_caves"][0]["object_ids"] = []
    result = apply_review_decisions(
        _decisions(action), staging_reports=StagingReports(pig=pig), data_dir=tmp_path
    )
    assert not result.has_errors
    assert len(result.written_paths) == 1
    assert not has_errors(validate_data_dir(tmp_path))


def test_measurement_without_catalog_refs_can_target_unassigned_object(tmp_path):
    records = _sample(tmp_path)
    obj = records["objects/KSW/KSW-0001.yml"]
    obj["cave_id"] = None
    obj["best_measurement"].update(mode="manual", reason="Keep operator measurement")
    records["caves/C-0001.yml"]["object_ids"] = ["KSW-0002"]
    for path, data in records.items():
        _write(tmp_path / path, data)
    tpn = _tpn_staging()
    tpn["matched_measurements"][0]["cave_external_refs"] = []
    result = apply_review_decisions(
        {"decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}]},
        staging_reports=StagingReports(tpn=tpn),
        data_dir=tmp_path,
    )
    assert not result.has_errors
    assert result.applied_decisions[0].cave_id is None
    assert result.written_paths == (tmp_path / "objects/KSW/KSW-0001.yml",)
    import yaml

    actual = yaml.safe_load(result.written_paths[0].read_text())
    assert actual["best_measurement"] == obj["best_measurement"]
    assert len(actual["measurements"]) == 2
    assert not has_errors(validate_data_dir(tmp_path))


@pytest.mark.parametrize("kind", ["cave", "object"])
@pytest.mark.parametrize("case", ["missing", "duplicate"])
@pytest.mark.parametrize("write", [False, True])
def test_invalid_create_cannot_commit_other_valid_decisions(tmp_path, kind, case, write):
    _sample(tmp_path)
    reports = StagingReports(pig=_pig_staging(), tpn=_tpn_staging())
    decision = {"action": f"create_{kind}", "source": "PIG", "record_number": 1}
    if case == "missing":
        decision[f"{kind}_id"] = "C-9999" if kind == "cave" else "KSW-9999"
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        {
            "decisions": [
                {"action": "add_measurement", "source": "TPN", "record_number": 1},
                decision,
            ]
        },
        staging_reports=reports,
        data_dir=tmp_path,
        write=write,
    )
    assert result.has_errors and result.written_paths == ()
    code = (
        f"STAGING_{kind.upper()}_PROPOSAL_MISSING"
        if case == "missing"
        else f"{kind.upper()}_ALREADY_EXISTS"
    )
    assert [(i.code, i.severity, i.decision_index) for i in result.issues] == [(code, "error", 2)]
    assert result.issues[0].description
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "case,code",
    [
        ("source", "MEASUREMENT_SOURCE_UNSUPPORTED"),
        ("update", "STAGING_MEASUREMENT_UPDATE_MISSING"),
        ("target", "TARGET_OBJECT_MISSING"),
        ("measurement", "STAGING_MEASUREMENT_INVALID"),
        ("duplicate", "MEASUREMENT_ALREADY_EXISTS"),
    ],
)
@pytest.mark.parametrize("write", [False, True])
def test_invalid_measurement_cannot_commit_other_valid_decisions(tmp_path, case, code, write):
    _sample(tmp_path)
    tpn = _tpn_staging()
    decision = {"action": "add_measurement", "source": "TPN", "record_number": 1}
    if case == "source":
        decision["source"] = "PIG"
    elif case == "update":
        decision["record_number"] = 99
    elif case == "target":
        decision["target_object_id"] = "KSW-9999"
    elif case == "measurement":
        tpn["matched_measurements"][0]["measurement"] = None
    else:
        tpn["matched_measurements"][0]["measurement"]["id"] = "m-001"
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        {
            "decisions": [
                {"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0002"},
                decision,
            ]
        },
        staging_reports=StagingReports(tpn=tpn),
        data_dir=tmp_path,
        write=write,
    )
    assert result.has_errors and result.written_paths == ()
    assert [(i.code, i.severity, i.decision_index) for i in result.issues] == [(code, "error", 2)]
    assert result.issues[0].description
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("kind", ["cave", "object", "measurement"])
@pytest.mark.parametrize("field,value", [("source", "bad"), ("record_number", 0)])
def test_invalid_create_source_is_readable_and_blocks_batch(tmp_path, kind, field, value):
    decisions = _decisions("create_cave", "create_object")
    decisions["decisions"].append(
        {
            "action": "add_measurement" if kind == "measurement" else f"create_{kind}",
            "source": "PIG",
            "record_number": 1,
            field: value,
        }
    )
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        decisions, staging_reports=StagingReports(pig=_pig_staging()), data_dir=tmp_path
    )
    assert result.has_errors and result.written_paths == ()
    assert result.issues[0].code == (
        "DECISION_SOURCE_INVALID" if field == "source" else "DECISION_RECORD_INVALID"
    )
    assert result.issues[0].severity == "error"
    assert result.issues[0].description
    assert _snapshot(tmp_path) == before


def test_malformed_cave_proposal_blocks_valid_object(tmp_path):
    pig = _pig_staging()
    pig["proposed_caves"][0]["object_ids"] = "bad"
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        _decisions("create_object", "create_cave"),
        staging_reports=StagingReports(pig=pig),
        data_dir=tmp_path,
    )
    assert result.has_errors and result.written_paths == ()
    assert result.issues[0].code == "STAGING_PROPOSAL_INVALID"
    assert result.issues[0].decision_index == 2
    assert "object_ids" in result.issues[0].description
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("kind", ["cave", "object"])
def test_explicit_create_selects_requested_proposal(tmp_path, kind):
    pig = _pig_staging()
    original = pig[f"proposed_{kind}s"][0]
    if kind == "cave":
        original["object_ids"] = []
        selected_id = "C-0002"
        expected = tmp_path / "caves/C-0002.yml"
    else:
        original["cave_id"] = None
        selected_id = "KSW-0002"
        expected = tmp_path / "objects/KSW/KSW-0002.yml"
    pig[f"proposed_{kind}s"].append({**deepcopy(original), "id": selected_id})
    decisions = _decisions(f"create_{kind}")
    decisions["decisions"][0][f"{kind}_id"] = selected_id
    result = apply_review_decisions(
        decisions, staging_reports=StagingReports(pig=pig), data_dir=tmp_path
    )
    assert not result.has_errors
    assert result.written_paths == (expected,)
    assert not has_errors(validate_data_dir(tmp_path))


@pytest.mark.parametrize("warning_first", [False, True])
def test_warning_cannot_bypass_final_catalog_validation(tmp_path, warning_first):
    from test_staging_review import _tpn_review_only_staging

    decisions = _decisions("create_object")
    warning = {"action": "reject", "source": "TPN", "record_number": 2}
    decisions["decisions"].insert(0 if warning_first else 1, warning)
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        decisions,
        staging_reports=StagingReports(pig=_pig_staging(), tpn=_tpn_review_only_staging()),
        data_dir=tmp_path,
    )
    assert result.has_errors and result.written_paths == ()
    assert [(i.code, i.severity) for i in result.issues] == [
        ("DECISION_REASON_MISSING", "warning"),
        ("PROPOSED_DATA_INVALID", "error"),
    ]
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("warning_first", [False, True])
def test_warning_cannot_drop_deferred_catalog_references(tmp_path, warning_first):
    _sample(tmp_path)
    tpn = _tpn_staging()
    tpn["rows"].append({"record_number": 2, "status": "rejected"})
    decisions = [{"action": "add_measurement", "source": "TPN", "record_number": 1}]
    decisions.insert(
        0 if warning_first else 1, {"action": "reject", "source": "TPN", "record_number": 2}
    )
    result = apply_review_decisions(
        {"decisions": decisions}, staging_reports=StagingReports(tpn=tpn), data_dir=tmp_path
    )
    assert not result.has_errors
    assert [(i.code, i.severity) for i in result.issues] == [("DECISION_REASON_MISSING", "warning")]
    import yaml

    cave = yaml.safe_load((tmp_path / "caves/C-0001.yml").read_text())
    assert tpn["matched_measurements"][0]["cave_external_refs"][0] in cave["external_refs"]
    assert not has_errors(validate_data_dir(tmp_path))


def test_invalid_proposal_is_not_consumed_by_later_decision(tmp_path):
    pig = _pig_staging()
    pig["proposed_objects"][0]["measurements"] = None
    decisions = _decisions("create_object")
    decisions["decisions"].append(
        {"action": "add_measurement", "source": "TPN", "record_number": 1}
    )
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        decisions, staging_reports=StagingReports(pig=pig, tpn=_tpn_staging()), data_dir=tmp_path
    )
    assert result.has_errors and result.written_paths == ()
    assert [(i.code, i.severity) for i in result.issues] == [
        ("STAGING_PROPOSAL_INVALID", "error"),
        ("TARGET_OBJECT_MISSING", "error"),
    ]
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("existing", [False, True])
def test_missing_relative_attachment_is_reported_before_writes(tmp_path, existing):
    attachment = {
        "id": "a-001",
        "kind": "inne",
        "path": "missing-relative-pbi040.txt",
        "created_at": "2026-09-19T12:00:00Z",
        "created_by": "reviewer",
    }
    if existing:
        records = _sample(tmp_path)
        obj = records["objects/KSW/KSW-0001.yml"]
        obj["attachments"] = [attachment]
        _write(tmp_path / "objects/KSW/KSW-0001.yml", obj)
        reports = StagingReports()
        decisions = {"decisions": []}
    else:
        pig = _pig_staging()
        pig["proposed_objects"][0]["attachments"] = [attachment]
        reports = StagingReports(pig=pig)
        decisions = _decisions("create_cave", "create_object")
    before = _snapshot(tmp_path)
    result = apply_review_decisions(decisions, staging_reports=reports, data_dir=tmp_path)
    assert result.has_errors and result.written_paths == ()
    assert "ATTACHMENT_PATH_MISSING" in result.issues[0].description
    assert _snapshot(tmp_path) == before
