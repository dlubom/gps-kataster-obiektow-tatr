"""The same lossless, safe YAML policy applies to records and decisions."""

from datetime import UTC, date, datetime

import pytest
import yaml

from gps_kataster_obiektow_tatr.data_loader import YamlDataLoadError, load_dataset
from gps_kataster_obiektow_tatr.staging_review import ReviewDecisionError, load_review_decisions


@pytest.fixture(params=["object", "cave", "relation", "decisions"])
def yaml_input(request, tmp_path):
    kind = request.param
    if kind == "decisions":
        return tmp_path / "decisions.yml", load_review_decisions, ReviewDecisionError
    directory = {"object": "objects/KSW", "cave": "caves", "relation": "relations"}[kind]
    path = tmp_path / directory / "record.yaml"
    path.parent.mkdir(parents=True)

    def read_record(_path):
        return load_dataset(tmp_path).records()[0].raw_data

    return path, read_record, YamlDataLoadError


@pytest.mark.parametrize(
    ("content", "key", "first_line", "second_line"),
    [
        ("measurements: [{id: m-001}]\nmeasurements: []\n", "measurements", 1, 2),
        ("measurements:\n  - id: m-001\n    id: m-002\n", "id", 2, 3),
        ("decisions:\n  - action: reject\n    action: create_object\n", "action", 2, 3),
        ("id: same\nid: same\n", "id", 1, 2),
        ('id: first\n"id": second\n', "id", 1, 2),
        ("entry: {id: first, id: second}\n", "id", 1, 1),
        ("1: first\ntrue: second\n", True, 1, 2),
    ],
)
def test_duplicate_keys_report_both_locations(yaml_input, content, key, first_line, second_line):
    path, read, error = yaml_input
    path.write_text(content, encoding="utf-8")

    with pytest.raises(error) as exc_info:
        read(path)

    message = str(exc_info.value)
    assert str(path) in message
    assert f"duplicate key {key!r}" in message
    assert f"line {first_line}," in message
    assert f"line {second_line}," in message
    assert path.read_text(encoding="utf-8") == content


@pytest.mark.parametrize(
    ("content", "message", "line"),
    [
        ("first: &value text\nsecond: *value\n", "YAML aliases are not supported", 2),
        ("first: &value {id: first}\nsecond: *value\n", "YAML aliases are not supported", 2),
        ("first: &value [*value]\n", "YAML aliases are not supported", 1),
        ("entry:\n  <<: {id: merged}\n  id: explicit\n", "YAML merge keys are not supported", 2),
        ("entry:\n  <<: [{id: first}, {id: second}]\n", "YAML merge keys are not supported", 2),
    ],
)
def test_aliases_and_merge_keys_are_explicit_errors(yaml_input, content, message, line):
    path, read, error = yaml_input
    path.write_text(content, encoding="utf-8")
    with pytest.raises(error) as exc_info:
        read(path)
    assert str(path) in str(exc_info.value)
    assert message in str(exc_info.value)
    assert f"line {line}," in str(exc_info.value)


def test_safe_types_dates_and_independent_mapping_keys_are_preserved(yaml_input):
    path, read, _ = yaml_input
    content = """\
observed_date: 2026-09-06
reviewed_at: 2026-09-06T12:00:00Z
quoted_date: "2026-09-06"
empty: null
flag: true
number: 1.25
text: &unused "Zażółć"
'<<': literal
items: [{id: first}, {id: second}]
"""
    path.write_text(content, encoding="utf-8")
    loaded = read(path)
    assert loaded == {
        "observed_date": date(2026, 9, 6),
        "reviewed_at": datetime(2026, 9, 6, 12, tzinfo=UTC),
        "quoted_date": "2026-09-06",
        "empty": None,
        "flag": True,
        "number": 1.25,
        "text": "Zażółć",
        "<<": "literal",
        "items": [{"id": "first"}, {"id": "second"}],
    }
    # The project subclass must not change PyYAML's global constructor table.
    assert yaml.safe_load("id: first\nid: second\n") == {"id": "second"}


@pytest.mark.parametrize(
    "content",
    [
        "value: !!str {=: kept, id: first, id: second}\n",
        "value: !!str {=: kept, <<: {id: merged}}\n",
        "value: !!int {=: 1, id: first, id: second}\n",
        "? !!str {=: id, ignored: value}\n: hidden\n",
    ],
)
def test_scalar_tag_cannot_hide_mapping_keys(yaml_input, content):
    path, read, error = yaml_input
    path.write_text(content, encoding="utf-8")
    with pytest.raises(error) as exc_info:
        read(path)
    message = str(exc_info.value)
    assert "scalar-tagged mappings are not supported" in message
    assert str(path) in message
    assert "line 1," in message


@pytest.mark.parametrize(
    "content", ["value: !!python/name:os.system ''\n", "? [a, b]\n: c\n", "!!map []\n"]
)
def test_unsafe_tags_and_unhashable_keys_remain_yaml_errors(yaml_input, content):
    path, read, error = yaml_input
    path.write_text(content, encoding="utf-8")
    with pytest.raises(error, match="invalid YAML"):
        read(path)
