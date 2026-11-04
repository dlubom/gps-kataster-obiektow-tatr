import json
import math
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError

from gps_kataster_obiektow_tatr.models import RECORD_MODELS

AUDIT = {
    "created_at": "2024-02-29T01:02:03.012300+01:30",
    "created_by": "operator",
    "updated_at": "2024-02-29T01:02:03Z",
    "updated_by": "operator",
}


@pytest.fixture(scope="module")
def schemas():
    schema_dir = Path(__file__).resolve().parents[1] / "schema"
    return {
        kind: Draft202012Validator(
            json.loads((schema_dir / f"{kind}.schema.json").read_text(encoding="utf-8")),
            format_checker=FormatChecker(),
        )
        for kind in RECORD_MODELS
    }


@pytest.fixture
def object_data():
    return {
        **AUDIT,
        "schema_version": 1.0,
        "id": "ABC-0001",
        "category": "jaskinia_otwor",
        "id_assignment": {
            "method": "auto",
            "assigned_from_measurement_id": "m-001",
            "assigned_prefix": "ABC",
        },
        "external_refs": [
            {"system": "PIG", "ref_type": "url", "external_id": "1", "url": "HTTPS://EXAMPLE.COM"},
            {
                "system": "PIG",
                "ref_type": "url",
                "external_id": "1",
                "url": "HTTPS://EXAMPLE.COM",
                "notes": None,
            },
        ],
        "measurements": [
            {
                "created_at": AUDIT["created_at"],
                "created_by": AUDIT["created_by"],
                "id": "m-001",
                "lat": 49,
                "lon": 19.2,
                "x_1992": 10,
                "y_1992": 20.5,
                "source": "wlasne",
                "observed_date": "2024-02-29",
                "method": "siec_pomiarowa",
                "verification_status": "nieweryfikowany",
                "tags": ["b", "a"],
                "horizontal_accuracy_m": None,
            }
        ],
        "best_measurement": {
            "mode": "auto",
            "measurement_id": "m-001",
            "reason": None,
            "updated_at": AUDIT["updated_at"],
            "updated_by": AUDIT["updated_by"],
        },
        "attachments": [
            {
                "id": "a-001",
                "kind": "zdjecie",
                "path": "photos/photo.jpg",
                "date": "2024-02-29",
                "created_at": AUDIT["created_at"],
                "created_by": AUDIT["created_by"],
            }
        ],
    }


def test_object_preserves_supplied_values_and_optional_presence(object_data, schemas):
    schemas["object"].validate(object_data)
    before = deepcopy(object_data)
    record = RECORD_MODELS["object"].model_validate(object_data)
    actual = record.model_dump(exclude_unset=True)
    assert actual == before == object_data
    assert type(actual["schema_version"]) is float
    assert type(actual["measurements"][0]["lat"]) is int


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("schema_version",), True),
        (("schema_version",), "1"),
        (("schema_version",), 2),
        (("measurements", 0, "lat"), True),
        (("measurements", 0, "lat"), "49"),
        (("measurements", 0, "lat"), 91),
        (("measurements", 0, "x_1992"), 10**500),
        (("measurements", 0, "x_1992"), float("nan")),
        (("measurements", 0, "elevation_m"), float("inf")),
        (("measurements", 0, "vertical_accuracy_m"), float("-inf")),
        (("measurements", 0, "horizontal_accuracy_m"), -1),
        (("measurements", 0, "observed_date"), "2023-02-29"),
        (("measurements", 0, "observed_date"), "20240229"),
        (("measurements", 0, "observed_date"), "2024-02-29T00:00:00Z"),
        (("measurements", 0, "observed_at"), "2024-02-29T00:00:00"),
        (("measurements", 0, "observed_at"), "2024-02-29T00:00:00+01:60"),
        (("measurements", 0, "observed_at"), "2024-02-29T00:00:00Z\n"),
        (("measurements", 0, "tags"), None),
        (("measurements", 0, "tags"), ["a", "a"]),
        (("external_refs", 0, "url"), "relative/path"),
        (("external_refs", 0, "url"), "https://example.com/%gg"),
        (("external_refs", 0, "url"), "https://example.com\n"),
        (("attachments", 0, "date"), "2024-02-30"),
    ],
)
def test_object_rejects_invalid_structure(object_data, schemas, path, value):
    target = object_data
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    with pytest.raises(ValidationError) as exc_info:
        RECORD_MODELS["object"].model_validate(object_data)
    assert any(error["loc"] == path for error in exc_info.value.errors())
    # JSON itself has no NaN or infinity tokens.
    if not isinstance(value, float) or math.isfinite(value):
        assert not schemas["object"].is_valid(object_data)


@pytest.mark.parametrize(
    ("field", "discriminator", "reason"),
    [
        ("best_measurement", "mode", "reason"),
        ("id_assignment", "method", "prefix_override_reason"),
    ],
)
def test_manual_variants_require_nonempty_reasons(object_data, field, discriminator, reason):
    variant = object_data[field]
    variant[discriminator] = "manual"
    variant.pop(reason, None)
    with pytest.raises(ValidationError, match=reason):
        RECORD_MODELS["object"].model_validate(object_data)
    for invalid in (None, ""):
        variant[reason] = invalid
        with pytest.raises(ValidationError, match=reason):
            RECORD_MODELS["object"].model_validate(object_data)
    variant[reason] = "decyzja"
    RECORD_MODELS["object"].model_validate(object_data)


@pytest.mark.parametrize("field", ["external_refs", "attachments"])
def test_duplicate_objects_in_unique_lists_are_rejected(object_data, field):
    items = object_data[field]
    items.append(dict(reversed(list(items[0].items()))))
    with pytest.raises(ValidationError, match="unique"):
        RECORD_MODELS["object"].model_validate(object_data)


@pytest.fixture
def cave_data():
    return {
        **AUDIT,
        "schema_version": 1,
        "id": "C-0001",
        "name": "Jaskinia",
        "external_refs": [],
        "object_ids": ["ABC-0001", "AB-0002"],
    }


@pytest.fixture
def relation_data():
    return {
        "schema_version": 1,
        "id": "R-0001",
        "from_object_id": "AB-0002",
        "to_object_id": "ABC-0001",
        "relation_type": "sasiad",
        "notes": None,
    }


def test_cave_and_relation_share_id_and_version_constraints(cave_data, relation_data):
    for kind, record in [("cave", cave_data), ("relation", relation_data)]:
        model = RECORD_MODELS[kind]
        assert model.model_validate(record).model_dump(exclude_unset=True) == record
        for invalid_id in ("a-001", "AA-0001"):
            with pytest.raises(ValidationError, match="id"):
                model.model_validate(dict(record, id=invalid_id))
    with pytest.raises(ValidationError, match="unique"):
        RECORD_MODELS["cave"].model_validate(dict(cave_data, object_ids=["AB-0002", "AB-0002"]))


# Separate traversal paths through source mappings from Pydantic error locations,
# which include the selected branch of each discriminated union.
RECORD_PATHS = [
    ("object", (), (), "category"),
    ("cave", (), (), "name"),
    ("relation", (), (), "relation_type"),
    ("object", ("id_assignment",), ("id_assignment", "auto"), "assigned_prefix"),
    ("object", ("best_measurement",), ("best_measurement", "auto"), "measurement_id"),
    ("object", ("external_refs", 0), ("external_refs", 0), "external_id"),
    ("object", ("attachments", 0), ("attachments", 0), "path"),
    ("object", ("measurements", 0), ("measurements", 0), "lat"),
]


@pytest.mark.parametrize(("kind", "path", "location", "required"), RECORD_PATHS)
@pytest.mark.parametrize("mutation", ["unknown_field", "omit_required", "null_required"])
def test_models_reject_unknown_fields_and_missing_or_null_required_fields(
    kind, path, location, required, mutation, request, schemas
):
    data = request.getfixturevalue(f"{kind}_data")
    target = data
    for part in path:
        target = target[part]
    if mutation == "unknown_field":
        field, error_type = "unknown_field", "extra_forbidden"
        target[field] = "extra"
    elif mutation == "omit_required":
        field, error_type = required, "missing"
        del target[field]
    else:
        field, error_type = required, None
        target[field] = None

    with pytest.raises(ValidationError) as exc_info:
        RECORD_MODELS[kind].model_validate(data)
    assert any(
        error["loc"] == (*location, field) and (error_type is None or error["type"] == error_type)
        for error in exc_info.value.errors()
    )
    assert not schemas[kind].is_valid(data)
