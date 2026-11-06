"""Canonical YAML stores source facts; read models may contain derived projections."""

import json
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest
import yaml

from gps_kataster_obiektow_tatr.catalog_records import write_dataset
from gps_kataster_obiektow_tatr.data_loader import (
    CATALOG_FORMAT,
    DataKind,
    LoadedYamlRecord,
    load_yaml_dataset,
)
from gps_kataster_obiektow_tatr.postgres import (
    CatalogLoadError,
    _catalog_rows,
    _read_snapshots,
    open_catalog,
)


@pytest.fixture
def canonical(tmp_path, make_data_dir):
    make_data_dir(tmp_path)
    (tmp_path / "publications").mkdir()
    (tmp_path / "catalog.json").write_text(json.dumps(CATALOG_FORMAT))
    fixtures = Path(__file__).parent / "fixtures"
    obj = yaml.safe_load((fixtures / "valid-object.yml").read_text())
    obj["membership_ordinal"] = 7
    m = obj["measurements"][0]
    m.pop("x_1992")
    m.pop("y_1992")
    obj["best_measurement"].pop("measurement_id")
    cave = yaml.safe_load((fixtures / "valid-cave.yml").read_text())
    cave.pop("object_ids")
    directory = tmp_path / "objects/KSW"
    directory.mkdir()
    (directory / f"{obj['id']}.yml").write_text(yaml.safe_dump(obj, sort_keys=False))
    (tmp_path / "caves/C-0001.yml").write_text(yaml.safe_dump(cave, sort_keys=False))
    return tmp_path


def test_canonical_membership_has_one_authority(canonical):
    rows, _ = _read_snapshots(canonical)
    obj = next(values for _, table, values in rows if table == "objects")
    assert obj["cave_id"] == "C-0001"
    assert obj["membership_ordinal"] == 7


def test_read_projection_cannot_override_explicit_membership_order(canonical):
    dataset = load_yaml_dataset(canonical)
    dataset.caves[0].data["object_ids"] = ["KSW-0001"]
    rows, _ = _catalog_rows(dataset)
    obj = next(values for _, table, values in rows if table == "objects")
    assert obj["membership_ordinal"] == 7


@pytest.mark.parametrize("field", ["object_ids", "derived_coordinates", "auto_measurement_id"])
def test_canonical_input_rejects_computed_source_fields(canonical, field):
    path = canonical / ("caves/C-0001.yml" if field == "object_ids" else "objects/KSW/KSW-0001.yml")
    data = yaml.safe_load(path.read_text())
    if field == "object_ids":
        data[field] = ["KSW-0001"]
    elif field == "derived_coordinates":
        data["measurements"][0]["x_1992"] = 1.0
    else:
        data["best_measurement"]["measurement_id"] = "m-001"
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(CatalogLoadError, match="derived|computed") as caught:
        _read_snapshots(canonical)
    assert caught.value.path == path


@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("mode", ["auto", "manual"])
@pytest.mark.parametrize("suffix", [".yml", ".yaml"])
def test_note_edit_keeps_source_geometry_and_policy_only(canonical, native, mode, suffix):
    original_path = canonical / "objects/KSW/KSW-0001.yml"
    path = original_path.with_suffix(suffix)
    original_path.rename(path)
    original = yaml.safe_load(path.read_text())
    m = original["measurements"][0]
    if native:
        m.pop("lat")
        m.pop("lon")
        m.update(input_srid=2180, input_x=562729.5, input_y=152838.5)
    if mode == "manual":
        original["best_measurement"].update(mode="manual", measurement_id="m-001", reason="Chosen")
    path.write_text(yaml.safe_dump(original, sort_keys=False))
    with open_catalog(canonical) as catalog:
        dataset = catalog.dataset()
        before = deepcopy(dataset.objects[0].data)
        dataset.objects[0].data["notes"] = "Edited note"
        write_dataset(dataset, canonical)
    saved = yaml.safe_load(path.read_text())
    assert saved["measurements"] == original["measurements"]
    assert saved["best_measurement"] == original["best_measurement"]
    assert "computed_best_measurement_id" not in saved
    assert "object_ids" not in yaml.safe_load((canonical / "caves/C-0001.yml").read_text())
    with open_catalog(canonical) as catalog:
        after = catalog.dataset().objects[0].data
    assert after == {**before, "notes": "Edited note"}


@pytest.mark.parametrize("directory", ["objects/KSW", "caves", "relations", "publications"])
def test_snapshot_preserves_assets_inside_entity_directories(canonical, directory):
    from gps_kataster_obiektow_tatr.validator import _validate_attachments

    asset = canonical / directory / "evidence.yaml" / "field-photo.jpg"
    asset.parent.mkdir()
    asset.write_bytes(b"Original field photo\x00\xff")
    dataset = load_yaml_dataset(canonical)
    attachment = {"object_id": "KSW-0001", "id": "a-001", "path": str(asset)}
    dataset.objects[0].data["attachments"] = [
        {k: v for k, v in attachment.items() if k != "object_id"}
        | {"kind": "zdjecie", "created_at": "2026-11-05T00:00:00Z", "created_by": "test"}
    ]
    arguments = {"paths": {}, "repo_root": canonical}
    assert not _validate_attachments([attachment], **arguments)

    write_dataset(dataset, canonical, changed={("object", "KSW-0001")})

    assert asset.read_bytes() == b"Original field photo\x00\xff"
    assert not _validate_attachments([attachment], **arguments)


def test_snapshot_keeps_unchanged_yaml_paths_and_bytes(canonical):
    cave = canonical / "caves/C-0001.yaml"
    (canonical / "caves/C-0001.yml").rename(cave)
    cave.write_text("# Authored cave record\n" + cave.read_text())
    before = cave.read_bytes()
    dataset = load_yaml_dataset(canonical)
    dataset.objects[0].data["notes"] = "Edited object only"

    write_dataset(dataset, canonical, changed={("object", "KSW-0001")})

    assert cave.read_bytes() == before
    assert not cave.with_suffix(".yml").exists()


def _entity_bytes(root):
    return {
        p: p.read_bytes()
        for name in ("caves", "objects", "relations", "publications")
        for p in sorted((root / name).rglob("*"))
        if p.is_file() and p.suffix in {".yml", ".yaml"}
    }


@pytest.mark.parametrize("suffix", [".yml", ".yaml"])
@pytest.mark.parametrize("hint", [False, True], ids=["serialize-all", "dirty-hint"])
def test_write_result_matches_published_bytes_and_removals(canonical, suffix, hint):
    for path in tuple(_entity_bytes(canonical)):
        path.rename(path.with_suffix(suffix))
    kept = canonical / f"publications/kept{suffix}"
    kept.write_text("# Keep authored formatting\nid: kept\ncitation: Unchanged source\n")
    removed = canonical / f"publications/old{suffix}"
    removed.write_text("id: old\ncitation: Removed source\n")
    asset = canonical / "relations/evidence.yaml/photo.jpg"
    asset.parent.mkdir()
    asset.write_bytes(b"Photo retained outside the entity result")
    dataset = load_yaml_dataset(canonical)
    dataset.objects[0].data["notes"] = "Edited object"
    dataset.caves[0].data["notes"] = "Edited cave"

    def record(kind, name, values):
        return LoadedYamlRecord(kind, canonical / f"{name}{suffix}", values, values)

    dataset = replace(
        dataset,
        relations=(
            record(
                DataKind.RELATION,
                "relations/R-0001",
                {
                    "id": "R-0001",
                    "from_object_id": "KSW-0001",
                    "to_object_id": "KSW-0001",
                    "relation_type": "inne",
                },
            ),
        ),
        publications=(
            record(
                DataKind.PUBLICATION,
                "publications/z-new",
                {
                    "id": "z-new",
                    "citation": "New Z source",
                },
            ),
            record(
                DataKind.PUBLICATION,
                "publications/a-new",
                {
                    "id": "a-new",
                    "citation": "New A source",
                },
            ),
            next(r for r in dataset.publications if r.data["id"] == "kept"),
        ),
    )
    before = _entity_bytes(canonical)
    changed = {("object", "KSW-0001"), ("cave", "C-0001")} if hint else None

    result = write_dataset(dataset, canonical, changed=changed)

    after = _entity_bytes(canonical)
    assert result.written_paths == tuple(p for p in after if before.get(p) != after[p])
    assert result.removed_paths == tuple(p for p in before if p not in after) == (removed,)
    assert isinstance(result.written_paths, tuple) and isinstance(result.removed_paths, tuple)
    with pytest.raises(FrozenInstanceError):
        result.written_paths = ()
    assert asset.read_bytes() == b"Photo retained outside the entity result"
    if hint:
        assert kept.read_bytes() == before[kept]
        assert kept not in result.written_paths
    again = write_dataset(dataset, canonical, changed=changed)
    assert again.written_paths == again.removed_paths == ()
    assert _entity_bytes(canonical) == after


def test_write_result_includes_legacy_adoption_outside_dirty_ids(canonical):
    (canonical / "catalog.json").unlink()
    obj = canonical / "objects/KSW/KSW-0001.yml"
    cave = canonical / "caves/C-0001.yml"
    values = yaml.safe_load(obj.read_text())
    values.pop("membership_ordinal")
    values["best_measurement"]["measurement_id"] = "m-001"
    values["measurements"][0].update(x_1992=562729.5, y_1992=152838.5)
    obj.write_text(yaml.safe_dump(values, sort_keys=False))
    values = yaml.safe_load(cave.read_text())
    values["object_ids"] = ["KSW-0001"]
    cave.write_text(yaml.safe_dump(values, sort_keys=False))
    dataset = load_yaml_dataset(canonical)
    dataset.objects[0].data["notes"] = "Edited object only"
    before = _entity_bytes(canonical)

    result = write_dataset(dataset, canonical, changed={("object", "KSW-0001")})

    after = _entity_bytes(canonical)
    assert result.written_paths == tuple(p for p in after if before.get(p) != after[p])
    assert result.written_paths == (cave, obj)
    assert result.removed_paths == ()
    assert write_dataset(load_yaml_dataset(canonical), canonical).written_paths == ()


@pytest.mark.parametrize("failure", ["serialization", "swap", "first-publish"])
def test_write_result_is_not_returned_when_publication_fails(canonical, monkeypatch, failure):
    from gps_kataster_obiektow_tatr import catalog_records

    dataset = load_yaml_dataset(canonical)
    dataset.objects[0].data["notes"] = "Must not be published"
    before = {p: p.read_bytes() for p in canonical.rglob("*") if p.is_file()}

    def fail(*args, **kwargs):
        raise OSError("Injected publication failure")

    if failure == "serialization":
        original = yaml.safe_dump

        def fail_last_record(data, *args, **kwargs):
            if data["id"] == "C-0001":
                fail()
            return original(data, *args, **kwargs)

        monkeypatch.setattr(yaml, "safe_dump", fail_last_record)
    elif failure == "swap":
        monkeypatch.setattr(catalog_records, "_exchange_directories", fail)
    else:
        monkeypatch.setattr(catalog_records.os, "replace", fail)
    destination = canonical / "new" if failure == "first-publish" else canonical
    with pytest.raises(OSError, match="Injected publication failure"):
        write_dataset(dataset, destination)
    assert {p: p.read_bytes() for p in canonical.rglob("*") if p.is_file()} == before
    assert not tuple(destination.parent.glob(f".{destination.name}-snapshot-*"))


def test_snapshot_removes_omitted_records_without_removing_assets(canonical):
    from dataclasses import replace

    publication = canonical / "publications/old-source.yaml"
    publication.write_text("id: old-source\ncitation: Old source\n")
    asset = publication.with_suffix(".txt")
    asset.write_bytes(b"Source notes retained independently of the publication")
    dataset = replace(load_yaml_dataset(canonical), publications=())

    write_dataset(dataset, canonical)

    assert not publication.exists()
    assert asset.read_bytes() == b"Source notes retained independently of the publication"


def test_snapshot_preserves_asset_symlink_without_following_it(canonical):
    external = canonical.parent / (canonical.name + "-field-photo.jpg")
    external.write_bytes(b"Original external photo")
    link = canonical / "objects/KSW/field-photo.jpg"
    link.symlink_to(external)

    write_dataset(load_yaml_dataset(canonical), canonical)

    assert link.is_symlink()
    assert link.readlink() == external
    assert external.read_bytes() == b"Original external photo"


@pytest.mark.parametrize("directory", ["objects", "objects/KSW"])
def test_snapshot_does_not_write_through_entity_directory_symlinks(canonical, directory):
    dataset = load_yaml_dataset(canonical)
    original = canonical / directory
    external = canonical.parent / (canonical.name + "-external")
    original.rename(external)
    original.symlink_to(external, target_is_directory=True)
    before = {p.relative_to(external): p.read_bytes() for p in external.rglob("*") if p.is_file()}

    with pytest.raises(ValueError, match="symlink"):
        write_dataset(dataset, canonical)

    assert original.is_symlink()
    assert {
        p.relative_to(external): p.read_bytes() for p in external.rglob("*") if p.is_file()
    } == before


def test_source_serialization_does_not_mutate_read_model(canonical):
    dataset = load_yaml_dataset(canonical)
    before = deepcopy(dataset)
    result = write_dataset(dataset, canonical / "new")
    assert dataset == before
    assert result.written_paths == tuple(_entity_bytes(canonical / "new"))
    assert result.removed_paths == ()


def test_source_proposal_preserves_authored_fields_and_rejects_projection(canonical):
    from gps_kataster_obiektow_tatr import catalog_records, postgres, validator

    adapt = getattr(catalog_records, "source_dataset", None)
    validate = getattr(validator, "validated_source_proposal", None)
    assert callable(adapt) and callable(validate), "Source proposals need their own input boundary"
    loaded = load_yaml_dataset(canonical)
    obj = loaded.objects[0].raw_data
    obj.pop("notes", None)
    obj["measurements"][0]["elevation_m"] = None
    before = deepcopy(loaded)
    proposal = adapt(loaded)
    assert proposal.objects[0].data == obj
    assert loaded == before
    with validate(proposal, data_dir=canonical) as (catalog, issues):
        assert not validator.has_errors(issues)
        projection = catalog.dataset()
        assert projection.objects[0].data["measurements"][0]["elevation_m"] is None
    with (
        pytest.raises(TypeError, match="SourceDataset"),
        postgres.open_source_proposal(projection),
    ):
        pytest.fail("A projection cannot masquerade as a source proposal")
