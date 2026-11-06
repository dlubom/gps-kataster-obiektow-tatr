#!/usr/bin/env python3
"""Build the normal release exports plus provenance in a fresh artifact directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gps_kataster_obiektow_tatr.build_db import check_artifact_set  # noqa: E402
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts  # noqa: E402
from gps_kataster_obiektow_tatr.report_formatting import utc_timestamp  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--merge-sha", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    parser.add_argument("--generated-at")
    parser.add_argument("--history-repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    output = args.output_dir
    if output.exists() or output.is_symlink():
        parser.error(f"output directory already exists: {output}")
    stamp = args.generated_at or utc_timestamp()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Publish only a complete fresh set; never upload files left from an older build.
    with TemporaryDirectory(prefix="pr-preview-", dir=output.parent) as temporary:
        staging = Path(temporary)
        package = staging / "exports"
        result = build_release_artifacts(
            data_dir=args.data_dir,
            output_dir=package,
            generated_at=stamp,
            source_commit=args.merge_sha,
            base_ref=args.base_sha,
            history_repo=args.history_repo,
        )
        assets = result.artifact_paths
        check_artifact_set(package, assets)
        provenance = {
            "kind": "pr-preview",
            "repository": args.repository,
            "pr_number": args.pr_number,
            "head_sha": args.head_sha,
            "base_sha": args.base_sha,
            "merge_sha": args.merge_sha,
            "run_id": args.run_id,
            "run_attempt": args.run_attempt,
            "generated_at": stamp,
        }
        manifest = package / "preview.json"
        manifest.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
        checksums = "".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
            for p in sorted([*assets, manifest])
        )
        (package / "SHA256SUMS").write_text(checksums, encoding="utf-8")
        package.rename(output)
    print(f"PR #{args.pr_number}: {len(assets)} release exports + provenance/checksums in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
