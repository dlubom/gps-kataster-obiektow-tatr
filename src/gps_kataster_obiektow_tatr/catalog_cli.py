"""Shared catalogue arguments and diagnostic rendering, without command policy."""

import sys
from pathlib import Path

from gps_kataster_obiektow_tatr.data_loader import DEFAULT_DATA_DIR
from gps_kataster_obiektow_tatr.validator import format_issue

REPO_ROOT = Path(__file__).resolve().parents[2]


def add_catalog_arguments(parser):
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Data root directory. Defaults to data/.",
    )
    parser.add_argument(
        "--history-repo",
        type=Path,
        default=REPO_ROOT,
        help="Git repository containing the accepted baseline.",
    )
    parser.add_argument(
        "--base-ref",
        default="origin/main",
        help="Accepted Git baseline; missing baseline is an error.",
    )


def add_generated_at_argument(parser):
    parser.add_argument(
        "--generated-at",
        default=None,
        help="Override generated timestamp, mainly for deterministic tests.",
    )


def print_issues(issues):
    for issue in issues:
        print(format_issue(issue))


def print_error(error):
    print(f"error: {error}", file=sys.stderr)
    return 1
