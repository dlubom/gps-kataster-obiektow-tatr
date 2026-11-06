"""The YAML and proposal adapters reject coercion before PostgreSQL sees values."""

import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from gps_kataster_obiektow_tatr.catalog_records import record_rows
from gps_kataster_obiektow_tatr.data_loader import load_yaml_dataset
from gps_kataster_obiektow_tatr.postgres import CatalogLoadError, _catalog_rows, _read_snapshots


@pytest.fixture
def source(tmp_path, make_data_dir):
    make_data_dir(tmp_path)
    fixtures = Path(__file__).parent / "fixtures"
    obj = yaml.safe_load((fixtures / "valid-object.yml").read_text())
    cave = yaml.safe_load((fixtures / "valid-cave.yml").read_text())
    cave["object_ids"] = [obj["id"]]
    return tmp_path, obj, cave


def save(source):
    root, obj, cave = source
    for folder, data in (("objects", obj), ("caves", cave)):
        (root / folder / f"{data['id']}.yml").write_text(yaml.safe_dump(data))
    return root


@pytest.mark.parametrize("entry", ["yaml", "proposal"])
@pytest.mark.parametrize(
    "location,field,value",
    [
        ("object", "schema_version", 1.4),
        ("object", "schema_version", True),
        ("object", "schema_version", "1"),
        ("object", "name_local", 123),
        ("measurement", "source_ref", 123),
        ("measurement", "horizontal_accuracy_m", "5.2"),
        ("measurement", "vertical_accuracy_m", False),
        ("measurement", "elevation_m", "1240"),
        ("assignment", "assigned_prefix", 123),
        ("best", "measurement_id", 123),
    ],
)
def test_scalar_types_cannot_be_coerced(source, entry, location, field, value):
    root, obj, _ = source
    target = {
        "object": obj,
        "measurement": obj["measurements"][0],
        "assignment": obj["id_assignment"],
        "best": obj["best_measurement"],
    }[location]
    target[field] = value
    save(source)
    with pytest.raises(CatalogLoadError, match=field) as caught:
        if entry == "yaml":
            _read_snapshots(root)
        else:
            _catalog_rows(load_yaml_dataset(root))
    assert caught.value.path == root / "objects/KSW-0001.yml"


@pytest.mark.parametrize(
    "field,value",
    [
        ("measurements", [None]),
        ("measurements", ["m-001"]),
        ("measurements", [{1: "unexpected"}]),
        ("external_refs", [False]),
        ("citations", [None]),
        ("attachments", [12]),
        ("id_assignment", []),
        ("best_measurement", [["mode", "auto"]]),
    ],
)
def test_malformed_children_have_controlled_file_diagnostics(source, field, value):
    root, obj, _ = source
    obj[field] = value
    save(source)
    with pytest.raises(CatalogLoadError, match=field) as caught:
        _read_snapshots(root)
    assert caught.value.path == root / "objects/KSW-0001.yml"


@pytest.mark.parametrize("owner", ["object", "cave", "publication"])
@pytest.mark.parametrize(
    "url",
    [
        "not a URL",
        "https://",
        "https://exa mple.com",
        "https://[bad",
        "https://example.com:wrong",
        "https://example.com/\npath",
        "https://example.com\\bad",
        "https://example.com/<page>",
        "https://user@@example.com",
    ],
)
def test_reference_and_publication_urls_are_validated(source, owner, url):
    _, obj, cave = source
    if owner == "publication":
        data = {"id": "example", "citation": "A source", "url": url}
    else:
        data = obj if owner == "object" else cave
        data["external_refs"] = [
            {"system": "inne", "ref_type": "url", "external_id": "source", "url": url}
        ]
    with pytest.raises(ValueError, match="url"):
        record_rows(owner, data)


@pytest.mark.parametrize(
    "url",
    [
        None,
        "https://example.com/path?a=1#part",
        "http://example.com",
        "ftp://example.com/file",
        "urn:isbn:9780000000000",
        "https://example.com/%3Cpage%3E?name=za%C5%BC%C3%B3%C5%82%C4%87",
    ],
)
def test_optional_and_absolute_reference_urls_are_preserved(url):
    data = {"id": "example", "citation": "A source", "url": url}
    assert record_rows("publication", data)[0][1]["url"] == url


def test_valid_numeric_values_and_null_presence_are_preserved(source):
    _, obj, _ = source
    m = obj["measurements"][0]
    m.update(elevation_m=1240, horizontal_accuracy_m=None)
    m.pop("vertical_accuracy_m")
    before = deepcopy(obj)
    row = next(values for table, values in record_rows("object", obj) if table == "measurements")
    assert row["elevation_m"] == 1240
    assert row["horizontal_accuracy_m"] is None
    assert "vertical_accuracy_m" not in row
    assert obj == before


@pytest.fixture(params=["objects", "caves", "relations", "publications"])
def incomplete_canonical_source(request, tmp_path, make_canonical_data_dir):
    root = make_canonical_data_dir(tmp_path / "data")
    path = root / request.param
    path.rmdir()
    return root, path


@pytest.mark.parametrize("damage", ["missing", "file"])
def test_incomplete_canonical_source_fails_before_database(
    incomplete_canonical_source, damage, monkeypatch
):
    from gps_kataster_obiektow_tatr import postgres
    from gps_kataster_obiektow_tatr.data_loader import DataDirectoryError
    from gps_kataster_obiektow_tatr.validator import validate_data_dir

    root, path = incomplete_canonical_source
    if damage == "file":
        path.write_bytes(b"this is a file, not a directory")

    def unexpected(*args, **kwargs):
        pytest.fail("Incomplete canonical input reached PostgreSQL")

    monkeypatch.setattr(postgres, "_open_rows", unexpected)
    for read in (load_yaml_dataset, postgres.read_catalog_projection):
        with pytest.raises(DataDirectoryError) as raised:
            read(root)
        assert raised.value.path == path
    issues = validate_data_dir(root)
    assert [(i.code, i.severity, i.path) for i in issues] == [
        ("DATA_DIRECTORY_INVALID", "error", path)
    ]
    assert not path.exists() if damage == "missing" else path.read_bytes().startswith(b"this")


@pytest.mark.parametrize("damage", ["missing", "file"])
def test_incomplete_canonical_source_cli_reports_directory_path(
    incomplete_canonical_source, damage
):
    root, path = incomplete_canonical_source
    if damage == "file":
        path.write_bytes(b"not a directory")
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "scripts/validate.py"),
            "--data-dir",
            str(root),
        ],
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "KATASTER_DATABASE_URL": "postgresql://postgres@127.0.0.1:1/postgres?connect_timeout=1",
        },
    )
    assert result.returncode == 1
    assert result.stdout.startswith(f"DATA_DIRECTORY_INVALID\terror\t{path}\t")
    assert "Traceback" not in result.stdout + result.stderr


def test_complete_empty_canonical_source_and_publications_are_readable(
    tmp_path, make_canonical_data_dir
):
    from gps_kataster_obiektow_tatr.postgres import read_catalog_projection
    from gps_kataster_obiektow_tatr.validator import validate_data_dir

    root = make_canonical_data_dir(tmp_path / "data")
    assert load_yaml_dataset(root).records() == ()
    assert read_catalog_projection(root).records() == ()
    assert validate_data_dir(root) == ()
    (root / "publications/source.yml").write_text(
        'id: source\ncitation: "Katalog Tatr, 1994"\nurl: null\n', encoding="utf-8"
    )
    (record,) = read_catalog_projection(root).publications
    assert record.data["id"] == "source"
    assert record.data["citation"] == "Katalog Tatr, 1994"
    assert record.data["url"] is None


def test_legacy_accepts_absent_bibliography_but_rejects_a_file(tmp_path, make_data_dir):
    from gps_kataster_obiektow_tatr.data_loader import DataDirectoryError, iter_yaml_paths

    root = make_data_dir(tmp_path / "data")
    path = root / "publications"
    assert load_yaml_dataset(root).publications == ()
    assert iter_yaml_paths(path) == ()
    path.write_bytes(b"not a bibliography directory")
    # Optional-source traversal stays permissive; the dataset boundary owns the layout.
    assert iter_yaml_paths(path) == ()
    with pytest.raises(DataDirectoryError) as raised:
        load_yaml_dataset(root)
    assert raised.value.path == path
