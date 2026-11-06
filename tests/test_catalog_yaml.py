from gps_kataster_obiektow_tatr.data_loader import load_yaml_dataset


def test_yaml_loader_preserves_publication_fields(tmp_path, make_canonical_data_dir):
    make_canonical_data_dir(tmp_path)
    publications = tmp_path / "publications"
    (publications / "example.yml").write_text(
        'id: example\ncitation: "Katalog Tatr, 1994"\nurl: null\n', encoding="utf-8"
    )

    (record,) = load_yaml_dataset(tmp_path).publications

    assert record.data == {"id": "example", "citation": "Katalog Tatr, 1994", "url": None}
    assert "doi" not in record.data


def test_row_mapping_rejects_scalar_tags():
    from pathlib import Path

    import pytest
    import yaml

    from gps_kataster_obiektow_tatr.catalog_records import record_rows

    record = yaml.safe_load((Path(__file__).parent / "fixtures/valid-object.yml").read_text())
    record["measurements"][0]["tags"] = "GNSS"
    with pytest.raises(ValueError, match="tags must be a list"):
        record_rows("object", record)


def test_yaml_catalog_rejects_repeated_cave_member(tmp_path, make_data_dir):
    from pathlib import Path

    import pytest
    import yaml

    from gps_kataster_obiektow_tatr.postgres import CatalogLoadError, _read_snapshots

    make_data_dir(tmp_path)
    fixtures = Path(__file__).parent / "fixtures"
    obj = yaml.safe_load((fixtures / "valid-object.yml").read_text())
    cave = yaml.safe_load((fixtures / "valid-cave.yml").read_text())
    cave["object_ids"] = [obj["id"], obj["id"]]
    (tmp_path / "objects" / f"{obj['id']}.yml").write_text(yaml.safe_dump(obj))
    (tmp_path / "caves" / f"{cave['id']}.yml").write_text(yaml.safe_dump(cave))

    with pytest.raises(CatalogLoadError, match="DUPLICATE_CAVE_OBJECT_ID"):
        _read_snapshots(tmp_path)


def test_yaml_writer_preserves_existing_key_order_when_editing_notes(tmp_path, make_data_dir):
    from dataclasses import replace
    from pathlib import Path

    import yaml

    from gps_kataster_obiektow_tatr.catalog_records import write_dataset

    make_data_dir(tmp_path)
    fixtures = Path(__file__).parent / "fixtures"
    for kind, name in (("objects", "valid-object.yml"), ("caves", "valid-cave.yml")):
        record = yaml.safe_load((fixtures / name).read_text())
        directory = tmp_path / kind
        if kind == "objects":
            directory /= record["id"].split("-")[0]
            directory.mkdir()
        (directory / f"{record['id']}.yml").write_text(
            yaml.safe_dump(record, allow_unicode=True, sort_keys=False)
        )
    dataset = load_yaml_dataset(tmp_path)
    original = dataset.objects[0].data
    changed = dict(reversed(list(original.items())))
    changed["notes"] = "Edited note"
    changed["measurements"] = [dict(reversed(list(m.items()))) for m in original["measurements"]]
    dataset = replace(dataset, objects=(replace(dataset.objects[0], data=changed),))

    write_dataset(dataset, tmp_path)

    actual = yaml.safe_load(dataset.objects[0].path.read_text())
    assert [key for key in actual if key in original] == list(original)
    assert list(actual["measurements"][0]) == [
        key for key in original["measurements"][0] if key not in {"x_1992", "y_1992"}
    ]
    assert actual["notes"] == "Edited note"
