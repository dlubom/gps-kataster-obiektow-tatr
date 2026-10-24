import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from gps_kataster_obiektow_tatr import data_loader
from gps_kataster_obiektow_tatr.best_measurements_export import export_best_measurements
from gps_kataster_obiektow_tatr.build_db import build_sqlite_database
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
)


@pytest.fixture(params=INPUT_CASES)
def invalid_input(request, tmp_path, make_data_dir):
    data_dir = tmp_path / "invalid-data"
    case = request.param
    if case == "missing-root":
        return data_dir, data_dir
    if case == "file-root":
        data_dir.write_text("not a directory", encoding="utf-8")
        return data_dir, data_dir
    make_data_dir(data_dir)
    kind, name = case.split("-", maxsplit=1)
    bad_path = data_dir / name
    bad_path.rmdir()
    if kind == "file":
        bad_path.write_text("not a directory", encoding="utf-8")
    return data_dir, bad_path


def test_loader_rejects_incomplete_input(invalid_input):
    data_dir, bad_path = invalid_input
    with pytest.raises(ValueError) as error:
        data_loader.load_dataset(data_dir)
    assert type(error.value).__name__ == "DataDirectoryError"
    assert error.value.path == bad_path
    assert str(bad_path) in str(error.value)


def test_validator_reports_input_path(invalid_input):
    data_dir, bad_path = invalid_input
    issues = validate_data_dir(data_dir)
    assert len(issues) == 1
    assert issues[0].code == "DATA_DIRECTORY_INVALID"
    assert issues[0].severity == ValidationSeverity.ERROR
    assert issues[0].path == bad_path
    assert str(bad_path) in issues[0].description


@pytest.mark.parametrize("operation", ["sqlite", "export", "release", "validate"])
@pytest.mark.parametrize("interface", ["api", "cli"])
@pytest.mark.parametrize("existing", [False, True], ids=["new-output", "existing-release"])
def test_invalid_input_preserves_outputs(
    invalid_input, tmp_path, make_data_dir, operation, interface, existing
):
    data_dir, bad_path = invalid_input
    output_root = tmp_path / "output"
    sqlite_path = output_root / "katalog.sqlite"
    output_dir = output_root / "exports"
    if existing:
        # Build a real nonempty release, so R1 cannot replace it with empty artifacts.
        good_data = make_data_dir(tmp_path / "good-data")
        (good_data / "objects" / "KSW").mkdir()
        (good_data / "objects" / "KSW" / "KSW-0001.yml").write_bytes(
            (REPO_ROOT / "data/objects/KSW/KSW-0001.yml").read_bytes()
        )
        cave = yaml.safe_load((REPO_ROOT / "data/caves/C-0002.yml").read_text(encoding="utf-8"))
        cave["object_ids"] = ["KSW-0001"]
        (good_data / "caves" / "C-0002.yml").write_text(yaml.safe_dump(cave), encoding="utf-8")
        release = build_release_artifacts(
            data_dir=good_data,
            sqlite_path=sqlite_path,
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
                if operation == "sqlite":
                    build_sqlite_database(data_dir=data_dir, output_path=sqlite_path)
                elif operation == "export":
                    export_best_measurements(data_dir=data_dir, output_dir=output_dir)
                else:
                    build_release_artifacts(
                        data_dir=data_dir, sqlite_path=sqlite_path, output_dir=output_dir
                    )
            assert type(error.value).__name__ == "DataDirectoryError"
            assert str(bad_path) in str(error.value)
    else:
        result = subprocess.run(
            _command(operation, data_dir, sqlite_path, output_dir),
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


@pytest.mark.parametrize("operation", ["tpn", "review"])
def test_import_cli_reports_invalid_data_directory(invalid_input, tmp_path, operation):
    data_dir, bad_path = invalid_input
    output_dir = tmp_path / "reports"
    if operation == "tpn":
        source_path = tmp_path / "source.csv"
        source_path.write_text("GLOBALID,NAZWA\n", encoding="utf-8")
        command = [
            "import_tpn.py",
            "--tpn-source",
            str(source_path),
            "--no-pig-staging",
        ]
    else:
        decisions_path = tmp_path / "decisions.yml"
        decisions_path.write_text("decisions: []\n", encoding="utf-8")
        command = [
            "apply_review.py",
            "--decisions",
            str(decisions_path),
            "--no-pig-staging",
            "--no-tpn-staging",
        ]
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/importers" / command[0]),
            *command[1:],
            "--data-dir",
            str(data_dir),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert str(bad_path) in result.stderr
    assert "Traceback" not in result.stderr
    assert not output_dir.exists()


@pytest.mark.parametrize("interface", ["api", "cli"])
def test_explicit_empty_dataset_is_valid(tmp_path, make_data_dir, interface):
    data_dir = make_data_dir(tmp_path / "empty-data")
    assert data_loader.load_dataset(data_dir).records() == ()
    assert validate_data_dir(data_dir) == ()
    sqlite_path = tmp_path / "output" / "katalog.sqlite"
    output_dir = tmp_path / "output" / "exports"
    if interface == "api":
        result = build_release_artifacts(
            data_dir=data_dir, sqlite_path=sqlite_path, output_dir=output_dir
        )
        assert result.export_result.feature_count == 0
        assert len(result.artifact_paths) == 13
    else:
        for operation in ("validate", "sqlite", "export", "release"):
            result = subprocess.run(
                _command(operation, data_dir, sqlite_path, output_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, result.stdout + result.stderr
    assert sqlite_path.is_file()
    assert len(tuple(output_dir.iterdir())) == 12


def _snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _command(operation, data_dir, sqlite_path, output_dir):
    scripts = {
        "validate": ("validate.py", []),
        "sqlite": ("build_db.py", ["--output", str(sqlite_path)]),
        "export": ("export_best_measurements.py", ["--output-dir", str(output_dir)]),
        "release": (
            "build_release_artifacts.py",
            ["--sqlite-output", str(sqlite_path), "--output-dir", str(output_dir)],
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
