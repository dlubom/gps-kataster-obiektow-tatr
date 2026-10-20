"""The PR download uses release exports without running PR code with write access."""

import shlex
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _workflow(name: str) -> dict:
    return yaml.safe_load((REPO_ROOT / ".github/workflows" / name).read_text())


def test_pr_data_builds_the_merge_candidate_with_read_only_permissions() -> None:
    workflow = _workflow("pr-data.yml")
    assert workflow["name"] == "PR data exports"
    assert set(workflow["on"]) == {"pull_request"}
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] is True
    job = workflow["jobs"]["build"]
    assert "permissions" not in job
    checkout = job["steps"][0]
    assert checkout["uses"] == "actions/checkout@v4"
    assert checkout["with"] == {
        "ref": "${{ github.sha }}",
        "fetch-depth": 0,
        "persist-credentials": False,
    }
    verify = next(step for step in job["steps"] if step["name"] == "Verify merge candidate")
    assert verify["env"] == {
        "HEAD_SHA": "${{ github.event.pull_request.head.sha }}",
        "BASE_SHA": "${{ github.event.pull_request.base.sha }}",
        "MERGE_SHA": "${{ github.sha }}",
    }
    assert 'test "$(git rev-parse HEAD)" = "$MERGE_SHA"' in verify["run"]
    assert 'test "$(git show -s --format=%P HEAD)" = "$BASE_SHA $HEAD_SHA"' in verify["run"]
    build = next(step for step in job["steps"] if step.get("id") == "build")
    assert "scripts/build_pr_data_preview.py" in build["run"]
    for flag in (
        "--pr-number",
        "--head-commit",
        "--base-commit",
        "--merge-commit",
        "--run-id",
        "--run-attempt",
    ):
        assert flag in build["run"]
    upload = next(step for step in job["steps"] if step.get("id") == "upload")
    assert upload["uses"] == "actions/upload-artifact@v4"
    assert upload["with"] == {
        "name": "${{ steps.build.outputs.artifact_name }}",
        "path": "build/pr-data/exports/",
        "if-no-files-found": "error",
        "retention-days": 90,
    }


def test_publisher_uses_only_trusted_workflow_code_and_minimal_permissions() -> None:
    workflow = _workflow("publish-pr-data.yml")
    assert set(workflow["on"]) == {"workflow_run"}
    assert workflow["on"]["workflow_run"] == {
        "workflows": ["PR data exports"],
        "types": ["in_progress", "completed"],
    }
    assert workflow["permissions"] == {
        "contents": "read",
        "actions": "read",
        "pull-requests": "write",
    }
    assert workflow["concurrency"]["cancel-in-progress"] is False
    job = workflow["jobs"]["publish"]
    assert "github.event.workflow_run.event == 'pull_request'" in job["if"]
    assert len(job["steps"]) == 2
    checkout, publish = job["steps"]
    assert checkout["uses"] == "actions/checkout@v4"
    assert checkout["with"] == {
        "ref": "${{ github.workflow_sha }}",
        "persist-credentials": False,
    }
    assert publish["uses"] == "actions/github-script@v8"
    assert "publish_pr_data.cjs" in publish["with"]["script"]
    assert "${{" not in publish["with"]["script"]
    assert not any("run" in step for step in job["steps"])


def test_preview_and_official_release_share_the_complete_asset_list() -> None:
    from gps_kataster_obiektow_tatr.release_artifacts import RELEASE_ASSET_FILENAMES

    release = _workflow("release.yml")
    command = release["jobs"]["release"]["steps"][-1]["run"]
    uploaded = {
        Path(token).name
        for token in shlex.split(command.replace("\\\n", ""))
        if token.startswith("build/exports/")
    }
    assert uploaded == set(RELEASE_ASSET_FILENAMES)
    assert len(uploaded) == 9


def test_ci_executes_the_publisher_behavior_tests() -> None:
    workflow = _workflow("validate.yml")
    commands = [step.get("run", "") for step in workflow["jobs"]["validate"]["steps"]]
    assert "node --test tests/test_pr_data_publisher.cjs" in commands
