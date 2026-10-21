"""Guard the workflow's security boundaries and execute CLI rejection paths."""

import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]


def test_dispatch_has_read_planner_separate_writer_and_one_lock():
    path = REPO / ".github/workflows/tpn-sync.yml"
    assert path.exists(), "manual dispatch workflow missing"
    wf = yaml.safe_load(path.read_text())
    assert set(wf["on"]) == {"workflow_dispatch", "schedule"}
    assert wf["on"]["schedule"] == [{"cron": "17 3 1 * *"}]
    assert wf["permissions"] == {"contents": "read"}
    assert wf["concurrency"] == {"group": "tpn-sync", "cancel-in-progress": False}
    assert set(wf["jobs"]) == {"prepare", "publish"}
    prepare, publish = wf["jobs"]["prepare"], wf["jobs"]["publish"]
    assert prepare["permissions"] == {"contents": "read", "pull-requests": "read"}
    assert publish["permissions"] == {"contents": "write", "pull-requests": "write"}
    assert publish["needs"] == "prepare"
    check = next(
        s for s in prepare["steps"] if s.get("with", {}).get("name", "").startswith("tpn-check-")
    )
    assert check["if"] == "always()" and check["with"]["retention-days"] == 14
    for job in (prepare, publish):
        assert "refs/heads/main" in job["if"]
        checkout = next(
            s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout@")
        )
        assert checkout["with"]["ref"] == "${{ github.sha }}"
        assert checkout["with"]["persist-credentials"] is False
        assert all("${{ inputs." not in s.get("run", "") for s in job["steps"])
        entrypoint = next(s for s in job["steps"] if "scripts/run_tpn_sync.py" in s.get("run", ""))
        assert entrypoint["env"]["TPN_OPERATION"] == "${{ inputs.operation || 'prepare' }}"
        assert entrypoint["env"]["TPN_MONTHLY_ENABLED"] == "${{ vars.TPN_MONTHLY_ENABLED }}"


def test_cli_rejects_non_main_before_network_and_has_no_writes(tmp_path):
    script = REPO / "scripts/run_tpn_sync.py"
    assert script.exists(), "workflow CLI missing"
    result = subprocess.run(
        [sys.executable, str(script), "plan", "--output", str(tmp_path / "transfer")],
        env={**os.environ, "GITHUB_REF": "refs/heads/untrusted", "GITHUB_TOKEN": "test-token"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1 and "main" in result.stderr
    assert not (tmp_path / "transfer").exists()
