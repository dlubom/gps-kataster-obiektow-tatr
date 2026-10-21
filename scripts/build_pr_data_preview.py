#!/usr/bin/env python3
"""Build the complete release data package for one pull-request merge revision."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gps_kataster_obiektow_tatr.best_measurements_export import (  # noqa: E402
    BestMeasurementsExportValidationError,
)
from gps_kataster_obiektow_tatr.build_db import BuildDatabaseValidationError  # noqa: E402
from gps_kataster_obiektow_tatr.data_loader import (  # noqa: E402
    DEFAULT_DATA_DIR,
    DataDirectoryError,
)
from gps_kataster_obiektow_tatr.release_artifacts import (  # noqa: E402
    RELEASE_ASSET_FILENAMES,
    build_release_artifacts,
)
from gps_kataster_obiektow_tatr.validator import format_issue  # noqa: E402


def _positive_integer(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if result <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return result


def _commit(value: str) -> str:
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise argparse.ArgumentTypeError("must be a lowercase 40-character commit SHA")
    return value


def _timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an ISO timestamp with a timezone") from exc
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("must be an ISO timestamp with a timezone")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-number", required=True, type=_positive_integer)
    parser.add_argument("--head-commit", required=True, type=_commit)
    parser.add_argument("--base-commit", required=True, type=_commit)
    parser.add_argument("--merge-commit", required=True, type=_commit)
    parser.add_argument("--run-id", required=True, type=_positive_integer)
    parser.add_argument("--run-attempt", required=True, type=_positive_integer)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("build/pr-data"), help="Preview package root."
    )
    parser.add_argument("--generated-at", type=_timestamp)
    return parser


def _check_release_assets(output_dir: Path) -> None:
    expected = set(RELEASE_ASSET_FILENAMES)
    actual = {path.name for path in output_dir.iterdir()}
    missing = expected - actual
    extra = actual - expected
    invalid = {
        name
        for name in expected & actual
        if not (output_dir / name).is_file() or (output_dir / name).is_symlink()
    }
    if missing or extra or invalid:
        raise ValueError(
            "Invalid release asset set: "
            f"missing={sorted(missing)}, extra={sorted(extra)}, invalid={sorted(invalid)}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    generated_at = args.generated_at or datetime.now(UTC).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")
    output_dir = args.output_dir / "exports"
    artifact_name = (
        f"pr-data-{args.pr_number}-h{args.head_commit}-b{args.base_commit}"
        f"-m{args.merge_commit}-r{args.run_id}-a{args.run_attempt}"
    )
    try:
        if output_dir.is_symlink() or (
            output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir()))
        ):
            raise ValueError(f"Preview export directory is not empty: {output_dir}")
        build_release_artifacts(
            data_dir=args.data_dir,
            sqlite_path=args.output_dir / "katalog.sqlite",
            output_dir=output_dir,
            generated_at=generated_at,
            release_version=f"pr-{args.pr_number}-{args.head_commit[:12]}",
            source_commit=args.merge_commit,
        )
        _check_release_assets(output_dir)
        provenance = {
            "pr_number": args.pr_number,
            "head_commit": args.head_commit,
            "base_commit": args.base_commit,
            "merge_commit": args.merge_commit,
            "run_id": args.run_id,
            "run_attempt": args.run_attempt,
            "generated_at": generated_at,
        }
        (output_dir / "preview.json").write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        manifest_names = sorted((*RELEASE_ASSET_FILENAMES, "preview.json"))
        (output_dir / "SHA256SUMS").write_text(
            "".join(
                f"{hashlib.sha256((output_dir / name).read_bytes()).hexdigest()}  {name}\n"
                for name in manifest_names
            ),
            encoding="utf-8",
        )
        if github_output := os.environ.get("GITHUB_OUTPUT"):
            with Path(github_output).open("a", encoding="utf-8") as stream:
                stream.write(f"artifact_name={artifact_name}\n")
    except (BuildDatabaseValidationError, BestMeasurementsExportValidationError) as exc:
        for issue in exc.issues:
            print(format_issue(issue), file=sys.stderr)
        return 1
    except (DataDirectoryError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for filename in (*RELEASE_ASSET_FILENAMES, "preview.json", "SHA256SUMS"):
        print(f"wrote: {output_dir / filename}")
    print(f"artifact: {artifact_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
