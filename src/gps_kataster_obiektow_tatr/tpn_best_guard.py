"""Read-only protection and explicit best planning for the TPN path.

The general V1 selector is unchanged. This module neither appends measurements
nor applies decisions or migrations; its result is a proposal for a future applier.
"""

from __future__ import annotations

import re
from copy import deepcopy

from .best_measurement import select_default_best_measurement_id
from .tpn_api import require

POLICY = {
    "version": "tpn-best-protection-v1",
    "scope": "whole_object_all_history_regardless_of_source_status_accuracy_or_best",
    "structured": [
        "manual",
        "method_gnss",
        "elevation_gnss",
        "tag_gnss",
        "tag_gnss_anchor",
        "own_verified",
        "gnss_report",
        "tag_geodetic",
        "tag_geodezja",
    ],
    "unclear_text": "GNSS/RTK/PPK/geodetic terms require review, never automatic qualification",
    "text_separators": "underscores are scanned as spaces; raw text remains unchanged",
    "review_text_pattern": (
        r"\b(?:gnss\w*|dgnss\w*|rtk\w*|ppk\w*|geodez\w*|geodet\w*"
        r"|geodes\w*|tachim\w*|tachym\w*)"
    ),
    "review_fields": {
        "measurement": ["source_ref", "device", "notes", "tags"],
        "attachment": ["path", "caption"],
        "object": ["notes"],
    },
    "migration": "protected_auto_to_manual_requires_separate_manifest_approval",
}

_GEODETIC_TEXT = re.compile(POLICY["review_text_pattern"], re.IGNORECASE)


def _history(obj: dict) -> dict:
    measurements = obj.get("measurements")
    require(isinstance(measurements, list) and bool(measurements), "missing measurement history")
    require(all(isinstance(m, dict) for m in measurements), "invalid measurement history")
    ids = [m.get("id") for m in measurements]
    require(all(isinstance(i, str) and i for i in ids), "invalid measurement ID")
    # Shared safety checks: duplicate IDs and non-finite values, including old history.
    select_default_best_measurement_id(measurements)
    best = obj.get("best_measurement")
    require(isinstance(best, dict) and best.get("mode") in ("auto", "manual"), "invalid best mode")
    require(best.get("measurement_id") in ids, "best measurement missing from history")
    if best["mode"] == "manual":
        require(
            isinstance(best.get("reason"), str) and bool(best["reason"].strip()),
            "manual reason required",
        )
    return best


def assess_protection(obj: dict) -> dict:
    """Return evidence for the whole object, without inferring accuracy or truth."""
    best = _history(obj)
    evidence = []
    review = []

    def inspect_text(record, fields, **identity):
        for field in fields:
            value = record.get(field)
            values = value if isinstance(value, list) else [value]
            if any(
                isinstance(v, str) and _GEODETIC_TEXT.search(v.replace("_", " ")) for v in values
            ):
                review.append(
                    {
                        "basis": "unqualified_geodetic_text",
                        **identity,
                        "field": field,
                        "value": deepcopy(value),
                    }
                )

    if best["mode"] == "manual":
        evidence.append({"basis": "manual", "measurement_id": best["measurement_id"]})
    for m in obj["measurements"]:
        bases = []
        if m.get("method") == "gnss":
            bases.append("method_gnss")
        if m.get("elevation_source") == "gnss":
            bases.append("elevation_gnss")
        for tag in ("gnss", "gnss_anchor", "geodetic", "geodezja"):
            if tag in (m.get("tags") or []):
                bases.append("tag_" + tag)
        if m.get("source") == "wlasne" and m.get("verification_status") == "zweryfikowany":
            bases.append("own_verified")
        for basis in bases:
            evidence.append({"basis": basis, "measurement_id": m["id"]})
        if not bases:
            inspect_text(m, POLICY["review_fields"]["measurement"], measurement_id=m["id"])
    for attachment in obj.get("attachments", []):
        if attachment.get("kind") == "raport_gnss":
            evidence.append(
                {
                    "basis": "gnss_report",
                    "measurement_id": attachment.get("measurement_id"),
                    "attachment_id": attachment["id"],
                }
            )
        else:
            inspect_text(
                attachment,
                POLICY["review_fields"]["attachment"],
                attachment_id=attachment["id"],
                measurement_id=attachment.get("measurement_id"),
            )
    inspect_text(obj, POLICY["review_fields"]["object"], object_id=obj.get("id"))
    return {
        "protected": bool(evidence),
        "requires_review": bool(review) and not evidence,
        "evidence": evidence,
        "review_evidence": review,
    }


def plan_best_action(obj: dict, additions: list[dict], best_action: dict) -> dict:
    """Preview an explicit best choice; reject protected replacement before any write.

    ``can_apply`` only describes this guard. A future applier must independently
    validate the batch, provenance, preimages and human approval (PBI-100).
    Protected auto→manual is always blocked here pending separate manifest approval.
    """
    before = _history(obj)
    protection = assess_protection(obj)
    require(isinstance(additions, list) and bool(additions), "TPN additions required")
    require(
        all(isinstance(m, dict) and m.get("source") == "TPN" for m in additions),
        "only TPN additions allowed",
    )
    ids = [m.get("id") for m in additions]
    require(all(isinstance(i, str) and i for i in ids), "invalid new measurement ID")
    combined = [*obj["measurements"], *additions]
    default = select_default_best_measurement_id(combined)
    require(
        isinstance(best_action, dict)
        and set(best_action) == {"action", "measurement_id", "resulting_mode", "reason"},
        "explicit best_action fields required",
    )
    kind = best_action["action"]
    mode = best_action["resulting_mode"]
    selected = best_action["measurement_id"]
    reason = best_action["reason"]
    require(kind in ("keep", "select_new"), "unknown best_action")
    require(mode in ("auto", "manual"), "invalid resulting mode")
    if kind == "keep":
        require(selected == before["measurement_id"], "keep must retain the indicated current best")
        require(
            before["mode"] != "manual" or mode == "manual", "keep cannot remove manual protection"
        )
    else:
        require(
            not protection["protected"] and not protection["requires_review"],
            "TPN_BEST_PROTECTED: replacement blocked",
        )
        require(selected in ids, "select_new must name a new measurement")
    require(
        mode != "auto" or selected == default,
        "explicit manual mode required to preserve the selected ID",
    )
    if mode == "manual" or kind == "select_new":
        require(isinstance(reason, str) and bool(reason.strip()), "explicit best reason required")
    else:
        require(reason is None or isinstance(reason, str), "invalid best reason")
    # Keep the existing manual rationale/audit intact when its ID/mode remain unchanged.
    after = deepcopy(before)
    if selected != before["measurement_id"] or mode != before["mode"]:
        # A proposal has no new audit author/time; only the future authorized
        # application may supply those. Never reuse the previous author's audit.
        after = {"mode": mode, "measurement_id": selected, "reason": reason}
    mode_change = {"before": before["mode"], "after": mode} if mode != before["mode"] else None
    blockers = []
    if protection["requires_review"]:
        blockers.append("geodetic_evidence_review_required")
    if protection["protected"] and mode_change:
        blockers.append("migration_manifest_approval_required")
    return {
        "before": deepcopy(before),
        "after": after,
        "default_after": default,
        "mode_change": mode_change,
        "protection": protection,
        "can_apply": not blockers,
        "blockers": blockers,
    }


def audit_catalog(catalog) -> dict:
    """Propose concrete pins, never approve them or change catalog values."""
    from .tpn_normalization import digest

    objects, migrations = [], []
    for identity, obj in sorted(catalog.objects.items()):
        protection = assess_protection(obj)
        if not protection["protected"] and not protection["requires_review"]:
            continue
        best = obj["best_measurement"]
        entry = {
            "object_id": identity,
            "name": obj.get("name_local"),
            "path": catalog.paths[identity],
            "preimage_sha256": catalog.hashes[catalog.paths[identity]],
            "best_before": deepcopy(best),
            "protection": protection,
            "selected_measurement": deepcopy(
                next(m for m in obj["measurements"] if m["id"] == best["measurement_id"])
            ),
        }
        objects.append(entry)
        if protection["protected"] and best["mode"] == "auto":
            reason = (
                "Ochrona istniejącego wyboru best przed synchronizacją TPN: "
                + ", ".join(sorted({e["basis"] for e in protection["evidence"]}))
                + ". Zachowano pomiar "
                + best["measurement_id"]
                + "; bez zmiany współrzędnych, statusu i dokładności."
            )
            migrations.append(
                {
                    "object_id": identity,
                    "path": entry["path"],
                    "preimage_sha256": entry["preimage_sha256"],
                    "before": deepcopy(best),
                    "after": {
                        "mode": "manual",
                        "measurement_id": best["measurement_id"],
                        "reason": reason,
                    },
                    "evidence": deepcopy(protection["evidence"]),
                    "approval_status": "pending",
                }
            )
    return {
        "format": "tpn-best-protection-audit",
        "format_version": 1,
        "policy": {"version": POLICY["version"], "hash": digest(POLICY), "rules": deepcopy(POLICY)},
        "catalog_hash": catalog.hash,
        "approval_status": "pending",
        "objects": objects,
        "migration_proposals": migrations,
    }


def render_audit(report: dict) -> str:
    """Human-readable manifest; full best preimages remain in JSON."""
    import html

    def cell(value):
        return html.escape(str(value)).replace("|", "&#124;").replace("\n", " ")

    lines = [
        "# Ochrona best — manifest do akceptacji",
        "",
        "Status: pending. Raport nie zatwierdza ani nie wykonuje migracji.",
        "",
        f"Katalog: `{report['catalog_hash']}`",
        "",
        "| Obiekt | Best | Tryb | Podstawa |",
        "|---|---|---|---|",
    ]
    for entry in report["objects"]:
        bases = ", ".join(sorted({e["basis"] for e in entry["protection"]["evidence"]}))
        if entry["protection"]["requires_review"]:
            bases = "review — blokada select_new; " + "; ".join(
                f"{e['basis']} ({e['field']}): {e['value']}"
                for e in entry["protection"]["review_evidence"]
            )
        best = entry["best_before"]
        lines.append(
            f"| {entry['object_id']} | {best['measurement_id']} | {best['mode']} | {cell(bases)} |"
        )
    lines.extend(["", "## Proponowane migracje auto → manual", ""])
    for proposal in report["migration_proposals"]:
        lines.extend(
            [
                f"- {proposal['object_id']}/{proposal['before']['measurement_id']}: "
                + cell(proposal["after"]["reason"])
            ]
        )
    return "\n".join(lines) + "\n"
