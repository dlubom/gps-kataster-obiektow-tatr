#!/usr/bin/env python3
"""Validate canonical YAML, PostgreSQL state and accepted Git history."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gps_kataster_obiektow_tatr.catalog_cli import add_catalog_arguments, print_issues  # noqa: E402
from gps_kataster_obiektow_tatr.validator import (  # noqa: E402
    CatalogValidationError,
    exit_code_for_issues,
    history_checked_catalog,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Validate canonical YAML, PostgreSQL state and accepted Git history."
    )
    add_catalog_arguments(parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the validator command line interface."""

    args = build_parser().parse_args(argv)
    import psycopg

    from gps_kataster_obiektow_tatr.data_loader import (
        DataDirectoryError,
        YamlDataLoadError,
    )
    from gps_kataster_obiektow_tatr.postgres import CatalogLoadError
    from gps_kataster_obiektow_tatr.validator import (
        ValidationIssue,
        ValidationSeverity,
        _sql_issue,
    )

    try:
        with history_checked_catalog(
            args.data_dir, base_ref=args.base_ref, history_repo=args.history_repo
        ) as (_, _, issues):
            pass
    except CatalogValidationError as exc:
        issues = exc.issues
    except (CatalogLoadError, psycopg.Error) as exc:
        issues = (_sql_issue(exc),)
    except (DataDirectoryError, YamlDataLoadError) as exc:
        code = "DATA_DIRECTORY_INVALID" if isinstance(exc, DataDirectoryError) else "YAML_INVALID"
        issues = (ValidationIssue(code, ValidationSeverity.ERROR, exc.path, str(exc)),)
    if not issues:
        print("OK: no validation issues")
        return 0

    print_issues(issues)

    return exit_code_for_issues(issues)


if __name__ == "__main__":
    raise SystemExit(main())
