"""Legacy declarations and an explicit migration retain their own real Git baseline."""

import subprocess
import sys
from copy import deepcopy

import pytest
import yaml
from export_test_support import REPO_ROOT, accept_source, cli_args, write_yaml

from gps_kataster_obiektow_tatr.build_db import build_database
from gps_kataster_obiektow_tatr.catalog_records import write_dataset
from gps_kataster_obiektow_tatr.data_loader import load_yaml_dataset
from gps_kataster_obiektow_tatr.postgres import restore_dump
from gps_kataster_obiektow_tatr.validator import CatalogValidationError, validated_proposal


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


@pytest.mark.parametrize(
    "damage,code",
    [
        ("missing-member", "OBJECT_CAVE_MEMBERSHIP_MISSING"),
        ("no-cave-id", "CAVE_OBJECT_MEMBERSHIP_MISMATCH"),
        ("two-caves", "CAVE_OBJECT_MEMBERSHIP_MISMATCH"),
        ("coordinates", "COORDINATE_MISMATCH"),
    ],
)
def test_legacy_declarations_block_explicit_migration_before_writes(tmp_path, damage, code):
    data, obj, cave = legacy_source(tmp_path)
    if damage == "missing-member":
        cave["object_ids"] = []
    elif damage == "no-cave-id":
        obj["cave_id"] = None
    elif damage == "two-caves":
        other = deepcopy(cave)
        other["id"] = "C-0002"
        write_yaml(data / "caves/C-0002.yml", other)
    else:
        obj["measurements"][0]["x_1992"] += 100
    write_yaml(data / "objects/KSW/KSW-0001.yml", obj)
    write_yaml(data / "caves/C-0001.yml", cave)
    before = {p.relative_to(data): p.read_bytes() for p in data.rglob("*") if p.is_file()}
    # Conversion is deliberate only in tests of migration itself.
    with (
        pytest.raises(CatalogValidationError) as error,
        validated_proposal(load_yaml_dataset(data), data_dir=data) as (catalog, _),
    ):
        write_dataset(catalog.dataset(), data)
    assert code in {i.code for i in error.value.issues}
    assert all(i.path is not None for i in error.value.issues if i.code == code)
    assert {p.relative_to(data): p.read_bytes() for p in data.rglob("*") if p.is_file()} == before
    assert not (data / "catalog.json").exists()


def test_explicit_legacy_migration_builds_against_the_original_accepted_commit(tmp_path):
    data, _, _ = legacy_source(tmp_path)
    baseline = accept_source(data)
    accepted_bytes = {p.relative_to(data): p.read_bytes() for p in data.rglob("*") if p.is_file()}
    with validated_proposal(load_yaml_dataset(data), data_dir=data) as (catalog, _):
        projection = catalog.dataset()
    write_dataset(projection, data)
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
    "script", ["validate", "build_db", "export_best_measurements", "build_release_artifacts"]
)
def test_legacy_cli_checks_declarations_before_outputs(tmp_path, script):
    data, obj, _ = legacy_source(tmp_path)
    baseline = accept_source(data)
    obj["measurements"][0]["x_1992"] += 100
    write_yaml(data / "objects/KSW/KSW-0001.yml", obj)
    output = tmp_path / "exports"
    output.mkdir()
    previous = output / "katalog.dump"
    previous.write_bytes(b"accepted release")
    before = {p.relative_to(data): p.read_bytes() for p in data.rglob("*") if p.is_file()}
    args = [
        sys.executable,
        str(REPO_ROOT / f"scripts/{script}.py"),
        "--data-dir",
        str(data),
        *cli_args(baseline),
    ]
    if script != "validate":
        args += [
            "--output" if script == "build_db" else "--output-dir",
            str(previous if script == "build_db" else output),
        ]
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "COORDINATE_MISMATCH" in result.stdout + result.stderr
    assert "Traceback" not in result.stdout + result.stderr
    assert {p.name: p.read_bytes() for p in output.iterdir()} == {
        "katalog.dump": b"accepted release"
    }
    assert {p.relative_to(data): p.read_bytes() for p in data.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize(
    "script", ["build_db", "export_best_measurements", "build_release_artifacts"]
)
def test_legacy_cli_rejects_yaml_linked_to_a_managed_output(tmp_path, script):
    data, _, _ = legacy_source(tmp_path)
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
def test_legacy_builders_retain_snapshot_size_limits(tmp_path, monkeypatch, limit, builder):
    from gps_kataster_obiektow_tatr import postgres
    from gps_kataster_obiektow_tatr.best_measurements_export import export_best_measurements
    from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts

    data, _, _ = legacy_source(tmp_path)
    baseline = accept_source(data)
    output = tmp_path / "exports"
    monkeypatch.setattr(postgres, limit, 1)
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
    obj["best_measurement"]["measurement_id"] = "m-002"
    write_yaml(path, obj)
    result = build_database(data_dir=data, output_path=tmp_path / "katalog.dump", **baseline)
    assert result.dump_path.is_file()
    assert not any(i.severity == "error" for i in result.validation_issues)
