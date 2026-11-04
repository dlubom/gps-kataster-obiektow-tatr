"""A failed build must preserve the last successful artifacts."""

import sqlite3

import pytest
from test_catalog_contract import _catalog, _write_yaml

from gps_kataster_obiektow_tatr import release_artifacts
from gps_kataster_obiektow_tatr.best_measurements_export import export_best_measurements
from gps_kataster_obiektow_tatr.build_db import build_sqlite_database


def test_export_path_collision_preserves_previous_files(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _catalog(data_dir)
    output_dir = tmp_path / "exports"
    output_dir.mkdir()
    csv = output_dir / "best-measurements.csv"
    csv.write_bytes(b"previous CSV")
    (output_dir / "best-measurements.gpx").mkdir()

    with pytest.raises(OSError):
        export_best_measurements(data_dir=data_dir, output_dir=output_dir)

    assert csv.read_bytes() == b"previous CSV"
    assert not (output_dir / "best-measurements.geojson").exists()


def test_late_release_failure_preserves_previous_artifacts(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _catalog(data_dir)
    output_dir = tmp_path / "exports"
    sqlite_path = tmp_path / "db" / "catalog.sqlite"
    first = release_artifacts.build_release_artifacts(
        data_dir=data_dir, sqlite_path=sqlite_path, output_dir=output_dir
    )
    old_contents = {path: path.read_bytes() for path in first.artifact_paths}
    (output_dir / "unrelated.txt").write_text("unrelated")

    def fail_excel(**kwargs):
        kwargs["output_path"].write_bytes(b"partial XLSX")
        raise OSError("simulated XLSX writer failure")

    monkeypatch.setattr(release_artifacts, "write_excel_export", fail_excel)
    with pytest.raises(OSError, match="simulated XLSX writer failure"):
        release_artifacts.build_release_artifacts(
            data_dir=data_dir,
            sqlite_path=sqlite_path,
            output_dir=output_dir,
            generated_at="2020-01-01T00:00:00Z",
        )

    assert {path: path.read_bytes() for path in first.artifact_paths} == old_contents
    assert (output_dir / "unrelated.txt").read_text() == "unrelated"


def test_sqlite_binds_large_finite_integer_as_real(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    obj, source_path = _catalog(data_dir)
    value = 2**63
    obj["measurements"][0]["elevation_m"] = value
    _write_yaml(source_path, obj)
    previous_source = source_path.read_bytes()
    result = build_sqlite_database(data_dir=data_dir, output_path=tmp_path / "db.sqlite")

    with sqlite3.connect(result.sqlite_path) as db:
        assert db.execute(
            "SELECT elevation_m, typeof(elevation_m) FROM measurements"
        ).fetchone() == (
            float(value),
            "real",
        )
    assert source_path.read_bytes() == previous_source


def test_replace_failure_rolls_back_published_files(tmp_path, monkeypatch):
    from pathlib import Path

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _catalog(data_dir)
    output_dir = tmp_path / "exports"
    output_dir.mkdir()
    csv = output_dir / "best-measurements.csv"
    csv.write_bytes(b"previous CSV")
    original_replace = Path.replace

    def fail_at_gpx(self, target):
        if self.suffix == ".new" and target.name == "best-measurements.gpx":
            raise OSError("simulated GPX publication failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_at_gpx)
    with pytest.raises(OSError, match="simulated GPX publication failure"):
        export_best_measurements(data_dir=data_dir, output_dir=output_dir)

    assert list(output_dir.iterdir()) == [csv]
    assert csv.read_bytes() == b"previous CSV"


def test_sqlite_leaves_unrelated_file_at_legacy_temp_path(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _catalog(data_dir)
    sqlite_path = tmp_path / "db.sqlite"
    other_file = tmp_path / "db.sqlite.tmp"
    other_file.write_bytes(b"unrelated")

    build_sqlite_database(data_dir=data_dir, output_path=sqlite_path)

    assert sqlite_path.is_file()
    assert other_file.read_bytes() == b"unrelated"
