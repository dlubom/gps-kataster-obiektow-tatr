from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "validate.yml"
BUILD_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "build.yml"
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


def test_build_workflow_generates_and_uploads_artifacts_after_main_merge() -> None:
    workflow = yaml.safe_load(BUILD_WORKFLOW.read_text(encoding="utf-8"))

    assert workflow["name"] == "build"
    assert workflow["on"]["push"]["branches"] == ["main"]
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["permissions"] == {"contents": "read"}

    steps = workflow["jobs"]["build"]["steps"]
    run_commands = [step["run"].strip() for step in steps if "run" in step]
    assert run_commands == [
        "uv sync",
        "uv run python scripts/validate.py",
        "uv run python scripts/build_release_artifacts.py",
    ]

    upload_step = next(step for step in steps if step["name"] == "Upload build artifacts")
    assert upload_step["uses"] == "actions/upload-artifact@v4"
    assert upload_step["with"]["if-no-files-found"] == "error"
    upload_paths = set(upload_step["with"]["path"].splitlines())
    assert upload_paths == {
        "build/katalog.sqlite",
        "build/exports/best-measurements.geojson",
        "build/exports/best-measurements.csv",
        "build/exports/best-measurements.gpx",
        "build/exports/best-measurements.shp.zip",
        "build/exports/katalog.sqlite.zip",
        "build/exports/metadata.json",
    }


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
    assert run_commands == [
        "uv sync",
        "uv run python scripts/validate.py",
        "uv run python scripts/build_release_artifacts.py",
        (
            'gh release create "${GITHUB_REF_NAME}" \\\n'
            "  build/exports/best-measurements.geojson \\\n"
            "  build/exports/best-measurements.csv \\\n"
            "  build/exports/best-measurements.gpx \\\n"
            "  build/exports/best-measurements.shp.zip \\\n"
            "  build/exports/katalog.sqlite.zip \\\n"
            "  build/exports/metadata.json \\\n"
            '  --title "${GITHUB_REF_NAME}" \\\n'
            '  --notes "Generated catalog artifacts for ${GITHUB_REF_NAME}."'
        ),
    ]

    release_step = steps[-1]
    assert release_step["name"] == "Publish GitHub Release"
    assert release_step["env"] == {"GH_TOKEN": "${{ github.token }}"}
