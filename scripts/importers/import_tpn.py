#!/usr/bin/env python3
"""Generate reviewable TPN staging proposals without writing final YAML."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gps_kataster_obiektow_tatr.data_loader import DEFAULT_DATA_DIR  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_staging import (  # noqa: E402
    DEFAULT_PIG_STAGING_PATH,
    DEFAULT_TPN_SOURCE,
    DEFAULT_TPN_STAGING_DIR,
    build_tpn_staging,
    write_staging_files,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Generate TPN staging proposals without creating final YAML.",
    )
    parser.add_argument(
        "--tpn-source",
        type=Path,
        default=DEFAULT_TPN_SOURCE,
        help="TPN CSV or XLSX source path. Defaults to the repository CSV export.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Existing final data directory used only to avoid proposed ID collisions.",
    )
    parser.add_argument(
        "--pig-staging",
        type=Path,
        default=DEFAULT_PIG_STAGING_PATH,
        help="Optional PIG staging JSON used as a matching baseline.",
    )
    parser.add_argument(
        "--no-pig-staging",
        action="store_true",
        help="Do not use the default PIG staging JSON as a matching baseline.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_TPN_STAGING_DIR,
        help="Staging output directory. Defaults to build/staging/tpn.",
    )
    parser.add_argument(
        "--generated-at",
        default=None,
        help="Override generated timestamp, mainly for deterministic tests.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the TPN staging importer command line interface."""

    args = build_parser().parse_args(argv)
    generated_at = args.generated_at or _utc_timestamp()
    pig_staging_path = None if args.no_pig_staging else args.pig_staging

    report = build_tpn_staging(
        args.tpn_source,
        generated_at=generated_at,
        data_dir=args.data_dir,
        pig_staging_path=pig_staging_path,
    )
    json_path, markdown_path = write_staging_files(report, output_dir=args.output_dir)
    counts = _status_counts(report)

    print(f"wrote: {json_path}")
    print(f"wrote: {markdown_path}")
    print(
        "TPN staging: "
        f"{report.record_count} records, "
        f"{counts['matched']} matched, "
        f"{counts['new']} new, "
        f"{counts['unresolved']} unresolved, "
        f"{counts['rejected']} rejected, "
        f"{len(report.issues)} issues"
    )

    return 0


def _status_counts(report: object) -> dict[str, int]:
    counts = {"matched": 0, "new": 0, "unresolved": 0, "rejected": 0}
    for row in report.rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    return counts


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
