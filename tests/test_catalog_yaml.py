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


def test_yaml_catalog_rejects_repeated_computed_cave_member(tmp_path, make_canonical_data_dir):
    from pathlib import Path

    import pytest
    import yaml

    from gps_kataster_obiektow_tatr.postgres import CatalogLoadError, _read_snapshots

    make_canonical_data_dir(tmp_path)
    fixtures = Path(__file__).parent / "fixtures"
    obj = yaml.safe_load((fixtures / "canonical-object.yml").read_text())
    cave = yaml.safe_load((fixtures / "canonical-cave.yml").read_text())
    cave["object_ids"] = [obj["id"], obj["id"]]
    (tmp_path / "objects" / f"{obj['id']}.yml").write_text(yaml.safe_dump(obj))
    (tmp_path / "caves" / f"{cave['id']}.yml").write_text(yaml.safe_dump(cave))

    with pytest.raises(CatalogLoadError, match="computed membership"):
        _read_snapshots(tmp_path)
