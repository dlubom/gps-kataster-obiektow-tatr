"""Exercise history protection against real Git commits."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from gps_kataster_obiektow_tatr.data_loader import load_dataset
from gps_kataster_obiektow_tatr.measurement_history import check_measurement_history

REPO_ROOT = Path(__file__).resolve().parents[1]
OBJECT_PATH = Path("data/objects/KSZ/KSZ-0001.yml")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def measurement(measurement_id: str) -> dict:
    return {
        "id": measurement_id,
        "lat": 49.2,
        "lon": 19.8,
        "x_1992": 150000.0,
        "y_1992": 560000.0,
        "elevation_m": None,
        "source": "TPN",
        "source_ref": "TPN:source-record",
        "observed_date": "2022-05-25",
        "method": "source_record",
        "verification_status": "nieweryfikowany",
        "created_at": "2026-05-16T10:22:49Z",
        "created_by": "importer:tpn",
    }


def write_object(repo: Path, measurements: list[dict]) -> None:
    (repo / OBJECT_PATH).write_text(
        yaml.safe_dump({"id": "KSZ-0001", "measurements": measurements}), encoding="utf-8"
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / OBJECT_PATH).parent.mkdir(parents=True)
    for directory in ("caves", "relations"):
        path = tmp_path / "data" / directory
        path.mkdir()
        (path / ".gitkeep").touch()
    write_object(tmp_path, [measurement("m-001"), measurement("m-002")])
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "Accepted catalogue")
    git(tmp_path, "update-ref", "refs/remotes/origin/main", "HEAD")
    return tmp_path


def check(repo: Path, **kwargs):
    return check_measurement_history(load_dataset(repo / "data"), repo_root=repo, **kwargs)


def test_allows_appending_and_editing_review_metadata(repo: Path) -> None:
    first = measurement("m-001")
    first.update(
        notes="Incorrect point",
        tags=["field-check"],
        verification_status="odrzucony",
        verified_by="reviewer",
        verified_at="2026-11-04T12:00:00Z",
    )
    write_object(repo, [first, measurement("m-002"), measurement("m-003")])
    assert check(repo) == ()


@pytest.mark.parametrize("field", ["lat", "source_ref", "created_at"])
def test_rejects_rewriting_existing_measurement(repo: Path, field: str) -> None:
    first = measurement("m-001")
    first[field] = 50.1 if field == "lat" else "changed"
    write_object(repo, [first, measurement("m-002")])

    (issue,) = check(repo)
    assert issue.code == "MEASUREMENT_HISTORY_CHANGED"
    assert issue.path == repo / OBJECT_PATH
    assert field in issue.description and "m-001" in issue.description


def test_rejects_removing_explicit_null_from_history(repo: Path) -> None:
    first = measurement("m-001")
    del first["elevation_m"]
    write_object(repo, [first, measurement("m-002")])
    assert check(repo)[0].code == "MEASUREMENT_HISTORY_CHANGED"


def test_rejects_adding_previously_absent_source_field(repo: Path) -> None:
    first = measurement("m-001")
    first["device"] = None
    write_object(repo, [first, measurement("m-002")])
    assert check(repo)[0].code == "MEASUREMENT_HISTORY_CHANGED"


@pytest.mark.parametrize(
    "ids",
    [
        ["m-001"],
        ["m-002", "m-001"],
        ["m-001", "m-003", "m-002"],
        ["m-001", "m-003"],
    ],
)
def test_requires_accepted_order_and_presence(repo: Path, ids: list[str]) -> None:
    write_object(repo, [measurement(mid) for mid in ids])
    assert check(repo)[0].code == "MEASUREMENT_HISTORY_PREFIX_CHANGED"


def test_rejects_deleting_object(repo: Path) -> None:
    (repo / OBJECT_PATH).unlink()
    (issue,) = check(repo)
    assert issue.code == "MEASUREMENT_HISTORY_OBJECT_REMOVED"
    assert issue.path == repo / OBJECT_PATH
    assert "KSZ-0001" in issue.description


def test_explicit_accepted_sha_catches_committed_candidate_rewrite(repo: Path) -> None:
    base_sha = git(repo, "rev-parse", "HEAD")
    write_object(repo, [measurement("m-001")])
    git(repo, "commit", "-am", "Rewrite")
    assert check(repo, base_ref=base_sha)[0].code == "MEASUREMENT_HISTORY_PREFIX_CHANGED"
    assert check(repo, base_ref="HEAD")[0].code == "HISTORY_BASELINE_UNAVAILABLE"
    assert (
        check(repo, base_ref=git(repo, "rev-parse", "HEAD"))[0].code
        == "HISTORY_BASELINE_UNAVAILABLE"
    )


def test_missing_default_baseline_fails_closed(repo: Path) -> None:
    git(repo, "update-ref", "-d", "refs/remotes/origin/main")
    assert check(repo)[0].code == "HISTORY_BASELINE_UNAVAILABLE"


def test_accepts_explicit_sha_at_accepted_main_tip(repo: Path) -> None:
    assert check(repo, base_ref=git(repo, "rev-parse", "HEAD")) == ()


def test_rejects_default_ref_that_is_not_an_ancestor(repo: Path) -> None:
    old_tip = git(repo, "rev-parse", "HEAD")
    git(repo, "commit", "--allow-empty", "-m", "Advanced main")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(repo, "checkout", "--detach", old_tip)
    git(repo, "commit", "--allow-empty", "-m", "Divergent candidate")
    (issue,) = check(repo)
    assert issue.code == "HISTORY_BASELINE_UNAVAILABLE"
    assert "ancestor" in issue.description


def test_fails_when_accepted_commit_has_no_objects(repo: Path) -> None:
    git(repo, "rm", str(OBJECT_PATH))
    git(repo, "commit", "-m", "No baseline data")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    (repo / OBJECT_PATH).parent.mkdir(parents=True)
    write_object(repo, [measurement("m-001")])
    assert check(repo)[0].code == "HISTORY_BASELINE_UNAVAILABLE"


def test_shallow_clone_without_required_baseline_fails_closed(repo: Path, tmp_path: Path) -> None:
    base_sha = git(repo, "rev-parse", "HEAD")
    git(repo, "commit", "--allow-empty", "-m", "Candidate")
    clone = tmp_path / "shallow"
    git(repo, "clone", "--depth", "1", repo.as_uri(), str(clone))
    assert check(clone, base_ref=base_sha)[0].code == "HISTORY_BASELINE_UNAVAILABLE"


@pytest.mark.parametrize(
    "broken_source",
    [
        "id: KSZ-0001\nmeasurements: []\n",
        "id: KSZ-0001\nmeasurements: [{id: m-001}]\n",
        "id: KSZ-0001\nmeasurements: []\nmeasurements: []\n",
    ],
)
def test_incomplete_or_ambiguous_baseline_fails_closed(repo: Path, broken_source: str) -> None:
    (repo / OBJECT_PATH).write_text(broken_source, encoding="utf-8")
    git(repo, "commit", "-am", "Malformed baseline")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    write_object(repo, [measurement("m-001")])
    assert check(repo)[0].code == "HISTORY_BASELINE_UNAVAILABLE"


def test_cli_reports_unavailable_baseline(repo: Path) -> None:
    git(repo, "update-ref", "-d", "refs/remotes/origin/main")
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/check_measurement_history.py"),
            "--repo-root",
            str(repo),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "HISTORY_BASELINE_UNAVAILABLE" in result.stdout
