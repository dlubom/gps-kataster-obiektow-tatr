#!/usr/bin/env python3
"""Download TPN caves, sinkholes and mines to one pretty-printed JSON file."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gps_kataster_obiektow_tatr.tpn_download import (  # noqa: E402
    fetch_snapshot,
    write_snapshot,
)
from gps_kataster_obiektow_tatr.tpn_elevation import ElevationClient  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_simple import enrich_simple, simplify_snapshot  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--output", type=Path, help="New JSON file; existing paths are never replaced"
    )
    source.add_argument(
        "--input", type=Path, help="Reuse an existing raw snapshot without downloading"
    )
    parser.add_argument(
        "--simple-dir", type=Path, help="New simple.json and optional NMT files here"
    )
    parser.add_argument(
        "--with-nmt", action="store_true", help="Add simple-nmt.json and NMT evidence"
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="Seconds per HTTP request")
    args = parser.parse_args(argv)
    if (args.input or args.with_nmt) and args.simple_dir is None:
        parser.error("--input and --with-nmt require --simple-dir")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output = (
        args.output
        if args.output is not None
        else (REPO_ROOT / "data" / "sources" / "tpn" / "api" / f"tpn-{stamp}.json")
    )
    try:
        targets = []
        if args.simple_dir is not None:
            targets = [args.simple_dir / "simple.json"]
            if args.with_nmt:
                targets += [
                    args.simple_dir / "simple-nmt.json",
                    args.simple_dir / "nmt-evidence.json",
                ]
        resolved_targets = set()
        for target in targets + ([] if args.input else [output]):
            resolved = target.resolve()
            if resolved in resolved_targets:
                raise ValueError(f"Output paths collide: {resolved}. Choose a different --output.")
            resolved_targets.add(resolved)
            if target.exists() or target.is_symlink():
                raise FileExistsError(f"Output already exists: {target}")
        if args.input:
            output = args.input
            raw = output.read_bytes()
            snapshot = json.loads(raw)
        else:
            snapshot = fetch_snapshot(timeout=args.timeout)
            write_snapshot(output, snapshot)
            raw = output.read_bytes()
        if args.simple_dir is not None:
            plain = simplify_snapshot(snapshot)
            write_snapshot(targets[0], plain)
            print(targets[0].resolve(), flush=True)
            if args.with_nmt:
                client = ElevationClient(timeout=args.timeout)

                def progress(done, total):
                    if done == 1 or done % 25 == 0 or done == total:
                        print(f"NMT: {done}/{total}", file=sys.stderr, flush=True)

                enriched, evidence = enrich_simple(plain, fetch=client.fetch, progress=progress)
                write_snapshot(
                    targets[2],
                    {
                        "input_file": str(output.resolve()),
                        "input_sha256": hashlib.sha256(raw).hexdigest(),
                        "note": (
                            "NMT = wysokość gruntu w m n.p.m.; dokładny układ pionowy "
                            "i dokładność nieznane. Zaokrąglenie do 0,01 m jest "
                            "formatowaniem, nie dokładnością."
                        ),
                        "records": evidence,
                    },
                )
                write_snapshot(targets[1], enriched)
                print(targets[1].resolve(), flush=True)
        print(output.resolve())
        for name, layer in snapshot["layers"].items():
            print(f"{name}: {layer['record_count']}")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
