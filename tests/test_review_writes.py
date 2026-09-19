"""Review write failures preserve original bytes or leave explicit recovery evidence."""

from pathlib import Path

import pytest
import yaml
from test_cave_membership import _sample, _snapshot

from gps_kataster_obiektow_tatr.staging_review import StagingReports, apply_review_decisions


def _review(root, **kwargs):
    return apply_review_decisions(
        {"decisions": [{"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0002"}]},
        staging_reports=StagingReports(),
        data_dir=root,
        **kwargs,
    )


@pytest.mark.parametrize("operation", ["write", "serialize"])
def test_second_preparation_failure_preserves_every_file(tmp_path, monkeypatch, operation):
    _sample(tmp_path)
    before = _snapshot(tmp_path)
    calls = 0
    owner, name = (Path, "write_text") if operation == "write" else (yaml, "safe_dump")
    original = getattr(owner, name)

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            if operation == "write":
                raise OSError("injected second write")
            raise yaml.YAMLError("injected second serialization")
        return original(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(owner, name, fail_second)
        result = _review(tmp_path)
    assert result.has_errors
    assert result.written_paths == ()
    assert result.issues[-1].code == "REVIEW_WRITE_FAILED"
    assert "injected second" in result.issues[-1].description
    assert _snapshot(tmp_path) == before
    assert not _review(tmp_path).has_errors


@pytest.mark.parametrize("new", [False, True])
@pytest.mark.parametrize("failure_at", [1, 2, 3])
def test_replace_failure_rolls_back_and_retry_works(tmp_path, monkeypatch, new, failure_at):
    from test_review_validation import _decisions
    from test_staging_review import _pig_staging

    from gps_kataster_obiektow_tatr.validator import has_errors, validate_data_dir

    if new:

        def review():
            return apply_review_decisions(
                _decisions("create_cave", "create_object"),
                staging_reports=StagingReports(pig=_pig_staging()),
                data_dir=tmp_path,
            )
    else:
        _sample(tmp_path)

        def review():
            return _review(tmp_path)

    before = _snapshot(tmp_path)
    original = Path.replace
    calls = 0

    def fail(path, target):
        nonlocal calls
        calls += 1
        if calls == failure_at:
            raise OSError("injected replace failure")
        return original(path, target)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "replace", fail)
        result = review()
    assert result.has_errors and result.written_paths == ()
    assert result.issues[-1].code == "REVIEW_WRITE_FAILED"
    assert all(d.status == "write_failed" for d in result.applied_decisions)
    assert _snapshot(tmp_path) == before
    assert not review().has_errors
    assert not has_errors(validate_data_dir(tmp_path))
    assert not (tmp_path / ".review-recovery").exists()


def test_rollback_failure_preserves_backups_and_blocks_retry(tmp_path, monkeypatch):
    import json

    _sample(tmp_path)
    before = _snapshot(tmp_path)
    original = Path.replace
    calls = 0

    def fail(path, target):
        nonlocal calls
        calls += 1
        if calls in (2, 4):
            raise OSError("injected commit and rollback failure")
        return original(path, target)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "replace", fail)
        result = _review(tmp_path)
    assert result.has_errors and not result.written_paths
    issue = result.issues[-1]
    assert issue.code == "REVIEW_RECOVERY_REQUIRED"
    assert "Rollback incomplete" in issue.description
    assert "staging_review_decisions.md#odzyskiwanie" in issue.description
    recovery = tmp_path / ".review-recovery"
    manifest = json.loads((recovery / "manifest.json").read_text())
    for entry in manifest["entries"]:
        assert (recovery / f"{entry['index']}.original").read_bytes() == before[entry["path"]]
    remaining = _snapshot(tmp_path)
    for write in (False, True):
        blocked = _review(tmp_path, write=write)
        assert blocked.has_errors and blocked.applied_decisions == ()
        assert blocked.issues[0].code == "REVIEW_RECOVERY_REQUIRED"
        assert str(recovery) in blocked.issues[0].description
        assert (
            "docs/asdlc/staging_review_decisions.md#odzyskiwanie-po-bledzie-zapisu"
            in blocked.issues[0].description
        )
        assert _snapshot(tmp_path) == remaining
    # Exercise the documented manual restore, then a fresh successful retry.
    import shutil

    for entry in manifest["entries"]:
        shutil.copy2(recovery / f"{entry['index']}.original", tmp_path / entry["path"])
    shutil.rmtree(recovery)
    assert _snapshot(tmp_path) == before
    assert not _review(tmp_path).has_errors


@pytest.mark.parametrize("kind", ["directory", "file", "dangling_symlink"])
@pytest.mark.parametrize("write", [True, False])
def test_any_recovery_evidence_blocks_before_loading(tmp_path, kind, write):
    evidence = tmp_path / ".review-recovery"
    if kind == "directory":
        evidence.mkdir()
    elif kind == "file":
        evidence.write_text("unknown recovery state")
    else:
        evidence.symlink_to(tmp_path / "missing")
    # The catalog is deliberately unreadable; recovery must take precedence.
    (tmp_path / "caves").mkdir()
    (tmp_path / "caves/C-0001.yml").write_text("[")
    result = _review(tmp_path, write=write)
    assert result.has_errors and result.written_paths == ()
    assert result.issues[0].code == "REVIEW_RECOVERY_REQUIRED"
    assert result.applied_decisions == ()


@pytest.mark.parametrize("after_commit", [False, True])
def test_cleanup_error_is_reported_and_never_allows_silent_retry(
    tmp_path, monkeypatch, after_commit
):
    import shutil

    _sample(tmp_path)
    before = _snapshot(tmp_path)
    original = Path.replace

    def fail_replace(path, target):
        if path.suffix == ".prepared":
            raise OSError("commit failure")
        return original(path, target)

    def fail_cleanup(path):
        raise OSError("cleanup failure")

    with monkeypatch.context() as patch:
        patch.setattr(shutil, "rmtree", fail_cleanup)
        if not after_commit:
            patch.setattr(Path, "replace", fail_replace)
        result = _review(tmp_path)
    assert result.has_errors
    assert result.issues[-1].code == "REVIEW_RECOVERY_REQUIRED"
    assert "cleanup failed" in result.issues[-1].description
    expected_state = (
        "All final files committed; do not replay decisions"
        if after_commit
        else "Original bytes restored; new files removed"
    )
    assert expected_state in result.issues[-1].description
    assert (
        "docs/asdlc/staging_review_decisions.md#odzyskiwanie-po-bledzie-zapisu"
        in result.issues[-1].description
    )
    recovery = tmp_path / ".review-recovery"
    assert (recovery / "COMMITTED").exists() == after_commit
    actual = {p: b for p, b in _snapshot(tmp_path).items() if not p.startswith(".review-recovery/")}
    assert (actual != before) == after_commit
    assert _review(tmp_path).issues[0].code == "REVIEW_RECOVERY_REQUIRED"


def test_success_preserves_modes_and_yaml_extensions(tmp_path):
    from gps_kataster_obiektow_tatr.build_db import build_sqlite_database

    _sample(tmp_path)
    path = tmp_path / "objects/KSW/KSW-0001.yml"
    path = path.rename(path.with_suffix(".yaml"))
    path.chmod(0o640)
    result = _review(tmp_path)
    assert not result.has_errors
    assert path in result.written_paths
    assert path.stat().st_mode & 0o777 == 0o640
    assert not path.with_suffix(".yml").exists()
    build_sqlite_database(data_dir=tmp_path, output_path=tmp_path / "check.sqlite")


def test_dry_run_and_empty_batch_do_not_prepare_files(tmp_path, monkeypatch):
    _sample(tmp_path)
    before = _snapshot(tmp_path)

    def forbidden(*args, **kwargs):
        pytest.fail("dry-run or empty batch attempted a write")

    monkeypatch.setattr(Path, "write_text", forbidden)
    assert not _review(tmp_path, write=False).has_errors
    result = apply_review_decisions(
        {"decisions": []}, staging_reports=StagingReports(), data_dir=tmp_path
    )
    assert not result.has_errors and not result.written_paths
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("failure", ["backup", "mode", "manifest", "commit_marker", "parent"])
def test_preparation_and_commit_metadata_failures(tmp_path, monkeypatch, failure):
    import shutil

    _sample(tmp_path)
    before = _snapshot(tmp_path)
    copy = shutil.copy2
    mode = shutil.copymode
    write = Path.write_text
    mkdir = Path.mkdir

    def fail_copy(src, dst, *args, **kwargs):
        if Path(dst).name == "1.original":
            raise OSError("backup failed")
        return copy(src, dst, *args, **kwargs)

    def fail_mode(src, dst, *args, **kwargs):
        if Path(dst).name == "1.prepared":
            raise OSError("chmod failed")
        return mode(src, dst, *args, **kwargs)

    def fail_write(path, *args, **kwargs):
        if path.name == ("manifest.json" if failure == "manifest" else "committed.tmp"):
            raise OSError("metadata write failed")
        return write(path, *args, **kwargs)

    def fail_mkdir(path, *args, **kwargs):
        if path == tmp_path / "objects/KSW":
            raise OSError("parent preparation failed")
        return mkdir(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        if failure == "backup":
            patch.setattr(shutil, "copy2", fail_copy)
        elif failure == "mode":
            patch.setattr(shutil, "copymode", fail_mode)
        elif failure == "parent":
            patch.setattr(Path, "mkdir", fail_mkdir)
        else:
            patch.setattr(Path, "write_text", fail_write)
        result = _review(tmp_path)
    assert result.has_errors and not result.written_paths
    assert result.issues[-1].code == "REVIEW_WRITE_FAILED"
    assert _snapshot(tmp_path) == before
    assert not _review(tmp_path).has_errors


def test_mixed_new_and_existing_records_roll_back(tmp_path, monkeypatch):
    from copy import deepcopy

    from test_review_validation import _decisions
    from test_staging_review import _pig_staging

    _sample(tmp_path)
    pig = deepcopy(_pig_staging())
    cave = pig["proposed_caves"][0]
    obj = pig["proposed_objects"][0]
    cave["id"] = "C-9999"
    cave["object_ids"] = ["KSW-9999"]
    obj["id"] = "KSW-9999"
    obj["cave_id"] = "C-9999"
    # Explicit proposal ids avoid relying on row matching from a different fixture.
    decisions = _decisions("create_cave", "create_object")
    decisions["decisions"][0]["cave_id"] = "C-9999"
    decisions["decisions"][1]["object_id"] = "KSW-9999"
    decisions["decisions"].append(
        {"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0002"}
    )
    before = _snapshot(tmp_path)
    original = Path.replace

    def fail(path, target):
        if Path(target).name == "KSW-9999.yml":
            raise OSError("last mixed record failed")
        return original(path, target)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "replace", fail)
        result = apply_review_decisions(
            decisions, staging_reports=StagingReports(pig=pig), data_dir=tmp_path
        )
    assert result.has_errors
    assert result.issues[-1].code == "REVIEW_WRITE_FAILED"
    assert _snapshot(tmp_path) == before
    retry = apply_review_decisions(
        decisions, staging_reports=StagingReports(pig=pig), data_dir=tmp_path
    )
    assert not retry.has_errors
    assert len(retry.written_paths) == 5


@pytest.mark.parametrize("report_failure", [False, True])
def test_cli_failed_rollback_writes_truthful_error_report(
    tmp_path, monkeypatch, capsys, report_failure
):
    import importlib.util
    import json

    root = tmp_path / "data"
    _sample(root)
    script = Path(__file__).resolve().parents[1] / "scripts/importers/apply_review.py"
    spec = importlib.util.spec_from_file_location("review_cli", script)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    decisions = tmp_path / "decisions.yml"
    decisions.write_text(
        yaml.safe_dump(
            {"decisions": [{"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0002"}]}
        )
    )
    original = Path.replace
    calls = 0

    def fail(path, target):
        nonlocal calls
        calls += 1
        if calls >= 2:
            raise OSError("commit and restore failure")
        return original(path, target)

    monkeypatch.setattr(Path, "replace", fail)
    output = tmp_path / "report"
    if report_failure:

        def fail_report(*args, **kwargs):
            raise OSError("report disk full")

        monkeypatch.setattr(cli, "write_review_report_files", fail_report)
    assert (
        cli.main(
            [
                "--decisions",
                str(decisions),
                "--data-dir",
                str(root),
                "--output-dir",
                str(output),
                "--no-pig-staging",
                "--no-tpn-staging",
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "REVIEW_RECOVERY_REQUIRED" in captured.err
    assert "final YAML was not written" not in captured.err
    assert "wrote final YAML" not in captured.out
    if report_failure:
        assert "Review report write failed" in captured.err
        assert (root / ".review-recovery/manifest.json").is_file()
        return
    report = json.loads((output / "staging-review.json").read_text())
    assert report["issues"][-1]["code"] == "REVIEW_RECOVERY_REQUIRED"
    assert "Rollback incomplete" in (output / "staging-review.md").read_text()


def test_partial_commit_marker_write_cannot_claim_commit_after_rollback(tmp_path, monkeypatch):
    import shutil

    _sample(tmp_path)
    before = _snapshot(tmp_path)
    write = Path.write_text

    def partial_write(path, *args, **kwargs):
        result = write(path, *args, **kwargs)
        if path.name == "committed.tmp":
            raise OSError("close failed after marker bytes written")
        return result

    def fail_cleanup(path):
        raise OSError("cleanup failed")

    monkeypatch.setattr(Path, "write_text", partial_write)
    monkeypatch.setattr(shutil, "rmtree", fail_cleanup)
    result = _review(tmp_path)
    assert result.has_errors
    assert result.issues[-1].code == "REVIEW_RECOVERY_REQUIRED"
    recovery = tmp_path / ".review-recovery"
    assert not (recovery / "COMMITTED").exists()
    assert (recovery / "committed.tmp").is_file()
    assert all((tmp_path / p).read_bytes() == b for p, b in before.items())


def test_new_pair_can_create_nested_data_directory(tmp_path):
    from test_review_validation import _decisions
    from test_staging_review import _pig_staging

    root = tmp_path / "new/nested/data"
    result = apply_review_decisions(
        _decisions("create_cave", "create_object"),
        staging_reports=StagingReports(pig=_pig_staging()),
        data_dir=root,
    )
    assert not result.has_errors
    assert len(result.written_paths) == 2
    assert all(p.is_file() for p in result.written_paths)
    assert not (root / ".review-recovery").exists()


def test_recovery_claim_failure_does_not_remove_other_evidence(tmp_path, monkeypatch):
    _sample(tmp_path)
    before = _snapshot(tmp_path)
    mkdir = Path.mkdir
    recovery = tmp_path / ".review-recovery"

    def competing_claim(path, *args, **kwargs):
        if path == recovery:
            mkdir(path)
            (path / "other-operation").write_bytes(b"keep me")
            raise FileExistsError("another operation owns recovery")
        return mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", competing_claim)
    result = _review(tmp_path)
    assert result.has_errors
    assert result.issues[-1].code == "REVIEW_RECOVERY_REQUIRED"
    assert (recovery / "other-operation").read_bytes() == b"keep me"
    assert all((tmp_path / p).read_bytes() == b for p, b in before.items())
