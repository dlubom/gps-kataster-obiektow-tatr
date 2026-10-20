"""Revision-bound TPN batch planning, atomic application and merge verification."""

from __future__ import annotations

import difflib
import io
import re
import tarfile
import tempfile
from contextlib import contextmanager
from copy import deepcopy
from itertools import islice
from pathlib import Path

from .tpn_api import require
from .tpn_batch_actions import DomainPlan
from .tpn_batch_protocol import prepare_documents, validate_documents
from .tpn_best_migration import verified_manual_selection_tree
from .tpn_candidates import CandidatePolicy
from .tpn_changes import Catalog, compare
from .tpn_duplicate_state import read_accepted_duplicates
from .tpn_normalization import CSV_PATH, canonical, digest, exact_json, read_csv, same_location
from .tpn_snapshot import POLICY, sha256, validate_id
from .tpn_source_state import STATE_PATH, git, validate_state
from .tpn_transaction import batch_lock, publish_tree, tree_hashes


def batch_path(batch_id):
    validate_id(batch_id)
    return f"data/source_reviews/tpn/{batch_id}"


def json_bytes(value):
    return canonical(value) + b"\n"


@contextmanager
def base_checkout(root, commit):
    require(
        isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit), "invalid base commit"
    )
    raw = git(root, "archive", "--format=tar", commit)
    with tempfile.TemporaryDirectory(prefix="tpn-base-") as folder:
        base = Path(folder).resolve()
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            for item in archive:
                path = Path(item.name)
                require(
                    not path.is_absolute()
                    and ".." not in path.parts
                    and not item.issym()
                    and not item.islnk(),
                    "unsafe Git base entry",
                )
                if item.isdir():
                    (base / path).mkdir(parents=True, exist_ok=True)
                else:
                    require(item.isfile(), "nonregular Git base entry")
                    (base / path).parent.mkdir(parents=True, exist_ok=True)
                    (base / path).write_bytes(archive.extractfile(item).read())
        # Git does not preserve empty required directories.
        for name in ("objects", "caves", "relations"):
            (base / "data" / name).mkdir(parents=True, exist_ok=True)
        yield base


def accepted_state_at(root, commit):
    paths = git(root, "ls-tree", "--name-only", commit, "--", STATE_PATH).decode().splitlines()
    return exact_json(git(root, "show", f"{commit}:{STATE_PATH}")) if paths else None


def _evidence_differences(expected, actual, path="$"):
    """Describe exact mismatches without changing the canonical acceptance rule."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        if expected.keys() != actual.keys():
            yield path + "/keys", sorted(expected), sorted(actual)
        for key in sorted(expected.keys() & actual.keys()):
            escaped = key.replace("~", "~0").replace("/", "~1")
            yield from _evidence_differences(expected[key], actual[key], path + "/" + escaped)
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            yield path + "/length", len(expected), len(actual)
        for index, (left, right) in enumerate(zip(expected, actual, strict=False)):
            yield from _evidence_differences(left, right, f"{path}/{index}")
    elif canonical(expected) != canonical(actual):
        yield path, expected, actual


def verify_changes(root, base, changes, allow_merged=False):
    require(
        changes.get("format") == "tpn-changes"
        and type(changes.get("format_version")) is int
        and changes["format_version"] == 1,
        "unsupported changes format/version",
    )
    accepted = changes.get("accepted_state_commit")
    require(
        isinstance(accepted, str) and re.fullmatch(r"[0-9a-f]{40}", accepted),
        "missing accepted main commit",
    )
    main = git(root, "rev-parse", "refs/remotes/origin/main").decode().strip()
    require(main == accepted or allow_merged, "main advanced: regenerate review from current main")
    if allow_merged:
        git(root, "merge-base", "--is-ancestor", accepted, main)
    state = accepted_state_at(root, accepted)
    require(digest(state) == changes["state_hash"], "accepted state mismatch")
    snapshots = list((base / "data/sources/tpn/snapshots").glob("*/manifest.json"))
    matches = [
        p.parent
        for p in snapshots
        if exact_json(p.read_bytes()).get("snapshot_hash") == changes["snapshot_hash"]
    ]
    require(len(matches) == 1, "snapshot must be durable in base Git commit")
    policy = changes.get("candidate_policy")
    expected = compare(
        base,
        matches[0],
        batch_id=changes["batch_id"],
        base_commit=changes["base_commit"],
        state=state,
        candidate_policy=CandidatePolicy(policy["name_similarity_threshold"], policy["radius_m"])
        if policy
        else None,
        protect_best="best_protection" in changes,
        duplicate_resolutions=read_accepted_duplicates(root, accepted) if policy else None,
    )
    expected["accepted_state_commit"] = accepted
    actual = {k: v for k, v in changes.items() if k != "execution"}
    if canonical(expected) != canonical(actual):
        details = "; ".join(
            f"{path}: expected={canonical(left).decode()[:200]} "
            f"actual={canonical(right).decode()[:200]}"
            for path, left, right in islice(_evidence_differences(expected, actual), 12)
        )
        require(False, "changes evidence/schema mismatch; regenerate report; " + details)
    return state


def prepare_batch(root, report, proposals=None):
    root = Path(root).resolve()
    with base_checkout(root, report["base_commit"]) as base:
        verify_changes(root, base, report)
        require(Catalog(root).hash == report["catalog_hash"], "stale catalog before preparation")
    return prepare_documents(report, proposals)


def current_nonbatch(root, batch_id):
    prefix = f"source_reviews/tpn/{batch_id}/"
    return {k: v for k, v in tree_hashes(root / "data").items() if not k.startswith(prefix)}


def result_hashes(base, files):
    hashes = dict(Catalog(base).hashes)
    for p, raw in files.items():
        if p.startswith(("data/objects/", "data/caves/", "data/relations/")):
            if raw is None:
                hashes.pop(p, None)
            else:
                hashes[p] = sha256(raw)
    return hashes, digest(sorted(hashes.items()))


def make_state(changes, decisions, previous, domain, files):
    policy = changes["policy_hash"]
    state = (
        deepcopy(previous)
        if previous
        else {
            "format": "tpn-source-state",
            "format_version": 1,
            "accepted_snapshot_hash": changes["snapshot_hash"],
            "policy_hash": policy,
            "bindings": {},
            "resolutions": [],
            "deferred": [],
        }
    )
    # A partially reviewed batch cannot advertise a new accepted baseline.
    pending = any(d["status"] == "pending" for d in decisions["decisions"])
    if not pending:
        state["accepted_snapshot_hash"] = changes["snapshot_hash"]
    rows = {r["change_id"]: r for r in changes["records"]}
    after_hashes, after_catalog = result_hashes(domain.root, files)
    for d in decisions["decisions"]:
        if d["status"] == "pending":
            continue
        row = rows[d["change_id"]]
        oid = domain.row_targets.get(d["change_id"])
        if oid is None and d["target"]:
            oid = d["target"].get("object_id")
        target = {"object_id": oid, "cave_id": domain.objects[oid].get("cave_id")} if oid else None
        target_paths = []
        if oid:
            target_paths.append(domain.paths[oid])
            if target["cave_id"]:
                target_paths.append(domain.paths[target["cave_id"]])
            target_paths.extend(
                domain.paths[r["id"]]
                for r in domain.catalog.relations
                if oid in (r.get("from_object_id"), r.get("to_object_id"))
            )
        locations = domain.applied[d["change_id"]] if d["status"] == "approve" else []
        if d["status"] == "approve" and oid:
            obj = domain.objects[oid]
            if any(
                r.get("system") == "TPN"
                and r.get("ref_type") == "source_globalid"
                and r["external_id"].strip("{}").lower() == row["globalid"]
                for r in obj["external_refs"]
            ):
                state["bindings"][row["globalid"]] = oid
            if (
                not locations
                and len(row["history"]["current_matches"]) == 1
                and row["source_after"]
            ):
                match = row["history"]["current_matches"][0]
                # Do not attribute another GUID's measurement to this GUID.
                if match["source_globalid"] == row["globalid"]:
                    csv_evidence = None
                    inherited_csv = any(
                        r["globalid"] == row["globalid"]
                        and any(
                            loc["measurement_id"] == match["measurement_id"]
                            and loc["csv_evidence"] is not None
                            for loc in r["applied_locations"]
                        )
                        for r in state["resolutions"]
                    )
                    if (
                        match["basis"] in ("csv_conversion_tolerance", "accepted_csv_bootstrap")
                        or inherited_csv
                    ):
                        csv_record = read_csv(domain.root / CSV_PATH).get(row["globalid"])
                        require(
                            csv_record is not None
                            and same_location(csv_record, row["source_after"]),
                            "bootstrap provenance no longer matches source",
                        )
                        csv_evidence = {
                            "kind": "csv_bootstrap",
                            "path": CSV_PATH.as_posix(),
                            "raw_sha256": sha256((domain.root / CSV_PATH).read_bytes()),
                        }
                    locations = [
                        {
                            "location_hash": row["location_hash"],
                            "measurement_id": match["measurement_id"],
                            "source_snapshot_hash": changes["snapshot_hash"],
                            "csv_evidence": csv_evidence,
                        }
                    ]
        resolution = {
            **{
                k: d[k]
                for k in (
                    "globalid",
                    "revision_hash",
                    "status",
                    "reviewed_by",
                    "reviewed_at",
                    "reason",
                )
            },
            "snapshot_hash": changes["snapshot_hash"],
            "target": target,
            "preimage": d["preimage"],
            "catalog_hash": changes["catalog_hash"],
            "policy_hash": policy,
            "batch_id": changes["batch_id"],
            "changes_hash": decisions["changes_hash"],
            "applied_locations": locations,
            "result_hashes": {p: after_hashes[p] for p in sorted(target_paths)},
            "result_catalog_hash": after_catalog,
            "absence": {
                "baseline": changes["baseline"],
                "previous_revision_hash": row["source_before"]["revision_hash"],
            }
            if row["source_after"] is None
            else None,
        }
        state["resolutions"] = [
            r
            for r in state["resolutions"]
            if (r["globalid"], r["revision_hash"]) != (d["globalid"], d["revision_hash"])
        ] + [resolution]
    state["deferred"] = [
        {k: r[k] for k in ("globalid", "revision_hash", "snapshot_hash")}
        for r in state["resolutions"]
        if r["status"] == "defer"
    ]
    validate_state(state, policy)
    return state


def export_rows(dataset):
    from dataclasses import asdict

    from .best_measurements_export import _collect_best_measurement_rows

    objects = {r.data["id"]: r.data for r in dataset.objects}
    caves = {r.data["id"]: r.data for r in dataset.caves}
    return {
        row.object_id: {
            "best": asdict(row),
            "full_object": objects[row.object_id],
            "cave": caves.get(row.cave_id),
        }
        for row in _collect_best_measurement_rows(dataset)
    }


def _compute(root, base, changes, decisions, reviewers, allow_pending, allow_merged=False):
    previous = verify_changes(root, base, changes, allow_merged)
    validate_documents(changes, decisions, reviewers=reviewers, allow_pending=allow_pending)
    domain = DomainPlan(base, changes, decisions)
    files = domain.run()
    state = make_state(changes, decisions, previous, domain, files)
    # Candidate state is local to the PR until main's human merge.
    files[STATE_PATH] = json_bytes(state)
    old_rows, new_rows = export_rows(domain.dataset), export_rows(domain.future)
    exports = [
        {"object_id": oid, "before": old_rows.get(oid), "after": new_rows.get(oid)}
        for oid in sorted(old_rows.keys() | new_rows.keys())
        if old_rows.get(oid) != new_rows.get(oid)
    ]
    diff = "".join(
        "".join(
            difflib.unified_diff(
                (base / p).read_text().splitlines(True) if (base / p).exists() else [],
                raw.decode().splitlines(True),
                fromfile="a/" + p,
                tofile="b/" + p,
            )
        )
        for p, raw in sorted(files.items())
    )
    return files, {
        "format": "tpn-batch-plan",
        "format_version": 1,
        "batch_id": changes["batch_id"],
        "decisions_hash": sha256(json_bytes(decisions)),
        "changes_hash": decisions["changes_hash"],
        "files": {p: sha256(raw) for p, raw in sorted(files.items())},
        "id_map": {f"{kind}:{key}": ident for (kind, key), ident in sorted(domain.keys.items())},
        "measurement_map": {
            f"{oid}:{key}": mid for (oid, key), mid in sorted(domain.measurement_keys.items())
        },
        "best_changes": domain.best_changes,
        "export_changes": exports,
        "diff": diff,
        "pending": sum(d["status"] == "pending" for d in decisions["decisions"]),
        "deferred": state["deferred"],
    }


def _plan(root, changes, decisions, reviewers, allow_pending=True, check_only=False):
    prefix = batch_path(changes["batch_id"])
    receipt_path = root / prefix / "application.json"
    receipt = exact_json(receipt_path.read_bytes()) if receipt_path.exists() else None
    # A historical result may be verified/replayed after its own human merge.
    # A merely advanced main never authorizes applying old or edited decisions.
    main = git(root, "rev-parse", "refs/remotes/origin/main").decode().strip()
    main_paths = (
        git(root, "ls-tree", "--name-only", main, "--", prefix + "/application.json")
        .decode()
        .splitlines()
    )
    allow_merged = False
    if receipt and main_paths:
        merged_receipt = exact_json(git(root, "show", main + ":" + prefix + "/application.json"))
        merged_decisions = exact_json(git(root, "show", main + ":" + prefix + "/decisions.yml"))
        allow_merged = canonical(merged_receipt) == canonical(receipt) and canonical(
            merged_decisions
        ) == canonical(decisions)
    with base_checkout(root, changes["base_commit"]) as base:
        require(
            tree_hashes(root / "config") == tree_hashes(base / "config"),
            "configuration preimage changed",
        )
        require(
            (root / POLICY).read_bytes() == (base / POLICY).read_bytes(), "policy preimage changed"
        )
        require(
            tree_hashes(root / "schema") == tree_hashes(base / "schema"), "schema preimage changed"
        )
        files, plan = _compute(
            root, base, changes, decisions, reviewers, allow_pending, allow_merged
        )
        base_tree = current_nonbatch(base, changes["batch_id"])
        outcome = dict(base_tree)
        for p, raw in files.items():
            outcome[p.removeprefix("data/")] = sha256(raw)
        current = current_nonbatch(root, changes["batch_id"])
        checked_outcome = outcome
        if check_only:
            checked_outcome = verified_manual_selection_tree(
                root,
                batch_id=changes["batch_id"],
                plan_hash=digest(plan),
                expected_tree=outcome,
            )
            require(current == checked_outcome, "actual diff/output does not match decisions")
            require(
                receipt is not None and receipt["plan_hash"] == digest(plan),
                "missing/inconsistent application plan",
            )
        if receipt:
            require(
                receipt.get("format") == "tpn-batch-application"
                and receipt.get("format_version") == 1
                and receipt.get("changes_hash") == decisions["changes_hash"],
                "application basis mismatch",
            )
            # A receipt is evidence, never authority to overwrite data. Reconstruct its
            # result from the immutable Git base and archived decision snapshot.
            from .tpn_source_state import hash_value

            hash_value(receipt.get("decisions_hash"))
            history_path = root / prefix / "applications" / (receipt["decisions_hash"] + ".json")
            archived = exact_json(history_path.read_bytes())
            require(
                set(archived) == {"application", "decisions"}
                and archived["application"] == receipt,
                "application history mismatch",
            )
            old_decisions = archived["decisions"]
            require(
                sha256(json_bytes(old_decisions)) == receipt["decisions_hash"],
                "archived decisions mismatch",
            )
            old_reviewers = {
                d["reviewed_by"] for d in old_decisions["decisions"] if d["reviewed_by"] is not None
            }
            old_files, old_plan = _compute(
                root, base, changes, old_decisions, old_reviewers, True, allow_merged
            )
            old_outcome = dict(base_tree)
            for p, raw in old_files.items():
                old_outcome[p.removeprefix("data/")] = sha256(raw)
            require(
                receipt["plan_hash"] == digest(old_plan)
                and canonical(receipt["plan"]) == canonical(old_plan)
                and receipt["result_tree"] == old_outcome,
                "application result evidence mismatch",
            )
            checked_old_outcome = (
                verified_manual_selection_tree(
                    root,
                    batch_id=changes["batch_id"],
                    plan_hash=digest(old_plan),
                    expected_tree=old_outcome,
                )
                if check_only
                else old_outcome
            )
            require(
                current == checked_old_outcome,
                "previous result/output changed; new review required",
            )
            # Every older linked decision remains durable, even after rejection of
            # an automatic proposal. Validate the chain, not only its newest tip.
            prior = receipt.get("previous_decisions_hash")
            seen = {receipt["decisions_hash"]}
            while prior is not None:
                hash_value(prior)
                require(prior not in seen, "cyclic decision history")
                seen.add(prior)
                older = exact_json(
                    (root / prefix / "applications" / (prior + ".json")).read_bytes()
                )
                require(
                    set(older) == {"application", "decisions"}
                    and sha256(json_bytes(older["decisions"])) == prior,
                    "invalid previous decision history",
                )
                old_app = older["application"]
                people = {
                    d["reviewed_by"]
                    for d in older["decisions"]["decisions"]
                    if d["reviewed_by"] is not None
                }
                ofiles, oplan = _compute(
                    root, base, changes, older["decisions"], people, True, allow_merged
                )
                otree = dict(base_tree)
                for p, raw in ofiles.items():
                    otree[p.removeprefix("data/")] = sha256(raw)
                require(
                    old_app["plan_hash"] == digest(oplan)
                    and canonical(old_app["plan"]) == canonical(oplan)
                    and old_app["result_tree"] == otree,
                    "invalid previous application",
                )
                prior = old_app.get("previous_decisions_hash")
        elif not check_only:
            require(current == base_tree, "stale preimage/catalog/data outside base")
        # The active batch is immutable except the editable decision file and supplied documents.
        folder = root / prefix
        if folder.exists():
            for path in folder.rglob("*"):
                if path.is_dir():
                    continue
                name = path.relative_to(folder).as_posix()
                require(
                    name
                    in (
                        "changes.json",
                        "decisions.yml",
                        "report.md",
                        "checksums.json",
                        "application.json",
                    )
                    or name.startswith("applications/"),
                    "unknown batch evidence file",
                )
            if (folder / "changes.json").exists():
                require(
                    (folder / "changes.json").read_bytes() == json_bytes(changes),
                    "immutable changes file mismatch",
                )
        plan["noop"] = bool(
            receipt and receipt.get("plan_hash") == digest(plan) and current == checked_outcome
        )
        # noop is a runtime observation, not part of the deterministic plan hash.
        stable = {k: v for k, v in plan.items() if k != "noop"}
        application = {
            "format": "tpn-batch-application",
            "format_version": 1,
            "changes_hash": decisions["changes_hash"],
            "decisions_hash": sha256(json_bytes(decisions)),
            "plan_hash": digest(stable),
            "result_tree": outcome,
            "plan": stable,
            "previous_decisions_hash": receipt.get("previous_decisions_hash")
            if receipt and plan["noop"]
            else receipt["decisions_hash"]
            if receipt
            else None,
        }
        if check_only:
            require(canonical(application) == canonical(receipt), "application receipt mismatch")
        # Previously committed evidence is append-only, including intermediate reviews.
        for name in (
            git(root, "ls-tree", "-r", "--name-only", "HEAD", "--", prefix + "/applications")
            .decode()
            .splitlines()
        ):
            require(
                (root / name).is_file()
                and (root / name).read_bytes() == git(root, "show", "HEAD:" + name),
                "committed decision history modified or missing",
            )
        outputs = dict(files)
        if receipt:
            old_files = receipt["plan"]["files"]
            # Replan from base; remove ONLY own hash-verified generated files.
            for p in old_files.keys() - files.keys():
                outputs[p] = (base / p).read_bytes() if (base / p).exists() else None
        outputs[prefix + "/changes.json"] = json_bytes(changes)
        outputs[prefix + "/decisions.yml"] = json_bytes(decisions)  # JSON is a strict YAML subset.
        outputs[prefix + "/application.json"] = json_bytes(application)
        history = prefix + "/applications/" + application["decisions_hash"] + ".json"
        archive = json_bytes({"application": application, "decisions": decisions})
        if (root / history).exists():
            require((root / history).read_bytes() == archive, "immutable decision history mismatch")
        outputs[history] = archive
        return plan, outputs


def plan_batch(root, changes, decisions, *, reviewers, allow_pending=True):
    root = Path(root).resolve()
    plan, _ = _plan(root, changes, decisions, reviewers, allow_pending)
    return plan


def apply_batch(root, changes, decisions, *, reviewers):
    root = Path(root).resolve()
    with batch_lock(root):
        expected = tree_hashes(root / "data")
        config_hash = tree_hashes(root / "config")
        schema_hash = tree_hashes(root / "schema")
        policy_hash = sha256((root / POLICY).read_bytes())
        main_commit = git(root, "rev-parse", "refs/remotes/origin/main")
        plan, outputs = _plan(root, changes, decisions, reviewers)
        if not plan["noop"]:
            # Re-run the same complete planner, including PBI-099, immediately before staging.
            again, _ = _plan(root, changes, decisions, reviewers)
            require(again == plan, "plan changed during preflight")

            def precommit():
                require(
                    tree_hashes(root / "config") == config_hash
                    and tree_hashes(root / "schema") == schema_hash
                    and sha256((root / POLICY).read_bytes()) == policy_hash
                    and git(root, "rev-parse", "refs/remotes/origin/main") == main_commit,
                    "configuration/main changed during transaction",
                )

            publish_tree(root, outputs, expected, precommit=precommit)
    return plan


def load_batch(root, batch_id):
    from .yaml_io import load_unique_yaml

    folder = root / batch_path(batch_id)
    return exact_json((folder / "changes.json").read_bytes()), load_unique_yaml(
        folder / "decisions.yml"
    )


def check_batch(root, batch_id):
    root = Path(root).resolve()
    changes, decisions = load_batch(root, batch_id)
    reviewers = {d["reviewed_by"] for d in decisions["decisions"] if d["reviewed_by"] is not None}
    plan, _ = _plan(root, changes, decisions, reviewers, allow_pending=False, check_only=True)
    return plan
