#!/usr/bin/env python3
"""Generate browsable Markdown cards from source YAML."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gps_kataster_obiektow_tatr.catalog_cards import (  # noqa: E402
    DEFAULT_CATALOG_DIR,
    CatalogCardsValidationError,
    build_catalog_cards,
)
from gps_kataster_obiektow_tatr.data_loader import DEFAULT_DATA_DIR  # noqa: E402
from gps_kataster_obiektow_tatr.validator import format_issue  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wygeneruj karty Markdown z danych YAML.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_CATALOG_DIR)
    args = parser.parse_args(argv)

    try:
        index = build_catalog_cards(data_dir=args.data_dir, output_dir=args.output_dir)
    except CatalogCardsValidationError as exc:
        for issue in exc.issues:
            print(format_issue(issue), file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"wrote: {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
