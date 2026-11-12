"""Shared export rows are detached, read-only and prepared once per release."""

from dataclasses import FrozenInstanceError, replace

import pytest
from export_test_support import initialize_source, source, valid_cave, valid_object, write_yaml

from gps_kataster_obiektow_tatr.export_data import prepare_export_data
from gps_kataster_obiektow_tatr.postgres import open_catalog


@pytest.fixture
def catalogue_dataset(tmp_path):
    data = initialize_source(tmp_path / "data")
    write_yaml(
        data / "caves/C-0001.yml",
        {**valid_cave(), "name": "Śnieżna", "system_cave_id": "C-0002"},
    )
    write_yaml(
        data / "caves/C-0002.yml",
        {**valid_cave(), "id": "C-0002", "name": "Wielka Śnieżna", "external_refs": []},
    )
    write_yaml(data / "objects/KSW/KSW-0001.yml", {**valid_object(), "name_local": "Otwór główny"})
    unlinked = valid_object()
    del unlinked["name_local"]
    unlinked.update(
        id="KSW-0002", category="ponor", cave_id=None, membership_ordinal=None, external_refs=[]
    )
    write_yaml(data / "objects/KSW/KSW-0002.yml", unlinked)
    with open_catalog(data) as catalog:
        return catalog.dataset()


def test_cave_without_objects_is_exported(catalogue_dataset):
    assert catalogue_dataset.caves[1].data["object_ids"] == []

    prepared = prepare_export_data(catalogue_dataset)

    assert prepared.cave_count == 2
    assert [
        (row["cave_id"], row["cave_name"], row["system_cave_id"]) for row in prepared.caves
    ] == [
        ("C-0001", "Śnieżna", "C-0002"),
        ("C-0002", "Wielka Śnieżna", None),
    ]


@pytest.mark.parametrize("has_history", [False, True], ids=["without-history", "with-history"])
def test_object_without_best_is_in_catalogue_export(catalogue_dataset, has_history):
    with_best = prepare_export_data(catalogue_dataset)
    _, unlinked = catalogue_dataset.objects
    # Simulate a SQL read model with no resolved selection. Canonical validation
    # currently requires both a Best policy and at least one measurement.
    unlinked.data["best_measurement"]["measurement_id"] = None
    if not has_history:
        unlinked.data["computed_best_measurement_id"] = None
        unlinked.data["measurements"] = []

    prepared = prepare_export_data(catalogue_dataset)

    assert prepared.objects == with_best.objects
    assert prepared.caves == with_best.caves
    assert [row.object_id for row in prepared.best] == ["KSW-0001"]
    assert [row["object_id"] for row in prepared.selected] == ["KSW-0001"]
    assert [row["selected"] for row in prepared.history if row["object_id"] == "KSW-0002"] == (
        ["Nie", "Nie"] if has_history else []
    )


def test_catalogue_rows_preserve_nulls_unicode_and_order(catalogue_dataset):
    prepared = prepare_export_data(
        replace(
            catalogue_dataset,
            objects=catalogue_dataset.objects[::-1],
            caves=catalogue_dataset.caves[::-1],
        )
    )

    assert prepared.objects == (
        {
            "object_id": "KSW-0001",
            "name": "Otwór główny",
            "cave_id": "C-0001",
            "category": "jaskinia_otwor",
        },
        {"object_id": "KSW-0002", "name": None, "cave_id": None, "category": "ponor"},
    )
    assert [row["cave_id"] for row in prepared.caves] == ["C-0001", "C-0002"]
    with pytest.raises(TypeError):
        prepared.objects[0]["name"] = "changed"
    catalogue_dataset.objects[0].data["name_local"] = "changed"
    assert prepared.objects[0]["name"] == "Otwór główny"


def test_explicit_selection_missing_from_history_is_rejected(catalogue_dataset):
    catalogue_dataset.objects[0].data["best_measurement"]["measurement_id"] = "m-999"

    with pytest.raises(ValueError, match="Selected measurement KSW-0001/m-999 is missing"):
        prepare_export_data(catalogue_dataset)


def test_prepared_rows_keep_manual_best_and_cannot_change_the_shared_history(tmp_path):
    data, _ = source(tmp_path)
    with open_catalog(data) as catalog:
        dataset = catalog.dataset()
    obj = dataset.objects[0].data
    obj["best_measurement"].update(
        mode="manual", measurement_id="m-001", reason="Retain the older point"
    )
    obj["measurements"][0]["tags"] = ["survey_anchor"]
    prepared = prepare_export_data(dataset, generated_at="2026-11-05T12:00:00Z")

    assert prepared.best[0].measurement_id == "m-001"
    assert prepared.best[0].computed_best_measurement_id == "m-002"
    assert [r["selected"] for r in prepared.history] == ["Tak", "Nie"]
    assert prepared.selected[0] is prepared.history[0]
    with pytest.raises(TypeError):
        prepared.history[0]["elevation_m"] = 9999
    with pytest.raises(TypeError):
        prepared.history[0]["tags"][0] = "gnss_anchor"
    with pytest.raises(FrozenInstanceError):
        prepared.best[0].measurement_id = "m-002"
    with pytest.raises(FrozenInstanceError):
        prepared.generated_at = "changed"

    obj["measurements"][0]["tags"].append("gnss_anchor")
    obj["measurements"][0]["elevation_m"] = 9999
    obj["external_refs"][0]["external_id"] = "changed"
    assert prepared.history[0]["tags"] == ("survey_anchor",)
    assert prepared.history[0]["tags_json"] == '["survey_anchor"]'
    assert prepared.history[0]["elevation_m"] == 1240
    assert prepared.history[0]["tpn_globalid"] != "changed"


def test_release_prepares_once_and_shares_rows_with_all_serializers(tmp_path, monkeypatch):
    import gps_kataster_obiektow_tatr.release_artifacts as module

    data, baseline = source(tmp_path)
    original_prepare = module.prepare_export_data
    prepared = []

    def prepare(*args, **kwargs):
        assert not prepared, "a release must prepare export rows only once"
        result = original_prepare(*args, **kwargs)
        prepared.append(result)
        return result

    monkeypatch.setattr(module, "prepare_export_data", prepare)
    for name in (
        "write_best_measurements",
        "write_geopackage",
        "write_excel_export",
        "write_release_statistics",
    ):
        original = getattr(module, name)

        def consume(export_data, *args, _original=original, **kwargs):
            assert export_data is prepared[0]
            return _original(export_data, *args, **kwargs)

        monkeypatch.setattr(module, name, consume)
    result = module.build_release_artifacts(
        data_dir=data,
        output_dir=tmp_path / "exports",
        generated_at="2026-11-05T12:00:00Z",
        **baseline,
    )
    assert len(result.artifact_paths) == 13
    assert result.export_result.metadata["generated_at"] == "2026-11-05T12:00:00Z"
