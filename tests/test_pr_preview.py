import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import yaml
from test_release_artifacts import _write_sample_data

from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_pr_preview.py"
HEAD, BASE, MERGE = "a" * 40, "b" * 40, "c" * 40
STAMP = "2026-10-21T18:00:00Z"


def _build(data_dir: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--data-dir",
            str(data_dir),
            "--output-dir",
            str(output),
            "--repository",
            "example/catalog",
            "--pr-number",
            "7",
            "--head-sha",
            HEAD,
            "--base-sha",
            BASE,
            "--merge-sha",
            MERGE,
            "--run-id",
            "123",
            "--run-attempt",
            "2",
            "--generated-at",
            STAMP,
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )


def test_preview_contains_exact_release_exports_with_provenance_and_checksums(tmp_path):
    data = tmp_path / "data"
    _write_sample_data(data)
    before = {p.relative_to(data): p.read_bytes() for p in data.rglob("*.yml")}
    output = tmp_path / "preview"
    result = _build(data, output)
    assert result.returncode == 0, result.stdout + result.stderr

    release = build_release_artifacts(
        data_dir=data,
        sqlite_path=tmp_path / "release.sqlite",
        output_dir=tmp_path / "release",
        generated_at=STAMP,
        source_commit=MERGE,
    )
    expected = {p.name: p for p in release.artifact_paths if p != release.sqlite_result.sqlite_path}
    assert set(p.name for p in output.iterdir()) == set(expected) | {"preview.json", "SHA256SUMS"}
    assert len(expected) == 12
    assert {
        "best-measurements.gpx",
        "chocholowska-lejowa-koscieliska.gpx",
        "mietusia-sucha-woda.gpx",
        "pozostale-pl-sk.gpx",
    } <= set(expected)
    for name, path in expected.items():
        if name.endswith((".zip", ".xlsx")):
            with zipfile.ZipFile(path) as left, zipfile.ZipFile(output / name) as right:
                # SQLite name is fixed in the production preview and the normal release.
                if name == "katalog.sqlite.zip":
                    assert right.namelist() == ["katalog.sqlite"]
                    assert right.read("katalog.sqlite") == left.read(left.namelist()[0])
                else:
                    assert right.namelist() == left.namelist()
                    assert all(right.read(n) == left.read(n) for n in left.namelist())
        else:
            assert (output / name).read_bytes() == path.read_bytes()
    manifest = json.loads((output / "preview.json").read_text())
    assert manifest == {
        "repository": "example/catalog",
        "pr_number": 7,
        "head_sha": HEAD,
        "base_sha": BASE,
        "merge_sha": MERGE,
        "run_id": 123,
        "run_attempt": 2,
        "generated_at": STAMP,
        "kind": "pr-preview",
    }
    checksums = (output / "SHA256SUMS").read_text().splitlines()
    assert len(checksums) == 13
    assert {line.split("  ")[1] for line in checksums} == set(expected) | {"preview.json"}
    for line in checksums:
        digest, name = line.split("  ")
        assert digest == hashlib.sha256((output / name).read_bytes()).hexdigest()
    assert before == {p.relative_to(data): p.read_bytes() for p in data.rglob("*.yml")}


def test_preview_refuses_existing_output_without_changing_it(tmp_path):
    data, output = tmp_path / "data", tmp_path / "preview"
    _write_sample_data(data)
    output.mkdir()
    (output / "old.zip").write_bytes(b"previous result")
    result = _build(data, output)
    assert result.returncode != 0
    assert "already exists" in result.stderr
    assert list(output.iterdir()) == [output / "old.zip"]
    assert (output / "old.zip").read_bytes() == b"previous result"


def test_invalid_input_does_not_publish_partial_preview(tmp_path):
    output = tmp_path / "preview"
    result = _build(tmp_path / "missing", output)
    assert result.returncode != 0
    assert not output.exists()


def test_preview_workflows_keep_write_token_out_of_pr_code():
    build = yaml.safe_load((ROOT / ".github/workflows/pr-preview.yml").read_text())
    publish = yaml.safe_load((ROOT / ".github/workflows/publish-pr-preview.yml").read_text())
    assert set(build["on"]) == {"pull_request"}
    assert build["run-name"] == "PR export preview #${{ github.event.pull_request.number }}"
    assert build["on"]["pull_request"]["types"] == ["opened", "synchronize", "reopened"]
    assert build["permissions"] == {"contents": "read"}
    steps = build["jobs"]["preview"]["steps"]
    assert steps[0]["with"]["ref"] == "${{ github.sha }}"
    upload = next(s for s in steps if s.get("uses", "").startswith("actions/upload-artifact@"))
    assert upload["with"]["retention-days"] == 14
    assert upload["with"]["if-no-files-found"] == "error"
    assert "run_attempt" in upload["with"]["name"]
    assert set(publish["on"]) == {"workflow_run"}
    assert publish["concurrency"].get("queue") == "max"
    assert publish["concurrency"]["group"] == (
        "pr-preview-comment-${{ github.event.workflow_run.head_repository.id }}-"
        "${{ github.event.workflow_run.display_title }}"
    )
    assert publish["on"]["workflow_run"]["workflows"] == [build["name"]]
    assert publish["permissions"] == {
        "contents": "read",
        "actions": "read",
        "pull-requests": "write",
    }
    trusted_steps = publish["jobs"]["comment"]["steps"]
    assert trusted_steps[0]["with"]["ref"] == "${{ github.sha }}"
    assert "download-artifact" not in str(trusted_steps)
    assert "uv " not in str(trusted_steps)


def test_node_publisher_suite():
    result = subprocess.run(
        ["node", "--test", "tests/test_pr_preview_publisher.cjs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
