#!/usr/bin/env python3
"""Build the generated PostgreSQL dump catalog from source YAML."""

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

from gps_kataster_obiektow_tatr.build_db import (  # noqa: E402
    DEFAULT_DUMP_PATH,
    build_database,
)
from gps_kataster_obiektow_tatr.catalog_cli import (  # noqa: E402
    add_catalog_arguments,
    add_generated_at_argument,
    print_error,
    print_issues,
)
from gps_kataster_obiektow_tatr.report_formatting import utc_timestamp  # noqa: E402
from gps_kataster_obiektow_tatr.validator import CatalogValidationError  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(description="Build build/katalog.dump from YAML data.")
    add_catalog_arguments(parser)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_DUMP_PATH,
        help="PostgreSQL dump output path. Defaults to build/katalog.dump.",
    )
    add_generated_at_argument(parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the PostgreSQL dump build command line interface."""

    args = build_parser().parse_args(argv)
    generated_at = args.generated_at or utc_timestamp()

    try:
        result = build_database(
            data_dir=args.data_dir,
            base_ref=args.base_ref,
            history_repo=args.history_repo,
            output_path=args.output,
            generated_at=generated_at,
        )
    except CatalogValidationError as exc:
        print_issues(exc.issues)
        return 1
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        return print_error(exc)

    metadata = result.metadata
    print(f"wrote: {result.dump_path}")
    print(
        "PostgreSQL dump build: "
        f"{metadata['object_count']} objects, "
        f"{metadata['cave_count']} caves, "
        f"{metadata['measurement_count']} measurements, "
        f"{metadata['validation_warning_count']} validation warnings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
