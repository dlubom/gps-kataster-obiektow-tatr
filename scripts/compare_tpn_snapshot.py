#!/usr/bin/env python3
"""Compare a verified TPN snapshot with the catalog and state accepted on main."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gps_kataster_obiektow_tatr.tpn_api import require  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_candidates import CandidatePolicy  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_changes import compare, render_markdown  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_duplicate_state import read_accepted_duplicates  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_normalization import canonical  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_snapshot import sha256, write_bytes  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_source_state import git, read_accepted_state  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--qualify-new", action="store_true")
    parser.add_argument("--name-similarity-threshold", default="0.90")
    parser.add_argument("--radius-m", default="100")
    args = parser.parse_args(argv)
    try:
        root = args.repo_root.resolve()
        output = args.output_dir.absolute()
        require(output.resolve() == output, "output path contains symlink")
        require(
            any(
                output.is_relative_to(root / allowed) and output != root / allowed
                for allowed in ("build", "data/source_reviews/tpn")
            ),
            "output must be a new report directory under build or data/source_reviews/tpn",
        )
        require(not output.exists(), "report directory already exists")
        state, accepted_commit = read_accepted_state(root)
        head = git(root, "rev-parse", "HEAD").decode().strip()
        report = compare(
            root,
            args.snapshot.resolve(),
            batch_id=args.batch_id,
            base_commit=head,
            state=state,
            candidate_policy=CandidatePolicy(args.name_similarity_threshold, args.radius_m)
            if args.qualify_new
            else None,
            duplicate_resolutions=read_accepted_duplicates(root, accepted_commit)
            if args.qualify_new
            else None,
        )
        report["accepted_state_commit"] = accepted_commit
        payload = canonical(report) + b"\n"
        markdown = render_markdown(report).encode()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.mkdir()  # Exclusive; never overwrite another report or partial run.
        try:
            write_bytes(output / "changes.json", payload)
            write_bytes(output / "report.md", markdown)
            write_bytes(
                output / "checksums.json",
                canonical({"changes.json": sha256(payload), "report.md": sha256(markdown)}) + b"\n",
            )
        except BaseException:
            shutil.rmtree(output)
            raise
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"TPN_COMPARISON_INVALID: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "output": str(output),
                "changes_hash": sha256(payload),
                "requires_pr": report["requires_pr"],
                "summary": report["summary"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
