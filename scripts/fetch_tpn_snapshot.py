#!/usr/bin/env python3
"""Fetch a complete public TPN snapshot or verify a saved snapshot offline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gps_kataster_obiektow_tatr.tpn_api import SnapshotError  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_snapshot import fetch_snapshot, verify_snapshot  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch", help="Read public API; never modify domain YAML")
    fetch.add_argument("--repo-root", type=Path, default=ROOT)
    fetch.add_argument("--snapshot-id", required=True)
    fetch.add_argument("--page-size", type=int, default=2000)
    fetch.add_argument("--attempts", type=int, default=2)
    verify = commands.add_parser("verify", help="Offline raw-byte and semantic readback")
    verify.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    try:
        path = (
            fetch_snapshot(args.repo_root, args.snapshot_id, args.page_size, args.attempts)
            if args.command == "fetch"
            else args.path
        )
        manifest = verify_snapshot(path)
    except SnapshotError as exc:
        print(f"TPN_SNAPSHOT_INVALID: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "path": str(path),
                "snapshot_hash": manifest["snapshot_hash"],
                "feature_count": manifest["checks"]["feature_count"],
                "complete": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
