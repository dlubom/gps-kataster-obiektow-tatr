"""Run diagnostics are artifacts, never catalog or decision updates."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from html import escape
from pathlib import Path

from .tpn_batch import json_bytes
from .tpn_changes import render_markdown


def source_report(output, report, snapshot):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_bytes(json_bytes(report))
    (output / "report.md").write_text(render_markdown(report), encoding="utf-8")
    shutil.copytree(snapshot, output / "snapshot")


def run_report(output, result, opened=(), *, error=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    pulls = []
    for pull in opened:
        created = pull.get("created_at")
        age = None
        if created:
            age = max(0, (now - datetime.fromisoformat(created.replace("Z", "+00:00"))).days)
        pulls.append(
            {
                "number": pull["number"],
                "head": pull["head"]["sha"],
                "created_at": created,
                "age_days": age,
            }
        )
    path = output / "diagnostics.json"
    # Preserve the planner's backlog context if the CLI subsequently reports failure.
    doc = json.loads(path.read_text()) if path.exists() else {}
    doc.update(
        {
            k: result[k]
            for k in ("outcome", "event_name", "run_id", "main", "repository")
            if k in result
        }
    )
    doc["checked_at"] = now.isoformat().replace("+00:00", "Z")
    if opened or "open_prs" not in doc:
        doc["open_prs"] = pulls
    if (report_path := output / "check/report.json").exists():
        report = json.loads(report_path.read_text())
        doc.update({k: report[k] for k in ("requires_pr", "summary", "snapshot_hash", "baseline")})
        doc["deferred_count"] = len(report["deferred"])
    if error is not None:
        doc.update(outcome="error", error=str(error))
    path.write_bytes(json_bytes(doc))
    return doc


def render_run_summary(result, diagnostic):
    lines = ["## Sprawdzenie TPN", "", "Wynik: `" + diagnostic["outcome"] + "`.", ""]
    if diagnostic["outcome"] == "disabled":
        lines.append("Schedule wyłączony: wymagany odbiór PBI-102 i TPN_MONTHLY_ENABLED=true.")
    if error := diagnostic.get("error"):
        lines.append("Błąd: " + escape(error))
    if "requires_pr" in diagnostic and diagnostic["outcome"] != "error":
        lines.append("Świeże źródło wymaga review: **" + str(diagnostic["requires_pr"]) + "**.")
        lines.append(
            "Klasyfikacje: `" + json.dumps(diagnostic["summary"], ensure_ascii=False) + "`."
        )
        lines.append("Zachowane odroczenia: " + str(diagnostic["deferred_count"]) + ".")
    numbers = [p["number"] for p in diagnostic.get("open_prs", [])]
    if result.get("pr_number") and result["pr_number"] not in numbers:
        numbers.append(result["pr_number"])
    for number in numbers:
        lines.append(f"[PR #{number}](https://github.com/{diagnostic['repository']}/pull/{number})")
    for pull in diagnostic.get("open_prs", []):
        lines.append(
            f"Zaległość PR #{pull['number']}: {pull['age_days']} dni; HEAD `{pull['head']}`."
        )
    if head := result.get("head"):
        lines.append("HEAD: `" + head + "`; pending: " + str(result["pending"]) + ".")
    lines.extend(
        [
            "",
            "Diagnostyka i świeży odczyt: artefakt tego przebiegu (14 dni).",
            "Po publikacji człowiek wybiera **Approve workflows to run** i sprawdza CI "
            "oraz eksporty dokładnego HEAD. Pending blokuje merge; merge tylko ludzki.",
            "",
        ]
    )
    return "\n".join(lines)
