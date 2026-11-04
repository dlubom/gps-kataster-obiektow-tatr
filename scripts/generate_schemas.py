#!/usr/bin/env python3
"""Generate the published JSON Schema files from the catalog record models."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gps_kataster_obiektow_tatr.models import RECORD_MODELS  # noqa: E402

SCHEMA_DIR = REPO_ROOT / "schema"
SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
SCHEMA_BASE_ID = "https://example.local/gps-kataster-obiektow-tatr/schema"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check for stale generated schemas.")
    args = parser.parse_args(argv)
    stale = []

    for kind, model in RECORD_MODELS.items():
        path = SCHEMA_DIR / f"{kind}.schema.json"
        schema = {
            "$schema": SCHEMA_DIALECT,
            "$id": f"{SCHEMA_BASE_ID}/{path.name}",
            **model.model_json_schema(mode="validation"),
        }
        expected = (json.dumps(schema, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        if args.check:
            if not path.is_file() or path.read_bytes() != expected:
                stale.append(path.name)
        else:
            path.write_bytes(expected)

    if stale:
        print(f"Stale JSON Schema files: {', '.join(stale)}", file=sys.stderr)
        print("Regenerate with: uv run python scripts/generate_schemas.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
