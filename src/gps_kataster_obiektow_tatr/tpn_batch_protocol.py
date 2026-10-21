"""Strict executable TPN decisions. Raw API/comment strings never become code."""

from __future__ import annotations

import re
from copy import deepcopy

from .tpn_api import globalid, require
from .tpn_normalization import canonical
from .tpn_snapshot import sha256, validate_id, validate_time
from .tpn_source_state import hash_value, path_hashes

HEADER = {
    "batch_id",
    "snapshot_hash",
    "base_commit",
    "catalog_hash",
    "state_hash",
    "policy_version",
    "policy_hash",
}
DECISION = {
    "change_id",
    "globalid",
    "revision_hash",
    "target",
    "preimage",
    "status",
    "reviewed_by",
    "reviewed_at",
    "reason",
    "actions",
}
PROPOSAL = {
    "change_id",
    "target",
    "preimage",
    "actions",
    "conflict_acknowledgements",
    "candidate_acknowledgements",
}
ACTION_FIELDS = {
    "append_measurement": ({"object_id", "measurement_key", "location_hash", "best_action"}, set()),
    "update_metadata": (
        {"target", "field", "before", "after"},
        {"clear", "reason", "append_text", "revision_hash"},
    ),
    "attach_source": ({"target", "reference", "evidence"}, set()),
    "create_cave": ({"cave_key"}, set()),
    "new_object": (
        {"object_key", "location_hash", "initial_best"},
        {"cave_key", "category", "evidence"},
    ),
    "link_cave": ({"cave_id"}, {"object_id", "object_key"}),
}


def fields(value, required, optional=frozenset()):
    require(
        isinstance(value, dict)
        and required <= value.keys()
        and value.keys() <= required | optional,
        "missing/unknown executable fields",
    )


def nonempty(value):
    require(isinstance(value, str) and bool(value.strip()), "nonempty text required")


def target(value):
    if value is None:
        return
    fields(value, {"cave_id"}, {"object_id"})
    require(value.get("object_id") is not None or value["cave_id"] is not None, "empty target")
    for name, ident in value.items():
        if ident is not None:
            pattern = r"[A-Z]{2,3}-[0-9]{4,}" if name == "object_id" else r"C-[0-9]{4,}"
            require(isinstance(ident, str) and re.fullmatch(pattern, ident), "invalid target ID")


def validate_actions(actions):
    require(isinstance(actions, list), "actions must be a list")
    for a in actions:
        require(
            isinstance(a, dict)
            and isinstance(a.get("action"), str)
            and a["action"] in ACTION_FIELDS,
            "unsupported action",
        )
        required, optional = ACTION_FIELDS[a["action"]]
        fields(a, required | {"action"}, optional)
        kind = a["action"]
        for key in ("object_key", "cave_key", "measurement_key"):
            if key in a:
                validate_id(a[key])
        if "object_id" in a:
            require(
                isinstance(a["object_id"], str)
                and re.fullmatch(r"[A-Z]{2,3}-[0-9]{4,}", a["object_id"]),
                "invalid object ID",
            )
        if "location_hash" in a:
            hash_value(a["location_hash"])
        if kind == "link_cave":
            require(("object_id" in a) != ("object_key" in a), "link requires one object selector")
            target({"cave_id": a["cave_id"]})
        elif kind == "append_measurement":
            b = a["best_action"]
            fields(b, {"action", "resulting_mode", "reason"}, {"measurement_id", "measurement_key"})
            require(b["action"] in ("keep", "select_new"), "unsupported best action")
            expected = "measurement_id" if b["action"] == "keep" else "measurement_key"
            require(
                set(b) == {"action", "resulting_mode", "reason", expected}, "invalid best selector"
            )
            nonempty(b[expected])
            require(b["resulting_mode"] in ("auto", "manual"), "invalid best mode")
            require(b["reason"] is None or isinstance(b["reason"], str), "invalid best reason")
        elif kind in ("update_metadata", "attach_source"):
            t = a["target"]
            fields(t, {"kind", "id"}, {"measurement_id"})
            require(t["kind"] in ("object", "cave", "measurement"), "invalid metadata target")
            target(
                {"object_id": t["id"], "cave_id": None}
                if t["kind"] != "cave"
                else {"cave_id": t["id"]}
            )
            require(
                ("measurement_id" in t) == (t["kind"] == "measurement"),
                "invalid measurement selector",
            )
            if "measurement_id" in t:
                nonempty(t["measurement_id"])
            if kind == "update_metadata":
                allowed = {
                    "object": {"name_local", "category", "notes"},
                    "cave": {"name", "system_name", "notes"},
                    "measurement": {"notes"},
                }
                require(
                    isinstance(a["field"], str) and a["field"] in allowed[t["kind"]],
                    "metadata field forbidden",
                )
                if a["field"] == "notes":
                    require(
                        set(a)
                        == {
                            "action",
                            "target",
                            "field",
                            "before",
                            "after",
                            "append_text",
                            "revision_hash",
                        },
                        "notes require append_text and revision",
                    )
                    nonempty(a["append_text"])
                    hash_value(a["revision_hash"])
                else:
                    require(
                        "append_text" not in a and "revision_hash" not in a,
                        "invalid non-note action",
                    )
                    require(
                        a["after"] is None or isinstance(a["after"], str), "invalid metadata value"
                    )
                    if a["after"] is None or not a["after"].strip():
                        require(a.get("clear") is True, "clearing requires clear:true")
                        nonempty(a.get("reason"))
                    elif "clear" in a:
                        require(a["clear"] is False, "invalid clear flag")
            else:
                require(t["kind"] != "measurement", "reference belongs to entity")
                fields(a["reference"], {"system", "ref_type", "external_id"})
                nonempty(a["evidence"])
                r = a["reference"]
                if t["kind"] == "object":
                    require(
                        r["system"] == "TPN"
                        and r["ref_type"] == "source_globalid"
                        and globalid(r["external_id"]) == r["external_id"],
                        "typed TPN reference required",
                    )
                else:
                    require(
                        r["system"] == "NR_INWENT" and r["ref_type"] == "inventory_number",
                        "typed inventory reference required",
                    )
                    nonempty(r["external_id"])
        elif kind == "new_object":
            require(a["initial_best"] == "first_measurement", "invalid initial best")
            if "category" in a:
                require(
                    a["category"] in ("jaskinia_otwor", "sztolnia", "ponor", "wywierzysko"),
                    "invalid category",
                )
                nonempty(a.get("evidence"))


def prepare_documents(report, proposals=None):
    """Bind explicit operator proposals without altering source/candidate evidence."""
    require("execution" not in report, "already prepared changes")
    changes = deepcopy(report)
    rows = [r for r in report["records"] if r["actionable"] or r["requires_review"]]
    if proposals is None:
        proposals = [
            {
                "change_id": r["change_id"],
                "target": r["target"],
                "preimage": r["preimage"],
                "actions": [],
                "conflict_acknowledgements": [],
                "candidate_acknowledgements": [],
            }
            for r in rows
        ]
    changes["execution"] = {
        "format": "tpn-execution-proposals",
        "format_version": 2,
        "proposals": deepcopy(proposals),
    }
    decisions = {
        "format": "tpn-decisions",
        "format_version": 1,
        **{k: report[k] for k in HEADER},
        "changes_hash": sha256(canonical(changes) + b"\n"),
        "decisions": [],
    }
    by_id = {r["change_id"]: r for r in rows}
    for p in proposals:
        r = by_id[p["change_id"]]
        decisions["decisions"].append(
            {
                **{k: r[k] for k in ("change_id", "globalid", "revision_hash")},
                "target": deepcopy(p["target"]),
                "preimage": deepcopy(p["preimage"]),
                "actions": deepcopy(p["actions"]),
                "status": "pending",
                "reviewed_by": None,
                "reviewed_at": None,
                "reason": "",
            }
        )
    validate_documents(changes, decisions, reviewers=set(), allow_pending=True)
    return changes, decisions


def validate_documents(changes, decisions, *, reviewers, allow_pending=True):
    fields(decisions, HEADER | {"format", "format_version", "changes_hash", "decisions"})
    require(
        decisions["format"] == "tpn-decisions"
        and type(decisions["format_version"]) is int
        and decisions["format_version"] == 1,
        "unsupported decisions format/version",
    )
    validate_id(decisions["batch_id"])
    for k in HEADER:
        require(decisions[k] == changes[k], f"decisions {k} mismatch")
    require(
        decisions["changes_hash"] == sha256(canonical(changes) + b"\n"), "changes hash mismatch"
    )
    execution = changes.get("execution")
    fields(execution, {"format", "format_version", "proposals"})
    require(
        execution["format"] == "tpn-execution-proposals"
        and type(execution["format_version"]) is int
        and execution["format_version"] in (1, 2),
        "unsupported proposals format/version",
    )
    rows = {
        r["change_id"]: r for r in changes["records"] if r["actionable"] or r["requires_review"]
    }
    require(
        isinstance(execution["proposals"], list) and isinstance(decisions["decisions"], list),
        "invalid decision lists",
    )
    proposals = {}
    for p in execution["proposals"]:
        fields(p, PROPOSAL)
        require(
            isinstance(p["change_id"], str)
            and p["change_id"] in rows
            and p["change_id"] not in proposals,
            "unknown/duplicate proposal",
        )
        target(p["target"])
        path_hashes(p["preimage"])
        validate_actions(p["actions"])
        for k in ("conflict_acknowledgements", "candidate_acknowledgements"):
            require(
                isinstance(p[k], list)
                and all(isinstance(x, str) for x in p[k])
                and len(p[k]) == len(set(p[k])),
                "invalid acknowledgements",
            )
        proposals[p["change_id"]] = p
    require(set(proposals) == set(rows), "missing record proposals")
    seen = set()
    for d in decisions["decisions"]:
        fields(d, DECISION)
        key = d["change_id"]
        require(
            isinstance(key, str) and key in rows and key not in seen, "unknown/duplicate decision"
        )
        seen.add(key)
        r, p = rows[key], proposals[key]
        for k in ("globalid", "revision_hash"):
            require(d[k] == r[k], "revision/GUID mismatch")
        for k in ("target", "preimage"):
            require(d[k] == p[k], "decision target/preimage mismatch")
        require(
            isinstance(d["status"], str)
            and d["status"] in ("pending", "approve", "reject", "defer"),
            "unsupported status",
        )
        require(isinstance(d["reason"], str), "invalid reason")
        validate_actions(d["actions"])
        if d["status"] == "pending":
            require(allow_pending, "pending blocks merge")
            require(
                d["reviewed_by"] is None and d["reviewed_at"] is None,
                "pending cannot impersonate reviewer",
            )
            require(d["actions"] == p["actions"], "pending proposal mismatch")
        else:
            nonempty(d["reason"])
            require(
                isinstance(d["reviewed_by"], str) and d["reviewed_by"] in reviewers,
                "unauthorized reviewer",
            )
            validate_time(d["reviewed_at"])
            require(
                d["actions"] == (p["actions"] if d["status"] == "approve" else []),
                "decision actions mismatch",
            )
        if d["status"] == "approve":
            require(
                set(p["conflict_acknowledgements"]) == set(r["conflicts"]), "unapproved conflict"
            )
            require(
                set(p["candidate_acknowledgements"]) == {c["key"] for c in r["candidates"]},
                "unapproved duplicate candidate",
            )
    require(seen == set(rows), "missing record decision")
