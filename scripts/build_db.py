#!/usr/bin/env python3
"""Build the generated SQLite catalog from source YAML."""

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

from gps_kataster_obiektow_tatr.build_db import (  # noqa: E402
    DEFAULT_SQLITE_PATH,
    BuildDatabaseValidationError,
    build_sqlite_database,
)
from gps_kataster_obiektow_tatr.data_loader import DEFAULT_DATA_DIR  # noqa: E402
from gps_kataster_obiektow_tatr.validator import format_issue  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(description="Build build/katalog.sqlite from YAML data.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Data root directory. Defaults to data/.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_SQLITE_PATH,
        help="SQLite output path. Defaults to build/katalog.sqlite.",
    )
    parser.add_argument(
        "--generated-at",
        default=None,
        help="Override generated timestamp, mainly for deterministic tests.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the SQLite build command line interface."""

    args = build_parser().parse_args(argv)
    generated_at = args.generated_at or _utc_timestamp()

    try:
        result = build_sqlite_database(
            data_dir=args.data_dir,
            output_path=args.output,
            generated_at=generated_at,
        )
    except BuildDatabaseValidationError as exc:
        for issue in exc.issues:
            print(format_issue(issue))
        return 1

    metadata = result.metadata
    print(f"wrote: {result.sqlite_path}")
    print(
        "SQLite build: "
        f"{metadata['object_count']} objects, "
        f"{metadata['cave_count']} caves, "
        f"{metadata['measurement_count']} measurements, "
        f"{metadata['validation_warning_count']} validation warnings"
    )
    return 0


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
