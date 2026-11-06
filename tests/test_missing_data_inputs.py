import subprocess
import sys
from pathlib import Path

import pytest
from export_test_support import accept_source, cli_args, write_sample_data

from gps_kataster_obiektow_tatr import data_loader
from gps_kataster_obiektow_tatr.best_measurements_export import export_best_measurements
from gps_kataster_obiektow_tatr.build_db import build_database
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts
from gps_kataster_obiektow_tatr.validator import ValidationSeverity, validate_data_dir

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_CASES = (
    "missing-root",
    "file-root",
    "missing-objects",
    "missing-caves",
    "missing-relations",
    "file-objects",
    "file-caves",
    "file-relations",
    "missing-publications",
    "file-publications",
)


@pytest.fixture(params=INPUT_CASES)
def invalid_input(request, tmp_path, make_canonical_data_dir):
    data_dir = tmp_path / "invalid-data"
    case = request.param
    if case == "missing-root":
        return data_dir, data_dir
    if case == "file-root":
        data_dir.write_text("not a directory", encoding="utf-8")
        return data_dir, data_dir
    make_canonical_data_dir(data_dir)
    kind, name = case.split("-", maxsplit=1)
    bad_path = data_dir / name
    bad_path.rmdir()
    if kind == "file":
        bad_path.write_text("not a directory", encoding="utf-8")
    return data_dir, bad_path


def test_loader_rejects_incomplete_input(invalid_input):
    data_dir, bad_path = invalid_input
    with pytest.raises(ValueError) as error:
        data_loader.load_yaml_dataset(data_dir)
    root_missing = bad_path == data_dir
    assert type(error.value).__name__ == (
        "YamlDataLoadError" if root_missing else "DataDirectoryError"
    )
    assert error.value.path == (data_dir / "catalog.json" if root_missing else bad_path)
    assert str(bad_path) in str(error.value)


def test_validator_reports_input_path(invalid_input):
    data_dir, bad_path = invalid_input
    issues = validate_data_dir(data_dir)
    assert len(issues) == 1
    root_missing = bad_path == data_dir
    assert issues[0].code == ("SQL_CATALOG_INVALID" if root_missing else "DATA_DIRECTORY_INVALID")
    assert issues[0].severity == ValidationSeverity.ERROR
    assert issues[0].path == (data_dir / "catalog.json" if root_missing else bad_path)
    assert str(bad_path) in issues[0].description


@pytest.mark.parametrize("operation", ["dump", "export", "release", "validate"])
@pytest.mark.parametrize("interface", ["api", "cli"])
@pytest.mark.parametrize("existing", [False, True], ids=["new-output", "existing-release"])
def test_invalid_input_preserves_outputs(
    invalid_input, tmp_path, make_data_dir, operation, interface, existing
):
    data_dir, bad_path = invalid_input
    output_root = tmp_path / "output"
    dump_path = output_root / "katalog.dump"
    output_dir = output_root / "exports"
    if existing:
        # Build a real nonempty release, so R1 cannot replace it with empty artifacts.
        good_data = write_sample_data(tmp_path / "good-data")
        baseline = accept_source(good_data)
        release = build_release_artifacts(
            **baseline,
            data_dir=good_data,
            output_dir=output_dir,
            generated_at="2026-10-15T00:00:00Z",
        )
        assert release.export_result.feature_count == 1
        assert release.export_result.metadata["counts"]["measurements"] == 2
    before = _snapshot(output_root)
    assert len(before) == (13 if existing else 0)
    if interface == "api":
        if operation == "validate":
            assert any(issue.severity == "error" for issue in validate_data_dir(data_dir))
        else:
            with pytest.raises(ValueError) as error:
                if operation == "dump":
                    build_database(data_dir=data_dir, output_path=dump_path)
                elif operation == "export":
                    export_best_measurements(data_dir=data_dir, output_dir=output_dir)
                else:
                    build_release_artifacts(data_dir=data_dir, output_dir=output_dir)
            assert type(error.value).__name__ == "DataDirectoryError"
            assert str(bad_path) in str(error.value)
    else:
        result = subprocess.run(
            _command(operation, data_dir, dump_path, output_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1, result.stdout + result.stderr
        assert str(bad_path) in result.stdout + result.stderr
        assert "Traceback" not in result.stdout + result.stderr
    assert _snapshot(output_root) == before
    if not existing:
        assert not output_root.exists()


@pytest.mark.parametrize("interface", ["api", "cli"])
def test_explicit_empty_dataset_is_valid(tmp_path, make_canonical_data_dir, interface):
    data_dir = make_canonical_data_dir(tmp_path / "data")
    baseline = accept_source(data_dir)
    assert data_loader.load_yaml_dataset(data_dir).records() == ()
    assert validate_data_dir(data_dir) == ()
    dump_path = tmp_path / "output" / "katalog.dump"
    output_dir = tmp_path / "output" / "exports"
    if interface == "api":
        result = build_release_artifacts(**baseline, data_dir=data_dir, output_dir=output_dir)
        assert result.export_result.feature_count == 0
        assert len(result.artifact_paths) == 13
    else:
        for operation in ("validate", "dump", "export", "release"):
            command = _command(operation, data_dir, dump_path, output_dir)
            command += cli_args(baseline)
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, result.stdout + result.stderr
    assert not dump_path.is_file() if interface == "api" else dump_path.is_file()
    assert len(tuple(output_dir.iterdir())) == 13


def _snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _command(operation, data_dir, dump_path, output_dir):
    scripts = {
        "validate": ("validate.py", []),
        "dump": ("build_db.py", ["--output", str(dump_path)]),
        "export": ("export_best_measurements.py", ["--output-dir", str(output_dir)]),
        "release": (
            "build_release_artifacts.py",
            ["--output-dir", str(output_dir)],
        ),
    }
    name, options = scripts[operation]
    return [
        sys.executable,
        str(REPO_ROOT / "scripts" / name),
        "--data-dir",
        str(data_dir),
        *options,
    ]
