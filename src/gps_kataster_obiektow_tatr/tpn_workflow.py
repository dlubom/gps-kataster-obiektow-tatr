"""Offline preparation for the manual workflow; Git and PR content are data."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from .tpn_api import require
from .tpn_batch import (
    accepted_state_at,
    apply_batch,
    base_checkout,
    batch_path,
    check_batch,
    json_bytes,
    load_batch,
    prepare_batch,
)
from .tpn_candidates import CandidatePolicy
from .tpn_changes import compare, render_markdown
from .tpn_duplicate_state import read_accepted_duplicates
from .tpn_snapshot import SNAPSHOTS, validate_id, verify_snapshot
from .tpn_source_state import git
from .tpn_workflow_reporting import source_report

TRANSFER_REF = "refs/heads/tpn-candidate"
BRANCH_PREFIX = "tpn-sync/"
DATA_PREFIXES = (
    "data/objects/",
    "data/caves/",
    "data/relations/",
    "data/source_reviews/tpn/",
    "data/source_state/tpn/",
    "data/sources/tpn/snapshots/",
)


def run_git(root, *args, input=None, env=None):
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(root), *args],
        input=input,
        capture_output=True,
        env=env,
        check=False,
    )
    require(
        result.returncode == 0, "Git operation failed: " + result.stderr.decode(errors="replace")
    )
    return result.stdout.decode().strip()


def commit_data(root, message, *, previous_head=None):
    run_git(root, "add", "--force", "--all", "--", "data")
    tree = run_git(root, "write-tree")
    head = run_git(root, "rev-parse", "HEAD")
    if tree == run_git(root, "rev-parse", "HEAD^{tree}") and previous_head is None:
        return head
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "github-actions[bot]",
        "GIT_COMMITTER_NAME": "github-actions[bot]",
        "GIT_AUTHOR_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
        "GIT_COMMITTER_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
    }
    parents = ["-p", head]
    if previous_head and previous_head != head:
        parents += ["-p", previous_head]
    result = run_git(root, "commit-tree", tree, *parents, input=(message + "\n").encode(), env=env)
    run_git(root, "reset", "--soft", result)
    return result


def validate_branch(root, main, head):
    """Reject executable changes and nonregular entries before any PR data is read."""
    run_git(root, "merge-base", "--is-ancestor", main, head)
    changes = git(root, "diff", "--raw", "--no-renames", "-z", main, head, "--").split(b"\0")
    for index in range(0, len(changes) - 1, 2):
        header, path = changes[index].decode(), changes[index + 1].decode()
        old_mode, mode, *_ = header.removeprefix(":").split()
        require(path.startswith(DATA_PREFIXES), "PR path outside allowed data: " + path)
        require(mode in ("100644", "000000"), "PR requires regular files; invalid mode")
        if path.startswith("data/sources/tpn/snapshots/"):
            require(old_mode == "000000" and mode == "100644", "accepted snapshot is immutable")


def workspace(source, main, folder, *, head=None):
    """Only trusted main is checked out; the PR supplies a regular data tree."""
    folder = Path(folder)
    run_git(source, "clone", "--quiet", "--no-hardlinks", "--no-checkout", str(source), str(folder))
    run_git(folder, "checkout", "--quiet", "--detach", main)
    run_git(folder, "update-ref", "refs/remotes/origin/main", main)
    # Git omits empty required directories, just as in base_checkout().
    for name in ("objects", "caves", "relations"):
        (folder / "data" / name).mkdir(parents=True, exist_ok=True)
    if head and head != main:
        validate_branch(folder, main, head)
        with base_checkout(folder, head) as candidate:
            shutil.rmtree(folder / "data")
            shutil.copytree(candidate / "data", folder / "data")
        # No code is taken from head; its diff has been restricted to regular data.
        run_git(folder, "reset", "--soft", head)
    return folder


def automatic_proposals(report):
    proposals = []
    for row in report["records"]:
        if not (row["actionable"] or row["requires_review"]):
            continue
        actions = []
        if row.get("new_record_qualification", {}).get("status") == "automatic_proposal":
            key = "opening-" + row["globalid"]
            actions = [
                {"action": "create_cave", "cave_key": key},
                {
                    "action": "new_object",
                    "object_key": key,
                    "cave_key": key,
                    "location_hash": row["location_hash"],
                    "initial_best": "first_measurement",
                },
            ]
        proposals.append(
            {
                "change_id": row["change_id"],
                "target": row["target"],
                "preimage": row["preimage"],
                "actions": actions,
                "conflict_acknowledgements": [],
                "candidate_acknowledgements": [],
            }
        )
    return proposals


def current_main(root, expected):
    require(run_git(root, "rev-parse", "refs/remotes/origin/main") == expected, "main advanced")


def prepare_candidate(
    root,
    main,
    batch_id,
    acquire,
    *,
    previous_head=None,
    proposals=None,
    report_dir=None,
    inspection_only=False,
):
    root = Path(root)
    validate_id(batch_id)
    current_main(root, main)
    require(run_git(root, "rev-parse", "HEAD") == main, "prepare must start from main")
    state = accepted_state_at(root, main)
    require(state is not None, "accepted initial batch requires human merge of PBI-101")
    snap = acquire(root, batch_id)
    verify_snapshot(snap)
    require(Path(snap) == root / SNAPSHOTS / batch_id, "snapshot outside workflow namespace")
    snapshot_commit = (
        main
        if inspection_only
        else commit_data(root, "chore: preserve TPN workflow snapshot " + batch_id)
    )
    report = compare(
        root,
        snap,
        batch_id=batch_id,
        base_commit=snapshot_commit,
        state=state,
        candidate_policy=CandidatePolicy(),
        protect_best=True,
        duplicate_resolutions=read_accepted_duplicates(root, main),
    )
    report["accepted_state_commit"] = main
    if report_dir is not None:
        source_report(report_dir, report, snap)
    if inspection_only:
        return {"outcome": "existing", "summary": report["summary"]}
    if not report["requires_pr"]:
        return {"outcome": "noop", "summary": report["summary"]}
    proposals = automatic_proposals(report) if proposals is None else proposals
    changes, decisions = prepare_batch(root, report, proposals)
    folder = root / batch_path(batch_id)
    folder.mkdir(parents=True)
    (folder / "changes.json").write_bytes(json_bytes(changes))
    (folder / "decisions.yml").write_bytes(json_bytes(decisions))
    (folder / "proposals.yml").write_bytes(json_bytes(proposals))
    (folder / "report.md").write_text(render_markdown(report), encoding="utf-8")
    plan = apply_batch(root, changes, decisions, reviewers=set())
    check_batch(root, batch_id, allow_pending=True)
    head = commit_data(root, "feat: propose TPN batch " + batch_id, previous_head=previous_head)
    return {"outcome": "publish", "head": head, "batch_id": batch_id, "pending": plan["pending"]}


def active_batch(root, main, head):
    paths = git(root, "diff", "--name-only", main, head, "--", "data/source_reviews/tpn")
    ids = {p.split("/")[3] for p in paths.decode().splitlines() if p.endswith("/changes.json")}
    require(len(ids) == 1, "expected exactly one active workflow batch")
    return ids.pop()


def verify_workflow_basis(root, main, batch_id, *, initial, actor):
    """Anchor the batch base to main, not merely to its own consistent receipt."""
    changes, decisions = load_batch(root, batch_id)
    require(changes["accepted_state_commit"] == main, "workflow basis uses stale main")
    base = changes["base_commit"]
    require(re.fullmatch(r"[0-9a-f]{40}", base), "invalid workflow base")
    require(run_git(root, "merge-base", main, base) == main, "workflow base is not from main")
    prefix = (SNAPSHOTS / batch_id).as_posix() + "/"
    delta = git(root, "diff", "--raw", "--no-renames", "-z", main, base, "--").split(b"\0")
    paths = []
    for index in range(0, len(delta) - 1, 2):
        header, path = delta[index].decode(), delta[index + 1].decode()
        old_mode, mode, *_ = header.removeprefix(":").split()
        require(
            path.startswith(prefix) and old_mode == "000000" and mode == "100644",
            "workflow base may add only its own snapshot; hidden data/code change",
        )
        paths.append(path)
    require(prefix + "manifest.json" in paths, "workflow base missing new snapshot")
    if initial:
        require(
            all(d["status"] == "pending" for d in decisions["decisions"]),
            "initial/recovered proposal must have all decisions pending",
        )
    else:
        require(
            all(
                d["reviewed_by"] == "github:" + actor
                for d in decisions["decisions"]
                if d["status"] != "pending"
            ),
            "workflow reviewer is not dispatcher",
        )
    return changes, decisions


def apply_candidate(root, main, batch_id, actor):
    current_main(root, main)
    changes, decisions = load_batch(root, batch_id)
    reviewer = "github:" + actor
    require(
        all(
            d["reviewed_by"] == reviewer for d in decisions["decisions"] if d["status"] != "pending"
        ),
        "final decisions must name the authorized dispatcher as reviewer",
    )
    before = run_git(root, "rev-parse", "HEAD")
    plan = apply_batch(root, changes, decisions, reviewers={reviewer})
    check_batch(root, batch_id, allow_pending=True)
    head = commit_data(root, "feat: apply reviewed TPN decisions " + batch_id)
    return {
        "outcome": "noop" if head == before else "publish",
        "head": head,
        "batch_id": batch_id,
        "pending": plan["pending"],
    }


def write_bundle(root, main, head, path):
    run_git(root, "update-ref", TRANSFER_REF, head)
    run_git(root, "bundle", "create", str(path), TRANSFER_REF, "^" + main)
