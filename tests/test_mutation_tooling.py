import tomllib
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
GITIGNORE = REPO_ROOT / ".gitignore"
MUTATION_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "mutation.yml"

MUTATED_PATHS = [
    "src/gps_kataster_obiektow_tatr/coordinates.py",
    "src/gps_kataster_obiektow_tatr/prefix_resolver.py",
    "src/gps_kataster_obiektow_tatr/validator.py",
]

MUTATION_TEST_SELECTION = [
    "tests/test_coordinates.py",
    "tests/test_prefix_resolver.py",
    "tests/test_validator.py",
]

MUTATION_PYTEST_SELECTION_ARGS = [
    "-k",
    ("not test_validate_script_exits_zero_for_warnings_and_nonzero_for_errors"),
]

MUTATION_SUPPORT_PATHS = [
    "src/gps_kataster_obiektow_tatr",
    "scripts",
    "config",
    "schema",
    "data/shapes",
]


def test_mutmut_is_configured_for_critical_modules() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    dev_dependencies = pyproject["dependency-groups"]["dev"]
    assert any(dependency.startswith("mutmut") for dependency in dev_dependencies)

    mutmut_config = pyproject["tool"]["mutmut"]
    assert mutmut_config["paths_to_mutate"] == MUTATED_PATHS
    assert mutmut_config["tests_dir"] == MUTATION_TEST_SELECTION
    assert mutmut_config["pytest_add_cli_args_test_selection"] == MUTATION_PYTEST_SELECTION_ARGS
    assert mutmut_config["also_copy"] == MUTATION_SUPPORT_PATHS
    assert mutmut_config["max_stack_depth"] == 8

    for relative_path in MUTATED_PATHS + MUTATION_TEST_SELECTION + MUTATION_SUPPORT_PATHS:
        assert (REPO_ROOT / relative_path).exists()


def test_mutation_workflow_is_manual_and_uses_local_mutmut_config() -> None:
    workflow = yaml.safe_load(MUTATION_WORKFLOW.read_text(encoding="utf-8"))

    assert workflow["name"] == "mutation"
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}

    steps = workflow["jobs"]["mutation"]["steps"]
    assert any(s.get("uses") == "./.github/actions/setup-runtime" for s in steps)
    runtime = yaml.safe_load((REPO_ROOT / ".github/actions/setup-runtime/action.yml").read_text())
    run_commands = [
        step["run"].strip() for step in [*runtime["runs"]["steps"], *steps] if "run" in step
    ]
    for command in [
        "uv sync --frozen",
        "uv run --frozen pytest",
        "uv run --frozen mutmut run --max-children 2",
        "uv run --frozen mutmut export-cicd-stats",
    ]:
        assert command in run_commands

    upload_step = workflow["jobs"]["mutation"]["steps"][-1]
    assert upload_step["uses"] == "actions/upload-artifact@v4"
    assert upload_step["with"]["path"] == "mutants/mutmut-cicd-stats.json"


def test_mutmut_generated_artifacts_are_ignored() -> None:
    ignored_patterns = GITIGNORE.read_text(encoding="utf-8").splitlines()

    assert "mutants/" in ignored_patterns
