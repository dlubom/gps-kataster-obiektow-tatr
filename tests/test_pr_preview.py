import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import yaml
from export_test_support import accept_source
from export_test_support import write_sample_data as _write_sample_data

from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_pr_preview.py"
HEAD, BASE, MERGE = "a" * 40, "b" * 40, "c" * 40
STAMP = "2026-10-21T18:00:00Z"


def _build(data_dir: Path, output: Path, baseline) -> subprocess.CompletedProcess[str]:
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
            baseline["base_ref"],
            "--merge-sha",
            MERGE,
            "--run-id",
            "123",
            "--run-attempt",
            "2",
            "--generated-at",
            STAMP,
            "--history-repo",
            str(baseline["history_repo"]),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )


def test_preview_contains_exact_release_exports_with_provenance_and_checksums(tmp_path):
    data = tmp_path / "data"
    _write_sample_data(data)
    baseline = accept_source(data)
    before = {p.relative_to(data): p.read_bytes() for p in data.rglob("*.yml")}
    output = tmp_path / "preview"
    result = _build(data, output, baseline)
    assert result.returncode == 0, result.stdout + result.stderr

    release = build_release_artifacts(
        **baseline,
        data_dir=data,
        output_dir=tmp_path / "release",
        generated_at=STAMP,
        source_commit=MERGE,
    )
    expected = {p.name: p for p in release.artifact_paths}
    assert set(p.name for p in output.iterdir()) == set(expected) | {"preview.json", "SHA256SUMS"}
    assert len(expected) == 13
    assert {
        "best-measurements.gpx",
        "chocholowska-lejowa-koscieliska.gpx",
        "mietusia-sucha-woda.gpx",
        "pozostale-pl-sk.gpx",
    } <= set(expected)
    for name, path in expected.items():
        if name.endswith((".zip", ".xlsx")):
            with zipfile.ZipFile(path) as left, zipfile.ZipFile(output / name) as right:
                assert right.namelist() == left.namelist()
                assert all(right.read(n) == left.read(n) for n in left.namelist())
        elif name == "katalog.dump":
            from gps_kataster_obiektow_tatr.postgres import restore_dump

            with restore_dump(path) as left, restore_dump(output / name) as right:
                assert left.fingerprints() == right.fingerprints()
        elif name == "katalog.gpkg":
            import sqlite3

            with sqlite3.connect(path) as left, sqlite3.connect(output / name) as right:
                for layer in ("best", "measurements"):
                    assert (
                        left.execute(f"SELECT * FROM {layer}").fetchall()
                        == right.execute(f"SELECT * FROM {layer}").fetchall()
                    )
        else:
            assert (output / name).read_bytes() == path.read_bytes()
    manifest = json.loads((output / "preview.json").read_text())
    assert manifest == {
        "repository": "example/catalog",
        "pr_number": 7,
        "head_sha": HEAD,
        "base_sha": baseline["base_ref"],
        "merge_sha": MERGE,
        "run_id": 123,
        "run_attempt": 2,
        "generated_at": STAMP,
        "kind": "pr-preview",
    }
    checksums = (output / "SHA256SUMS").read_text().splitlines()
    assert len(checksums) == 14
    assert {line.split("  ")[1] for line in checksums} == set(expected) | {"preview.json"}
    for line in checksums:
        digest, name = line.split("  ")
        assert digest == hashlib.sha256((output / name).read_bytes()).hexdigest()
    assert before == {p.relative_to(data): p.read_bytes() for p in data.rglob("*.yml")}


def test_preview_refuses_existing_output_without_changing_it(tmp_path):
    data, output = tmp_path / "data", tmp_path / "preview"
    _write_sample_data(data)
    baseline = accept_source(data)
    output.mkdir()
    (output / "old.zip").write_bytes(b"previous result")
    result = _build(data, output, baseline)
    assert result.returncode != 0
    assert "already exists" in result.stderr
    assert list(output.iterdir()) == [output / "old.zip"]
    assert (output / "old.zip").read_bytes() == b"previous result"


def test_invalid_input_does_not_publish_partial_preview(tmp_path):
    output = tmp_path / "preview"
    result = _build(tmp_path / "missing", output, {"base_ref": BASE, "history_repo": tmp_path})
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
    assert all(not s.get("uses", "").startswith("./") for s in trusted_steps)
    assert all("secrets" not in s and "permissions" not in s for s in steps)


def test_node_publisher_suite():
    result = subprocess.run(
        ["node", "--test", "tests/test_pr_preview_publisher.cjs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("workflow", "job", "events", "cache", "node"),
    [
        (
            "validate",
            "validate",
            {"pull_request": None, "push": {"branches": ["main"]}},
            "true",
            True,
        ),
        (
            "pr-preview",
            "preview",
            {"pull_request": {"types": ["opened", "synchronize", "reopened"]}},
            "false",
            False,
        ),
        ("release", "release", {"push": {"tags": ["v*"]}}, "true", False),
        ("mutation", "mutation", {"workflow_dispatch": None}, "true", True),
    ],
)
def test_shared_ci_setup_keeps_event_gates_and_service_clients(workflow, job, events, cache, node):
    from gps_kataster_obiektow_tatr.postgres import DOCKER_IMAGE

    config = yaml.safe_load((ROOT / f".github/workflows/{workflow}.yml").read_text())
    assert config["on"] == events  # No path filter can leave the required check pending.
    assert config["permissions"] == {"contents": "write" if workflow == "release" else "read"}
    job_config = config["jobs"][job]
    assert "if" not in job_config and "permissions" not in job_config
    if workflow == "validate":
        assert job_config["name"] == "Validate code and data"
    assert job_config["services"]["postgres"]["image"] == DOCKER_IMAGE
    assert job_config["runs-on"] == "ubuntu-24.04"
    steps = job_config["steps"]
    checkout = steps[0]
    assert checkout["uses"] == "actions/checkout@v4"
    assert checkout["with"]["fetch-depth"] == 0
    assert checkout["with"]["persist-credentials"] is False
    (setup,) = [s for s in steps if s.get("uses") == "./.github/actions/setup-runtime"]
    assert setup["with"] == {
        "postgres-port": "${{ job.services.postgres.ports['5432'] }}",
        "postgres-container": "${{ job.services.postgres.id }}",
        "enable-uv-cache": cache,
    }
    assert set(setup) == {"name", "uses", "with"}  # No conditional gate or extra secrets.
    (baseline,) = [s for s in steps if s.get("run") == "python scripts/ci_baseline.py"]
    assert steps.index(checkout) < steps.index(setup) < steps.index(baseline)
    assert all("if" not in s for s in (checkout, baseline))
    node_steps = [s for s in steps if s.get("uses") == "actions/setup-node@v4"]
    assert [s["with"] for s in node_steps] == ([{"node-version": "24.22.2"}] if node else [])
    if workflow in {"validate", "mutation"}:
        (tests,) = [s for s in steps if s.get("run") == "uv run --frozen pytest"]
        assert steps.index(baseline) < steps.index(tests)
    if workflow == "validate":
        (smoke,) = [s for s in steps if s.get("env", {}).get("KATASTER_DOCKER_SMOKE") == "1"]
        assert smoke["run"] == (
            "uv run --frozen pytest -q tests/test_postgres_runtime.py -k real_managed_docker"
        )
        assert "if" not in smoke
    if workflow in {"validate", "release"}:
        assert any(
            s.get("run")
            == 'uv run --frozen python scripts/validate.py --base-ref "$HISTORY_BASE_SHA"'
            for s in steps
        )
    if workflow == "pr-preview":
        (build,) = [s for s in steps if "scripts/build_pr_preview.py" in s.get("run", "")]
        assert '--base-sha "$PR_BASE_SHA"' in build["run"]
        assert steps.index(baseline) < steps.index(build)
    if workflow == "release":
        (build,) = [s for s in steps if "scripts/build_release_artifacts.py" in s.get("run", "")]
        assert '--base-ref "$HISTORY_BASE_SHA" --artifact-list' in build["run"]
        assert steps.index(baseline) < steps.index(build)


def test_shared_ci_runtime_keeps_pins_and_frozen_dependencies():
    action = yaml.safe_load((ROOT / ".github/actions/setup-runtime/action.yml").read_text())
    assert action["runs"]["using"] == "composite"
    assert set(action["inputs"]) == {"postgres-port", "postgres-container", "enable-uv-cache"}
    assert action["inputs"]["postgres-port"]["required"] is True
    assert action["inputs"]["postgres-container"]["required"] is True
    assert action["inputs"]["enable-uv-cache"]["default"] == "true"
    steps = action["runs"]["steps"]
    (python,) = [s for s in steps if s.get("uses") == "actions/setup-python@v5"]
    assert python["with"] == {"python-version": "3.12.13"}
    (uv,) = [s for s in steps if s.get("uses") == "astral-sh/setup-uv@v5"]
    assert uv["with"] == {"version": "0.11.8", "enable-cache": "${{ inputs.enable-uv-cache }}"}
    scripts = [s for s in steps if "run" in s]
    assert all(s["shell"] == "bash" and "if" not in s for s in scripts)
    assert any(s["run"].strip() == "uv sync --frozen" for s in scripts)
    assert any("gdal-bin=3.8.4+dfsg-3ubuntu3" in s["run"] for s in scripts)
    assert all("${{" not in s["run"] for s in scripts)  # Inputs enter the shell via env only.
    assert "permissions" not in action


@pytest.mark.parametrize("container", ["pg-service-123", "$(touch executed)"])
def test_ci_setup_exports_matching_clients_without_evaluating_input(tmp_path, container):
    action = yaml.safe_load((ROOT / ".github/actions/setup-runtime/action.yml").read_text())
    (step,) = [s for s in action["runs"]["steps"] if "PG_SERVICE_PORT" in s.get("env", {})]
    assert step["env"] == {
        "PG_SERVICE_PORT": "${{ inputs.postgres-port }}",
        "PG_SERVICE_CONTAINER": "${{ inputs.postgres-container }}",
    }
    output = tmp_path / "github-env"
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", step["run"]],
        cwd=tmp_path,
        env={
            **os.environ,
            "PG_SERVICE_PORT": "5439",
            "PG_SERVICE_CONTAINER": container,
            "GITHUB_ENV": str(output),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert output.read_text() == (
        "KATASTER_DATABASE_URL=postgresql://postgres:kataster-ci-only@127.0.0.1:5439/postgres\n"
        f"KATASTER_POSTGRES_CONTAINER={container}\n"
    )
    assert not (tmp_path / "executed").exists()
