from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "validate.yml"


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
