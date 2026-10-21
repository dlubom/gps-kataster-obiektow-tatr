"""GitHub I/O is simulated; the candidate Git history and batch checks are real."""

import importlib.util
import json
from copy import deepcopy

import pytest
from test_tpn_batch import batch_repo as batch_repo
from test_tpn_batch import git, hashes
from test_tpn_changes import feature
from test_tpn_workflow import accepted, acquisition


def integration():
    name = "gps_kataster_obiektow_tatr.tpn_workflow_github"
    assert importlib.util.find_spec(name) is not None, "GitHub workflow is not implemented"
    from gps_kataster_obiektow_tatr import tpn_workflow_github

    return tpn_workflow_github


class FakeGitHub:
    repository = "owner/catalog"

    def __init__(self, root, main):
        self.root, self.base = root, main
        self.items, self.refs, self.writes = [], {}, []
        self.permissions = {"maintainer": ("User", "write")}
        self.fail_create = False

    @property
    def git_url(self):
        return str(self.root)

    def authorize(self, login):
        kind, permission = self.permissions.get(login, ("User", "read"))
        if kind != "User" or permission not in ("write", "maintain", "admin"):
            raise ValueError("unauthorized human operator")

    def main(self):
        return self.base

    def pulls(self):
        return deepcopy(self.items)

    def pull(self, number):
        return deepcopy(next(p for p in self.items if p["number"] == number))

    def branches(self):
        return dict(self.refs)

    def push(self, root, head, branch):
        old = self.refs.get(branch)
        if old:
            git(root, "merge-base", "--is-ancestor", old, head)
        git(self.root, "fetch", str(root), head)
        self.refs[branch] = head
        for pull in self.items:
            if pull["head"]["ref"] == branch:
                pull["head"]["sha"] = head
        self.writes.append(("push", branch, head))

    def create_pull(self, branch, batch):
        if self.fail_create:
            raise OSError("injected GitHub failure after push")
        p = {
            "number": 17,
            "state": "open",
            "draft": True,
            "base": {"ref": "main"},
            "head": {
                "ref": branch,
                "sha": self.refs[branch],
                "repo": {"full_name": self.repository},
            },
        }
        self.items.append(p)
        self.writes.append(("draft", branch))
        return p


def plan(g, root, output, **kwargs):
    options = dict(
        operation="prepare",
        run_id="123",
        actor="maintainer",
        triggering_actor="maintainer",
        trusted_sha=g.base,
        pr_number=0,
        expected_head="",
        acquire=acquisition([feature(lon=19.802)]),
    )
    options.update(kwargs)
    return integration().plan_workflow(root, g, output=output, **options)


def test_one_draft_pr_no_main_mutation_and_open_retry(batch_repo, tmp_path):
    i = integration()
    root, _ = batch_repo
    main = accepted(batch_repo)
    g = FakeGitHub(root, main)
    before = hashes(root)
    out = tmp_path / "transfer"
    result = plan(g, root, out)
    assert result["outcome"] == "publish"
    i.publish_workflow(
        root,
        g,
        out,
        actor="maintainer",
        triggering_actor="maintainer",
        trusted_sha=main,
        operation="prepare",
        run_id="123",
        pr_number=0,
        expected_head="",
    )
    assert len(g.items) == 1 and g.items[0]["draft"] is True
    assert git(root, "rev-parse", "refs/remotes/origin/main") == main
    assert hashes(root) == before
    second = plan(g, root, tmp_path / "retry", run_id="124")
    assert second["outcome"] == "existing"
    assert len(g.writes) == 2


def test_noop_and_invalid_source_have_no_remote_side_effects(batch_repo, tmp_path):
    integration()
    root, _ = batch_repo
    g = FakeGitHub(root, accepted(batch_repo))
    result = plan(g, root, tmp_path / "noop", acquire=acquisition([feature(lon=19.801)]))
    assert result["outcome"] == "noop"

    def fail(*args):
        raise ValueError("incomplete source")

    with pytest.raises(ValueError, match="incomplete"):
        plan(g, root, tmp_path / "bad", acquire=fail)
    assert not g.writes


@pytest.mark.parametrize("who", ["reader", "robot"])
def test_untrusted_operator_cannot_prepare_or_publish(batch_repo, tmp_path, who):
    i = integration()
    root, _ = batch_repo
    main = accepted(batch_repo)
    g = FakeGitHub(root, main)
    g.permissions["robot"] = ("Bot", "admin")
    out = tmp_path / "transfer"
    with pytest.raises(ValueError, match="unauthorized"):
        plan(g, root, out, triggering_actor=who)
    plan(g, root, out)
    with pytest.raises(ValueError, match="unauthorized"):
        i.publish_workflow(
            root,
            g,
            out,
            actor="maintainer",
            triggering_actor=who,
            trusted_sha=main,
            operation="prepare",
            run_id="123",
            pr_number=0,
            expected_head="",
        )
    assert not g.writes


@pytest.mark.parametrize("tamper", ["bundle", "metadata", "main", "open"])
def test_publish_rechecks_bundle_context_and_live_state(batch_repo, tmp_path, tamper):
    i = integration()
    root, _ = batch_repo
    main = accepted(batch_repo)
    g = FakeGitHub(root, main)
    out = tmp_path / "transfer"
    plan(g, root, out)
    if tamper == "bundle":
        # Alter only the informational prerequisite description: still a valid
        # bundle of the same commits, so Git's parser/head check cannot detect it.
        bundle = out / "candidate.bundle"
        header, pack = bundle.read_bytes().split(b"\n\n", 1)
        lines = header.split(b"\n")
        lines = [
            line[:41] + b" altered description" if line.startswith(b"-") else line for line in lines
        ]
        bundle.write_bytes(b"\n".join(lines) + b"\n\n" + pack)
    elif tamper == "metadata":
        doc = json.loads((out / "plan.json").read_text())
        doc["repository"] = "somebody/else"
        (out / "plan.json").write_text(json.dumps(doc))
    elif tamper == "main":
        g.base = "f" * 40
    else:
        g.items.append(
            {
                "state": "open",
                "number": 45,
                "base": {"ref": "main"},
                "head": {
                    "ref": "tpn-sync/other",
                    "sha": "f" * 40,
                    "repo": {"full_name": g.repository},
                },
            }
        )
    if tamper == "open":
        result = i.publish_workflow(
            root,
            g,
            out,
            actor="maintainer",
            triggering_actor="maintainer",
            trusted_sha=main,
            operation="prepare",
            run_id="123",
            pr_number=0,
            expected_head="",
        )
        assert result["outcome"] == "existing"
    else:
        with pytest.raises(ValueError, match="bundle hash" if tamper == "bundle" else None):
            i.publish_workflow(
                root,
                g,
                out,
                actor="maintainer",
                triggering_actor="maintainer",
                trusted_sha=main,
                operation="prepare",
                run_id="123",
                pr_number=0,
                expected_head="",
            )
    assert not g.writes


def test_failure_after_push_recovers_same_branch_and_pr(batch_repo, tmp_path):
    i = integration()
    root, _ = batch_repo
    main = accepted(batch_repo)
    g = FakeGitHub(root, main)
    out = tmp_path / "first"
    first = plan(g, root, out)
    g.fail_create = True
    with pytest.raises(OSError):
        i.publish_workflow(
            root,
            g,
            out,
            actor="maintainer",
            triggering_actor="maintainer",
            trusted_sha=main,
            operation="prepare",
            run_id="123",
            pr_number=0,
            expected_head="",
        )
    assert len(g.refs) == 1 and not g.items
    retry = tmp_path / "recovery"
    recovered = plan(g, root, retry, run_id="125")
    assert recovered["head"] == first["head"] and recovered["branch"] == first["branch"]
    g.fail_create = False
    i.publish_workflow(
        root,
        g,
        retry,
        actor="maintainer",
        triggering_actor="maintainer",
        trusted_sha=main,
        operation="prepare",
        run_id="125",
        pr_number=0,
        expected_head="",
    )
    assert len(g.refs) == len(g.items) == 1
    assert len([w for w in g.writes if w[0] == "push"]) == 1


def test_closed_without_merge_does_not_accept_source_baseline(batch_repo, tmp_path):
    i = integration()
    root, _ = batch_repo
    main = accepted(batch_repo)
    g = FakeGitHub(root, main)
    out = tmp_path / "one"
    plan(g, root, out)
    i.publish_workflow(
        root,
        g,
        out,
        actor="maintainer",
        triggering_actor="maintainer",
        trusted_sha=main,
        operation="prepare",
        run_id="123",
        pr_number=0,
        expected_head="",
    )
    g.items[0]["state"] = "closed"
    again = plan(g, root, tmp_path / "two", run_id="126")
    assert again["outcome"] == "publish" and again["branch"] != g.items[0]["head"]["ref"]
    assert g.base == main


def test_apply_and_refresh_append_to_same_pr_and_check_exact_head(batch_repo, tmp_path):
    i = integration()
    root, _ = batch_repo
    main = accepted(batch_repo)
    g = FakeGitHub(root, main)
    out = tmp_path / "initial"
    initial = plan(g, root, out)
    i.publish_workflow(
        root,
        g,
        out,
        actor="maintainer",
        triggering_actor="maintainer",
        trusted_sha=main,
        operation="prepare",
        run_id="123",
        pr_number=0,
        expected_head="",
    )
    # Only decisions from the PR are edited, with no checkout/execution of its code.
    from gps_kataster_obiektow_tatr.tpn_workflow import commit_data, workspace

    work = workspace(root, main, tmp_path / "operator", head=initial["head"])
    file = work / "data/source_reviews/tpn/gha-123/decisions.yml"
    decisions = json.loads(file.read_text())
    decisions["decisions"][0].update(
        status="defer",
        reviewed_by="github:maintainer",
        reviewed_at="2026-10-21T12:00:00Z",
        reason="Wait for evidence",
        actions=[],
    )
    file.write_text(json.dumps(decisions))
    edited = commit_data(work, "operator review")
    g.push(work, edited, initial["branch"])
    with pytest.raises(ValueError, match="HEAD"):
        plan(
            g,
            root,
            tmp_path / "stale",
            operation="apply",
            pr_number=17,
            expected_head=initial["head"],
        )
    apply_out = tmp_path / "apply"
    applied = plan(
        g, root, apply_out, operation="apply", pr_number=17, expected_head=edited, run_id="127"
    )
    assert applied["pending"] == 0
    i.publish_workflow(
        root,
        g,
        apply_out,
        actor="maintainer",
        triggering_actor="maintainer",
        trusted_sha=main,
        operation="apply",
        run_id="127",
        pr_number=17,
        expected_head=edited,
    )
    git(root, "merge-base", "--is-ancestor", edited, applied["head"])
    (root / "trusted_code.py").write_text("# New code accepted independently on main\n")
    git(root, "add", "--", "trusted_code.py")
    git(root, "commit", "-qm", "main advanced during review")
    main = git(root, "rev-parse", "HEAD")
    git(root, "update-ref", "refs/remotes/origin/main", main)
    g.base = main
    with pytest.raises(ValueError):
        plan(
            g,
            root,
            tmp_path / "stale-main",
            operation="apply",
            pr_number=17,
            expected_head=applied["head"],
            run_id="129",
        )
    refresh_out = tmp_path / "refresh"
    refreshed = plan(
        g,
        root,
        refresh_out,
        operation="refresh",
        pr_number=17,
        expected_head=applied["head"],
        run_id="128",
    )
    assert refreshed["pending"] == 1
    i.publish_workflow(
        root,
        g,
        refresh_out,
        actor="maintainer",
        triggering_actor="maintainer",
        trusted_sha=main,
        operation="refresh",
        run_id="128",
        pr_number=17,
        expected_head=applied["head"],
    )
    git(root, "merge-base", "--is-ancestor", applied["head"], refreshed["head"])
    git(root, "merge-base", "--is-ancestor", main, refreshed["head"])
    assert (
        git(root, "show", refreshed["head"] + ":trusted_code.py")
        == "# New code accepted independently on main"
    )
    assert len(g.items) == 1 and g.refs[initial["branch"]] == refreshed["head"]


def test_rest_pagination_and_human_permission_check():
    from gps_kataster_obiektow_tatr.tpn_workflow_api import GitHub

    api = GitHub("owner/catalog", "test-token")
    requests = []

    def repo(path, *args):
        requests.append(path)
        if "permission" in path:
            return {"permission": "write"}
        return [{}] * 100 if path.endswith("&page=1") else [{"last": True}]

    api.repo = repo
    api.request = lambda *args: {"type": "Bot"}
    assert len(api.pages("pulls?state=all")) == 101
    with pytest.raises(ValueError, match="unauthorized"):
        api.authorize("robot")
    api.request = lambda *args: {"type": "User"}
    api.authorize("maintainer")
    assert any("page=2" in path for path in requests)


@pytest.mark.parametrize("stage", ["recovery", "publisher"])
def test_orphan_cannot_smuggle_history_edit_in_batch_base(batch_repo, tmp_path, stage):
    """A self-consistent receipt cannot authorize data hidden before its base."""
    i = integration()
    root, _ = batch_repo
    main = accepted(batch_repo)
    from gps_kataster_obiektow_tatr.tpn_batch import (
        accepted_state_at,
        apply_batch,
        batch_path,
        json_bytes,
        prepare_batch,
    )
    from gps_kataster_obiektow_tatr.tpn_candidates import CandidatePolicy
    from gps_kataster_obiektow_tatr.tpn_changes import compare
    from gps_kataster_obiektow_tatr.tpn_workflow import commit_data, workspace

    work = workspace(root, main, tmp_path / "forged")
    file = work / "data/objects/KSW/KSW-0001.yml"
    import yaml

    obj = yaml.safe_load(file.read_text())
    obj["measurements"][0]["elevation_m"] = 9876
    file.write_text(yaml.safe_dump(obj, allow_unicode=True))
    snap = acquisition([feature(lon=19.802)])(work, "gha-forged")
    base = commit_data(work, "hide history edit before batch base")
    report = compare(
        work,
        snap,
        batch_id="gha-forged",
        base_commit=base,
        state=accepted_state_at(work, main),
        protect_best=True,
        candidate_policy=CandidatePolicy(),
    )
    report["accepted_state_commit"] = main
    changes, decisions = prepare_batch(work, report)
    folder = work / batch_path("gha-forged")
    folder.mkdir(parents=True)
    (folder / "changes.json").write_bytes(json_bytes(changes))
    (folder / "decisions.yml").write_bytes(json_bytes(decisions))
    apply_batch(work, changes, decisions, reviewers=set())
    forged = commit_data(work, "self-consistent forged candidate")
    g = FakeGitHub(root, main)
    if stage == "recovery":
        g.push(work, forged, "tpn-sync/gha-forged")
        g.writes.clear()
    with pytest.raises(ValueError, match="base|basis"):
        if stage == "recovery":
            plan(g, root, tmp_path / "recovery-forged")
        else:
            from gps_kataster_obiektow_tatr.tpn_snapshot import sha256
            from gps_kataster_obiektow_tatr.tpn_workflow import write_bundle

            out = tmp_path / "publisher-forged"
            doc = plan(g, root, out)
            bundle = out / "candidate.bundle"
            bundle.unlink()
            write_bundle(work, main, forged, bundle)
            doc.update(
                head=forged, batch_id="gha-forged", bundle_sha256=sha256(bundle.read_bytes())
            )
            (out / "plan.json").write_text(json.dumps(doc))
            i.publish_workflow(
                root,
                g,
                out,
                actor="maintainer",
                triggering_actor="maintainer",
                trusted_sha=main,
                operation="prepare",
                run_id="123",
                pr_number=0,
                expected_head="",
            )
    assert not g.writes


def test_orphan_recovery_cannot_adopt_fabricated_final_reviewer(batch_repo, tmp_path):
    integration()
    root, _ = batch_repo
    main = accepted(batch_repo)
    g = FakeGitHub(root, main)
    out = tmp_path / "orphan"
    doc = plan(g, root, out)
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch, load_batch
    from gps_kataster_obiektow_tatr.tpn_workflow import commit_data

    work = out / "work"
    changes, decisions = load_batch(work, doc["batch_id"])
    decisions["decisions"][0].update(
        status="defer",
        reviewed_by="github:impersonated",
        reviewed_at="2026-10-21T12:00:00Z",
        reason="Forged reviewer",
        actions=[],
    )
    apply_batch(work, changes, decisions, reviewers={"github:impersonated"})
    forged = commit_data(work, "fabricated operator")
    g.push(work, forged, doc["branch"])
    g.writes.clear()
    with pytest.raises(ValueError, match="pending|reviewer"):
        plan(g, root, tmp_path / "orphan-recovery", run_id="124")
    assert not g.writes


def test_fork_with_reserved_branch_name_cannot_block_workflow(batch_repo, tmp_path):
    integration()
    root, _ = batch_repo
    g = FakeGitHub(root, accepted(batch_repo))
    g.items.append(
        {
            "state": "open",
            "number": 99,
            "base": {"ref": "main"},
            "head": {"ref": "tpn-sync/unrelated", "repo": {"full_name": "fork/catalog"}},
        }
    )
    g.items.append(
        {
            "state": "closed",
            "number": 98,
            "base": {"ref": "main"},
            "head": {"ref": "tpn-sync/deleted-fork", "repo": None},
        }
    )
    assert plan(g, root, tmp_path / "own-batch")["outcome"] == "publish"
