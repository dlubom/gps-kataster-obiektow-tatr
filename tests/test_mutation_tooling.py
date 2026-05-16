import tomllib
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
GITIGNORE = REPO_ROOT / ".gitignore"
MUTATION_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "mutation.yml"

MUTATED_PATHS = [
    "src/gps_kataster_obiektow_tatr/best_measurement.py",
    "src/gps_kataster_obiektow_tatr/coordinates.py",
    "src/gps_kataster_obiektow_tatr/prefix_resolver.py",
    "src/gps_kataster_obiektow_tatr/validator.py",
    "src/gps_kataster_obiektow_tatr/pig_staging.py",
    "src/gps_kataster_obiektow_tatr/tpn_staging.py",
    "src/gps_kataster_obiektow_tatr/staging_review.py",
]

MUTATION_TEST_SELECTION = [
    "tests/test_best_measurement.py",
    "tests/test_coordinates.py",
    "tests/test_prefix_resolver.py",
    "tests/test_validator.py",
    "tests/test_pig_staging.py",
    "tests/test_tpn_staging.py",
    "tests/test_staging_review.py",
]

MUTATION_PYTEST_SELECTION_ARGS = [
    "-k",
    (
        "not test_validate_script_exits_zero_for_warnings_and_nonzero_for_errors "
        "and not test_cli_writes_staging_artifacts_without_final_yaml "
        "and not test_cli_applies_sample_decisions_and_final_yaml_passes_validate_py"
    ),
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

    run_commands = [
        step["run"].strip() for step in workflow["jobs"]["mutation"]["steps"] if "run" in step
    ]
    assert run_commands == [
        "uv sync",
        "uv run pytest",
        "uv run mutmut run --max-children 2",
        "uv run mutmut export-cicd-stats",
    ]

    upload_step = workflow["jobs"]["mutation"]["steps"][-1]
    assert upload_step["uses"] == "actions/upload-artifact@v4"
    assert upload_step["with"]["path"] == "mutants/mutmut-cicd-stats.json"


def test_mutmut_generated_artifacts_are_ignored() -> None:
    ignored_patterns = GITIGNORE.read_text(encoding="utf-8").splitlines()

    assert "mutants/" in ignored_patterns
