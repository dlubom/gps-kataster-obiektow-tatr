"""Read-only planning followed by a separately authorized, checked publication."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

from .tpn_api import require
from .tpn_batch import base_checkout, batch_path, check_batch, json_bytes, load_batch
from .tpn_normalization import canonical, exact_json
from .tpn_snapshot import fetch_snapshot, sha256
from .tpn_workflow import (
    BRANCH_PREFIX,
    TRANSFER_REF,
    active_batch,
    apply_candidate,
    automatic_proposals,
    prepare_candidate,
    run_git,
    validate_branch,
    verify_workflow_basis,
    workspace,
    write_bundle,
)
from .tpn_workflow_reporting import run_report
from .yaml_io import load_unique_yaml

PLAN_KEYS = {
    "format",
    "format_version",
    "operation",
    "run_id",
    "repository",
    "main",
    "actor",
    "triggering_actor",
    "pr_number",
    "requested_head",
    "expected_head",
    "head",
    "branch",
    "batch_id",
    "pending",
    "outcome",
    "bundle_sha256",
    "event_name",
}


def enabled_event(operation, event_name, monthly_enabled, pr_number, expected_head):
    require(event_name in ("workflow_dispatch", "schedule"), "unsupported workflow event")
    if event_name == "schedule":
        require(
            operation == "prepare" and pr_number == 0 and expected_head == "",
            "schedule supports only untargeted prepare",
        )
        require(type(monthly_enabled) is bool, "invalid monthly activation")
        return monthly_enabled
    return True


def own_pull(pull, repository):
    return (pull["head"].get("repo") or {}).get("full_name") == repository and pull.get(
        "base", {}
    ).get("ref") == "main"


def open_sync(pulls, repository):
    return [
        p
        for p in pulls
        if p["state"] == "open"
        and own_pull(p, repository)
        and p["head"]["ref"].startswith(BRANCH_PREFIX)
    ]


def authorize_context(root, api, trusted_sha, actor, triggering_actor):
    api.authorize(actor)
    if triggering_actor != actor:
        api.authorize(triggering_actor)
    require(re.fullmatch(r"[0-9a-f]{40}", trusted_sha), "invalid trusted SHA")
    require(
        api.main() == trusted_sha == run_git(root, "rev-parse", "HEAD"),
        "main advanced or code is not the trusted main SHA; dispatch again on main",
    )


def require_pull(api, pull, expected_head):
    require(
        pull["state"] == "open"
        and pull["base"]["ref"] == "main"
        and pull["head"]["repo"]["full_name"] == api.repository
        and re.fullmatch(r"tpn-sync/[A-Za-z0-9_-]+", pull["head"]["ref"]),
        "not an open same-repository TPN workflow PR",
    )
    require(pull["head"]["sha"] == expected_head, "PR HEAD changed; review exact HEAD again")


def plan_workflow(
    root,
    api,
    *,
    output,
    operation,
    run_id,
    actor,
    triggering_actor,
    trusted_sha,
    pr_number=0,
    expected_head="",
    acquire=None,
    event_name="workflow_dispatch",
    monthly_enabled=False,
):
    require(operation in ("prepare", "apply", "refresh"), "unsupported operation")
    require(re.fullmatch(r"[0-9]+", run_id), "invalid run ID")
    require(type(pr_number) is int and pr_number >= 0, "invalid PR number")
    enabled = enabled_event(operation, event_name, monthly_enabled, pr_number, expected_head)
    if enabled:
        authorize_context(root, api, trusted_sha, actor, triggering_actor)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    require(not (output / "plan.json").exists(), "transfer already exists; no overwrite")
    doc = {
        "format": "tpn-workflow-transfer",
        "format_version": 2,
        "event_name": event_name,
        "operation": operation,
        "run_id": run_id,
        "repository": api.repository,
        "main": trusted_sha,
        "actor": actor,
        "triggering_actor": triggering_actor,
        "pr_number": pr_number,
        "requested_head": expected_head,
        "expected_head": "",
        "head": "",
        "branch": "",
        "batch_id": "",
        "pending": 0,
        "outcome": "noop",
        "bundle_sha256": "",
    }
    if not enabled:
        doc["outcome"] = "disabled"
        (output / "plan.json").write_bytes(json_bytes(doc))
        run_report(output, doc)
        return doc
    pulls = api.pulls()
    opened = open_sync(pulls, api.repository)
    run_report(output, doc, opened)
    if operation == "prepare" and opened:
        work = workspace(root, trusted_sha, output / "work")
        prepare_candidate(
            work,
            trusted_sha,
            "gha-" + run_id,
            acquire or (lambda r, ident: fetch_snapshot(r, ident, 500, 2)),
            inspection_only=True,
            report_dir=output / "check",
        )
        doc["outcome"] = "existing"
    else:
        old_head, custom_proposals = None, None
        if operation == "prepare":
            require(pr_number == 0 and expected_head == "", "prepare cannot target a PR")
            known = {p["head"]["ref"] for p in pulls if own_pull(p, api.repository)}
            orphans = {b: h for b, h in api.branches().items() if b not in known}
            require(len(orphans) <= 1, "multiple orphan TPN branches; operator review required")
            if orphans:
                doc["branch"], old_head = next(iter(orphans.items()))
                doc["expected_head"] = old_head
            else:
                doc["branch"] = BRANCH_PREFIX + "gha-" + run_id
        else:
            require(
                pr_number > 0 and re.fullmatch(r"[0-9a-f]{40}", expected_head),
                "apply/refresh require PR number and exact expected_head",
            )
            pull = api.pull(pr_number)
            require_pull(api, pull, expected_head)
            require(
                len(opened) == 1 and opened[0]["number"] == pr_number,
                "another open TPN PR requires review",
            )
            doc["branch"], old_head = pull["head"]["ref"], expected_head
            doc["expected_head"] = old_head
        if old_head:
            require(re.fullmatch(r"[0-9a-f]{40}", old_head), "invalid remote head")
            run_git(root, "fetch", "--no-tags", api.git_url, old_head)
            fork = run_git(root, "merge-base", trusted_sha, old_head)
            validate_branch(root, fork, old_head)
        # Recovery and apply read ONLY regular PR data into a main-code workspace.
        recovery = operation == "prepare" and old_head is not None
        work = workspace(
            root,
            trusted_sha,
            output / "work",
            head=old_head if operation == "apply" or recovery else None,
        )
        if operation == "apply" or recovery:
            batch = active_batch(work, trusted_sha, old_head)
            verify_workflow_basis(
                work, trusted_sha, batch, initial=recovery, actor=triggering_actor
            )
            if recovery:
                inspection = workspace(root, trusted_sha, output / "inspection")
                prepare_candidate(
                    inspection,
                    trusted_sha,
                    "gha-" + run_id,
                    acquire or (lambda r, ident: fetch_snapshot(r, ident, 500, 2)),
                    inspection_only=True,
                    report_dir=output / "check",
                )
                check_batch(work, batch, allow_pending=True)
                result = {
                    "outcome": "publish",
                    "head": old_head,
                    "batch_id": batch,
                    "pending": sum(
                        d["status"] == "pending" for d in load_batch(work, batch)[1]["decisions"]
                    ),
                }
            else:
                result = apply_candidate(work, trusted_sha, batch, triggering_actor)
        else:
            if operation == "refresh":
                fork = run_git(root, "merge-base", trusted_sha, old_head)
                batch = active_batch(root, fork, old_head)
                with base_checkout(root, old_head) as previous:
                    changes, _ = load_batch(previous, batch)
                    proposed = load_unique_yaml(previous / batch_path(batch) / "proposals.yml")
                    bound = changes["execution"]["proposals"]
                    # Refresh binds edits into execution; they remain human proposals
                    # on subsequent refreshes. Only untouched defaults are regenerated.
                    if canonical(proposed) != canonical(bound) or canonical(bound) != canonical(
                        automatic_proposals(changes)
                    ):
                        custom_proposals = proposed
            result = prepare_candidate(
                work,
                trusted_sha,
                "gha-" + run_id,
                acquire or (lambda r, ident: fetch_snapshot(r, ident, 500, 2)),
                previous_head=old_head,
                proposals=custom_proposals,
                report_dir=output / "check",
            )
        doc.update({k: v for k, v in result.items() if k in doc})
        if doc["outcome"] == "publish":
            verify_workflow_basis(
                work,
                trusted_sha,
                doc["batch_id"],
                initial=operation != "apply",
                actor=triggering_actor,
            )
            bundle = output / "candidate.bundle"
            write_bundle(work, trusted_sha, doc["head"], bundle)
            doc["bundle_sha256"] = sha256(bundle.read_bytes())
    (output / "plan.json").write_bytes(json_bytes(doc))
    run_report(output, doc, opened)
    return doc


def publish_workflow(
    root,
    api,
    output,
    *,
    operation,
    run_id,
    actor,
    triggering_actor,
    trusted_sha,
    pr_number=0,
    expected_head="",
    event_name="workflow_dispatch",
    monthly_enabled=False,
):
    require(
        enabled_event(operation, event_name, monthly_enabled, pr_number, expected_head),
        "monthly schedule disabled before publication",
    )
    authorize_context(root, api, trusted_sha, actor, triggering_actor)
    output = Path(output).resolve()
    doc = exact_json((output / "plan.json").read_bytes())
    require(
        set(doc) == PLAN_KEYS
        and doc["format"] == "tpn-workflow-transfer"
        and type(doc["format_version"]) is int
        and doc["format_version"] == 2,
        "invalid workflow transfer",
    )
    for key, expected in {
        "operation": operation,
        "run_id": run_id,
        "repository": api.repository,
        "main": trusted_sha,
        "actor": actor,
        "triggering_actor": triggering_actor,
        "pr_number": pr_number,
        "requested_head": expected_head,
        "event_name": event_name,
    }.items():
        require(doc[key] == expected, "transfer context mismatch: " + key)
    if doc["outcome"] in ("noop", "existing"):
        return doc
    require(
        doc["outcome"] == "publish" and re.fullmatch(r"tpn-sync/[A-Za-z0-9_-]+", doc["branch"]),
        "invalid publication branch/outcome",
    )
    require(re.fullmatch(r"[0-9a-f]{40}", doc["head"]), "invalid candidate SHA")
    bundle = output / "candidate.bundle"
    require(sha256(bundle.read_bytes()) == doc["bundle_sha256"], "bundle hash mismatch")
    run_git(root, "fetch", "--no-tags", str(bundle), TRANSFER_REF)
    require(run_git(root, "rev-parse", "FETCH_HEAD") == doc["head"], "bundle head mismatch")
    validate_branch(root, trusted_sha, doc["head"])
    with tempfile.TemporaryDirectory(prefix="tpn-publish-") as directory:
        work = workspace(root, trusted_sha, Path(directory) / "work", head=doc["head"])
        require(active_batch(work, trusted_sha, doc["head"]) == doc["batch_id"], "batch mismatch")
        _, decisions = verify_workflow_basis(
            work, trusted_sha, doc["batch_id"], initial=operation != "apply", actor=triggering_actor
        )
        require(
            doc["pending"] == sum(d["status"] == "pending" for d in decisions["decisions"]),
            "pending count mismatch",
        )
        check_batch(work, doc["batch_id"], allow_pending=True)
        # Recheck all live state immediately before the ordinary, non-forced push.
        require(api.main() == trusted_sha, "main advanced before publication")
        opened = open_sync(api.pulls(), api.repository)
        if operation == "prepare" and opened:
            result = {**doc, "outcome": "existing", "head": "", "pending": 0}
            run_report(output, result, opened)
            return result
        if operation != "prepare":
            pull = api.pull(pr_number)
            require(pull["head"]["sha"] in (doc["expected_head"], doc["head"]), "PR HEAD changed")
            require_pull(api, pull, pull["head"]["sha"])
            require(
                len(opened) == 1 and opened[0]["number"] == pr_number,
                "open PR changed before publication",
            )
        remote = api.branches().get(doc["branch"])
        require(remote in (doc["expected_head"] or None, doc["head"]), "remote branch changed")
        if doc["expected_head"]:
            run_git(work, "merge-base", "--is-ancestor", doc["expected_head"], doc["head"])
        if remote != doc["head"]:
            api.authorize(actor)
            if triggering_actor != actor:
                api.authorize(triggering_actor)
            api.push(work, doc["head"], doc["branch"])
        require(api.branches().get(doc["branch"]) == doc["head"], "remote SHA readback failed")
        if operation == "prepare":
            # Recover the exact branch after a push/PR failure; never create a second batch.
            require(
                not open_sync(api.pulls(), api.repository),
                "another TPN PR appeared after push; preserve branch",
            )
            pull = api.create_pull(doc["branch"], doc["batch_id"])
            require_pull(api, pull, doc["head"])
            return {**doc, "pr_number": pull["number"]}
    return doc
