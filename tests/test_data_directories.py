"""Missing inputs must never replace real artifacts with an empty catalog."""

import json
import runpy
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from test_staging_review import _pig_staging
from test_tpn_staging import _tpn_row, _write_tpn_csv

from gps_kataster_obiektow_tatr.data_loader import (
    DataDirectoryError,
    YamlDataLoadError,
    check_data_directory,
    load_dataset,
    load_import_target_dataset,
)
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts
from gps_kataster_obiektow_tatr.staging_review import StagingReports, apply_review_decisions
from gps_kataster_obiektow_tatr.tpn_staging import build_tpn_staging
from gps_kataster_obiektow_tatr.validator import has_errors, validate_data_dir

REPO_ROOT = Path(__file__).resolve().parents[1]
STAMP = "2026-09-20T12:00:00Z"


def _pair():
    return {
        "reviewed_at": STAMP,
        "reviewed_by": "test",
        "decisions": [
            {"action": action, "source": "PIG", "record_number": 1}
            for action in ("create_cave", "create_object")
        ],
    }


def _snapshot(path):
    return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()}


def _bad_input(tmp_path, case):
    path = tmp_path / "input"
    if case == "file":
        path.write_text("preserve input file\n")
    elif case == "dangling_link":
        path.symlink_to(tmp_path / "absent-target", target_is_directory=True)
    elif case in {"objects", "caves", "relations"}:
        path.mkdir()
        (path / case).write_text("preserve invalid subtree\n")
    return path


@pytest.mark.parametrize(
    "case", ["missing", "file", "dangling_link", "objects", "caves", "relations"]
)
def test_loader_rejects_invalid_directory_paths(tmp_path, case):
    data_dir = _bad_input(tmp_path, case)
    before = _snapshot(tmp_path)
    with pytest.raises(YamlDataLoadError) as caught:
        load_dataset(data_dir)
    assert str(data_dir) in str(caught.value)
    reason = (
        "does not exist" if case in {"missing", "dangling_link"} else "expected a data directory"
    )
    assert reason in str(caught.value)
    issues = validate_data_dir(data_dir)
    assert [(i.code, i.severity) for i in issues] == [("DATA_DIRECTORY_INVALID", "error")]
    assert issues[0].path == caught.value.path
    assert str(data_dir) in issues[0].description
    assert reason in issues[0].description
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("case", ["missing", "file"])
@pytest.mark.parametrize(
    "operation",
    ["validate", "build_db", "export_best_measurements", "build_release_artifacts", "review"],
)
def test_cli_invalid_input_preserves_artifacts(tmp_path, case, operation):
    data_dir = _bad_input(tmp_path, case)
    output = tmp_path / "output"
    output.mkdir()
    for name in (
        "katalog.sqlite",
        "katalog.sqlite.zip",
        "best-measurements.csv",
        "best-measurements.geojson",
        "best-measurements.gpx",
        "best-measurements.shp.zip",
        "metadata.json",
    ):
        (output / name).write_bytes(b"existing artifact: " + name.encode())
    decisions = tmp_path / "decisions.yml"
    decisions.write_text(yaml.safe_dump(_pair()))
    staging = tmp_path / "pig.json"
    staging.write_text(json.dumps(_pig_staging()))
    script = "importers/apply_review" if operation == "review" else operation
    command = [sys.executable, str(REPO_ROOT / f"scripts/{script}.py"), "--data-dir", str(data_dir)]
    if operation == "review":
        command += [
            "--decisions",
            str(decisions),
            "--pig-staging",
            str(staging),
            "--no-tpn-staging",
            "--output-dir",
            str(tmp_path / "reports"),
        ]
    elif operation == "build_db":
        command += ["--output", str(output / "katalog.sqlite")]
    elif operation != "validate":
        command += ["--output-dir", str(output)]
        if operation == "build_release_artifacts":
            command += ["--sqlite-output", str(output / "katalog.sqlite")]
    before = _snapshot(output)
    result = subprocess.run(command, capture_output=True, text=True, cwd=REPO_ROOT)
    assert result.returncode == 1, result.stdout + result.stderr
    assert str(data_dir) in result.stdout + result.stderr
    assert "Traceback" not in result.stdout + result.stderr
    assert _snapshot(output) == before
    if case == "missing":
        assert not data_dir.exists()
    else:
        assert data_dir.read_text() == "preserve input file\n"


def test_existing_empty_directory_is_a_valid_zero_record_catalog(tmp_path):
    data_dir = tmp_path / "empty"
    data_dir.mkdir()
    assert load_dataset(data_dir).records() == ()
    assert validate_data_dir(data_dir) == ()
    result = build_release_artifacts(
        data_dir=data_dir,
        sqlite_path=tmp_path / "catalog.sqlite",
        output_dir=tmp_path / "exports",
        generated_at=STAMP,
    )
    with sqlite3.connect(result.sqlite_result.sqlite_path) as db:
        assert db.execute("SELECT count(*) FROM objects").fetchone() == (0,)
    assert result.export_result.feature_count == 0
    assert not _snapshot(data_dir)


@pytest.mark.parametrize("write", [False, True])
def test_review_requires_explicit_new_target(tmp_path, write):
    data_dir = tmp_path / "new"
    result = apply_review_decisions(
        _pair(), staging_reports=StagingReports(pig=_pig_staging()), data_dir=data_dir, write=write
    )
    assert result.has_errors
    assert result.issues[0].code == "FINAL_DATA_INVALID"
    assert not data_dir.exists()


def test_explicit_new_target_dry_run_then_import_valid_pair(tmp_path):
    data_dir = tmp_path / "parent" / "new"
    kwargs = {
        "staging_reports": StagingReports(pig=_pig_staging()),
        "data_dir": data_dir,
        "initialize_data_dir": True,
    }
    dry = apply_review_decisions(_pair(), write=False, **kwargs)
    assert not dry.has_errors and dry.written_paths == ()
    assert not data_dir.parent.exists()
    result = apply_review_decisions(_pair(), **kwargs)
    assert not result.has_errors and len(result.written_paths) == 2
    assert not (data_dir / "relations").exists()
    assert not has_errors(validate_data_dir(data_dir))
    artifacts = build_release_artifacts(
        data_dir=data_dir,
        sqlite_path=tmp_path / "catalog.sqlite",
        output_dir=tmp_path / "exports",
        generated_at=STAMP,
    )
    with sqlite3.connect(artifacts.sqlite_result.sqlite_path) as db:
        assert db.execute("SELECT id, cave_id FROM objects").fetchall() == [("KSW-0001", "C-0001")]
    assert artifacts.export_result.feature_count == 1


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize("case", ["file", "dangling_link", "objects", "caves", "relations"])
def test_initialization_does_not_accept_invalid_existing_paths(tmp_path, write, case):
    data_dir = _bad_input(tmp_path, case)
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        _pair(),
        staging_reports=StagingReports(pig=_pig_staging()),
        data_dir=data_dir,
        write=write,
        initialize_data_dir=True,
    )
    assert result.has_errors and result.written_paths == ()
    assert result.issues[0].code == "FINAL_DATA_INVALID"
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("case", ["empty", "bad_pair", "bad_decision"])
def test_new_target_is_not_created_without_valid_records(tmp_path, case):
    decisions = _pair()
    if case == "empty":
        decisions["decisions"] = []
    elif case == "bad_pair":
        decisions["decisions"] = decisions["decisions"][:1]
    else:
        decisions["decisions"][1]["record_number"] = 99
    data_dir = tmp_path / "new"
    result = apply_review_decisions(
        decisions,
        staging_reports=StagingReports(pig=_pig_staging()),
        data_dir=data_dir,
        initialize_data_dir=True,
    )
    assert result.has_errors == (case != "empty")
    assert result.written_paths == () and not data_dir.exists()


def test_initialization_validates_existing_catalog_before_decisions(tmp_path):
    objects = tmp_path / "objects/KSW"
    objects.mkdir(parents=True)
    (objects / "KSW-0001.yml").write_text("id: KSW-0001\n")
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        _pair(),
        staging_reports=StagingReports(pig=_pig_staging()),
        data_dir=tmp_path,
        initialize_data_dir=True,
    )
    assert result.has_errors and result.issues[0].code == "FINAL_DATA_INVALID"
    assert result.applied_decisions == () and _snapshot(tmp_path) == before


def test_directory_access_errors_are_reported(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("read denied")

    monkeypatch.setattr(Path, "stat", denied)
    with pytest.raises(
        DataDirectoryError, match="cannot access data directory.*read denied"
    ) as caught:
        check_data_directory(tmp_path)
    assert caught.value.path == tmp_path


def test_import_target_below_a_file_is_not_treated_as_missing(tmp_path):
    parent = tmp_path / "file"
    parent.write_bytes(b"preserve")
    with pytest.raises(DataDirectoryError, match="cannot access data directory"):
        load_import_target_dataset(parent / "new")
    assert parent.read_bytes() == b"preserve"


def test_directory_symlink_and_existing_import_target_keep_records(tmp_path):
    data_dir = tmp_path / "data"
    result = apply_review_decisions(
        _pair(),
        staging_reports=StagingReports(pig=_pig_staging()),
        data_dir=data_dir,
        initialize_data_dir=True,
    )
    assert not result.has_errors
    link = tmp_path / "link"
    link.symlink_to(data_dir, target_is_directory=True)
    dataset = load_import_target_dataset(link)
    assert len(dataset.objects) == len(dataset.caves) == 1
    assert dataset.relations == ()
    assert dataset.objects[0].path == link / "objects/KSW/KSW-0001.yml"


@pytest.mark.parametrize("dry_run", [False, True])
def test_review_cli_initialization(tmp_path, dry_run):
    main = runpy.run_path(str(REPO_ROOT / "scripts/importers/apply_review.py"))["main"]
    data_dir = tmp_path / "new"
    decision_path = tmp_path / "decisions.yml"
    decision_path.write_text(yaml.safe_dump(_pair()))
    pig_path = tmp_path / "pig.json"
    pig_path.write_text(json.dumps(_pig_staging()))
    args = [
        "--decisions",
        str(decision_path),
        "--pig-staging",
        str(pig_path),
        "--no-tpn-staging",
        "--data-dir",
        str(data_dir),
        "--init-data-dir",
        "--output-dir",
        str(tmp_path / "reports"),
    ]
    if dry_run:
        args.append("--dry-run")
    assert main(args) == 0
    if dry_run:
        assert not data_dir.exists()
    else:
        assert len(load_dataset(data_dir).objects) == 1


def test_tpn_staging_uses_existing_import_target_instead_of_empty_baseline(tmp_path):
    data_dir = tmp_path / "data"
    pig = _pig_staging()
    result = apply_review_decisions(
        _pair(),
        staging_reports=StagingReports(pig=pig),
        data_dir=data_dir,
        initialize_data_dir=True,
    )
    assert not result.has_errors
    cave = pig["proposed_caves"][0]
    measurement = pig["proposed_objects"][0]["measurements"][0]
    inventory = next(
        ref["external_id"] for ref in cave["external_refs"] if ref["system"] == "NR_INWENT"
    )
    source = tmp_path / "tpn.csv"
    _write_tpn_csv(
        source,
        [
            _tpn_row(
                nr_inwent=inventory,
                name=cave["name"],
                globalid="{test-globalid}",
                x_1992=str(measurement["x_1992"]),
                y_1992=str(measurement["y_1992"]),
            )
        ],
    )
    before = _snapshot(data_dir)
    report = build_tpn_staging(source, generated_at=STAMP, data_dir=data_dir, pig_staging_path=None)
    assert report.rows[0].status == "matched"
    assert report.rows[0].match_strategy == "nr_inwent"
    update = report.matched_measurements[0]
    assert (update["target_object_id"], update["target_cave_id"]) == ("KSW-0001", "C-0001")
    assert update["measurement"]["id"] == "m-002"
    assert not report.proposed_objects and not report.proposed_caves
    assert _snapshot(data_dir) == before
