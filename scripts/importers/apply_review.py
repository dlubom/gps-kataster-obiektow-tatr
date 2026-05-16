#!/usr/bin/env python3
"""Apply operator staging-review decisions and write final YAML."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gps_kataster_obiektow_tatr.data_loader import DEFAULT_DATA_DIR  # noqa: E402
from gps_kataster_obiektow_tatr.staging_review import (  # noqa: E402
    DEFAULT_PIG_STAGING_PATH,
    DEFAULT_REVIEW_OUTPUT_DIR,
    DEFAULT_TPN_STAGING_PATH,
    ReviewDecisionError,
    apply_review_decisions,
    load_review_decisions,
    load_staging_reports,
    write_review_report_files,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Apply staging-review decisions to final YAML data.",
    )
    parser.add_argument(
        "--decisions",
        type=Path,
        required=True,
        help="Operator decision YAML file.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Final data directory to write. Defaults to data/.",
    )
    parser.add_argument(
        "--pig-staging",
        type=Path,
        default=DEFAULT_PIG_STAGING_PATH,
        help="PIG staging JSON path. Missing files are ignored unless decisions reference them.",
    )
    parser.add_argument(
        "--no-pig-staging",
        action="store_true",
        help="Do not load a PIG staging report.",
    )
    parser.add_argument(
        "--tpn-staging",
        type=Path,
        default=DEFAULT_TPN_STAGING_PATH,
        help="TPN staging JSON path. Missing files are ignored unless decisions reference them.",
    )
    parser.add_argument(
        "--no-tpn-staging",
        action="store_true",
        help="Do not load a TPN staging report.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_REVIEW_OUTPUT_DIR,
        help="Directory for staging-review JSON/Markdown reports.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render the review report without writing final YAML.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the staging-review applier command line interface."""

    args = build_parser().parse_args(argv)
    try:
        decisions = load_review_decisions(args.decisions)
        staging_reports = load_staging_reports(
            pig_staging_path=None if args.no_pig_staging else args.pig_staging,
            tpn_staging_path=None if args.no_tpn_staging else args.tpn_staging,
        )
        result = apply_review_decisions(
            decisions,
            staging_reports=staging_reports,
            data_dir=args.data_dir,
            write=not args.dry_run,
        )
    except ReviewDecisionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    json_path, markdown_path = write_review_report_files(result, output_dir=args.output_dir)
    print(f"wrote: {json_path}")
    print(f"wrote: {markdown_path}")

    for path in result.written_paths:
        print(f"wrote final YAML: {path}")

    if result.has_errors:
        print(
            f"staging review failed: {len(result.issues)} issues, final YAML was not written",
            file=sys.stderr,
        )
        return 1

    print(
        "staging review: "
        f"{len(result.applied_decisions)} decisions, "
        f"{len(result.written_paths)} final YAML files, "
        f"{len(result.issues)} issues"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
