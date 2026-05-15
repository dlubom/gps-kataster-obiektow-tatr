import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = REPO_ROOT / "schema"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "schema"


def load_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as schema_file:
        schema = json.load(schema_file)
    assert isinstance(schema, dict)
    return schema


def load_yaml(path: Path) -> object:
    with path.open(encoding="utf-8") as fixture_file:
        return yaml.safe_load(fixture_file)


@pytest.fixture(scope="module")
def validators() -> dict[str, Draft202012Validator]:
    schema_paths = {
        "object": SCHEMA_DIR / "object.schema.json",
        "cave": SCHEMA_DIR / "cave.schema.json",
        "relation": SCHEMA_DIR / "relation.schema.json",
    }
    loaded_schemas = {name: load_json(path) for name, path in schema_paths.items()}

    for schema in loaded_schemas.values():
        Draft202012Validator.check_schema(schema)

    return {
        name: Draft202012Validator(schema, format_checker=FormatChecker())
        for name, schema in loaded_schemas.items()
    }


def validation_errors(validator: Draft202012Validator, fixture_name: str) -> list[str]:
    errors = validator.iter_errors(load_yaml(FIXTURE_DIR / fixture_name))
    return sorted(format_error(error) for error in errors)


def format_error(error: object) -> str:
    path = ".".join(str(path_part) for path_part in error.path)
    if not path:
        path = "<root>"
    return f"{path}: {error.message}"


@pytest.mark.parametrize(
    ("schema_name", "fixture_name"),
    [
        ("object", "valid-object.yml"),
        ("cave", "valid-cave.yml"),
        ("relation", "valid-relation.yml"),
    ],
)
def test_valid_schema_fixtures_pass(
    validators: dict[str, Draft202012Validator],
    schema_name: str,
    fixture_name: str,
) -> None:
    errors = validation_errors(validators[schema_name], fixture_name)

    assert errors == []


@pytest.mark.parametrize(
    ("schema_name", "fixture_name", "expected_error_fragment"),
    [
        ("object", "invalid-object-missing-id.yml", "'id' is a required property"),
        ("cave", "invalid-cave-bad-object-id.yml", "object_ids.0"),
        ("relation", "invalid-relation-type.yml", "relation_type"),
        (
            "object",
            "invalid-object-manual-best-without-reason.yml",
            "best_measurement.reason",
        ),
    ],
)
def test_invalid_schema_fixtures_fail_on_expected_fields(
    validators: dict[str, Draft202012Validator],
    schema_name: str,
    fixture_name: str,
    expected_error_fragment: str,
) -> None:
    errors = validation_errors(validators[schema_name], fixture_name)

    assert errors
    assert any(expected_error_fragment in error for error in errors), errors
