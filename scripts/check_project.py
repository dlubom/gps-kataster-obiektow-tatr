#!/usr/bin/env python3
"""Run the complete local gate while sharing one disposable PostgreSQL server."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gps_kataster_obiektow_tatr.postgres import _server  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", default="origin/main")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build/verification/exports")
    args = parser.parse_args(argv)
    # Pin the baseline before tests; do not silently validate against candidate HEAD.
    base = subprocess.run(
        ["git", "rev-parse", "--verify", f"{args.base_ref}^{{commit}}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    commands = [
        [sys.executable, "-m", "ruff", "format", "--check", "src", "tests", "scripts"],
        [sys.executable, "-m", "ruff", "check", "src", "tests", "scripts"],
        [sys.executable, "-m", "pytest"],
        [sys.executable, "scripts/validate.py", "--base-ref", base],
        [
            sys.executable,
            "scripts/build_release_artifacts.py",
            "--base-ref",
            base,
            "--output-dir",
            str(args.output_dir),
        ],
        ["git", "diff", "--check"],
    ]
    with _server() as (dsn, container):
        env = {**os.environ, "KATASTER_DATABASE_URL": dsn}
        if container:
            env["KATASTER_POSTGRES_CONTAINER"] = container
        for command in commands:
            print("+ " + " ".join(command), flush=True)
            result = subprocess.run(command, cwd=ROOT, env=env, check=False)
            if result.returncode:
                return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
