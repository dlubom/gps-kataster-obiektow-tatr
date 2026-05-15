#!/usr/bin/env python3
"""Validate source-of-truth YAML data."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gps_kataster_obiektow_tatr.data_loader import DEFAULT_DATA_DIR  # noqa: E402
from gps_kataster_obiektow_tatr.validator import (  # noqa: E402
    exit_code_for_issues,
    format_issue,
    validate_data_dir,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(description="Validate source-of-truth YAML data.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Data root directory. Defaults to data/.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the validator command line interface."""

    args = build_parser().parse_args(argv)
    issues = validate_data_dir(args.data_dir, repo_root=REPO_ROOT)

    if not issues:
        print("OK: no validation issues")
        return 0

    for issue in issues:
        print(format_issue(issue))

    return exit_code_for_issues(issues)


if __name__ == "__main__":
    raise SystemExit(main())
