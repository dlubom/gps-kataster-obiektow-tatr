#!/usr/bin/env python3
"""Resolve the real event history baseline; missing Git objects fail closed."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()


def resolve_baseline(event_name, event, ref):
    head = git("rev-parse", "HEAD")
    if event_name == "pull_request":
        base = event.get("pull_request", {}).get("base", {}).get("sha")
    elif event_name == "push" and ref == "refs/heads/main":
        base = event.get("before")
    elif event_name == "push" and ref.startswith("refs/tags/v"):
        # Only accepted commits may produce releases. Compare to their actual first parent.
        git("merge-base", "--is-ancestor", head, "origin/main")
        base = git("rev-parse", "HEAD^1")
    elif event_name == "workflow_dispatch":
        accepted = git("rev-parse", "origin/main")
        base = git("rev-parse", "HEAD^1") if head == accepted else accepted
    else:
        raise ValueError("Unsupported CI event/ref for history baseline")
    if not isinstance(base, str) or not re.fullmatch(r"[0-9a-f]{40}", base) or set(base) == {"0"}:
        raise ValueError("Missing or invalid event history baseline")
    if base == head:
        raise ValueError("Candidate HEAD cannot be its own history baseline")
    if git("rev-parse", "--verify", f"{base}^{{commit}}") != base:
        raise ValueError("History baseline is not an available commit")
    return base


def main():
    try:
        base = resolve_baseline(
            os.environ["GITHUB_EVENT_NAME"],
            json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text()),
            os.environ["GITHUB_REF"],
        )
        with Path(os.environ["GITHUB_ENV"]).open("a") as output:
            output.write(f"HISTORY_BASE_SHA={base}\n")
        print(f"History baseline: {base}")
        return 0
    except (KeyError, ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"History baseline unavailable: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
