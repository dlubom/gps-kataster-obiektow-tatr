"""Canonical YAML stores source facts; read models may contain derived projections."""

import json
from pathlib import Path

import pytest
import yaml

from gps_kataster_obiektow_tatr.data_loader import (
    CATALOG_FORMAT,
    load_yaml_dataset,
)
from gps_kataster_obiektow_tatr.postgres import (
    CatalogLoadError,
    _catalog_rows,
    _read_snapshots,
)


@pytest.fixture
def canonical(tmp_path, make_data_dir):
    make_data_dir(tmp_path)
    (tmp_path / "publications").mkdir()
    (tmp_path / "catalog.json").write_text(json.dumps(CATALOG_FORMAT))
    fixtures = Path(__file__).parent / "fixtures"
    obj = yaml.safe_load((fixtures / "canonical-object.yml").read_text())
    obj["membership_ordinal"] = 7
    cave = yaml.safe_load((fixtures / "canonical-cave.yml").read_text())
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
    dataset.caves[0].data["object_ids"] = ["KSW-0001"]  # read-model-only mutation
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


def test_cave_morphometry_reaches_postgres_with_source_and_missing_values(canonical):
    path = canonical / "caves/C-0001.yml"
    cave = yaml.safe_load(path.read_text())
    cave.update(
        system_cave_id="C-0002",
        length_m=2320,
        depth_m=None,
        denivelation_m=60,
        denivelation_qualifier="approximate",
        morphometry_source_ref="KKTJ 2026-07, PDF 03, s. 1, lp. 7",
    )
    path.write_text(yaml.safe_dump(cave))
    rows, _ = _read_snapshots(canonical)
    values = next(values for _, table, values in rows if table == "caves")
    assert values["system_cave_id"] == "C-0002"
    assert values["length_m"] == 2320
    assert values["depth_m"] is None
    assert values["denivelation_m"] == 60
    assert values["denivelation_qualifier"] == "approximate"
    assert values["morphometry_source_ref"] == cave["morphometry_source_ref"]
