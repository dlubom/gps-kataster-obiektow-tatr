"""Monthly cycles use real Git/snapshots/batches; only remote GitHub is simulated."""

import importlib.util
import json
import os
import subprocess
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from test_tpn_batch import batch_repo as batch_repo
from test_tpn_batch import git, hashes
from test_tpn_changes import feature
from test_tpn_workflow import accepted, acquisition, workflow
from test_tpn_workflow_github import FakeGitHub, integration, plan

REPO = Path(__file__).resolve().parents[1]


def monthly(g, root, output, **kwargs):
    return plan(g, root, output, event_name="schedule", monthly_enabled=True, **kwargs)


def publish(g, root, output, result):
    return integration().publish_workflow(
        root,
        g,
        output,
        operation="prepare",
        run_id=result["run_id"],
        actor="maintainer",
        triggering_actor="maintainer",
        trusted_sha=g.base,
        event_name="schedule",
        monthly_enabled=True,
    )


def test_schedule_disabled_never_contacts_api_or_changes_git(batch_repo, tmp_path):
    root, _ = batch_repo
    g = FakeGitHub(root, accepted(batch_repo))
    g.main = lambda: pytest.fail("disabled schedule contacted GitHub")
    before = hashes(root)
    result = plan(g, root, tmp_path / "disabled", event_name="schedule")
    assert result["outcome"] == "disabled"
    assert hashes(root) == before and not g.writes
    assert json.loads((tmp_path / "disabled/diagnostics.json").read_text())["outcome"] == "disabled"


@pytest.mark.parametrize("operation", ["apply", "refresh"])
def test_schedule_cannot_apply_human_decisions(batch_repo, tmp_path, operation):
    root, _ = batch_repo
    g = FakeGitHub(root, accepted(batch_repo))
    with pytest.raises(ValueError, match="schedule.*prepare"):
        monthly(g, root, tmp_path / operation, operation=operation)
    assert not g.writes


@pytest.mark.parametrize("lon,outcome", [(19.801, "noop"), (19.802, "publish")])
def test_manual_and_monthly_produce_same_source_result(batch_repo, tmp_path, lon, outcome):
    root, _ = batch_repo
    g = FakeGitHub(root, accepted(batch_repo))
    before = hashes(root)
    for name, invoke in (("manual", plan), ("monthly", monthly)):
        out = tmp_path / name
        result = invoke(g, root, out, acquire=acquisition([feature(lon=lon)]))
        assert result["outcome"] == outcome
        report = json.loads((out / "check/report.json").read_text())
        assert report["requires_pr"] is (outcome == "publish")
        assert report["accepted_state_commit"] == g.base
        assert (out / "check/report.md").is_file()
        assert (out / "check/snapshot/manifest.json").is_file()
        if name == "manual":
            manual = report
        else:
            assert report["records"] == manual["records"]
            assert report["deferred"] == manual["deferred"]
            assert report["summary"] == manual["summary"]
    assert hashes(root) == before and not g.writes


def test_two_months_of_open_pr_report_new_source_without_touching_review(
    batch_repo, tmp_path, monkeypatch
):
    from gps_kataster_obiektow_tatr import tpn_workflow_reporting as reporting

    root, _ = batch_repo
    g = FakeGitHub(root, accepted(batch_repo))
    first = monthly(g, root, tmp_path / "first")
    publish(g, root, tmp_path / "first", first)
    g.items[0]["created_at"] = "2026-10-01T03:17:00Z"
    before, pulls, refs = hashes(root), deepcopy(g.items), dict(g.refs)
    writes = list(g.writes)
    for run, date, age, lon in (
        ("124", "2026-11-01T03:17:00+00:00", 31, 19.803),
        ("125", "2026-12-01T03:17:00+00:00", 61, 19.804),
    ):

        class Clock(datetime):
            @classmethod
            def now(cls, tz=None, date=date):
                return datetime.fromisoformat(date).astimezone(tz or UTC)

        monkeypatch.setattr(reporting, "datetime", Clock)
        out = tmp_path / run
        result = monthly(g, root, out, run_id=run, acquire=acquisition([feature(lon=lon)]))
        assert result["outcome"] == "existing"
        diag = json.loads((out / "diagnostics.json").read_text())
        assert diag["open_prs"][0]["number"] == 17
        assert diag["open_prs"][0]["age_days"] == age
        assert diag["requires_pr"] is True
        report = json.loads((out / "check/report.json").read_text())
        assert float(report["records"][0]["source_after"]["location"]["lon"]) == lon
        assert not (out / "candidate.bundle").exists()
        assert g.items == pulls and g.refs == refs and g.writes == writes
        assert hashes(root) == before


def test_open_pr_does_not_hide_incomplete_api(batch_repo, tmp_path):
    root, _ = batch_repo
    g = FakeGitHub(root, accepted(batch_repo))
    first = monthly(g, root, tmp_path / "first")
    publish(g, root, tmp_path / "first", first)
    before = hashes(root)
    writes = list(g.writes)

    def fail(*args):
        raise ValueError("incomplete API")

    with pytest.raises(ValueError, match="incomplete API"):
        monthly(g, root, tmp_path / "failed", acquire=fail)
    assert hashes(root) == before and g.writes == writes


@pytest.mark.parametrize("failed_source", [False, True])
def test_orphan_recovery_still_checks_fresh_source(batch_repo, tmp_path, failed_source):
    root, _ = batch_repo
    g = FakeGitHub(root, accepted(batch_repo))
    first = monthly(g, root, tmp_path / "first")
    g.fail_create = True
    with pytest.raises(OSError):
        publish(g, root, tmp_path / "first", first)
    before, refs, writes = hashes(root), dict(g.refs), list(g.writes)

    def fail(*args):
        raise ValueError("incomplete API during recovery")

    out = tmp_path / "recovery"
    if failed_source:
        with pytest.raises(ValueError, match="incomplete API during recovery"):
            monthly(g, root, out, run_id="124", acquire=fail)
    else:
        result = monthly(g, root, out, run_id="124", acquire=acquisition([feature(lon=19.804)]))
        assert result["head"] == first["head"] and result["batch_id"] == first["batch_id"]
        report = json.loads((out / "check/report.json").read_text())
        assert float(report["records"][0]["source_after"]["location"]["lon"]) == 19.804
    assert hashes(root) == before and g.refs == refs and g.writes == writes


def test_closed_unmerged_pr_does_not_accept_source(batch_repo, tmp_path):
    root, _ = batch_repo
    g = FakeGitHub(root, accepted(batch_repo))
    first = monthly(g, root, tmp_path / "first")
    publish(g, root, tmp_path / "first", first)
    g.items[0].update(state="closed", merged_at=None)
    result = monthly(g, root, tmp_path / "next", run_id="124")
    assert result["outcome"] == "publish" and result["branch"] != first["branch"]
    assert result["main"] == g.base
    assert g.refs[first["branch"]] == first["head"]


def test_next_cycle_uses_merged_main_and_retains_defer(batch_repo, tmp_path):
    from gps_kataster_obiektow_tatr.tpn_batch import check_batch, load_batch

    root, _ = batch_repo
    main = accepted(batch_repo)
    w = workflow()
    w.prepare_candidate(root, main, "gha-1", acquisition([feature(lon=19.802)]))
    _, decisions = load_batch(root, "gha-1")
    decisions["decisions"][0].update(
        status="defer",
        reviewed_by="github:maintainer",
        reviewed_at="2026-10-21T12:00:00Z",
        reason="Need field evidence",
        actions=[],
    )
    (root / "data/source_reviews/tpn/gha-1/decisions.yml").write_text(json.dumps(decisions))
    git(root, "add", ".")
    git(root, "commit", "-qm", "human defer")
    w.apply_candidate(root, main, "gha-1", "maintainer")
    check_batch(root, "gha-1")
    # Only this isolated fixture simulates the human merge.
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    g = FakeGitHub(root, git(root, "rev-parse", "HEAD"))
    result = monthly(g, root, tmp_path / "same", acquire=acquisition([feature(lon=19.802)]))
    assert result["main"] != main and result["outcome"] == "noop"
    report = json.loads((tmp_path / "same/check/report.json").read_text())
    assert len(report["deferred"]) == 1
    result = monthly(
        g, root, tmp_path / "revision", run_id="124", acquire=acquisition([feature(lon=19.803)])
    )
    assert result["outcome"] == "publish"


def test_publisher_rechecks_activation_and_binds_event(batch_repo, tmp_path):
    root, _ = batch_repo
    g = FakeGitHub(root, accepted(batch_repo))
    result = monthly(g, root, tmp_path / "first")
    options = dict(
        operation="prepare",
        run_id="123",
        actor="maintainer",
        triggering_actor="maintainer",
        trusted_sha=g.base,
    )
    with pytest.raises(ValueError, match="disabled"):
        integration().publish_workflow(
            root, g, tmp_path / "first", event_name="schedule", **options
        )
    with pytest.raises(ValueError, match="event_name"):
        integration().publish_workflow(root, g, tmp_path / "first", **options)
    publish(g, root, tmp_path / "first", result)
    assert len(g.items) == 1


def test_publication_race_reports_actual_pr_in_separate_job(batch_repo, tmp_path):
    import shutil

    from gps_kataster_obiektow_tatr.tpn_workflow_reporting import render_run_summary, run_report

    root, _ = batch_repo
    g = FakeGitHub(root, accepted(batch_repo))
    planned = monthly(g, root, tmp_path / "plan")
    out = tmp_path / "publish"
    out.mkdir()
    for name in ("plan.json", "candidate.bundle"):
        shutil.copy2(tmp_path / "plan" / name, out / name)
    g.items.append(
        {
            "number": 45,
            "state": "open",
            "base": {"ref": "main"},
            "head": {"ref": "tpn-sync/human", "sha": "f" * 40, "repo": {"full_name": g.repository}},
        }
    )
    result = publish(g, root, out, planned)
    diagnostic = run_report(out, result)
    assert result["outcome"] == "existing" and not g.writes
    assert diagnostic["open_prs"][0]["number"] == 45
    summary = render_run_summary(result, diagnostic)
    assert "/pull/45" in summary
    assert planned["head"] not in summary


def test_disabled_cli_without_dispatch_inputs_writes_summary(tmp_path):
    output = tmp_path / "out"
    summary = tmp_path / "summary.md"
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/run_tpn_sync.py"), "plan", "--output", str(output)],
        env={
            **os.environ,
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": "a" * 40,
            "GITHUB_WORKFLOW_SHA": "a" * 40,
            "GITHUB_REPOSITORY": "owner/catalog",
            "GITHUB_TOKEN": "test-token",
            "GITHUB_EVENT_NAME": "schedule",
            "GITHUB_RUN_ID": "123",
            "GITHUB_ACTOR": "maintainer",
            "GITHUB_TRIGGERING_ACTOR": "maintainer",
            "GITHUB_STEP_SUMMARY": str(summary),
            "TPN_MONTHLY_ENABLED": "",
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["outcome"] == "disabled"
    assert "disabled" in summary.read_text()


def test_cli_error_leaves_diagnostics_and_summary(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("tpn_cli", REPO / "scripts/run_tpn_sync.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def fail(*args, **kwargs):
        raise ValueError("incomplete API")

    monkeypatch.setattr(module, "plan_workflow", fail)
    for key, value in {
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_SHA": "a" * 40,
        "GITHUB_WORKFLOW_SHA": "a" * 40,
        "GITHUB_REPOSITORY": "owner/catalog",
        "GITHUB_TOKEN": "test",
        "GITHUB_EVENT_NAME": "schedule",
        "GITHUB_RUN_ID": "123",
        "GITHUB_ACTOR": "maintainer",
        "GITHUB_TRIGGERING_ACTOR": "maintainer",
        "TPN_MONTHLY_ENABLED": "true",
        "TPN_OPERATION": "prepare",
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(sys, "argv", ["run_tpn_sync.py", "plan", "--output", str(tmp_path / "out")])
    assert module.main() == 1
    assert json.loads((tmp_path / "out/diagnostics.json").read_text())["outcome"] == "error"
    assert "incomplete API" in (tmp_path / "summary.md").read_text()
