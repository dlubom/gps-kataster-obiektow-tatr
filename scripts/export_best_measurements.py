#!/usr/bin/env python3
"""Export selected best measurements from source YAML."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gps_kataster_obiektow_tatr.best_measurements_export import (  # noqa: E402
    DEFAULT_EXPORT_DIR,
    export_best_measurements,
)
from gps_kataster_obiektow_tatr.catalog_cli import (  # noqa: E402
    add_catalog_arguments,
    add_generated_at_argument,
    print_error,
)
from gps_kataster_obiektow_tatr.report_formatting import utc_timestamp  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Export build/exports/best-measurements.* from YAML data."
    )
    add_catalog_arguments(parser)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_EXPORT_DIR,
        help="Export output directory. Defaults to build/exports/.",
    )
    add_generated_at_argument(parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the best-measurements export command line interface."""

    args = build_parser().parse_args(argv)
    generated_at = args.generated_at or utc_timestamp()

    try:
        result = export_best_measurements(
            data_dir=args.data_dir,
            base_ref=args.base_ref,
            history_repo=args.history_repo,
            output_dir=args.output_dir,
            generated_at=generated_at,
        )
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        return print_error(exc)

    for path in result.artifact_paths:
        print(f"wrote: {path}")
    print(f"best-measurements export: {result.feature_count} features")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
