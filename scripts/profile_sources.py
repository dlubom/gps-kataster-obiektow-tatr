#!/usr/bin/env python3
"""Profile PIG and TPN CSV exports before staging import."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gps_kataster_obiektow_tatr.source_profile import (  # noqa: E402
    profile_sources,
    write_report_files,
)

DEFAULT_PIG_CSV = REPO_ROOT / "data" / "sources" / "pig" / "pig_otwory_jaskin_.xlsx.-.Export.csv"
DEFAULT_TPN_CSV = REPO_ROOT / "data" / "sources" / "tpn" / "tpn_otwory_jaskin.xlsx.-.Export.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "build" / "reports"


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Profile PIG and TPN CSV exports without creating final YAML.",
    )
    parser.add_argument(
        "--pig-csv",
        type=Path,
        default=DEFAULT_PIG_CSV,
        help="PIG CSV export path. Defaults to the repository export.",
    )
    parser.add_argument(
        "--tpn-csv",
        type=Path,
        default=DEFAULT_TPN_CSV,
        help="TPN CSV export path. Defaults to the repository export.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Report output directory. Defaults to build/reports.",
    )
    parser.add_argument(
        "--generated-at",
        default=None,
        help="Override generated timestamp, mainly for deterministic tests.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the source profiler command line interface."""

    args = build_parser().parse_args(argv)
    generated_at = args.generated_at or _utc_timestamp()

    report = profile_sources(pig_csv=args.pig_csv, tpn_csv=args.tpn_csv)
    json_path, markdown_path = write_report_files(
        report,
        output_dir=args.output_dir,
        generated_at=generated_at,
    )

    print(f"wrote: {json_path}")
    print(f"wrote: {markdown_path}")
    for profile in report.profiles:
        print(
            f"{profile.source}: {profile.record_count} records, "
            f"{profile.column_count} columns, "
            f"{len(profile.missing_columns)} missing expected columns"
        )

    return 0


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
