from pathlib import Path
from shutil import copyfile

import pytest

from gps_kataster_obiektow_tatr.data_loader import (
    DataKind,
    YamlDataLoadError,
    load_dataset,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"
SCHEMA_FIXTURE_DIR = FIXTURE_DIR / "schema"


def test_load_dataset_reads_fixture_records_and_keeps_paths(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    object_path = data_dir / "objects" / "KSW" / "KSW-0001.yml"
    cave_path = data_dir / "caves" / "C-0001.yml"
    relation_path = data_dir / "relations" / "R-0001.yml"

    _copy_fixture(FIXTURE_DIR / "valid-object.yml", object_path)
    _copy_fixture(FIXTURE_DIR / "valid-cave.yml", cave_path)
    _copy_fixture(SCHEMA_FIXTURE_DIR / "valid-relation.yml", relation_path)

    dataset = load_dataset(data_dir)

    assert [record.kind for record in dataset.records()] == [
        DataKind.OBJECT,
        DataKind.CAVE,
        DataKind.RELATION,
    ]
    assert dataset.objects[0].path == object_path
    assert dataset.objects[0].data["id"] == "KSW-0001"
    assert dataset.caves[0].path == cave_path
    assert dataset.caves[0].data["id"] == "C-0001"
    assert dataset.relations[0].path == relation_path
    assert dataset.relations[0].data["id"] == "R-0001"


def test_missing_lists_are_normalized_in_memory_without_rewriting_yaml(
    tmp_path: Path, make_data_dir
) -> None:
    data_dir = make_data_dir(tmp_path / "data")
    object_path = data_dir / "objects" / "KSW" / "KSW-0001.yml"
    cave_path = data_dir / "caves" / "C-0001.yml"
    object_yaml = """\
schema_version: 1
id: KSW-0001
measurements:
  - id: m-001
"""
    cave_yaml = """\
schema_version: 1
id: C-0001
name: Jaskinia testowa
"""
    _write_yaml(object_path, object_yaml)
    _write_yaml(cave_path, cave_yaml)

    dataset = load_dataset(data_dir)
    loaded_object = dataset.objects[0]
    loaded_cave = dataset.caves[0]

    assert loaded_object.data["external_refs"] == []
    assert loaded_object.data["attachments"] == []
    assert loaded_object.data["measurements"][0]["tags"] == []
    assert "external_refs" not in loaded_object.raw_data
    assert "attachments" not in loaded_object.raw_data
    assert "tags" not in loaded_object.raw_data["measurements"][0]
    assert object_path.read_text(encoding="utf-8") == object_yaml

    assert loaded_cave.data["external_refs"] == []
    assert loaded_cave.data["object_ids"] == []
    assert "external_refs" not in loaded_cave.raw_data
    assert "object_ids" not in loaded_cave.raw_data
    assert cave_path.read_text(encoding="utf-8") == cave_yaml


def test_yaml_error_includes_source_path(tmp_path: Path, make_data_dir) -> None:
    data_dir = make_data_dir(tmp_path / "data")
    bad_path = data_dir / "objects" / "KSW" / "bad.yml"
    _write_yaml(bad_path, "id: [unterminated\n")

    with pytest.raises(YamlDataLoadError) as exc_info:
        load_dataset(data_dir)

    message = str(exc_info.value)
    assert str(bad_path) in message
    assert "invalid YAML" in message


def test_rejects_yaml_key_collisions_before_normalization(
    tmp_path: Path, make_data_dir, yaml_key_collision
) -> None:
    content, key, line = yaml_key_collision
    data_dir = make_data_dir(tmp_path / "data")
    path = data_dir / "objects" / "bad.yml"
    path.write_text(content, encoding="utf-8")
    before = path.read_bytes()

    with pytest.raises(YamlDataLoadError) as error:
        load_dataset(data_dir)

    assert error.value.path == path
    message = str(error.value)
    assert str(path) in message
    assert "duplicate key" in message
    assert key in message
    assert f"line {line}, column" in message
    assert path.read_bytes() == before


@pytest.mark.parametrize("directory", ["objects", "caves", "relations"])
def test_rejects_duplicate_keys_in_every_record_kind(tmp_path, make_data_dir, directory):
    data_dir = make_data_dir(tmp_path / "data")
    path = data_dir / directory / "bad.yml"
    path.write_text("id: first\nid: second\n", encoding="utf-8")
    with pytest.raises(YamlDataLoadError, match="duplicate key.*id"):
        load_dataset(data_dir)


def test_aliases_and_disjoint_merges_preserve_values_and_list_order(tmp_path, make_data_dir):
    data_dir = make_data_dir(tmp_path / "data")
    path = data_dir / "objects" / "good.yml"
    content = """\
id: KSW-0001
measurements:
  - &measurement
    <<: [{source: TPN}, {notes: Zażółć}]
    id: m-002
    tags: [second, first]
  - *measurement
  - <<: {id: m-001}
    source: PIG
"""
    path.write_text(content, encoding="utf-8")
    record = load_dataset(data_dir).objects[0]
    assert record.raw_data == {
        "id": "KSW-0001",
        "measurements": [
            {"id": "m-002", "source": "TPN", "notes": "Zażółć", "tags": ["second", "first"]},
            {"id": "m-002", "source": "TPN", "notes": "Zażółć", "tags": ["second", "first"]},
            {"id": "m-001", "source": "PIG"},
        ],
    }
    assert record.data["measurements"][2]["tags"] == []
    assert "tags" not in record.raw_data["measurements"][2]
    assert path.read_bytes() == content.encode("utf-8")


@pytest.mark.parametrize("content", ["? [not, a, scalar]\n: value\n", "!!python/tuple [1, 2]\n"])
def test_strict_loader_keeps_safe_yaml_errors(tmp_path, make_data_dir, content):
    data_dir = make_data_dir(tmp_path / "data")
    path = data_dir / "objects" / "bad.yml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(YamlDataLoadError, match="invalid YAML") as error:
        load_dataset(data_dir)
    assert error.value.path == path


def _copy_fixture(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    copyfile(source, destination)


def _write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
