"""Real Git event baselines, including missing and zero push bases."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sql_test_support import module


def git(tmp_path, *args):
    return subprocess.run(
        ["git", "-C", str(tmp_path), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def revisions(tmp_path, monkeypatch):
    git(tmp_path, "init")
    for value in ["accepted", "candidate"]:
        (tmp_path / "value").write_text(value)
        git(tmp_path, "add", "value")
        git(
            tmp_path,
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-qm",
            value,
        )
    head = git(tmp_path, "rev-parse", "HEAD")
    parent = git(tmp_path, "rev-parse", "HEAD^1")
    git(tmp_path, "update-ref", "refs/remotes/origin/main", head)
    monkeypatch.chdir(tmp_path)
    return parent, head


@pytest.mark.parametrize("event", ["pull_request", "push", "release", "workflow_dispatch"])
def test_ci_uses_actual_event_baseline(revisions, event):
    base, head = revisions
    resolver = module("ci_baseline")
    if event == "pull_request":
        value = resolver.resolve_baseline(
            event, {"pull_request": {"base": {"sha": base}}}, "refs/pull/7/merge"
        )
    elif event == "push":
        value = resolver.resolve_baseline(event, {"before": base}, "refs/heads/main")
    elif event == "release":
        value = resolver.resolve_baseline("push", {}, "refs/tags/v1.0.0")
    else:
        value = resolver.resolve_baseline(event, {}, "refs/heads/main")
    assert value == base and value != head


@pytest.mark.parametrize("base", [None, "", "0" * 40, "a" * 40, "HEAD"])
def test_ci_missing_or_unavailable_baseline_fails(revisions, base):
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        module("ci_baseline").resolve_baseline("push", {"before": base}, "refs/heads/main")


def test_ci_rejects_self_baseline_and_unaccepted_release(revisions, tmp_path):
    base, head = revisions
    resolver = module("ci_baseline")
    with pytest.raises(ValueError, match="own history"):
        resolver.resolve_baseline("push", {"before": head}, "refs/heads/main")
    git(tmp_path, "update-ref", "refs/remotes/origin/main", base)
    with pytest.raises(subprocess.CalledProcessError):
        resolver.resolve_baseline("push", {}, "refs/tags/v1.0.0")


@pytest.mark.parametrize(
    ("event", "ref", "payload"),
    [
        ("pull_request", "refs/pull/7/merge", "pr"),
        ("push", "refs/heads/main", "push"),
        ("push", "refs/tags/v1.0.0", "tag"),
        ("workflow_dispatch", "refs/heads/main", "manual"),
    ],
)
def test_ci_baseline_step_exports_real_event_sha(revisions, tmp_path, event, ref, payload):
    base, head = revisions
    source = Path(__file__).resolve().parents[1] / "scripts/ci_baseline.py"
    event_file = tmp_path / "event.json"
    event_file.write_text(
        json.dumps(
            {"pull_request": {"base": {"sha": base}}}
            if payload == "pr"
            else {"before": base}
            if payload == "push"
            else {}
        )
    )
    output = tmp_path / "github-env"
    output.write_text("KATASTER_POSTGRES_CONTAINER=existing-service\n")
    result = subprocess.run(
        [sys.executable, str(source)],
        cwd=tmp_path,
        env={
            **os.environ,
            "GITHUB_EVENT_NAME": event,
            "GITHUB_EVENT_PATH": str(event_file),
            "GITHUB_REF": ref,
            "GITHUB_ENV": str(output),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert output.read_text() == (
        f"KATASTER_POSTGRES_CONTAINER=existing-service\nHISTORY_BASE_SHA={base}\n"
    )
    assert head not in output.read_text()


def test_manual_ci_branch_uses_accepted_main_not_its_parent(revisions, tmp_path):
    base, head = revisions
    git(tmp_path, "update-ref", "refs/remotes/origin/main", base)
    (tmp_path / "value").write_text("branch candidate")
    git(tmp_path, "add", "value")
    git(
        tmp_path,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "branch candidate",
    )
    assert git(tmp_path, "rev-parse", "HEAD^1") == head
    assert (
        module("ci_baseline").resolve_baseline("workflow_dispatch", {}, "refs/heads/feature")
        == base
    )
    assert base != head


def test_ci_baseline_failure_does_not_export_candidate(revisions, tmp_path):
    _, head = revisions
    source = Path(__file__).resolve().parents[1] / "scripts/ci_baseline.py"
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps({"before": head}))
    output = tmp_path / "github-env"
    output.write_text("KATASTER_POSTGRES_CONTAINER=existing-service\n")
    result = subprocess.run(
        [sys.executable, str(source)],
        cwd=tmp_path,
        env={
            **os.environ,
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_EVENT_PATH": str(event_file),
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_ENV": str(output),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "own history baseline" in result.stderr
    assert output.read_text() == "KATASTER_POSTGRES_CONTAINER=existing-service\n"
