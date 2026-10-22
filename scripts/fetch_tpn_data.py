#!/usr/bin/env python3
"""Download TPN caves, sinkholes and mines to one pretty-printed JSON file."""

from __future__ import annotations

import argparse
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, help="New JSON file; existing paths are never replaced"
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="Seconds per HTTP request")
    args = parser.parse_args(argv)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output = (
        args.output
        if args.output is not None
        else (REPO_ROOT / "data" / "sources" / "tpn" / "api" / f"tpn-{stamp}.json")
    )
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Output already exists: {output}")
        snapshot = fetch_snapshot(timeout=args.timeout)
        write_snapshot(output, snapshot)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(output.resolve())
    for name, layer in snapshot["layers"].items():
        print(f"{name}: {layer['record_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
