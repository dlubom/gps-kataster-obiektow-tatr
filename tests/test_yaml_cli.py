"""Malformed YAML must never replace history or generated artifacts."""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992
from gps_kataster_obiektow_tatr.staging_review import StagingReports, apply_review_decisions

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = (
    "katalog.sqlite",
    "best-measurements.geojson",
    "best-measurements.csv",
    "best-measurements.gpx",
    "best-measurements.shp.zip",
    "katalog.sqlite.zip",
    "metadata.json",
)
LINK_DECISION = {"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"}


def _snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _write_dataset(root: Path) -> Path:
    object_path = root / "objects/KSW/KSW-0001.yml"
    object_path.parent.mkdir(parents=True)
    obj = yaml.safe_load((REPO_ROOT / "tests/fixtures/valid-object.yml").read_text())
    measurement = obj["measurements"][0]
    coords = wgs84_to_1992(lat=49.23459299, lon=19.87589498)
    measurement.update(lat=49.23459299, lon=19.87589498, x_1992=coords.x_1992, y_1992=coords.y_1992)
    object_path.write_text(yaml.safe_dump(obj, sort_keys=False), encoding="utf-8")
    cave_path = root / "caves/C-0001.yml"
    cave_path.parent.mkdir()
    cave = yaml.safe_load((REPO_ROOT / "tests/fixtures/valid-cave.yml").read_text())
    cave["object_ids"] = ["KSW-0001"]
    cave_path.write_text(yaml.safe_dump(cave, sort_keys=False), encoding="utf-8")
    return object_path


def _corrupt(path: Path, duplicate: str) -> None:
    content = path.read_text(encoding="utf-8")
    if duplicate == "measurements":
        # Legacy last-wins parsing loses this historical measurement and succeeds.
        content = "measurements: [{id: lost-history}]\n" + content
    else:
        content = content.replace("- id: m-001", "- id: lost-history\n  id: m-001")
    path.write_text(content, encoding="utf-8")


def _run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / script), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("duplicate", ["measurements", "id"])
@pytest.mark.parametrize(
    "command",
    ["validate.py", "build_db.py", "export_best_measurements.py", "build_release_artifacts.py"],
)
@pytest.mark.parametrize("existing_artifacts", [False, True])
def test_cli_duplicate_data_preserves_inputs_and_outputs(
    tmp_path: Path, duplicate: str, command: str, existing_artifacts: bool
) -> None:
    data_dir = tmp_path / "data"
    path = _write_dataset(data_dir)
    _corrupt(path, duplicate)
    before_data = _snapshot(data_dir)
    output_dir = tmp_path / "build"
    if existing_artifacts:
        output_dir.mkdir()
        for name in ARTIFACTS:
            (output_dir / name).write_bytes(f"old artifact: {name}".encode())
    before_output = _snapshot(output_dir)
    args = ["--data-dir", str(data_dir)]
    if command == "build_db.py":
        args += ["--output", str(output_dir / "katalog.sqlite")]
    elif command == "export_best_measurements.py":
        args += ["--output-dir", str(output_dir)]
    elif command == "build_release_artifacts.py":
        args += [
            "--output-dir",
            str(output_dir),
            "--sqlite-output",
            str(output_dir / "katalog.sqlite"),
        ]

    result = _run(command, *args)

    assert result.returncode == 1, result.stdout + result.stderr
    diagnostic = result.stdout + result.stderr
    assert str(path) in diagnostic
    assert f"duplicate key {duplicate!r}" in diagnostic
    assert "line " in diagnostic
    assert "Traceback" not in diagnostic
    assert _snapshot(data_dir) == before_data
    assert _snapshot(output_dir) == before_output


@pytest.mark.parametrize("duplicate", ["measurements", "id"])
@pytest.mark.parametrize("write", [False, True])
def test_review_duplicate_final_data_blocks_entire_batch(
    tmp_path: Path, duplicate: str, write: bool
):
    data_dir = tmp_path / "data"
    path = _write_dataset(data_dir)
    _corrupt(path, duplicate)
    before = _snapshot(data_dir)
    result = apply_review_decisions(
        {"decisions": [LINK_DECISION]},
        staging_reports=StagingReports(),
        data_dir=data_dir,
        write=write,
    )
    assert result.has_errors
    assert result.written_paths == ()
    assert result.applied_decisions == ()
    assert result.issues[0].code == "FINAL_DATA_INVALID"
    assert f"duplicate key {duplicate!r}" in result.issues[0].description
    assert _snapshot(data_dir) == before


@pytest.mark.parametrize("duplicate", ["action", "tagged_action", "measurements"])
def test_review_cli_rejects_duplicate_input_before_writing(tmp_path: Path, duplicate: str):
    data_dir = tmp_path / "data"
    object_path = _write_dataset(data_dir)
    decisions_path = tmp_path / "decisions.yml"
    # Separate dicts prevent safe_dump from producing aliases in a valid control.
    content = yaml.safe_dump(
        {"decisions": [dict(LINK_DECISION), dict(LINK_DECISION)]}, sort_keys=False
    )
    if duplicate in {"action", "tagged_action"}:
        replacement = (
            "- action: reject\n  action: link_cave"
            if duplicate == "action"
            else "- action: !!str {=: link_cave, action: reject, action: create_object}"
        )
        content = content.replace("- action: link_cave", replacement, 1)
        invalid_path = decisions_path
    else:
        _corrupt(object_path, duplicate)
        invalid_path = object_path
    decisions_path.write_text(content, encoding="utf-8")
    before = _snapshot(data_dir)
    review_dir = tmp_path / "review"
    result = _run(
        "importers/apply_review.py",
        "--data-dir",
        str(data_dir),
        "--decisions",
        str(decisions_path),
        "--no-pig-staging",
        "--no-tpn-staging",
        "--output-dir",
        str(review_dir),
    )
    assert result.returncode == 1
    diagnostic = result.stdout + result.stderr
    if duplicate == "measurements":
        diagnostic += (review_dir / "staging-review.json").read_text(encoding="utf-8")
    assert str(invalid_path) in diagnostic
    if duplicate == "tagged_action":
        assert "scalar-tagged mappings are not supported" in diagnostic
    else:
        assert f"duplicate key {duplicate!r}" in diagnostic
    assert "Traceback" not in diagnostic
    assert _snapshot(data_dir) == before
    if duplicate in {"action", "tagged_action"}:
        assert not review_dir.exists()


def test_valid_yaml_still_builds_all_artifacts_and_accepts_review(tmp_path: Path):
    data_dir = tmp_path / "data"
    _write_dataset(data_dir)
    result = apply_review_decisions(
        {"decisions": [LINK_DECISION]}, staging_reports=StagingReports(), data_dir=data_dir
    )
    assert not result.has_errors
    assert len(result.written_paths) == 2
    output_dir = tmp_path / "build"
    result = _run(
        "build_release_artifacts.py",
        "--data-dir",
        str(data_dir),
        "--output-dir",
        str(output_dir),
        "--sqlite-output",
        str(output_dir / "katalog.sqlite"),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert set(_snapshot(output_dir)) == set(ARTIFACTS)
