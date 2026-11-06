"""Shared export rows are detached, read-only and prepared once per release."""

from dataclasses import FrozenInstanceError

import pytest
from export_test_support import source

from gps_kataster_obiektow_tatr.postgres import open_catalog


def test_prepared_rows_keep_manual_best_and_cannot_change_the_shared_history(tmp_path):
    from gps_kataster_obiektow_tatr.export_data import prepare_export_data

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
