from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "validate.yml"
RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"
RUNTIME_ACTION = REPO_ROOT / ".github/actions/setup-runtime/action.yml"


def runtime_steps():
    return yaml.safe_load(RUNTIME_ACTION.read_text(encoding="utf-8"))["runs"]["steps"]


def test_validate_workflow_uses_local_validation_gate() -> None:
    workflow = yaml.safe_load(VALIDATE_WORKFLOW.read_text(encoding="utf-8"))

    assert workflow["name"] == "validate"
    assert set(workflow["on"]) == {"pull_request", "push"}
    assert workflow["on"]["push"]["branches"] == ["main"]

    steps = workflow["jobs"]["validate"]["steps"]
    assert any(s.get("uses") == "./.github/actions/setup-runtime" for s in steps)
    run_commands = [step["run"] for step in [*runtime_steps(), *steps] if "run" in step]
    assert "uv sync --frozen" in run_commands
    for command in (
        "uv run --frozen ruff format --check src tests scripts",
        "uv run --frozen ruff check src tests scripts",
        "uv run --frozen pytest",
        'uv run --frozen python scripts/validate.py --base-ref "$HISTORY_BASE_SHA"',
    ):
        assert command in run_commands
    assert workflow["jobs"]["validate"]["name"] == "Validate code and data"
    smoke = workflow["jobs"]["validate"]["steps"][-1]
    assert smoke["env"]["KATASTER_DOCKER_SMOKE"] == "1"
    assert "test_postgres_runtime.py -k real_managed_docker" in smoke["run"]


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


def test_release_workflow_is_tagged_without_license_confirmation_guard() -> None:
    workflow = yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))
    workflow_text = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert workflow["name"] == "release"
    assert workflow["on"]["push"]["tags"] == ["v*"]
    assert set(workflow["on"]) == {"push"}
    assert workflow["permissions"] == {"contents": "write"}
    assert set(workflow["jobs"]) == {"release"}
    assert "needs" not in workflow["jobs"]["release"]
    assert "SOURCE_LICENSE_CONFIRMED" not in workflow_text
    assert "license_guard" not in workflow_text


def test_release_workflow_publishes_expected_files_from_changelog() -> None:
    workflow = yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))

    steps = workflow["jobs"]["release"]["steps"]
    assert any(s.get("uses") == "./.github/actions/setup-runtime" for s in steps)
    run_commands = [step["run"].strip() for step in [*runtime_steps(), *steps] if "run" in step]
    assert "uv sync --frozen" in run_commands
    assert (
        'uv run --frozen python scripts/validate.py --base-ref "$HISTORY_BASE_SHA"' in run_commands
    )
    build_step = next(step for step in steps if step["name"] == "Build release artifacts")
    assert "--artifact-list > build/release-artifacts.list" in build_step["run"]
    assert '--base-ref "$HISTORY_BASE_SHA"' in build_step["run"]

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
    assert '"${artifacts[@]}"' in release_step["run"]
    assert "done < build/release-artifacts.list" in release_step["run"]


def test_all_database_workflows_use_same_pinned_runtime_and_history_gate():
    from gps_kataster_obiektow_tatr.postgres import DOCKER_IMAGE

    compose = yaml.safe_load((REPO_ROOT / "compose.yaml").read_text())
    assert compose["services"]["postgres"]["image"] == DOCKER_IMAGE
    assert compose["services"]["postgres"]["platform"] == "linux/amd64"
    assert compose["services"]["postgres"]["tmpfs"] == ["/var/lib/postgresql"]
    for name, job in [
        ("validate", "validate"),
        ("pr-preview", "preview"),
        ("release", "release"),
        ("mutation", "mutation"),
    ]:
        workflow = yaml.safe_load((REPO_ROOT / f".github/workflows/{name}.yml").read_text())
        config = workflow["jobs"][job]
        assert config["runs-on"] == "ubuntu-24.04"
        assert config["services"]["postgres"]["image"] == DOCKER_IMAGE
        steps = config["steps"]
        checkout = steps[0]
        assert checkout["with"]["fetch-depth"] == 0
        assert checkout["with"]["persist-credentials"] is False
        setup = next(s for s in steps if s.get("uses") == "./.github/actions/setup-runtime")
        assert setup["with"]["postgres-container"] == "${{ job.services.postgres.id }}"
        clients = next(s for s in runtime_steps() if "PG_SERVICE_CONTAINER" in s.get("env", {}))
        assert clients["env"]["PG_SERVICE_CONTAINER"] == "${{ inputs.postgres-container }}"
        assert "KATASTER_DATABASE_URL=" in clients["run"]
        assert any(s.get("run") == "python scripts/ci_baseline.py" for s in steps)
        assert any("gdal-bin=3.8.4+dfsg-3ubuntu3" in s.get("run", "") for s in runtime_steps())
        if name in ("validate", "mutation"):
            node = next(s for s in steps if s.get("uses", "").startswith("actions/setup-node@"))
            assert node["with"]["node-version"] == "24.22.2"
        sync = steps.index(setup)  # Frozen sync completes inside the shared action.
        assert any(s.get("run") == "uv sync --frozen" for s in runtime_steps())
        if name != "release":
            assert workflow["permissions"] == {"contents": "read"}
            assert "GH_TOKEN" not in str(steps)
        if name in ("release", "pr-preview"):
            build = next(i for i, s in enumerate(steps) if "scripts/build_" in s.get("run", ""))
            assert build > sync
            assert build < len(steps) - 1
