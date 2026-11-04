"""Check that artifact verification catches changes outside the primary CSV."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_catalog_artifacts.py"


def verify(data_dir: Path, artifact_dir: Path, baseline: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--data-dir",
            str(data_dir),
            "--sqlite-path",
            str(artifact_dir / "katalog.sqlite"),
            "--exports-dir",
            str(artifact_dir / "exports"),
            "--baseline-dir",
            str(baseline),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_verifier_reads_all_formats_and_rejects_differences(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    for name in ("objects", "caves", "relations"):
        (data_dir / name).mkdir(parents=True)
    baseline = tmp_path / "baseline"
    build_release_artifacts(
        data_dir=data_dir,
        sqlite_path=baseline / "katalog.sqlite",
        output_dir=baseline / "exports",
        generated_at="2026-11-04T00:00:00Z",
    )
    candidate = tmp_path / "candidate"
    shutil.copytree(baseline, candidate)

    result = verify(data_dir, candidate, baseline)
    assert result.returncode == 0, result.stderr

    markdown = candidate / "exports/statistics.md"
    original = markdown.read_text(encoding="utf-8")
    markdown.write_text(original + "\nUnexpected change.\n", encoding="utf-8")
    result = verify(data_dir, candidate, baseline)
    assert result.returncode == 1
    assert "baseline statistics.md differs" in result.stderr

    markdown.write_text(original, encoding="utf-8")
    with ZipFile(candidate / "exports/katalog.sqlite.zip", "w") as archive:
        archive.writestr("katalog.sqlite", b"unexpected database")
    result = verify(data_dir, candidate, baseline)
    assert result.returncode == 1
    assert "SQLite ZIP payload differs" in result.stderr
