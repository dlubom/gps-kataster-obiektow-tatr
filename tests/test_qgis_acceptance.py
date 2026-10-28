import hashlib
import importlib.util
import json
import os
import subprocess
import zipfile
from pathlib import Path

import pytest
import test_qgis_export
import yaml
from test_qgis_export import build

qgis_inputs = test_qgis_export.qgis_inputs

ROOT = Path(__file__).resolve().parents[1]


def verifier():
    spec = importlib.util.spec_from_file_location(
        "qgis_acceptance", ROOT / "scripts/verify_qgis_package.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "mutation", [None, "omitted", "coordinate", "best", "notes", "jktz", "path", "macro"]
)
def test_offline_acceptance_compares_actual_package_with_independent_sources(
    qgis_inputs, tmp_path, mutation
):
    package = tmp_path / "qgis.zip"
    members = build(qgis_inputs, package)
    manifest = json.loads(members["manifest.json"])
    if mutation in {"omitted", "coordinate", "best", "notes"}:
        name = "points/full.geojson" if mutation != "best" else "points/best.geojson"
        data = json.loads(members[name])
        if mutation == "omitted":
            data["features"].pop()
        elif mutation == "coordinate":
            data["features"][0]["geometry"]["coordinates"].reverse()
        elif mutation == "best":
            data["features"][0]["properties"]["measurement_id"] = "m-002"
        else:
            data["features"][0]["properties"]["notes"] = "Changed"
        members[name] = json.dumps(data).encode()
    elif mutation == "jktz":
        members["jktz/Alpha.shp"] += b"changed"
    elif mutation == "path":
        members["kataster.qgs"] = members["kataster.qgs"].replace(
            b"./points/best.geojson", b"/tmp/best.geojson"
        )
    elif mutation == "macro":
        members["kataster.qgs"] = members["kataster.qgs"].replace(
            b"</qgis>", b"<pythonCode>bad()</pythonCode></qgis>"
        )
    # Recompute hashes so mutations exercise source comparison, not just ZIP integrity.
    manifest["sha256"] = {
        n: hashlib.sha256(b).hexdigest() for n, b in members.items() if n != "manifest.json"
    }
    members["manifest.json"] = json.dumps(manifest).encode()
    with zipfile.ZipFile(package, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    sqlite_zip = tmp_path / "sqlite.zip"
    with zipfile.ZipFile(sqlite_zip, "w") as archive:
        archive.write(qgis_inputs["sqlite_path"], "katalog.sqlite")
    args = (package, sqlite_zip, qgis_inputs["jktz_source_dir"], tmp_path / "relocated")
    if mutation:
        with pytest.raises(ValueError):
            verifier().verify_sources(*args)
    else:
        result = verifier().verify_sources(*args)
        assert result["counts"]["full"] == 4
        assert (tmp_path / "relocated/kataster.qgs").is_file()


@pytest.mark.parametrize("fail_first", [False, True])
def test_container_gate_runs_both_pinned_versions_offline_and_propagates_failure(
    tmp_path, fail_first
):
    binary = tmp_path / "bin"
    binary.mkdir()
    log = tmp_path / "calls.jsonl"
    stub = binary / "docker"
    stub.write_text(
        "#!/usr/bin/env python3\nimport json,os,sys\nfrom pathlib import Path\n"
        "p=Path(os.environ['CALL_LOG'])\n"
        "with p.open('a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')\n"
        "if sys.argv[1]=='run' and os.environ['FAIL_FIRST']=='1': sys.exit(7)\n"
    )
    stub.chmod(0o755)
    package, sqlite_zip, source = tmp_path / "qgis.zip", tmp_path / "sqlite.zip", tmp_path / "jktz"
    package.touch()
    sqlite_zip.touch()
    source.mkdir()
    result = subprocess.run(
        [
            "bash",
            str(ROOT / "scripts/check_qgis_containers.sh"),
            str(package),
            str(sqlite_zip),
            str(source),
        ],
        env={
            **os.environ,
            "PATH": str(binary) + os.pathsep + os.environ["PATH"],
            "CALL_LOG": str(log),
            "FAIL_FIRST": str(int(fail_first)),
        },
        capture_output=True,
        text=True,
    )
    calls = [json.loads(s) for s in log.read_text().splitlines()]
    runs = [c for c in calls if c[0] == "run"]
    assert result.returncode == (7 if fail_first else 0), result.stderr
    assert len(runs) == (1 if fail_first else 2)
    for args in runs:
        assert args[args.index("--network") + 1] == "none"
        assert any(a.startswith("qgis/qgis:") and "@sha256:" in a for a in args)
        assert not any(str(ROOT / ".git") in a for a in args)
        assert "--package" in args and "--sqlite-zip" in args and "--jktz-source-dir" in args
        mounts = [args[i + 1] for i, a in enumerate(args) if a == "--mount"]
        assert len(mounts) == 4 and all("readonly" in m for m in mounts)


@pytest.mark.parametrize(
    "filename,job", [("release.yml", "release"), ("pr-preview.yml", "preview")]
)
def test_ci_resolves_once_then_validates_both_qgis_versions_before_upload(filename, job):
    steps = yaml.safe_load((ROOT / ".github/workflows" / filename).read_text())["jobs"][job][
        "steps"
    ]
    fetch = [i for i, s in enumerate(steps) if "scripts/fetch_jktz_release.py" in s.get("run", "")]
    build_indices = [
        i
        for i, s in enumerate(steps)
        if "scripts/build_release_artifacts.py" in s.get("run", "")
        or "scripts/build_pr_preview.py" in s.get("run", "")
    ]
    checks = [
        i for i, s in enumerate(steps) if "scripts/check_qgis_containers.sh" in s.get("run", "")
    ]
    assert len(fetch) == len(build_indices) == len(checks) == 1
    assert fetch[0] < build_indices[0] < checks[0] < len(steps) - 1
    assert "--jktz-source-dir build/inputs/jktz" in steps[build_indices[0]]["run"]
    assert "if" not in steps[checks[0]] and "continue-on-error" not in steps[checks[0]]
