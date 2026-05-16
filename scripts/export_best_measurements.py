#!/usr/bin/env python3
"""Export selected best measurements from source YAML."""

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

from gps_kataster_obiektow_tatr.best_measurements_export import (  # noqa: E402
    DEFAULT_EXPORT_DIR,
    BestMeasurementsExportValidationError,
    export_best_measurements,
)
from gps_kataster_obiektow_tatr.data_loader import DEFAULT_DATA_DIR  # noqa: E402
from gps_kataster_obiektow_tatr.validator import format_issue  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Export build/exports/best-measurements.* from YAML data."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Data root directory. Defaults to data/.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_EXPORT_DIR,
        help="Export output directory. Defaults to build/exports/.",
    )
    parser.add_argument(
        "--generated-at",
        default=None,
        help="Override generated timestamp, mainly for deterministic tests.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the best-measurements export command line interface."""

    args = build_parser().parse_args(argv)
    generated_at = args.generated_at or _utc_timestamp()

    try:
        result = export_best_measurements(
            data_dir=args.data_dir,
            output_dir=args.output_dir,
            generated_at=generated_at,
        )
    except BestMeasurementsExportValidationError as exc:
        for issue in exc.issues:
            print(format_issue(issue))
        return 1

    print(f"wrote: {result.geojson_path}")
    print(f"wrote: {result.csv_path}")
    print(f"wrote: {result.gpx_path}")
    print(f"wrote: {result.shapefile_zip_path}")
    print(f"best-measurements export: {result.feature_count} features")
    return 0


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
