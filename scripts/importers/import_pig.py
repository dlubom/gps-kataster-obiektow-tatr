#!/usr/bin/env python3
"""Generate reviewable PIG staging proposals without writing final YAML."""

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
from gps_kataster_obiektow_tatr.pig_staging import (  # noqa: E402
    DEFAULT_PIG_SOURCE,
    DEFAULT_PIG_STAGING_DIR,
    build_pig_staging,
    write_staging_files,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Generate PIG staging proposals without creating final YAML.",
    )
    parser.add_argument(
        "--pig-source",
        type=Path,
        default=DEFAULT_PIG_SOURCE,
        help="PIG CSV or XLSX source path. Defaults to the repository CSV export.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Existing final data directory used only to avoid proposed ID collisions.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_PIG_STAGING_DIR,
        help="Staging output directory. Defaults to build/staging/pig.",
    )
    parser.add_argument(
        "--generated-at",
        default=None,
        help="Override generated timestamp, mainly for deterministic tests.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the PIG staging importer command line interface."""

    args = build_parser().parse_args(argv)
    generated_at = args.generated_at or _utc_timestamp()

    report = build_pig_staging(
        args.pig_source,
        generated_at=generated_at,
        data_dir=args.data_dir,
    )
    json_path, markdown_path = write_staging_files(report, output_dir=args.output_dir)

    print(f"wrote: {json_path}")
    print(f"wrote: {markdown_path}")
    print(
        "PIG staging: "
        f"{report.record_count} records, "
        f"{len(report.proposed_caves)} cave proposals, "
        f"{len(report.proposed_objects)} object proposals, "
        f"{len(report.issues)} issues"
    )

    return 0


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
