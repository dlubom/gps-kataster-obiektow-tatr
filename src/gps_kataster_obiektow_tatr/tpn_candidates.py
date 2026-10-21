"""Read-only candidate evidence and conservative §6 new-record qualification."""

from __future__ import annotations

import re
from contextlib import suppress
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache

from .tpn_api import globalid, require
from .tpn_normalization import canonical, decimal, digest, distance, text
from .tpn_precision import reported_distance

CHECKS = {
    "new_unique_guid",
    "geometry",
    "category",
    "region",
    "measurement",
    "name",
    "standalone",
    "comparison_complete",
    "source_review_clear",
}


def normalize_name(value: str | None) -> str:
    # Never remove numbers, punctuation, diacritics or opening designators.
    return " ".join((text(value) or "").casefold().split())


@lru_cache(maxsize=32768)
def name_similarity(a: str, b: str) -> Decimal:
    """Symmetric normalized Levenshtein, exact decimal threshold comparison."""
    a, b = normalize_name(a), normalize_name(b)
    if not a or not b:
        return Decimal(0)
    if a == b:
        return Decimal(1)
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        new = [i]
        for j, cb in enumerate(b, 1):
            new.append(min(new[-1] + 1, row[j] + 1, row[j - 1] + (ca != cb)))
        row = new
    return Decimal(1) - Decimal(row[-1]) / max(len(a), len(b))


@dataclass(frozen=True)
class CandidatePolicy:
    name_similarity_threshold: Decimal = Decimal("0.90")
    radius_m: Decimal = Decimal("100")
    version: str = "tpn-candidates-v2"

    def __post_init__(self):
        require(
            self.version in ("tpn-candidates-v1", "tpn-candidates-v2"),
            "unsupported candidate policy version",
        )
        threshold, radius = decimal(self.name_similarity_threshold), decimal(self.radius_m)
        require(threshold is not None and 0 < threshold <= 1, "invalid name threshold")
        require(radius is not None and radius >= 100, "candidate radius must be >=100 m")
        object.__setattr__(self, "name_similarity_threshold", threshold)
        object.__setattr__(self, "radius_m", radius)

    def document(self) -> dict:
        return {
            "version": self.version,
            "normalization": "NFC-casefold-collapse-whitespace-preserve-markers",
            "name_metric": "1-levenshtein/max-length",
            "name_similarity_threshold": self.name_similarity_threshold,
            "radius_m": self.radius_m,
            "radius_rule": "max(configured-radius,known-horizontal-accuracies)",
            "boundary": "inclusive",
        }


def qualify(checks: dict, candidates: list) -> str:
    return (
        "automatic_proposal"
        if set(checks) == CHECKS
        and all(value is True for value in checks.values())
        and not candidates
        else "review"
    )


def pair_evidence(left: dict, right: dict, policy: CandidatePolicy) -> list[dict]:
    evidence = []
    if left["target"].get("globalid") in right.get("source_guids", []):
        evidence.append(
            {
                "code": "shared_source_guid",
                "globalid": left["target"]["globalid"],
                "candidate_source_guids": right["source_guids"],
            }
        )
    for group, code in (
        ("names", "exact_name"),
        ("inventories", "shared_inventory"),
        ("systems", "shared_system"),
    ):
        for a in left[group]:
            for b in right[group]:
                an, bn = normalize_name(a["value"]), normalize_name(b["value"])
                if not an or not bn:
                    continue
                if an == bn:
                    evidence.append({"code": code, "left": a, "right": b, "normalized": an})
                elif group == "names":
                    # Length bound avoids running quadratic DP for impossible pairs.
                    upper = Decimal(min(len(an), len(bn))) / max(len(an), len(bn))
                    if upper >= policy.name_similarity_threshold:
                        similarity = name_similarity(an, bn)
                        if similarity >= policy.name_similarity_threshold:
                            evidence.append(
                                {
                                    "code": "similar_name",
                                    "left": a,
                                    "right": b,
                                    "similarity": similarity,
                                    "threshold": policy.name_similarity_threshold,
                                }
                            )
    # SYSTEM names can also identify a cave named in NAZWA/OTWÓR/name_local.
    for ag, bg in (("systems", "names"), ("names", "systems")):
        for a in left[ag]:
            for b in right[bg]:
                if normalize_name(a["value"]) and normalize_name(a["value"]) == normalize_name(
                    b["value"]
                ):
                    evidence.append({"code": "shared_system", "left": a, "right": b})
    for a in left["positions"]:
        for b in right["positions"]:
            known = [policy.radius_m]
            for position in (a, b):
                accuracy = decimal(position.get("horizontal_accuracy_m"))
                require(accuracy is None or accuracy >= 0, "negative horizontal accuracy")
                if accuracy is not None:
                    known.append(accuracy)
            radius = max(known)
            separation = distance(a, b)
            if decimal(separation) <= radius:
                evidence.append(
                    {
                        "code": "nearby_position",
                        "distance_m": reported_distance(separation),
                        "radius_m": radius,
                        "left_position": a,
                        "right_position": b,
                    }
                )
    return evidence


def source_side(record: dict, *, origin: str, semantic: bool = False) -> dict:
    metadata = record["metadata"]
    # v1 remains available for exact replay of already published batch receipts.
    # In v2 current/baseline/snapshot are evidence locations, not distinct sides.
    key = (
        f"source:{record['globalid']}:{record['revision_hash']}"
        if semantic
        else f"source:{origin}:{record['globalid']}"
    )
    target = {"globalid": record["globalid"]}
    if not semantic:
        target["origin"] = origin
    field_origin = "source" if semantic else origin
    return {
        "key": key,
        "target": target,
        "names": [
            {"field": f"{field_origin}.{k}", "value": metadata[k]}
            for k in ("NAZWA", "OTWÓR")
            if metadata.get(k)
        ],
        "inventories": [{"field": f"{field_origin}.NR_INWENT", "value": metadata["NR_INWENT"]}]
        if metadata.get("NR_INWENT")
        else [],
        "systems": [{"field": f"{field_origin}.SYSTEM", "value": metadata["SYSTEM"]}]
        if metadata.get("SYSTEM")
        else [],
        "positions": [{**record["location"], "horizontal_accuracy_m": None}],
        "revision_hash": record["revision_hash"],
        "preimage": {},
    }


def catalog_sides(catalog) -> list[dict]:
    sides = []
    for identity, record in sorted(catalog.records.items()):
        if identity not in catalog.objects and identity not in catalog.caves:
            continue
        obj = identity in catalog.objects
        cave = catalog.caves.get(record.get("cave_id")) if obj else record
        identities = [identity] + ([cave["id"]] if obj and cave else [])
        preimage = {catalog.paths[i]: catalog.hashes[catalog.paths[i]] for i in identities}
        names = [
            {
                "field": f"{identity}.{'name_local' if obj else 'name'}",
                "value": record.get("name_local" if obj else "name"),
            }
        ]
        if obj and cave:
            names.append({"field": f"{cave['id']}.name", "value": cave.get("name")})
        refs = record.get("external_refs", []) + (
            cave.get("external_refs", []) if obj and cave else []
        )
        source_guids = set()
        for m in record.get("measurements", []):
            source_ref = m.get("source_ref")
            if (
                m.get("source") == "TPN"
                and isinstance(source_ref, str)
                and source_ref.startswith("TPN:")
            ):
                # Invalid provenance cannot establish identity.
                with suppress(ValueError):
                    source_guids.add(globalid(source_ref[4:]))
        sides.append(
            {
                "key": f"{'object' if obj else 'cave'}:{identity}",
                "source_guids": sorted(source_guids),
                "target": {
                    "object_id": identity if obj else None,
                    "cave_id": cave["id"] if cave else None,
                },
                "names": names,
                "inventories": [
                    {"field": f"{identity}.external_refs", "value": r["external_id"]}
                    for r in refs
                    if r.get("system") == "NR_INWENT" and r.get("ref_type") == "inventory_number"
                ],
                "systems": [{"field": f"{cave['id']}.system_name", "value": cave["system_name"]}]
                if cave and cave.get("system_name")
                else [],
                "positions": [
                    {
                        **m,
                        "is_best": record.get("best_measurement", {}).get("measurement_id")
                        == m["id"],
                    }
                    for m in record.get("measurements", [])
                ],
                "revision_hash": digest(record),
                "preimage": preimage,
            }
        )
    return sides


def resolution_status(
    left: dict,
    right: dict,
    policy: CandidatePolicy,
    catalog_hash: str,
    resolutions: list[dict],
    *,
    source_set_hash: str | None = None,
) -> dict:
    """Read remembered human evidence. No action, suppression or state write."""
    pair = sorted([left["key"], right["key"]])
    basis = {
        "sides": sorted([left, right], key=lambda x: x["key"]),
        "policy": policy.document(),
        "catalog_hash": catalog_hash,
        "source_set_hash": source_set_hash if source_set_hash is not None else digest([]),
    }
    checksum = digest(basis)
    matching = [r for r in resolutions if r["pair"] == pair]
    if not matching:
        return {
            "outcome": "unresolved",
            "status": "unreviewed",
            "basis_hash": checksum,
            "current_basis": basis,
        }
    require(len(matching) == 1, "duplicate pair resolution")
    remembered = matching[0]
    valid = remembered["basis_hash"] == checksum
    return {
        "outcome": remembered["outcome"] if valid else "unresolved",
        "status": "valid" if valid else "stale",
        "basis_hash": checksum,
        "remembered": remembered,
        "current_basis": basis,
    }


def augment(
    report: dict,
    catalog,
    current: dict,
    previous: dict,
    resolver,
    policy: CandidatePolicy,
    resolutions: list[dict],
    extra_sources: dict,
    historical_sides: list[dict] | None = None,
    source_inputs: dict | None = None,
) -> None:
    from .tpn_duplicate_state import validate_resolutions

    validate_resolutions(resolutions)
    semantic = policy.version == "tpn-candidates-v2"
    sides = catalog_sides(catalog) + (historical_sides or [])
    catalog_gaps = [
        {"key": s["key"], "reason": "missing positions or usable catalog names"}
        for s in sides
        if s["key"].startswith("object:")
        and (not s["positions"] or not any(normalize_name(n["value"]) for n in s["names"]))
    ]
    historical_guids = {}
    for origin, records in [
        ("current", current),
        ("baseline", previous),
        *sorted(extra_sources.items()),
    ]:
        sides.extend(
            source_side(record, origin=origin, semantic=semantic)
            for _, record in sorted(records.items())
        )
        if origin != "current":
            for guid, record in records.items():
                historical_guids.setdefault(guid, []).append({"origin": origin, "record": record})
    if semantic:
        # Keep every distinct revision and all catalog/competitor evidence, but
        # do not treat another copy of a revision in an accepted snapshot as new.
        unique = {canonical(side): side for side in sides}
        sides = [unique[key] for key in sorted(unique)]
    policy_doc = policy.document()
    report["candidate_policy"] = {**policy_doc, "policy_hash": digest(policy_doc)}
    report["duplicate_state_hash"] = digest(resolutions)
    report["candidate_source_inputs"] = source_inputs or {"complete": True}
    source_set_hash = digest(
        {
            "sides": sides,
            # A return to an older revision changes the current evidence even
            # when both revisions already belong to the historical side set.
            "current_source_revisions": {guid: r["revision_hash"] for guid, r in current.items()},
        }
        if semantic
        else sides
    )
    report["candidate_comparison_hash"] = source_set_hash
    report["candidate_catalog_gaps"] = catalog_gaps
    by_key = {s["key"]: s for s in sides}
    report["duplicate_resolution_checks"] = []
    for remembered in resolutions:
        a, b = [by_key.get(key) for key in remembered["pair"]]
        result = (
            resolution_status(
                a, b, policy, catalog.hash, [remembered], source_set_hash=source_set_hash
            )
            if a and b
            else {
                "status": "stale",
                "outcome": "unresolved",
                "remembered": remembered,
                "reason": "comparison side missing",
            }
        )
        report["duplicate_resolution_checks"].append({"pair": remembered["pair"], **result})
    for row in report["records"]:
        after = row["source_after"]
        if after is None or "unmapped_guid" not in row["classification"]:
            continue
        left = source_side(after, origin="current", semantic=semantic)
        candidates = []
        for right in sides:
            if right["target"].get("globalid") == row["globalid"]:
                continue
            evidence = pair_evidence(left, right, policy)
            if evidence:
                candidates.append(
                    {
                        "key": right["key"],
                        "target": right["target"],
                        "evidence": evidence,
                        "candidate_basis": right,
                        "resolution": resolution_status(
                            left,
                            right,
                            policy,
                            catalog.hash,
                            resolutions,
                            source_set_hash=source_set_hash,
                        ),
                    }
                )
        resolution_checks = [
            check
            for check in report["duplicate_resolution_checks"]
            if left["key"] in check["pair"]
            or (
                semantic
                and any(
                    isinstance(side.get("target"), dict)
                    and side["target"].get("globalid") == row["globalid"]
                    for side in check["remembered"]["basis"]["sides"]
                )
            )
        ]
        # A policy migration changes side keys. Use the remembered GUID to
        # require explicit review, never to silently migrate the old consent.
        stale_resolution = any(check["status"] == "stale" for check in resolution_checks)
        metadata = after["metadata"]
        point = after["location"]
        regions = resolver.qualification_regions(lat=float(point["lat"]), lon=float(point["lon"]))
        category = {
            "jaskinia": "jaskinia_otwor",
            "sztolnia": "sztolnia",
            "ponor": "ponor",
            "wywierzysko": "wywierzysko",
        }.get(normalize_name(metadata.get("GENEZA")))
        name_tokens = set(re.findall(r"\w+", normalize_name(metadata.get("NAZWA"))))
        category_cues = {
            "sztolnia": "sztolnia",
            "ponor": "ponor",
            "wywierzysko": "wywierzysko",
            "jaskinia": "jaskinia_otwor",
        }
        if any(
            token in name_tokens and expected != category
            for token, expected in category_cues.items()
        ):
            category = None  # Explicit source/name contradiction needs human classification.
        source_context = {
            k: metadata.get(k)
            for k in ("WER_LOK", "UWAGI", "OPIS", "TATER")
            if metadata.get(k) is not None
        }
        checks = {
            "new_unique_guid": "new_guid" in row["classification"]
            and not catalog.guids.get(row["globalid"])
            and row["globalid"] not in historical_guids,
            "geometry": regions["inside_pl_sk"],
            "category": category is not None,
            "region": len(regions["valleys"]) == 1 and bool(regions["valleys"][0]["prefix"]),
            "measurement": after["source_time"]["date_basis"] == "source_modified",
            "name": bool(normalize_name(metadata.get("NAZWA"))),
            "standalone": not metadata.get("SYSTEM") and not metadata.get("OTWÓR"),
            "comparison_complete": report["candidate_source_inputs"]["complete"]
            and not catalog_gaps,
            "source_review_clear": not source_context
            and not row["conflicts"]
            and not stale_resolution,
        }
        blocks = [
            {
                "code": "condition_failed",
                "condition": k,
                "evidence": {
                    "source": after,
                    "historical_guid": historical_guids.get(row["globalid"], []),
                    "regions": regions,
                    "category": category,
                    "source_context": source_context,
                    "conflicts": row["conflicts"],
                    "source_inputs": report["candidate_source_inputs"],
                    "catalog_gaps": catalog_gaps,
                    "remembered_resolutions": resolution_checks,
                },
            }
            for k, v in checks.items()
            if not v
        ]
        blocks.extend(
            {"code": "candidate_collision", "candidate_key": c["key"], "evidence": c["evidence"]}
            for c in candidates
        )
        row["candidates"] = candidates
        row["new_record_qualification"] = {
            "status": qualify(checks, candidates),
            "checks": checks,
            "blocks": blocks,
            "category": category,
            "regions": regions,
            "proposed_actions": [],
        }
        if stale_resolution:
            row["requires_review"] = True
            row["actionable"] = True
            row["review_status"] = "pending"
    report["requires_pr"] = any(row["actionable"] for row in report["records"])
    report["qualification_summary"] = {
        key: sum(
            r.get("new_record_qualification", {}).get("status") == key for r in report["records"]
        )
        for key in ("automatic_proposal", "review")
    }
