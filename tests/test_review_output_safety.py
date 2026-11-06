"""Public export commands must never exchange source or unrelated directories."""

import subprocess
import sys

import pytest
from export_test_support import REPO_ROOT, cli_args, source


def snapshot(root):
    return {
        str(p.relative_to(root)): ("link", str(p.readlink())) if p.is_symlink() else p.read_bytes()
        for p in root.rglob("*")
        if p.is_symlink() or p.is_file()
    }


@pytest.mark.parametrize("script", ["export_best_measurements", "build_release_artifacts"])
@pytest.mark.parametrize("destination", ["data", "child", "parent", "git", "git-child", "alias"])
def test_export_cli_rejects_source_and_repository_destinations(tmp_path, script, destination):
    data, baseline = source(tmp_path)
    output = {
        "data": data,
        "child": data / "new-exports",
        "parent": tmp_path,
        "git": baseline["history_repo"],
        "git-child": baseline["history_repo"] / ".git" / "exports",
        "alias": tmp_path / "alias" / "exports",
    }[destination]
    if destination == "alias":
        (tmp_path / "alias").symlink_to(data, target_is_directory=True)
    before = snapshot(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / f"scripts/{script}.py"),
            "--data-dir",
            str(data),
            *cli_args(baseline),
            "--output-dir",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Artifact destination overlaps" in result.stderr
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("script", ["export_best_measurements", "build_release_artifacts"])
@pytest.mark.parametrize("foreign", ["file", "directory", "symlink"])
def test_export_cli_preserves_unmanaged_output_entries(tmp_path, script, foreign):
    data, baseline = source(tmp_path)
    output = tmp_path / "exports"
    output.mkdir()
    (output / "best-measurements.csv").write_bytes(b"accepted export")
    if foreign == "file":
        (output / "operator-notes.txt").write_bytes(b"operator's notes")
    elif foreign == "directory":
        (output / "photos").mkdir()
        (output / "photos/keep.txt").write_bytes(b"keep")
    else:
        (output / "best-measurements.gpx").symlink_to(data / "catalog.json")
    before = snapshot(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / f"scripts/{script}.py"),
            "--data-dir",
            str(data),
            *cli_args(baseline),
            "--output-dir",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "unmanaged" in result.stderr
    assert snapshot(tmp_path) == before
