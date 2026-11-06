"""Current v2 fixtures retain their real accepted v1 Git baseline."""

import subprocess
import sys
from copy import deepcopy

import pytest
import yaml
from export_test_support import REPO_ROOT, accept_source, cli_args, write_yaml

from gps_kataster_obiektow_tatr.build_db import build_database
from gps_kataster_obiektow_tatr.postgres import restore_dump


def legacy_source(root):
    """Literal legacy files; redundant coordinates are part of the adapter contract."""
    data = root / "data"
    for name in ("objects", "caves", "relations"):
        (data / name).mkdir(parents=True)
        (data / name / ".gitkeep").touch()
    obj = yaml.safe_load((REPO_ROOT / "tests/fixtures/valid-object.yml").read_text())
    obj["measurements"][0].update(
        lat=49.23459299, lon=19.87589498, x_1992=152267.23, y_1992=563744.25
    )
    newer = deepcopy(obj["measurements"][0])
    newer.update(id="m-002", observed_date="2026-05-16")
    obj["measurements"].append(newer)
    obj["best_measurement"]["measurement_id"] = "m-002"
    cave = yaml.safe_load((REPO_ROOT / "tests/fixtures/valid-cave.yml").read_text())
    cave["object_ids"] = ["KSW-0001"]
    write_yaml(data / "objects/KSW/KSW-0001.yml", obj)
    write_yaml(data / "caves/C-0001.yml", cave)
    return data, obj, cave


def test_canonical_candidate_builds_against_the_original_legacy_commit(tmp_path):
    data, _, _ = legacy_source(tmp_path)
    baseline = accept_source(data)
    accepted_bytes = {p.relative_to(data): p.read_bytes() for p in data.rglob("*") if p.is_file()}
    from export_test_support import write_sample_data

    write_sample_data(data)
    obj = yaml.safe_load((data / "objects/KSW/KSW-0001.yml").read_text())
    cave = yaml.safe_load((data / "caves/C-0001.yml").read_text())
    assert "object_ids" not in cave
    assert "measurement_id" not in obj["best_measurement"]
    assert "x_1992" not in obj["measurements"][0]
    assert [m["id"] for m in obj["measurements"]] == ["m-001", "m-002"]
    assert {
        p.relative_to(baseline["history_repo"] / "data"): p.read_bytes()
        for p in (baseline["history_repo"] / "data").rglob("*")
        if p.is_file()
    } == accepted_bytes
    result = build_database(data_dir=data, output_path=tmp_path / "katalog.dump", **baseline)
    with restore_dump(result.dump_path) as restored:
        assert restored.connection.execute(
            "SELECT id,ST_X(input_geom) AS lon,ST_Y(input_geom) AS lat "
            "FROM measurements ORDER BY history_order"
        ).fetchall() == [
            {"id": "m-001", "lon": 19.87589498, "lat": 49.23459299},
            {"id": "m-002", "lon": 19.87589498, "lat": 49.23459299},
        ]


@pytest.mark.parametrize(
    "script", ["build_db", "export_best_measurements", "build_release_artifacts"]
)
def test_current_cli_rejects_yaml_linked_to_a_managed_output(tmp_path, script):
    from export_test_support import write_sample_data

    data = write_sample_data(tmp_path / "data")
    baseline = accept_source(data)
    output = tmp_path / "exports"
    output.mkdir()
    victim = output / ("katalog.dump" if script == "build_db" else "best-measurements.geojson")
    path = data / "objects/KSW/KSW-0001.yml"
    original = path.read_bytes()
    victim.write_bytes(original)
    path.unlink()
    path.symlink_to(victim)
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / f"scripts/{script}.py"),
            "--data-dir",
            str(data),
            *cli_args(baseline),
            "--output" if script == "build_db" else "--output-dir",
            str(victim if script == "build_db" else output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "YAML snapshots must not be symlinks" in result.stdout + result.stderr
    assert path.is_symlink() and path.read_bytes() == original
    assert {p.name: p.read_bytes() for p in output.iterdir()} == {victim.name: original}


@pytest.mark.parametrize("limit", ["MAX_FILE_BYTES", "MAX_CATALOG_BYTES"])
@pytest.mark.parametrize("builder", ["dump", "best", "release"])
def test_current_builders_retain_snapshot_size_limits(tmp_path, monkeypatch, limit, builder):
    from export_test_support import write_sample_data

    from gps_kataster_obiektow_tatr import postgres
    from gps_kataster_obiektow_tatr.best_measurements_export import export_best_measurements
    from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts

    data = write_sample_data(tmp_path / "data")
    baseline = accept_source(data)
    output = tmp_path / "exports"
    from gps_kataster_obiektow_tatr import data_loader

    monkeypatch.setattr(data_loader, limit, 1)
    with pytest.raises(postgres.CatalogLoadError, match="YAML snapshot size limit exceeded"):
        if builder == "dump":
            build_database(data_dir=data, output_path=output / "katalog.dump", **baseline)
        else:
            function = export_best_measurements if builder == "best" else build_release_artifacts
            function(data_dir=data, output_dir=output, **baseline)
    assert not output.exists()


def test_accepted_legacy_auto_cache_does_not_block_a_corrected_candidate(tmp_path):
    data, obj, _ = legacy_source(tmp_path)
    path = data / "objects/KSW/KSW-0001.yml"
    obj["best_measurement"]["measurement_id"] = "m-999"
    write_yaml(path, obj)
    baseline = accept_source(data)
    from export_test_support import write_sample_data

    write_sample_data(data)
    result = build_database(data_dir=data, output_path=tmp_path / "katalog.dump", **baseline)
    assert result.dump_path.is_file()
    assert not any(i.severity == "error" for i in result.validation_issues)
