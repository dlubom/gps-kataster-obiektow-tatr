#!/usr/bin/env python3
"""Check the YAML measurement history against an accepted Git revision."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gps_kataster_obiektow_tatr.data_loader import (  # noqa: E402
    DataDirectoryError,
    YamlDataLoadError,
    load_dataset,
)
from gps_kataster_obiektow_tatr.measurement_history import (  # noqa: E402
    DEFAULT_BASE_REF,
    check_measurement_history,
)
from gps_kataster_obiektow_tatr.validator import format_issue  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    """Run the history check and return a nonzero exit code for any error."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="Git worktree root.")
    parser.add_argument(
        "--data-dir", type=Path, help="Candidate data directory; defaults to data/."
    )
    parser.add_argument(
        "--base-ref",
        default=DEFAULT_BASE_REF,
        help="Full accepted Git commit SHA; defaults to origin/main.",
    )
    args = parser.parse_args(argv)
    try:
        dataset = load_dataset(args.data_dir or args.repo_root / "data")
    except (DataDirectoryError, YamlDataLoadError, OSError, UnicodeError) as exc:
        print(f"ERROR MEASUREMENT_HISTORY_INVALID: {exc}")
        return 1

    issues = check_measurement_history(dataset, repo_root=args.repo_root, base_ref=args.base_ref)
    if not issues:
        print("OK: accepted measurement history preserved")
        return 0
    for issue in issues:
        print(format_issue(issue))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
