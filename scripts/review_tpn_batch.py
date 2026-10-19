#!/usr/bin/env python3
"""Prepare, preview, apply or check revision-bound TPN decisions (offline)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gps_kataster_obiektow_tatr.tpn_api import require  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_batch import (  # noqa: E402
    apply_batch,
    batch_path,
    check_batch,
    json_bytes,
    load_batch,
    plan_batch,
    prepare_batch,
)
from gps_kataster_obiektow_tatr.tpn_normalization import exact_json  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_source_state import git  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_transaction import (  # noqa: E402
    batch_lock,
    publish_tree,
    tree_hashes,
)
from gps_kataster_obiektow_tatr.yaml_io import load_unique_yaml  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--changes", type=Path, required=True)
    prep.add_argument("--proposals", type=Path)
    for name in ("dry-run", "apply"):
        p = sub.add_parser(name)
        p.add_argument("--batch-id", required=True)
        p.add_argument(
            "--reviewer",
            action="append",
            required=True,
            help="Trusted local operator authorizes reviewer IDs; files do not authorize them.",
        )
    check = sub.add_parser("check")
    group = check.add_mutually_exclusive_group(required=True)
    group.add_argument("--batch-id")
    group.add_argument("--changed-from")
    args = parser.parse_args(argv)
    try:
        root = args.repo_root.resolve()
        if args.command == "prepare":
            report = exact_json(args.changes.read_bytes())
            proposals = load_unique_yaml(args.proposals) if args.proposals else None
            with batch_lock(root):
                expected = tree_hashes(root / "data")
                changes, decisions = prepare_batch(root, report, proposals)
                folder = batch_path(changes["batch_id"])
                require(not (root / folder).exists(), "batch already exists; no overwrite")
                publish_tree(
                    root,
                    {
                        folder + "/changes.json": json_bytes(changes),
                        folder + "/decisions.yml": json_bytes(decisions),
                    },
                    expected,
                )
            print(
                json_bytes(
                    {"batch_id": changes["batch_id"], "pending": len(decisions["decisions"])}
                ).decode(),
                end="",
            )
        elif args.command == "check":
            if args.batch_id:
                ids = [args.batch_id]
            else:
                import re

                require(
                    re.fullmatch(r"[0-9a-f]{40}", args.changed_from) is not None,
                    "invalid comparison commit",
                )
                paths = (
                    git(root, "diff", "--name-only", args.changed_from, "HEAD", "--", "data")
                    .decode()
                    .splitlines()
                )
                ids = sorted(
                    {
                        p.split("/")[3]
                        for p in paths
                        if p.startswith("data/source_reviews/tpn/") and len(p.split("/")) >= 5
                    }
                )
                require(
                    ids or not any(p.startswith("data/source_state/tpn/") for p in paths),
                    "source state changed without reviewed batch",
                )
            for ident in ids:
                check_batch(root, ident)
            print(json_bytes({"checked_batches": ids, "ready": True}).decode(), end="")
        else:
            changes, decisions = load_batch(root, args.batch_id)
            function = apply_batch if args.command == "apply" else plan_batch
            plan = function(root, changes, decisions, reviewers=set(args.reviewer))
            print(json_bytes(plan).decode(), end="")
    except (ValueError, OSError, KeyError, TypeError, StopIteration) as exc:
        print(f"TPN_BATCH_INVALID: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
