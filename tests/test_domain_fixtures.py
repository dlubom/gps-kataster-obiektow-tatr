import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = REPO_ROOT / "schema"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"

OBJECT_FIXTURES = (
    "valid-object.yml",
    "object-with-tpn-globalid.yml",
    "object-with-manual-best.yml",
)
CAVE_FIXTURES = (
    "valid-cave.yml",
    "cave-with-pig-and-nr-inwent.yml",
)


def load_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as schema_file:
        schema = json.load(schema_file)
    assert isinstance(schema, dict)
    return schema


def load_fixture(fixture_name: str) -> dict[str, Any]:
    with (FIXTURE_DIR / fixture_name).open(encoding="utf-8") as fixture_file:
        data = yaml.safe_load(fixture_file)
    assert isinstance(data, dict)
    return data


@pytest.fixture(scope="module")
def validators() -> dict[str, Draft202012Validator]:
    loaded_schemas = {
        "object": load_json(SCHEMA_DIR / "object.schema.json"),
        "cave": load_json(SCHEMA_DIR / "cave.schema.json"),
    }

    for schema in loaded_schemas.values():
        Draft202012Validator.check_schema(schema)

    return {
        name: Draft202012Validator(schema, format_checker=FormatChecker())
        for name, schema in loaded_schemas.items()
    }


def format_error(error: object) -> str:
    path = ".".join(str(path_part) for path_part in error.path)
    if not path:
        path = "<root>"
    return f"{path}: {error.message}"


@pytest.mark.parametrize(
    ("schema_name", "fixture_name"),
    [
        *[("object", fixture_name) for fixture_name in OBJECT_FIXTURES],
        *[("cave", fixture_name) for fixture_name in CAVE_FIXTURES],
    ],
)
def test_domain_fixtures_pass_schema(
    validators: dict[str, Draft202012Validator],
    schema_name: str,
    fixture_name: str,
) -> None:
    errors = validators[schema_name].iter_errors(load_fixture(fixture_name))

    assert sorted(format_error(error) for error in errors) == []


def test_domain_fixture_cave_object_cross_references_are_consistent() -> None:
    objects = {fixture["id"]: fixture for fixture in map(load_fixture, OBJECT_FIXTURES)}
    caves = {fixture["id"]: fixture for fixture in map(load_fixture, CAVE_FIXTURES)}

    assert len(objects) == len(OBJECT_FIXTURES)
    assert len(caves) == len(CAVE_FIXTURES)

    for object_id, object_fixture in objects.items():
        cave_id = object_fixture.get("cave_id")
        if cave_id is None:
            continue

        assert cave_id in caves
        assert object_id in caves[cave_id]["object_ids"]

    for cave_id, cave_fixture in caves.items():
        for object_id in cave_fixture["object_ids"]:
            assert object_id in objects
            assert objects[object_id].get("cave_id") == cave_id


def test_domain_fixture_internal_object_references_are_consistent() -> None:
    for object_fixture in map(load_fixture, OBJECT_FIXTURES):
        measurement_ids = {measurement["id"] for measurement in object_fixture["measurements"]}

        assert object_fixture["id_assignment"]["assigned_from_measurement_id"] in measurement_ids
        assert object_fixture["best_measurement"]["measurement_id"] in measurement_ids


def test_tpn_globalid_fixture_keeps_globalid_on_object() -> None:
    object_fixture = load_fixture("object-with-tpn-globalid.yml")

    assert {
        "system": "TPN",
        "ref_type": "source_globalid",
        "scope": "object",
    } in [
        {
            "system": external_ref["system"],
            "ref_type": external_ref["ref_type"],
            "scope": external_ref.get("scope"),
        }
        for external_ref in object_fixture["external_refs"]
    ]


def test_pig_and_inventory_fixture_keeps_catalog_refs_on_cave() -> None:
    cave_fixture = load_fixture("cave-with-pig-and-nr-inwent.yml")
    external_refs = cave_fixture["external_refs"]

    assert any(
        external_ref["system"] == "PIG" and external_ref["ref_type"] == "catalog_id"
        for external_ref in external_refs
    )
    assert any(
        external_ref["system"] == "NR_INWENT" and external_ref["ref_type"] == "inventory_number"
        for external_ref in external_refs
    )
    assert all(external_ref.get("scope") == "cave" for external_ref in external_refs)
