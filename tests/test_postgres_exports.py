"""Native export publication gates: no partial results or unverified archives."""

import json
import subprocess
from pathlib import Path

import pytest
from export_test_support import accept_source, source, write_sample_data, write_yaml
from export_test_support import excel_records as _excel_records

from gps_kataster_obiektow_tatr.build_db import build_database
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts


def test_release_has_only_thirteen_verified_assets(tmp_path):
    data, baseline = source(tmp_path)
    result = build_release_artifacts(data_dir=data, output_dir=tmp_path / "exports", **baseline)
    assert len(result.artifact_paths) == 13
    assert {p.name for p in result.artifact_paths} >= {"katalog.dump", "katalog.gpkg"}
    assert not any("sqlite" in p.name for p in result.artifact_paths)
    assert set((tmp_path / "exports").iterdir()) == set(result.artifact_paths)


@pytest.mark.parametrize("failure", ["dump", "geopackage", "excel"])
def test_late_failure_preserves_previous_output(tmp_path, monkeypatch, failure):
    import gps_kataster_obiektow_tatr.release_artifacts as module

    data, baseline = source(tmp_path)
    output = tmp_path / "exports"
    build_release_artifacts(data_dir=data, output_dir=output, **baseline)
    previous = {p.name: p.read_bytes() for p in output.iterdir()}

    def fail(*args, **kwargs):
        raise RuntimeError("injected readback/formatter failure")

    monkeypatch.setattr(
        module,
        {"dump": "verify_dump", "geopackage": "write_geopackage", "excel": "write_excel_export"}[
            failure
        ],
        fail,
    )
    with pytest.raises(RuntimeError, match="injected"):
        build_release_artifacts(data_dir=data, output_dir=output, **baseline)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == previous


def test_build_fails_closed_for_unavailable_baseline(tmp_path):
    data, baseline = source(tmp_path)
    with pytest.raises(ValueError, match="HISTORY_BASELINE_UNAVAILABLE"):
        build_database(
            data_dir=data,
            output_path=tmp_path / "katalog.dump",
            history_repo=baseline["history_repo"],
            base_ref="does-not-exist",
        )
    assert not (tmp_path / "katalog.dump").exists()


def test_empty_geopackage_still_declares_both_spatial_layers(tmp_path):
    import sqlite3

    data, baseline = source(tmp_path, empty=True)
    build_release_artifacts(data_dir=data, output_dir=tmp_path / "exports", **baseline)
    with sqlite3.connect(tmp_path / "exports/katalog.gpkg") as db:
        assert db.execute(
            "SELECT table_name,geometry_type_name,srs_id,z,m "
            "FROM gpkg_geometry_columns ORDER BY table_name"
        ).fetchall() == [("best", "POINT", 2180, 0, 0), ("measurements", "POINT", 2180, 0, 0)]
        for layer in ("best", "measurements"):
            assert db.execute(f"SELECT COUNT(*) FROM {layer}").fetchone() == (0,)
            declared = json.loads(
                (Path(__file__).parent / "fixtures/geopackage_fields.json").read_text()
            )
            assert [list(r[1:3]) for r in db.execute(f"PRAGMA table_info({layer})")] == declared


def test_manual_best_differs_from_sql_proposal_in_every_full_export(tmp_path):
    import csv
    import sqlite3

    from openpyxl import load_workbook

    from gps_kataster_obiektow_tatr.postgres import restore_dump

    data, baseline = source(tmp_path)
    import yaml

    path = data / "objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(path.read_text())
    obj["best_measurement"].update(
        mode="manual", measurement_id="m-001", reason="Keep the older PIG point"
    )
    write_yaml(path, obj)
    result = build_release_artifacts(data_dir=data, output_dir=tmp_path / "exports", **baseline)
    with result.export_result.csv_path.open() as stream:
        row = next(csv.DictReader(stream))
        assert (row["measurement_id"], row["computed_best_measurement_id"]) == ("m-001", "m-002")
    with sqlite3.connect(result.geopackage_path) as db:
        assert db.execute(
            "SELECT measurement_id,computed_best_measurement_id FROM best"
        ).fetchall() == [("m-001", "m-002")]
        assert db.execute(
            "SELECT measurement_id,selected FROM measurements ORDER BY measurement_id"
        ).fetchall() == [("m-001", "Tak"), ("m-002", "Nie")]
    book = load_workbook(result.excel_path)
    try:
        assert _excel_records(book["Best"])[0]["ID pomiaru"] == "m-001"
        rows = _excel_records(book["Full"])
        assert [r["Wybrany do eksportu"] for r in rows] == ["Tak", "Nie"]
        assert rows[0]["ID sugerowanego pomiaru"] == "m-002"
    finally:
        book.close()
    statistics = json.loads(result.statistics_paths[0].read_text())
    assert statistics["selected_points"]["by_source"] == {"PIG": 1}
    assert statistics["measurement_history"]["by_source"] == {"PIG": 1, "TPN": 1}
    with restore_dump(result.dump_path) as restored:
        assert (
            restored.connection.execute("SELECT id FROM catalog.v_best").fetchone()["id"] == "m-001"
        )
        assert (
            restored.connection.execute(
                "SELECT measurement_id FROM catalog.v_auto_best"
            ).fetchone()["measurement_id"]
            == "m-002"
        )


@pytest.mark.parametrize("damage", ["missing-manual", "duplicate-measurement", "bad-source"])
def test_native_invalid_sql_preserves_existing_outputs(tmp_path, damage):
    from copy import deepcopy

    data, baseline = source(tmp_path)
    import yaml

    path = data / "objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(path.read_text())
    if damage == "missing-manual":
        obj["best_measurement"].update(
            mode="manual", measurement_id="missing", reason="Native invalid reference"
        )
    elif damage == "duplicate-measurement":
        obj["measurements"].append(deepcopy(obj["measurements"][0]))
    else:
        obj["measurements"][0]["source"] = "not-a-source"
    write_yaml(path, obj)
    output = tmp_path / "exports"
    output.mkdir()
    (output / "old").write_bytes(b"accepted release")
    with pytest.raises(ValueError):
        build_release_artifacts(data_dir=data, output_dir=output, **baseline)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == {"old": b"accepted release"}


def test_corrupt_dump_restore_fails_before_publication(tmp_path, monkeypatch):
    from gps_kataster_obiektow_tatr.postgres import Catalog

    data, baseline = source(tmp_path)
    monkeypatch.setattr(Catalog, "dump", lambda self, path: path.write_bytes(b"PGDMP corrupted"))
    with pytest.raises(subprocess.CalledProcessError):
        build_release_artifacts(data_dir=data, output_dir=tmp_path / "exports", **baseline)
    assert not (tmp_path / "exports").exists()


def test_missing_native_gdal_blocks_publication(tmp_path, monkeypatch):
    import gps_kataster_obiektow_tatr.geopackage as module

    data, baseline = source(tmp_path)
    original = module.shutil.which
    monkeypatch.setattr(
        module.shutil, "which", lambda name: None if name == "ogr2ogr" else original(name)
    )
    with pytest.raises(ValueError, match="ogr2ogr unavailable"):
        build_release_artifacts(data_dir=data, output_dir=tmp_path / "exports", **baseline)
    assert not (tmp_path / "exports").exists()


def test_single_catalogue_supplies_every_writer(tmp_path, monkeypatch):
    from contextlib import contextmanager

    import gps_kataster_obiektow_tatr.postgres as module

    original = module._open_rows
    calls = []

    @contextmanager
    def counted(*args, **kwargs):
        calls.append(kwargs)
        with original(*args, **kwargs) as catalog:
            yield catalog

    monkeypatch.setattr(module, "_open_rows", counted)
    data = write_sample_data(tmp_path / "data")
    external_asset = tmp_path / "external-empty-asset"
    external_asset.mkdir()
    (data / "asset").symlink_to(external_asset, target_is_directory=True)
    baseline = accept_source(data)
    assert not list(external_asset.iterdir()), "baseline capture must not write through asset links"
    assert calls == []  # Fixture setup must not open a validating/converting database.
    build_release_artifacts(data_dir=data, output_dir=tmp_path / "exports", **baseline)
    assert calls == [{}]


@pytest.mark.parametrize("destination", ["file", "symlink"])
def test_destination_must_be_real_directory(tmp_path, destination):
    data, baseline = source(tmp_path)
    output = tmp_path / "exports"
    old = tmp_path / "old"
    old.write_bytes(b"previous")
    if destination == "file":
        output.write_bytes(b"previous")
    else:
        output.symlink_to(old)
    with pytest.raises(ValueError, match="real directory"):
        build_release_artifacts(data_dir=data, output_dir=output, **baseline)
    assert output.read_bytes() == b"previous"


def test_standalone_export_is_atomic_on_late_formatter_failure(tmp_path, monkeypatch):
    import gps_kataster_obiektow_tatr.best_measurements_export as module

    data, baseline = source(tmp_path)
    output = tmp_path / "exports"
    output.mkdir()
    (output / "old").write_bytes(b"accepted output")

    def fail(*args, **kwargs):
        raise RuntimeError("last metadata writer failed")

    monkeypatch.setattr(module, "_write_metadata", fail)
    with pytest.raises(RuntimeError, match="last metadata"):
        module.export_best_measurements(data_dir=data, output_dir=output, **baseline)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == {"old": b"accepted output"}


def test_excel_best_keeps_csv_numeric_precision_without_csv_reload(tmp_path):
    from openpyxl import load_workbook

    from gps_kataster_obiektow_tatr.excel_export import write_excel_export
    from gps_kataster_obiektow_tatr.export_data import prepare_export_data
    from gps_kataster_obiektow_tatr.postgres import open_catalog

    data, _ = source(tmp_path)
    with open_catalog(data) as catalog:
        dataset = catalog.dataset()
    dataset.objects[0].data["measurements"][1]["lat"] = 49.234592991234
    path = tmp_path / "workbook.xlsx"
    write_excel_export(
        prepare_export_data(dataset, generated_at="2026-11-01T00:00:00Z"),
        output_path=path,
        release_version=None,
        source_commit=None,
    )
    book = load_workbook(path)
    try:
        assert book["Best"]["D7"].value == 49.2345929912
    finally:
        book.close()


@pytest.mark.parametrize("damage", ["attribute", "geometry", "crs"])
def test_actual_gdal_readback_mismatch_preserves_previous_release(tmp_path, monkeypatch, damage):
    import json

    import gps_kataster_obiektow_tatr.geopackage as module

    data, baseline = source(tmp_path)
    output = tmp_path / "exports"
    output.mkdir()
    (output / "old").write_bytes(b"previous complete release")
    original = module._run

    def corrupt_readback(command):
        result = original(command)
        if "/vsistdout/" in command:
            payload = json.loads(result.stdout)
            if damage == "attribute":
                payload["features"][0]["properties"]["measurement_notes"] = "Readback mismatch"
            elif damage == "geometry":
                payload["features"][0]["geometry"]["coordinates"][0] += 1
            else:
                payload["crs"]["properties"]["name"] = "urn:ogc:def:crs:EPSG::4326"
            result.stdout = json.dumps(payload)
        return result

    monkeypatch.setattr(module, "_run", corrupt_readback)
    with pytest.raises(ValueError, match="GeoPackage"):
        build_release_artifacts(data_dir=data, output_dir=output, **baseline)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == {
        "old": b"previous complete release"
    }


@pytest.mark.parametrize("field", ["input_srid", "elevation_m", "object_id"])
def test_empty_geopackage_readback_rejects_wrong_declared_field_type(tmp_path, field):
    import sqlite3

    from gps_kataster_obiektow_tatr.data_loader import LoadedDataset
    from gps_kataster_obiektow_tatr.geopackage import (
        verify_geopackage,
        write_geopackage,
    )

    path = tmp_path / "empty.gpkg"
    from gps_kataster_obiektow_tatr.export_data import prepare_export_data

    write_geopackage(prepare_export_data(LoadedDataset(objects=(), caves=(), relations=())), path)
    layers = {"best": [], "measurements": []}
    with sqlite3.connect(path) as db:
        # An empty layer has no values to expose a changed declaration.
        definition = db.execute("SELECT sql FROM sqlite_schema WHERE name='best'").fetchone()[0]
        original = "REAL" if field != "object_id" else "TEXT"
        changed = "TEXT" if original == "REAL" else "REAL"
        assert f'"{field}" {original}' in definition
        db.execute("PRAGMA writable_schema=ON")
        db.execute(
            "UPDATE sqlite_schema SET sql=? WHERE name='best'",
            (definition.replace(f'"{field}" {original}', f'"{field}" {changed}'),),
        )
    with pytest.raises(ValueError, match="field declarations"):
        verify_geopackage(path, layers, catalogue_tables={"caves": (), "objects": ()})


@pytest.mark.parametrize("damage", ["missing", "extra", "outside", "symlink", "duplicate"])
def test_unexpected_artifact_set_preserves_previous_release(tmp_path, monkeypatch, damage):
    """Missing validation would publish an incomplete, extra or unsafe artifact set."""
    from dataclasses import replace

    import gps_kataster_obiektow_tatr.release_artifacts as module

    data, baseline = source(tmp_path)
    output = tmp_path / "exports"
    output.mkdir()
    (output / "old").write_bytes(b"previous complete release")
    original_best, original_excel = module.write_best_measurements, module.write_excel_export

    def best(*args, **kwargs):
        result = original_best(*args, **kwargs)
        if damage == "outside":
            return replace(result, geojson_path=tmp_path / result.geojson_path.name)
        if damage == "duplicate":
            return replace(result, gpx_path=result.csv_path)
        return result

    def excel(*args, **kwargs):
        path = original_excel(*args, **kwargs)
        if damage == "missing":
            path.unlink()
        elif damage == "extra":
            (path.parent / "unexpected.txt").write_text("must not be published")
        elif damage == "symlink":
            path.unlink()
            path.symlink_to(output / "old")
        return path

    monkeypatch.setattr(module, "write_best_measurements", best)
    monkeypatch.setattr(module, "write_excel_export", excel)
    with pytest.raises(ValueError, match="artifact"):
        build_release_artifacts(data_dir=data, output_dir=output, **baseline)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == {
        "old": b"previous complete release"
    }
