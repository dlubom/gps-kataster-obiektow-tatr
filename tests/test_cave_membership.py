"""Cave membership is symmetric in YAML, review writes and SQLite."""

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from gps_kataster_obiektow_tatr.build_db import (
    BuildDatabaseValidationError,
    build_sqlite_database,
)
from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992
from gps_kataster_obiektow_tatr.data_loader import load_dataset
from gps_kataster_obiektow_tatr.staging_review import StagingReports, apply_review_decisions
from gps_kataster_obiektow_tatr.validator import ValidationSeverity, has_errors, validate_data_dir

REPO_ROOT = Path(__file__).resolve().parents[1]
REVIEWED_AT = "2026-09-19T12:00:00Z"


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _sample(data_dir):
    obj = yaml.safe_load((REPO_ROOT / "tests/fixtures/valid-object.yml").read_text())
    coords = wgs84_to_1992(lat=49.23459299, lon=19.87589498)
    obj["measurements"][0].update(
        lat=49.23459299, lon=19.87589498, x_1992=coords.x_1992, y_1992=coords.y_1992
    )
    cave = yaml.safe_load((REPO_ROOT / "tests/fixtures/valid-cave.yml").read_text())
    cave["object_ids"] = ["KSW-0001", "KSW-0002"]
    records = {
        "objects/KSW/KSW-0001.yml": obj,
        "objects/KSW/KSW-0002.yml": {**deepcopy(obj), "id": "KSW-0002"},
        "caves/C-0001.yml": cave,
        "caves/C-0002.yml": {**deepcopy(cave), "id": "C-0002", "object_ids": []},
        "caves/C-0003.yml": {**deepcopy(cave), "id": "C-0003", "object_ids": []},
    }
    for path, data in records.items():
        _write(data_dir / path, data)
    return records


def _snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("case", ["missing_reverse", "other_cave", "no_cave", "two_caves"])
def test_inconsistent_membership_blocks_validation_and_sqlite(tmp_path, case):
    data_dir = tmp_path / "data"
    records = _sample(data_dir)
    obj = records["objects/KSW/KSW-0001.yml"]
    cave = records["caves/C-0001.yml"]
    if case == "missing_reverse":
        cave["object_ids"].remove(obj["id"])
        expected = ("OBJECT_CAVE_MEMBERSHIP_MISSING", data_dir / "objects/KSW/KSW-0001.yml")
    elif case == "other_cave":
        obj["cave_id"] = "C-0002"
        records["caves/C-0002.yml"]["object_ids"] = [obj["id"]]
        expected = ("CAVE_OBJECT_MEMBERSHIP_MISMATCH", data_dir / "caves/C-0001.yml")
    elif case == "no_cave":
        obj.pop("cave_id")
        expected = ("CAVE_OBJECT_MEMBERSHIP_MISMATCH", data_dir / "caves/C-0001.yml")
    else:
        records["caves/C-0002.yml"]["object_ids"] = [obj["id"]]
        expected = ("CAVE_OBJECT_MEMBERSHIP_MISMATCH", data_dir / "caves/C-0002.yml")
    for path, data in records.items():
        _write(data_dir / path, data)
    before = _snapshot(data_dir)
    errors = [i for i in validate_data_dir(data_dir) if i.severity == ValidationSeverity.ERROR]
    assert [(i.code, i.path) for i in errors] == [expected]
    assert "KSW-0001" in errors[0].description
    assert ("C-0002" if case == "two_caves" else "C-0001") in errors[0].description
    output = tmp_path / "katalog.sqlite"
    output.write_bytes(b"existing artifact")
    with pytest.raises(BuildDatabaseValidationError) as exc:
        build_sqlite_database(data_dir=data_dir, output_path=output)
    assert expected[0] in str(exc.value)
    assert output.read_bytes() == b"existing artifact"
    assert _snapshot(data_dir) == before


@pytest.mark.parametrize("cave_field", ["absent", None])
def test_unassigned_object_and_empty_caves_are_valid(tmp_path, cave_field):
    records = _sample(tmp_path)
    obj = records["objects/KSW/KSW-0001.yml"]
    obj.pop("cave_id")
    if cave_field is None:
        obj["cave_id"] = None
    records["caves/C-0001.yml"]["object_ids"].remove(obj["id"])
    for path, data in records.items():
        _write(tmp_path / path, data)
    issues = validate_data_dir(tmp_path)
    assert not has_errors(issues)
    assert "CAVE_ID_MISSING_FOR_CAVE_OPENING" in {i.code for i in issues}


@pytest.mark.parametrize("targets", [["C-0002"], ["C-0001"], ["C-0002", "C-0003"]])
@pytest.mark.parametrize("initially_linked", [True, False])
def test_link_cave_persists_symmetric_membership_and_preserves_history(
    tmp_path, targets, initially_linked
):
    data_dir = tmp_path / "data"
    records = _sample(data_dir)
    original = records["objects/KSW/KSW-0001.yml"]
    if not initially_linked:
        original.pop("cave_id")
        records["caves/C-0001.yml"]["object_ids"].remove(original["id"])
        for path, data in records.items():
            _write(data_dir / path, data)
    before = _snapshot(data_dir)
    decisions = {
        "reviewed_at": REVIEWED_AT,
        "reviewed_by": "reviewer",
        "decisions": [
            {"action": "link_cave", "object_id": "KSW-0001", "cave_id": target}
            for target in targets
        ],
    }
    dry_run = apply_review_decisions(
        decisions, staging_reports=StagingReports(), data_dir=data_dir, write=False
    )
    assert not dry_run.has_errors
    assert dry_run.written_paths == ()
    assert _snapshot(data_dir) == before
    result = apply_review_decisions(decisions, staging_reports=StagingReports(), data_dir=data_dir)
    assert not result.has_errors
    assert len(result.applied_decisions) == len(targets)
    for index, (applied, target) in enumerate(
        zip(result.applied_decisions, targets, strict=True), 1
    ):
        assert (applied.decision_index, applied.action, applied.status) == (
            index,
            "link_cave",
            "materialized",
        )
        assert (applied.object_id, applied.cave_id) == ("KSW-0001", target)
        assert "KSW-0001" in applied.description and target in applied.description
    touched_caves = set(targets) | ({"C-0001"} if initially_linked else set())
    assert set(result.written_paths) == {
        data_dir / "objects/KSW/KSW-0001.yml",
        *(data_dir / f"caves/{cave}.yml" for cave in touched_caves),
    }
    dataset = load_dataset(data_dir)
    objects = {r.data["id"]: r.raw_data for r in dataset.objects}
    caves = {r.data["id"]: r.raw_data for r in dataset.caves}
    expected = {
        **original,
        "cave_id": targets[-1],
        "updated_at": REVIEWED_AT,
        "updated_by": "reviewer",
    }
    assert objects["KSW-0001"] == expected
    assert objects["KSW-0002"] == records["objects/KSW/KSW-0002.yml"]
    for cave_id, cave in caves.items():
        members = ["KSW-0002"] if cave_id == "C-0001" else []
        if cave_id == targets[-1]:
            members = (
                (["KSW-0001", "KSW-0002"] if initially_linked else ["KSW-0002", "KSW-0001"])
                if cave_id == "C-0001"
                else ["KSW-0001"]
            )
        expected_cave = deepcopy(records[f"caves/{cave_id}.yml"])
        expected_cave["object_ids"] = members
        if cave_id in touched_caves:
            expected_cave.update(updated_at=REVIEWED_AT, updated_by="reviewer")
        assert cave == expected_cave
    assert not has_errors(validate_data_dir(data_dir))
    output = tmp_path / "katalog.sqlite"
    build_sqlite_database(data_dir=data_dir, output_path=output)
    with sqlite3.connect(output) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("SELECT id, cave_id FROM objects ORDER BY id").fetchall() == [
            ("KSW-0001", targets[-1]),
            ("KSW-0002", "C-0001"),
        ]
        assert {
            c: json.loads(ids) for c, ids in conn.execute("SELECT id, object_ids_json FROM caves")
        } == {c: record["object_ids"] for c, record in caves.items()}
        assert conn.execute(
            "SELECT object_id, id, lat, lon FROM measurements ORDER BY object_id"
        ).fetchall() == [
            (identifier, "m-001", 49.23459299, 19.87589498)
            for identifier in ["KSW-0001", "KSW-0002"]
        ]
    # Same target and audit metadata: byte-for-byte safe retry.
    decisions["decisions"] = [decisions["decisions"][-1]]
    after = _snapshot(data_dir)
    retry = apply_review_decisions(decisions, staging_reports=StagingReports(), data_dir=data_dir)
    assert not retry.has_errors
    assert _snapshot(data_dir) == after


@pytest.mark.parametrize("unassigned", [None, []])
def test_unassigned_or_malformed_cave_id_does_not_hide_later_missing_reverse(tmp_path, unassigned):
    records = _sample(tmp_path)
    records["objects/KSW/KSW-0001.yml"]["cave_id"] = unassigned
    records["caves/C-0001.yml"]["object_ids"] = []
    for path, data in records.items():
        _write(tmp_path / path, data)
    errors = [i for i in validate_data_dir(tmp_path) if i.severity == ValidationSeverity.ERROR]
    membership = [i for i in errors if i.code == "OBJECT_CAVE_MEMBERSHIP_MISSING"]
    assert len(membership) == 1
    assert membership[0].path == tmp_path / "objects/KSW/KSW-0002.yml"
    assert "KSW-0002" in membership[0].description
    assert {i.code for i in errors} == (
        {"OBJECT_CAVE_MEMBERSHIP_MISSING", "SCHEMA_VALIDATION"}
        if unassigned == []
        else {"OBJECT_CAVE_MEMBERSHIP_MISSING"}
    )


@pytest.mark.parametrize("missing", ["object", "cave"])
def test_missing_membership_target_reports_domain_error_without_crashing(tmp_path, missing):
    records = _sample(tmp_path)
    if missing == "object":
        path = "caves/C-0002.yml"
        records[path]["object_ids"] = ["KSW-9999"]
        code = "CAVE_OBJECT_REFERENCE_MISSING"
    else:
        path = "objects/KSW/KSW-0001.yml"
        records[path]["cave_id"] = "C-9999"
        records["caves/C-0001.yml"]["object_ids"].remove("KSW-0001")
        code = "CAVE_REFERENCE_MISSING"
    for relative, data in records.items():
        _write(tmp_path / relative, data)
    errors = [i for i in validate_data_dir(tmp_path) if i.severity == ValidationSeverity.ERROR]
    assert [(i.code, i.path) for i in errors] == [(code, tmp_path / path)]


@pytest.mark.parametrize(
    ("object_id", "cave_id", "code"),
    [
        (None, "C-0002", "LINK_CAVE_TARGET_MISSING"),
        ("KSW-0001", None, "LINK_CAVE_TARGET_MISSING"),
        (None, None, "LINK_CAVE_TARGET_MISSING"),
        ("KSW-9999", "C-0002", "LINK_OBJECT_MISSING"),
        ("KSW-0001", "C-9999", "LINK_CAVE_MISSING"),
    ],
)
def test_invalid_link_target_blocks_entire_batch_without_writes(tmp_path, object_id, cave_id, code):
    _sample(tmp_path)
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        {
            "decisions": [
                {"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0002"},
                {"action": "link_cave", "object_id": object_id, "cave_id": cave_id},
            ]
        },
        staging_reports=StagingReports(),
        data_dir=tmp_path,
    )
    assert result.has_errors
    assert result.written_paths == ()
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert (issue.code, issue.severity.value, issue.decision_index) == (code, "error", 2)
    assert isinstance(issue.description, str) and issue.description
    assert _snapshot(tmp_path) == before
