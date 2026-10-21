"""Manual TPN workflow: real Git, snapshots and applier, without GitHub writes."""

import importlib.util
import json
from pathlib import Path

import pytest
from test_tpn_batch import append_action, git, hashes, prepare
from test_tpn_batch import batch_repo as batch_repo
from test_tpn_changes import GUID2, feature, snapshot

REPO = Path(__file__).resolve().parents[1]


def workflow():
    name = "gps_kataster_obiektow_tatr.tpn_workflow"
    assert importlib.util.find_spec(name) is not None, "manual workflow is not implemented"
    from gps_kataster_obiektow_tatr import tpn_workflow

    return tpn_workflow


def accepted(root_and_snapshot):
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch

    root, _ = root_and_snapshot
    changes, decisions = prepare(root_and_snapshot)
    apply_batch(root, changes, decisions, reviewers={"human"})
    git(root, "add", ".")
    git(root, "commit", "-qm", "human accepted first batch")
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    return git(root, "rev-parse", "HEAD")


def acquisition(features):
    return lambda root, ident: snapshot(root, ident, features)


def test_prepare_requires_accepted_initial_batch(batch_repo):
    w = workflow()
    root, _ = batch_repo
    before = hashes(root)
    with pytest.raises(ValueError, match="human merge|accepted"):
        w.prepare_candidate(root, git(root, "rev-parse", "HEAD"), "gha-1", acquisition([]))
    assert hashes(root) == before


def test_prepare_pending_apply_replay_and_noop(batch_repo):
    w = workflow()
    from gps_kataster_obiektow_tatr.tpn_batch import check_batch, load_batch

    root, _ = batch_repo
    main = accepted(batch_repo)
    original = (root / "data/objects/KSW/KSW-0001.yml").read_bytes()
    result = w.prepare_candidate(root, main, "gha-2", acquisition([feature(lon=19.802)]))
    assert result["outcome"] == "publish"
    assert (root / "data/objects/KSW/KSW-0001.yml").read_bytes() == original
    changes, decisions = load_batch(root, "gha-2")
    assert decisions["decisions"][0]["status"] == "pending"
    assert decisions["decisions"][0]["reviewed_by"] is None
    with pytest.raises(ValueError, match="pending"):
        check_batch(root, "gha-2")
    decision_file = root / "data/source_reviews/tpn/gha-2/decisions.yml"
    decisions["decisions"][0].update(
        status="defer",
        reviewed_by="github:maintainer",
        reviewed_at="2026-10-21T12:00:00Z",
        reason="Need field evidence",
        actions=[],
    )
    decision_file.write_text(json.dumps(decisions))
    git(root, "add", str(decision_file))
    git(root, "commit", "-qm", "operator decision")
    head = git(root, "rev-parse", "HEAD")
    applied = w.apply_candidate(root, main, "gha-2", "maintainer")
    assert applied["head"] != head
    check_batch(root, "gha-2")
    assert w.apply_candidate(root, main, "gha-2", "maintainer")["outcome"] == "noop"
    # A human merge is simulated only in the isolated fixture.
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    merged = git(root, "rev-parse", "HEAD")
    result = w.prepare_candidate(root, merged, "gha-3", acquisition([feature(lon=19.802)]))
    assert result["outcome"] == "noop"


def test_automatic_new_yaml_has_pending_technical_audit(batch_repo):
    w = workflow()
    from gps_kataster_obiektow_tatr.tpn_batch import load_batch

    root, _ = batch_repo
    pig = root / "data/sources/pig"
    pig.mkdir()
    (pig / "pig_otwory_jaskin_.xlsx.-.Export.csv").write_text("ID,Nazwa,Inne nazwy,Nr inw.\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "complete candidate inputs")
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    main = accepted(batch_repo)
    f = feature(guid=GUID2, oid=2, lon=19.86, name="Unikatowy samodzielny otwór")
    f["geometry"]["y"] = 49.24
    f["attributes"].update(GENEZA="jaskinia", WER_LOK=None, UWAGI=None, OPIS=None, TATER=None)
    w.prepare_candidate(root, main, "gha-4", acquisition([feature(lon=19.801), f]))
    _, decisions = load_batch(root, "gha-4")
    assert all(d["status"] == "pending" for d in decisions["decisions"])
    objects = list((root / "data/objects").rglob("*.yml"))
    assert len(objects) == 2
    import yaml

    new = next(yaml.safe_load(p.read_text()) for p in objects if p.name != "KSW-0001.yml")
    assert new["created_by"] == "automatic:tpn-proposal"


def test_other_reviewer_and_changed_main_block_apply(batch_repo):
    w = workflow()
    root, _ = batch_repo
    main = accepted(batch_repo)
    w.prepare_candidate(root, main, "gha-5", acquisition([feature(lon=19.802)]))
    decision_file = root / "data/source_reviews/tpn/gha-5/decisions.yml"
    doc = json.loads(decision_file.read_text())
    doc["decisions"][0].update(
        status="approve",
        reviewed_by="github:somebody-else",
        reviewed_at="2026-10-21T12:00:00Z",
        reason="Fake attribution",
    )
    decision_file.write_text(json.dumps(doc))
    before = hashes(root)
    with pytest.raises(ValueError, match="reviewer|dispatcher"):
        w.apply_candidate(root, main, "gha-5", "maintainer")
    assert hashes(root) == before
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    with pytest.raises(ValueError, match="main"):
        w.apply_candidate(root, main, "gha-5", "maintainer")


def test_refresh_keeps_old_head_in_history_and_resets_pending(batch_repo):
    w = workflow()
    from gps_kataster_obiektow_tatr.tpn_batch import load_batch

    root, _ = batch_repo
    main = accepted(batch_repo)
    first = w.prepare_candidate(root, main, "gha-6", acquisition([feature(lon=19.802)]))
    old = first["head"]
    git(root, "reset", "--hard", main)
    second = w.prepare_candidate(
        root, main, "gha-7", acquisition([feature(lon=19.803)]), previous_head=old
    )
    git(root, "merge-base", "--is-ancestor", old, second["head"])
    git(root, "merge-base", "--is-ancestor", main, second["head"])
    _, decisions = load_batch(root, "gha-7")
    assert all(d["status"] == "pending" for d in decisions["decisions"])
    assert not (root / "data/source_reviews/tpn/gha-6").exists()
    assert git(root, "show", old + ":data/source_reviews/tpn/gha-6/decisions.yml")


def test_incomplete_source_never_creates_a_commit(batch_repo):
    w = workflow()
    root, _ = batch_repo
    main = accepted(batch_repo)

    def fail(*args):
        raise ValueError("incomplete API")

    with pytest.raises(ValueError, match="incomplete"):
        w.prepare_candidate(root, main, "gha-8", fail)
    assert git(root, "rev-parse", "HEAD") == main


def test_pr_code_and_symlinks_are_rejected_before_loading_data(batch_repo):
    w = workflow()
    root, _ = batch_repo
    main = accepted(batch_repo)
    (root / "injected.py").write_text("raise SystemExit('must never run')\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "malicious code")
    with pytest.raises(ValueError, match="path|data"):
        w.validate_branch(root, main, git(root, "rev-parse", "HEAD"))
    git(root, "reset", "--hard", main)
    (root / "data/objects/KSW/injected.yml").symlink_to("/tmp/secret")
    git(root, "add", ".")
    git(root, "commit", "-qm", "malicious symlink")
    with pytest.raises(ValueError, match="regular|mode|symlink"):
        w.validate_branch(root, main, git(root, "rev-parse", "HEAD"))


def test_pending_existing_proposal_is_visible_but_requires_human_to_apply(batch_repo):
    workflow()
    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch, check_batch

    root, _ = batch_repo
    changes, decisions = prepare(batch_repo, [append_action()], status="pending")
    decisions["decisions"][0].update(reviewed_by=None, reviewed_at=None)
    original = (root / "data/objects/KSW/KSW-0001.yml").read_bytes()
    plan = apply_batch(root, changes, decisions, reviewers=set())
    assert plan["pending"] == 1
    assert (root / "data/objects/KSW/KSW-0001.yml").read_bytes() == original
    with pytest.raises(ValueError, match="pending"):
        check_batch(root, "fixture-batch")
    decisions["decisions"][0].update(
        status="approve", reviewed_by="github:maintainer", reviewed_at="2026-10-21T12:00:00Z"
    )
    apply_batch(root, changes, decisions, reviewers={"github:maintainer"})
    import yaml

    assert (
        len(yaml.safe_load((root / "data/objects/KSW/KSW-0001.yml").read_text())["measurements"])
        == 2
    )
    check_batch(root, "fixture-batch")
