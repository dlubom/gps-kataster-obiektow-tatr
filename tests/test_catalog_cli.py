"""CLI channel policies are intentionally different; helpers must preserve them."""

import subprocess
import sys

import pytest
from export_test_support import REPO_ROOT, accept_source, cli_args, write_sample_data


@pytest.mark.parametrize(
    "script", ["validate", "build_db", "export_best_measurements", "build_release_artifacts"]
)
@pytest.mark.parametrize("damage", ["missing-directory", "missing-baseline"])
def test_catalog_cli_preserves_error_channels_and_output(tmp_path, script, damage):
    data = write_sample_data(tmp_path / "data")
    baseline = accept_source(data)
    if damage == "missing-directory":
        (data / "publications/.gitkeep").unlink()
        (data / "publications").rmdir()
        code = "DATA_DIRECTORY_INVALID"
    else:
        baseline["base_ref"] = "unavailable-ref"
        code = "HISTORY_BASELINE_UNAVAILABLE"
    output = tmp_path / "exports"
    output.mkdir()
    (output / "katalog.dump").write_bytes(b"accepted full release")
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
            str(output / "katalog.dump" if script == "build_db" else output),
        ]
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    assert result.returncode == 1
    stdout_policy = script == "validate" or (
        damage == "missing-baseline" and script != "export_best_measurements"
    )
    diagnostic, empty = (
        (result.stdout, result.stderr) if stdout_policy else (result.stderr, result.stdout)
    )
    assert empty == ""
    if stdout_policy:
        assert f"{code}\terror\t" in diagnostic
    else:
        assert diagnostic.startswith("error: ")
        assert ("required data directory" if damage == "missing-directory" else code) in diagnostic
    assert "full release artifacts" not in diagnostic  # Input validation precedes Best protection.
    assert "Traceback" not in diagnostic
    assert {p.name: p.read_bytes() for p in output.iterdir()} == {
        "katalog.dump": b"accepted full release"
    }
