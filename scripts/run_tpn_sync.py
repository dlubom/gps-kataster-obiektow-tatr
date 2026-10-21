#!/usr/bin/env python3
"""Trusted main entrypoint shared by manual and monthly TPN runs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gps_kataster_obiektow_tatr.tpn_api import require  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_workflow_api import GitHub  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_workflow_github import (  # noqa: E402
    plan_workflow,
    publish_workflow,
)
from gps_kataster_obiektow_tatr.tpn_workflow_reporting import (  # noqa: E402
    render_run_summary,
    run_report,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("plan", "publish"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {}
    trusted_context = False
    try:
        require(os.environ.get("GITHUB_REF") == "refs/heads/main", "dispatch only from main")
        trusted = os.environ["GITHUB_SHA"]
        require(
            os.environ["GITHUB_WORKFLOW_SHA"] == trusted, "workflow must come from trusted main"
        )
        trusted_context = True
        api = GitHub(os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"])
        number = os.environ.get("TPN_PR_NUMBER", "").strip()
        require(not number or number.isascii() and number.isdecimal(), "invalid PR number")
        options = {
            "operation": os.environ.get("TPN_OPERATION") or "prepare",
            "event_name": os.environ["GITHUB_EVENT_NAME"],
            "monthly_enabled": os.environ.get("TPN_MONTHLY_ENABLED") == "true",
            "run_id": os.environ["GITHUB_RUN_ID"],
            "actor": os.environ["GITHUB_ACTOR"],
            "triggering_actor": os.environ["GITHUB_TRIGGERING_ACTOR"],
            "trusted_sha": trusted,
            "pr_number": int(number) if number else 0,
            "expected_head": os.environ.get("TPN_EXPECTED_HEAD", "").strip(),
        }
        result = (
            plan_workflow(ROOT, api, output=args.output, **options)
            if args.phase == "plan"
            else publish_workflow(ROOT, api, args.output, **options)
        )
        if target := os.environ.get("GITHUB_OUTPUT"):
            with Path(target).open("a") as stream:
                stream.write("outcome=" + result["outcome"] + "\n")
        diagnostic = run_report(args.output, result)
        if target := os.environ.get("GITHUB_STEP_SUMMARY"):
            with Path(target).open("a") as stream:
                stream.write(render_run_summary(result, diagnostic))
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print("TPN_WORKFLOW_INVALID: " + str(exc), file=sys.stderr)
        if trusted_context:
            diagnostic = run_report(args.output, result, error=exc)
            if target := os.environ.get("GITHUB_STEP_SUMMARY"):
                with Path(target).open("a") as stream:
                    stream.write(render_run_summary(result, diagnostic))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
