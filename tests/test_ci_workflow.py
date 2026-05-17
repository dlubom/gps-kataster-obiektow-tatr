from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "validate.yml"
RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"


def test_validate_workflow_uses_local_validation_gate() -> None:
    workflow = yaml.safe_load(VALIDATE_WORKFLOW.read_text(encoding="utf-8"))

    assert workflow["name"] == "validate"
    assert set(workflow["on"]) == {"pull_request", "push"}
    assert workflow["on"]["push"]["branches"] == ["main"]

    run_commands = [step["run"] for step in workflow["jobs"]["validate"]["steps"] if "run" in step]
    assert run_commands == [
        "uv sync",
        "uv run ruff format --check src tests scripts",
        "uv run ruff check src tests scripts",
        "uv run pytest",
        "uv run python scripts/validate.py",
    ]


def test_validate_workflow_does_not_build_release_artifacts() -> None:
    workflow_text = VALIDATE_WORKFLOW.read_text(encoding="utf-8")

    forbidden_release_steps = [
        "scripts/build_db.py",
        "scripts/export_best_measurements.py",
        "actions/upload-artifact",
        "gh release",
    ]
    for forbidden_step in forbidden_release_steps:
        assert forbidden_step not in workflow_text


def test_no_automatic_build_workflow_after_main_merge() -> None:
    assert not (REPO_ROOT / ".github" / "workflows" / "build.yml").exists()


def test_release_workflow_is_tagged_and_requires_license_confirmation() -> None:
    workflow = yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))

    assert workflow["name"] == "release"
    assert workflow["on"]["push"]["tags"] == ["v*"]
    assert set(workflow["on"]) == {"push"}
    assert workflow["permissions"] == {"contents": "write"}
    assert workflow["jobs"]["release"]["needs"] == "license_guard"

    guard_step = workflow["jobs"]["license_guard"]["steps"][0]
    assert guard_step["name"] == "Confirm source data redistribution"
    assert guard_step["env"] == {"SOURCE_LICENSE_CONFIRMED": "${{ vars.SOURCE_LICENSE_CONFIRMED }}"}
    assert "SOURCE_LICENSE_CONFIRMED" in guard_step["run"]
    assert '!= "true"' in guard_step["run"]
    assert "gh release create" not in guard_step["run"]


def test_release_workflow_publishes_expected_files_only_after_guard() -> None:
    workflow = yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))

    steps = workflow["jobs"]["release"]["steps"]
    run_commands = [step["run"].strip() for step in steps if "run" in step]
    assert "uv sync" in run_commands
    assert "uv run python scripts/validate.py" in run_commands
    assert "uv run python scripts/build_release_artifacts.py" in run_commands

    notes_step = next(
        step for step in steps if step["name"] == "Extract release notes from CHANGELOG.md"
    )
    assert "CHANGELOG.md > release_notes.md" in notes_step["run"]
    assert "No CHANGELOG.md entry found" in notes_step["run"]

    release_step = steps[-1]
    assert release_step["name"] == "Publish GitHub Release"
    assert release_step["env"] == {"GH_TOKEN": "${{ github.token }}"}
    assert 'gh release create "${{ steps.version.outputs.VERSION }}"' in release_step["run"]
    assert "--notes-file release_notes.md" in release_step["run"]
    assert '--title "${{ steps.version.outputs.VERSION }}"' in release_step["run"]
    assert "build/exports/best-measurements.geojson" in release_step["run"]
    assert "build/exports/katalog.sqlite.zip" in release_step["run"]
    assert "build/exports/metadata.json" in release_step["run"]
