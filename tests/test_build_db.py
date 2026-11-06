import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from export_test_support import (
    GENERATED_AT,
    KSW_LAT,
    KSW_LON,
    REPO_ROOT,
    accept_source,
    cli_args,
)
from export_test_support import (
    valid_cave as _valid_cave,
)
from export_test_support import (
    valid_object as _valid_object,
)
from export_test_support import (
    write_sample_data as _write_sample_data,
)
from export_test_support import (
    write_yaml as _write_yaml,
)

from gps_kataster_obiektow_tatr.build_db import (
    build_database,
)
from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992
from gps_kataster_obiektow_tatr.postgres import restore_dump

BUILD_DB_SCRIPT = REPO_ROOT / "scripts" / "build_db.py"


@pytest.mark.parametrize("damage", ["missing-member", "no-cave-id", "two-caves"])
def test_asymmetric_cave_membership_blocks_dump_before_writes(tmp_path, damage):
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    baseline = accept_source(data_dir)
    output = tmp_path / "output/katalog.dump"
    build_database(**baseline, data_dir=data_dir, output_path=output)
    before = output.read_bytes()
    if damage == "missing-member":
        cave = _valid_cave()
        cave["object_ids"] = []
        _write_yaml(data_dir / "caves/C-0001.yml", cave)
        code = "Canonical YAML must not contain computed membership"
    elif damage == "no-cave-id":
        obj = _valid_object()
        obj["cave_id"] = None
        _write_yaml(data_dir / "objects/KSW/KSW-0001.yml", obj)
        code = "objects_check"
    else:
        cave = _valid_cave()
        cave["id"] = "C-0002"
        cave["object_ids"] = ["KSW-0001"]
        _write_yaml(data_dir / "caves/C-0002.yml", cave)
        code = "Canonical YAML must not contain computed membership"
    source_before = {p: p.read_bytes() for p in data_dir.rglob("*") if p.is_file()}
    for path in (output, tmp_path / "new-output/katalog.dump"):
        with pytest.raises(ValueError, match=code):
            build_database(**baseline, data_dir=data_dir, output_path=path)
        result = subprocess.run(
            [
                sys.executable,
                str(BUILD_DB_SCRIPT),
                "--data-dir",
                str(data_dir),
                "--output",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1
        assert code in result.stdout + result.stderr
        assert "Traceback" not in result.stdout + result.stderr
    assert output.read_bytes() == before
    assert set(output.parent.iterdir()) == {output}
    assert not (tmp_path / "new-output").exists()
    assert {p: p.read_bytes() for p in data_dir.rglob("*") if p.is_file()} == source_before


def test_relinked_cave_membership_matches_dump_and_yaml(tmp_path):
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    baseline = accept_source(data_dir)
    cave = _valid_cave()
    cave.update(id="C-0002")
    _write_yaml(data_dir / "caves/C-0002.yml", cave)
    object_path = data_dir / "objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(object_path.read_text())
    obj.update(cave_id="C-0002", membership_ordinal=1)
    _write_yaml(object_path, obj)
    output = tmp_path / "katalog.dump"
    build_database(**baseline, data_dir=data_dir, output_path=output)
    with restore_dump(output) as restored:
        dataset = restored.dataset()
        assert [(r.data["id"], r.data.get("cave_id")) for r in dataset.objects] == [
            ("KSW-0001", "C-0002")
        ]
        assert {r.data["id"]: r.data["object_ids"] for r in dataset.caves} == {
            "C-0001": [],
            "C-0002": ["KSW-0001"],
        }
        assert sum(len(r.data["measurements"]) for r in dataset.objects) == 2
        from sql_test_support import read_record

        for r in dataset.caves:
            assert "object_ids" not in read_record(data_dir / f"caves/{r.data['id']}.yml")
        source_object = read_record(data_dir / "objects/KSW/KSW-0001.yml")
        assert source_object["cave_id"] == "C-0002"
        assert source_object["membership_ordinal"] == 1


@pytest.mark.parametrize("variant", ["identical", "coordinates"])
def test_duplicate_local_measurement_id_blocks_dump_before_writes(tmp_path, variant):
    data_dir = tmp_path / "data"
    _write_sample_data(data_dir)
    baseline = accept_source(data_dir)
    output = tmp_path / "output"
    path = output / "katalog.dump"
    build_database(**baseline, data_dir=data_dir, output_path=path)
    before = path.read_bytes()
    source = data_dir / "objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(source.read_text())
    duplicate = deepcopy(obj["measurements"][1])
    if variant == "coordinates":
        duplicate.update(
            lat=49.235,
        )
    obj["measurements"].append(duplicate)
    _write_yaml(source, obj)
    source_before = source.read_bytes()

    for target in (path, tmp_path / "new-output/katalog.dump"):
        with pytest.raises(ValueError, match="measurements_pkey"):
            build_database(**baseline, data_dir=data_dir, output_path=target)
        result = subprocess.run(
            [
                sys.executable,
                str(BUILD_DB_SCRIPT),
                "--data-dir",
                str(data_dir),
                "--output",
                str(target),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1
        assert "measurements_pkey" in result.stdout + result.stderr
        assert str(data_dir) in result.stdout + result.stderr
        assert "Traceback" not in result.stdout + result.stderr
    assert path.read_bytes() == before
    assert set(output.iterdir()) == {path}
    assert not (tmp_path / "new-output").exists()
    assert source.read_bytes() == source_before


def test_build_database_writes_logical_tables_and_metadata(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    dump_path = tmp_path / "build" / "katalog.dump"
    _write_sample_data(data_dir)
    baseline = accept_source(data_dir)

    result = build_database(
        **baseline,
        data_dir=data_dir,
        output_path=dump_path,
        generated_at=GENERATED_AT,
    )

    assert result.dump_path == dump_path
    assert dump_path.read_bytes().startswith(b"PGDMP")
    assert result.metadata["generated_at"] == GENERATED_AT
    assert result.metadata["object_count"] == "1"
    assert result.metadata["cave_count"] == "1"
    assert result.metadata["measurement_count"] == "2"
    assert result.metadata["validation_error_count"] == "0"
    with restore_dump(dump_path) as restored:
        tables = set(restored.fingerprints())
        assert tables >= {
            "objects",
            "caves",
            "measurements",
            "object_external_refs",
            "cave_external_refs",
            "attachments",
            "relations",
            "best_policy",
            "publications",
            "v_best",
            "v_auto_best",
        }
        dataset = restored.dataset()
        obj = dataset.objects[0].data
        assert obj["best_measurement"]["mode"] == "auto"
        assert (
            obj["best_measurement"]["measurement_id"]
            == obj["computed_best_measurement_id"]
            == "m-002"
        )
        assert [m["id"] for m in obj["measurements"]] == ["m-001", "m-002"]
        assert obj["measurements"][1]["source"] == "TPN"
        assert (obj["measurements"][1]["lon"], obj["measurements"][1]["lat"]) == (KSW_LON, KSW_LAT)
        projected = wgs84_to_1992(lat=KSW_LAT, lon=KSW_LON)
        assert obj["measurements"][1]["x_1992"] == pytest.approx(projected.x_1992, abs=0.005)
        assert obj["measurements"][1]["y_1992"] == pytest.approx(projected.y_1992, abs=0.005)
        assert dataset.caves[0].data["external_refs"][0]["external_id"] == "1094"
        assert obj["external_refs"][0]["external_id"] == "{38626571-CAA6-4317-8900-D61A995020E9}"


def test_build_db_cli_creates_dump(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    dump_path = tmp_path / "build" / "katalog.dump"
    _write_sample_data(data_dir)
    baseline = accept_source(data_dir)

    result = subprocess.run(
        [
            sys.executable,
            str(BUILD_DB_SCRIPT),
            "--data-dir",
            str(data_dir),
            "--output",
            str(dump_path),
            "--generated-at",
            GENERATED_AT,
            *cli_args(baseline),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert dump_path.exists()
    assert "PostgreSQL dump build: 1 objects, 1 caves, 2 measurements" in result.stdout


def test_build_database_rejects_invalid_yaml(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    dump_path = tmp_path / "build" / "katalog.dump"
    _write_sample_data(data_dir)
    baseline = accept_source(data_dir)
    object_data = _valid_object()
    object_data["best_measurement"].update(
        mode="manual", measurement_id="m-999", reason="Invalid manual selection"
    )
    _write_yaml(data_dir / "objects" / "KSW" / "KSW-0001.yml", object_data)
    _write_yaml(data_dir / "caves" / "C-0001.yml", _valid_cave())

    with pytest.raises(ValueError, match="best_policy_object_id_manual_measurement_id_fkey"):
        build_database(
            **baseline,
            data_dir=data_dir,
            output_path=dump_path,
            generated_at=GENERATED_AT,
        )

    from gps_kataster_obiektow_tatr.validator import validate_data_dir

    assert "BEST_MEASUREMENT_MISSING" in {issue.code for issue in validate_data_dir(data_dir)}
    assert not dump_path.exists()
