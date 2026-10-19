#!/usr/bin/env python3
"""Audit TPN best protection and propose migrations without writing catalog data."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gps_kataster_obiektow_tatr.tpn_api import require  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_best_guard import audit_catalog, render_audit  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_changes import Catalog  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_normalization import canonical  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_snapshot import sha256, write_bytes  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = args.repo_root.resolve()
        output = args.output_dir.absolute()
        require(output.resolve() == output, "output path contains symlink")
        require(
            output.is_relative_to(root / "build") and output != root / "build",
            "output must be a new directory under build",
        )
        require(not output.exists(), "report directory already exists")
        report = audit_catalog(Catalog(root))
        payload = canonical(report) + b"\n"
        markdown = render_audit(report).encode()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.mkdir()
        try:
            write_bytes(output / "manifest.json", payload)
            write_bytes(output / "report.md", markdown)
            write_bytes(
                output / "checksums.json",
                canonical({"manifest.json": sha256(payload), "report.md": sha256(markdown)})
                + b"\n",
            )
        except BaseException:
            shutil.rmtree(output)
            raise
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"TPN_BEST_AUDIT_INVALID: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "output": str(output),
                "protected_or_review_objects": len(report["objects"]),
                "migration_proposals": len(report["migration_proposals"]),
                "approval_status": "pending",
                "manifest_sha256": sha256(payload),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
