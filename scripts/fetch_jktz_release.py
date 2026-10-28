#!/usr/bin/env python3
"""Download and verify one latest stable JKTZ snapshot before an offline QGIS build."""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gps_kataster_obiektow_tatr.jktz_snapshot import (  # noqa: E402
    DEFAULT_JKTZ_SOURCE_DIR,
    fetch_latest_jktz,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_JKTZ_SOURCE_DIR)
    args = parser.parse_args()
    try:
        path = fetch_latest_jktz(args.output_dir, token=os.environ.get("GH_TOKEN"))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Verified JKTZ snapshot: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
