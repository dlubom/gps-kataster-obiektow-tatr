"""Read-only TPN comparison, optionally including candidate qualification."""

from __future__ import annotations

import html
from collections import Counter, defaultdict
from pathlib import Path

from .data_loader import load_dataset
from .tpn_api import globalid, require
from .tpn_normalization import (
    CSV_PATH,
    VERSION,
    canonical,
    decimal,
    digest,
    distance,
    exact_json,
    read_csv,
    read_snapshot,
    same_location,
    text,
)
from .tpn_snapshot import POLICY, SNAPSHOTS, sha256, validate_id, validate_time
from .tpn_source_state import validate_state


class Catalog:
    def __init__(self, root: Path):
        dataset = load_dataset(root / "data")
        self.records = {}
        self.paths = {}
        self.hashes = {}
        self.guids = defaultdict(list)
        self.objects = {}
        self.caves = {}
        self.relations = []
        for record in dataset.records():
            path = record.path.relative_to(root).as_posix()
            require(record.path.resolve() == record.path, "catalog symlink")
            value = record.data
            identity = value.get("id")
            require(
                isinstance(identity, str) and bool(identity) and identity not in self.records,
                "missing/duplicate catalog ID",
            )
            self.records[identity] = value
            self.paths[identity] = path
            self.hashes[path] = sha256(record.path.read_bytes())
        for record in dataset.objects:
            obj = record.data
            self.objects[obj["id"]] = obj
            typed = set()
            for ref in obj["external_refs"]:
                if ref.get("system") == "TPN" and ref.get("ref_type") == "source_globalid":
                    guid = globalid(ref["external_id"])
                    require(guid not in typed, "duplicate typed reference within object")
                    typed.add(guid)
                    self.guids[guid].append(obj["id"])
            ids = [m.get("id") for m in obj["measurements"]]
            require(
                all(isinstance(x, str) and x for x in ids) and len(ids) == len(set(ids)),
                "invalid/duplicate measurement ID",
            )
            for m in obj["measurements"]:
                require(
                    type(m.get("lat")) in (int, float)
                    and type(m.get("lon")) in (int, float)
                    and -90 <= m["lat"] <= 90
                    and -180 <= m["lon"] <= 180,
                    "invalid catalog XY",
                )
        self.caves = {r.data["id"]: r.data for r in dataset.caves}
        self.relations = [r.data for r in dataset.relations]
        # Conservative full catalog + spatial input fingerprint. No spatial matching here.
        for folder in (root / "config", root / "data/shapes"):
            require(folder.is_dir(), "missing catalog configuration")
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    require(path.resolve() == path, "configuration symlink")
                    self.hashes[path.relative_to(root).as_posix()] = sha256(path.read_bytes())
        self.hash = digest(sorted(self.hashes.items()))

    def context(self, object_id: str | None) -> tuple[dict | None, dict, dict | None]:
        if object_id is None:
            return None, {}, None
        obj = self.objects[object_id]
        cave_id = obj.get("cave_id")
        require(cave_id is None or cave_id in self.caves, "missing target cave")
        relations = [
            r
            for r in self.relations
            if object_id in (r.get("from_object_id"), r.get("to_object_id"))
        ]
        identities = [object_id] + ([cave_id] if cave_id else []) + [r["id"] for r in relations]
        preimage = {self.paths[x]: self.hashes[self.paths[x]] for x in identities}
        return (
            {"object_id": object_id, "cave_id": cave_id},
            preimage,
            {"object": obj, "cave": self.caves.get(cave_id), "relations": relations},
        )


class Sources:
    def __init__(self, root: Path, policy_hash: str):
        self.root, self.policy_hash = root, policy_hash
        self.cache = {}

    def by_hash(self, checksum: str) -> dict:
        if checksum not in self.cache:
            matches = []
            for path in sorted((self.root / SNAPSHOTS).glob("*/manifest.json")):
                manifest = exact_json(path.read_bytes())
                if manifest.get("snapshot_hash") == checksum:
                    matches.append(path.parent)
            require(len(matches) == 1, "accepted/evidence snapshot missing or ambiguous")
            manifest, records = read_snapshot(matches[0], self.policy_hash)
            require(manifest["snapshot_hash"] == checksum, "snapshot hash mismatch")
            self.cache[checksum] = records
        return self.cache[checksum]

    def baseline(self, reference: dict) -> dict:
        if reference["kind"] == "accepted_snapshot":
            return self.by_hash(reference["snapshot_hash"])
        require(
            reference["path"] == CSV_PATH.as_posix()
            and sha256((self.root / CSV_PATH).read_bytes()) == reference["raw_sha256"],
            "CSV baseline evidence mismatch",
        )
        return read_csv(self.root / CSV_PATH)


def measurement_guid(measurement: dict) -> str | None:
    ref = measurement.get("source_ref")
    if measurement.get("source") != "TPN" or not isinstance(ref, str) or not ref.startswith("TPN:"):
        return None
    try:
        return globalid(ref[4:])
    except ValueError:
        return None


def history_for(
    obj: dict | None, before: dict | None, after: dict | None, guid: str, applied: list[dict]
) -> dict:
    result = {"baseline_matches": [], "current_matches": [], "same_guid_measurements": []}
    if obj is None:
        return result
    linked = {
        globalid(r["external_id"])
        for r in obj["external_refs"]
        if r.get("system") == "TPN" and r.get("ref_type") == "source_globalid"
    }
    for m in obj["measurements"]:
        mguid = measurement_guid(m)
        if mguid not in linked:
            continue
        if mguid == guid:
            result["same_guid_measurements"].append(m["id"])
        for key, source in (("baseline_matches", before), ("current_matches", after)):
            if source is None or (key == "baseline_matches" and mguid != guid):
                continue
            # YAML from the historical CSV conversion has a 0.1 m bootstrap tolerance.
            # Later API equivalence is exact: sub-centimetre moves remain revisions.
            tolerance = before is not None and before["kind"] == "csv"
            agrees = (
                distance(source["location"], m) <= 0.1
                if tolerance
                else (
                    decimal(source["location"]["lat"]) == decimal(m["lat"])
                    and decimal(source["location"]["lon"]) == decimal(m["lon"])
                )
            )
            basis = "csv_conversion_tolerance" if tolerance else "exact_api_xy"
            if not agrees:
                for known in applied:
                    if (
                        known["object_id"] == obj["id"]
                        and known["globalid"] == mguid
                        and source["location_hash"] == known["location_hash"]
                        and (
                            distance(known["location"], m) <= 0.1
                            if known["basis"] == "accepted_csv_bootstrap"
                            else (
                                float(known["location"]["lat"]) == m["lat"]
                                and float(known["location"]["lon"]) == m["lon"]
                            )
                        )
                    ):
                        agrees, basis = True, known["basis"]
                        break
            if agrees:
                result[key].append(
                    {
                        "measurement_id": m["id"],
                        "source_globalid": mguid,
                        "distance_m": distance(source["location"], m),
                        "basis": basis,
                    }
                )
    return result


def local_differences(
    context: dict | None, before: dict | None, after: dict | None, history: dict
) -> list[dict]:
    if not context or not before:
        return []
    obj, cave = context["object"], context["cave"]
    metadata = before["metadata"]
    differences = []
    # These are field comparisons, never automatic assignments. NAZWA may refer
    # to either level; report both without guessing a target for a write.
    fields = [
        (
            "object.name_local",
            obj.get("name_local"),
            metadata.get("OTWÓR") or metadata["NAZWA"],
            "OTWÓR" if metadata.get("OTWÓR") else "NAZWA",
        )
    ]
    if cave:
        fields.extend(
            [
                ("cave.name", cave.get("name"), metadata["NAZWA"], "NAZWA"),
                ("cave.system_name", cave.get("system_name"), metadata["SYSTEM"], "SYSTEM"),
            ]
        )
    for path, current, old, source_field in fields:
        if text(current) != old:
            differences.append(
                {
                    "field": path,
                    "source_field": source_field,
                    "source_before": old,
                    "source_after": after["metadata"][source_field] if after else None,
                    "catalog_current": current,
                }
            )
    if history["same_guid_measurements"] and not history["baseline_matches"]:
        differences.append(
            {
                "field": "measurements.location",
                "source_before": before["location"],
                "source_after": after["location"] if after else None,
                "catalog_current": obj["measurements"],
            }
        )
    return differences


def absence_revision(before: dict, snapshot_hash: str, policy_hash: str) -> str:
    return digest(
        {
            "source_missing": before["revision_hash"],
            "snapshot_hash": snapshot_hash,
            "policy_hash": policy_hash,
        }
    )


def compare(
    repo_root: Path,
    snapshot_path: Path,
    *,
    batch_id: str,
    base_commit: str,
    state: dict | None = None,
    candidate_policy=None,
    duplicate_resolutions: list[dict] | None = None,
) -> dict:
    """Pure report generation; state is already accepted by the caller (CLI: main)."""
    root = Path(repo_root).resolve()
    validate_id(batch_id)
    policy_hash = sha256((root / POLICY).read_bytes())
    manifest, current = read_snapshot(snapshot_path, policy_hash)
    catalog = Catalog(root)
    sources = Sources(root, policy_hash)
    sources.cache[manifest["snapshot_hash"]] = current
    resolutions = []
    applied = []
    deferred_sources = {}
    absent_events = {}
    latest_absence = {}
    if state is None:
        previous = read_csv(root / CSV_PATH)
        baseline = {
            "kind": "csv_bootstrap",
            "path": CSV_PATH.as_posix(),
            "raw_sha256": sha256((root / CSV_PATH).read_bytes()),
        }
    else:
        validate_state(state, policy_hash)
        previous = sources.by_hash(state["accepted_snapshot_hash"])
        baseline = {"kind": "accepted_snapshot", "snapshot_hash": state["accepted_snapshot_hash"]}
        resolutions = state["resolutions"]
        for resolution in sorted(resolutions, key=lambda r: validate_time(r["reviewed_at"])):
            evidence = sources.by_hash(resolution["snapshot_hash"]).get(resolution["globalid"])
            # Absence events have no source record; their hash binds the complete
            # snapshot and is not a fabricated feature revision.
            if evidence is not None:
                require(
                    evidence["revision_hash"] == resolution["revision_hash"],
                    "resolution revision/evidence mismatch",
                )
                require(resolution["absence"] is None, "unexpected absence evidence")
            else:
                require(resolution["absence"] is not None, "missing absence evidence")
                evidence = sources.baseline(resolution["absence"]["baseline"]).get(
                    resolution["globalid"]
                )
                require(
                    evidence is not None
                    and evidence["revision_hash"] == resolution["absence"]["previous_revision_hash"]
                    and absence_revision(evidence, resolution["snapshot_hash"], policy_hash)
                    == resolution["revision_hash"],
                    "absence revision/evidence mismatch",
                )
                absent_events[(resolution["globalid"], resolution["revision_hash"])] = (
                    resolution,
                    evidence,
                )
                latest_absence[resolution["globalid"]] = (resolution, evidence)
            for location in resolution["applied_locations"]:
                source = sources.by_hash(location["source_snapshot_hash"]).get(
                    resolution["globalid"]
                )
                require(
                    source is not None
                    and source["location_hash"] == location["location_hash"]
                    and resolution["target"] is not None,
                    "applied location/evidence mismatch",
                )
                if location["csv_evidence"] is not None:
                    require(
                        sha256((root / CSV_PATH).read_bytes())
                        == location["csv_evidence"]["raw_sha256"],
                        "bootstrap CSV evidence changed",
                    )
                    old = read_csv(root / CSV_PATH).get(resolution["globalid"])
                    require(
                        old is not None and same_location(old, source),
                        "bootstrap location mismatch",
                    )
                    applied.append(
                        {
                            "object_id": resolution["target"]["object_id"],
                            "globalid": resolution["globalid"],
                            "location_hash": location["location_hash"],
                            "location": old["location"],
                            "basis": "accepted_csv_bootstrap",
                        }
                    )
                else:
                    applied.append(
                        {
                            "object_id": resolution["target"]["object_id"],
                            "globalid": resolution["globalid"],
                            "location_hash": location["location_hash"],
                            "location": source["location"],
                            "basis": "accepted_api_location",
                        }
                    )
        for entry in state["deferred"]:
            evidence = sources.by_hash(entry["snapshot_hash"]).get(entry["globalid"])
            if evidence is None and (entry["globalid"], entry["revision_hash"]) in absent_events:
                evidence = absent_events[(entry["globalid"], entry["revision_hash"])][1]
            if evidence is not None:
                deferred_sources[entry["globalid"]] = evidence
    rows = []
    for guid in sorted(set(previous) | set(current) | set(deferred_sources) | set(latest_absence)):
        fallback = latest_absence[guid][1] if guid in latest_absence else deferred_sources.get(guid)
        after = current.get(guid)
        before = previous.get(guid, fallback if after is None else None)
        ids = catalog.guids.get(guid, [])
        target, preimage, context = catalog.context(ids[0] if len(ids) == 1 else None)
        obj = context["object"] if context else None
        history = history_for(obj, before, after, guid, applied)
        differences = local_differences(context, before, after, history)
        conflicts = []
        if len(ids) > 1:
            conflicts.append("ambiguous_typed_globalid")
        if (
            state
            and guid in state["bindings"]
            and (not target or target["object_id"] != state["bindings"][guid])
        ):
            conflicts.append("binding_target_changed")
        if (
            len(history["baseline_matches"]) > 1
            or len([m for m in history["current_matches"] if m["source_globalid"] == guid]) > 1
        ):
            conflicts.append("ambiguous_history")
        if obj and not history["same_guid_measurements"] and not history["current_matches"]:
            conflicts.append("missing_source_history")
        if differences:
            conflicts.append("local_fields_differ")
        classes = []
        if after is None:
            classes.append("source_missing")
        elif before is None:
            classes.append("new_guid")
        else:
            if before["metadata"] != after["metadata"]:
                classes.append("metadata_changed")
            if not same_location(before, after):
                classes.append("location_changed")
            if not classes:
                classes.append(
                    "technical_only" if before["technical"] != after["technical"] else "unchanged"
                )
        if not ids and after is not None:
            classes.append("unmapped_guid")
        revision = (
            after["revision_hash"]
            if after
            else absence_revision(before, manifest["snapshot_hash"], policy_hash)
        )
        if guid not in previous and after is None and guid in latest_absence:
            revision = latest_absence[guid][0]["revision_hash"]
        matches = [
            r for r in resolutions if r["globalid"] == guid and r["revision_hash"] == revision
        ]
        status = "pending"
        valid_resolution = False
        if matches:
            resolution = matches[0]
            expected_catalog = (
                resolution["result_catalog_hash"]
                if resolution["status"] == "approve"
                else resolution["catalog_hash"]
            )
            expected_files = (
                resolution["result_hashes"]
                if resolution["status"] == "approve"
                else resolution["preimage"]
            )
            valid_resolution = (
                resolution["target"] == target
                and expected_catalog == catalog.hash
                and expected_files == preimage
            )
            if valid_resolution:
                status = resolution["status"]
            else:
                conflicts.append("stale_resolution")
        if conflicts:
            classes = [c for c in classes if c not in ("unchanged", "technical_only")] + [
                "local_conflict"
            ]
        substantive = any(c not in ("unchanged", "technical_only") for c in classes)
        if not substantive and not matches:
            status = "informational"
        bootstrap = None
        if (
            state is None
            and target
            and len(history["baseline_matches"]) == 1
            and "ambiguous_history" not in conflicts
        ):
            bootstrap = {
                "accepted": False,
                "globalid": guid,
                "object_id": target["object_id"],
                "measurement_id": history["baseline_matches"][0]["measurement_id"],
                "source": baseline,
                "preimage": preimage,
            }
        rows.append(
            {
                "change_id": guid + ":" + revision,
                "globalid": guid,
                "revision_hash": revision,
                "location_hash": after["location_hash"] if after else None,
                "classification": classes,
                "source_before": before,
                "source_after": after,
                "target": target,
                "preimage": preimage,
                "catalog_current": context,
                "candidates": [],
                "conflicts": conflicts,
                "proposal_origin": "automatic",
                "proposed_actions": [],
                "best_before": obj.get("best_measurement") if obj else None,
                "best_after": obj.get("best_measurement") if obj else None,
                "distance_m": distance(before["location"], after["location"])
                if before and after
                else None,
                "local_differences": differences,
                "history": history,
                "bootstrap_binding": bootstrap,
                "measurement_needed": bool(
                    after
                    and (before is None or not same_location(before, after))
                    and not history["current_matches"]
                ),
                "review_status": status,
                "requires_review": (substantive and not valid_resolution) or status == "defer",
                "actionable": (substantive or bool(matches)) and not valid_resolution,
            }
        )
    deferred = []
    for entry in state["deferred"] if state else []:
        evidence = sources.by_hash(entry["snapshot_hash"]).get(entry["globalid"])
        if evidence is None and (entry["globalid"], entry["revision_hash"]) in absent_events:
            evidence = absent_events[(entry["globalid"], entry["revision_hash"])][1]
        after = current.get(entry["globalid"])
        deferred.append(
            {
                **entry,
                "source": evidence,
                "status": "active"
                if after and after["revision_hash"] == entry["revision_hash"]
                else "superseded"
                if after
                else "source_missing",
            }
        )
    report = {
        "format": "tpn-changes",
        "format_version": 1,
        "batch_id": batch_id,
        "snapshot_hash": manifest["snapshot_hash"],
        "policy_version": VERSION,
        "policy_hash": policy_hash,
        "base_commit": base_commit,
        "catalog_hash": catalog.hash,
        "state_hash": digest(state),
        "baseline": baseline,
        "records": rows,
        "deferred": deferred,
        "requires_pr": any(r["actionable"] for r in rows),
        "summary": dict(sorted(Counter(c for r in rows for c in r["classification"]).items())),
    }
    if candidate_policy is not None:
        from .prefix_resolver import PrefixResolver
        from .tpn_candidate_sources import pig_sides
        from .tpn_candidates import augment

        historical_sides, source_inputs = pig_sides(root)
        extra_sources = {
            f"snapshot:{key}": value
            for key, value in sources.cache.items()
            if key != manifest["snapshot_hash"]
        }
        if state is not None:
            # Acceptance advances the comparison baseline, never erases the
            # original source names/locations as duplicate-warning evidence.
            extra_sources["historical_csv"] = read_csv(root / CSV_PATH)
        augment(
            report,
            catalog,
            current,
            previous,
            PrefixResolver(
                config_path=root / "config/prefixes.yml", shapes_dir=root / "data/shapes"
            ),
            candidate_policy,
            duplicate_resolutions if duplicate_resolutions is not None else [],
            extra_sources,
            historical_sides,
            source_inputs,
        )
    return report


def pretty_json(value: object, indent: int = 0) -> str:
    """Human readable exact JSON; no float round-trip while rendering decimals."""
    if isinstance(value, dict) and value:
        body = [
            " " * (indent + 2) + canonical(k).decode() + ": " + pretty_json(value[k], indent + 2)
            for k in sorted(value)
        ]
        return "{\n" + ",\n".join(body) + "\n" + " " * indent + "}"
    if isinstance(value, list) and value:
        return (
            "[\n"
            + ",\n".join(" " * (indent + 2) + pretty_json(v, indent + 2) for v in value)
            + "\n"
            + " " * indent
            + "]"
        )
    return canonical(value).decode()


def render_markdown(report: dict) -> str:
    """Field-level before/after tables and full current catalog evidence."""

    def cell(value):
        return html.escape(canonical(value).decode()).replace("|", "&#124;").replace("`", "&#96;")

    lines = [
        "# Porównanie TPN",
        "",
        f"Snapshot: `{report['snapshot_hash']}`",
        f"Baza: `{canonical(report['baseline']).decode()}`",
        f"Wymaga nowego review/PR: **{report['requires_pr']}**",
        "",
        "Odległości opisują różnicę XY, nie dokładność ani tożsamość. "
        "Brak akcji; best pozostaje bez zmian.",
        "",
        "```json",
        pretty_json(report["summary"]),
        "```",
    ]
    if "candidate_policy" in report:
        lines.extend(
            [
                "",
                "## Polityka kandydatów i kwalifikacja",
                "```json",
                pretty_json(
                    {
                        k: report[k]
                        for k in (
                            "candidate_policy",
                            "candidate_source_inputs",
                            "candidate_comparison_hash",
                            "qualification_summary",
                            "duplicate_resolution_checks",
                        )
                    }
                ),
                "```",
            ]
        )
    for row in report["records"]:
        lines.extend(
            [
                "",
                f"## {row['globalid']} — {', '.join(row['classification'])}",
                "",
                f"Cel: {row['target']}; review: {row['review_status']}; "
                f"różnica XY: {row['distance_m']} m",
                "",
                "### Źródło before / after",
                "",
                "| Pole | Before | After |",
                "|---|---|---|",
            ]
        )
        before, after = row["source_before"], row["source_after"]
        for section in ("metadata", "location", "technical", "source_time"):
            old = before.get(section) or {} if before else {}
            new = after.get(section) or {} if after else {}
            for field in sorted(set(old) | set(new)):
                lines.append(
                    f"| {section}.{field} | {cell(old.get(field))} | {cell(new.get(field))} |"
                )
        if "new_record_qualification" in row:
            lines.extend(
                [
                    "",
                    "### Kandydaci i blokady automatu",
                    "```json",
                    pretty_json(
                        {
                            "candidates": row["candidates"],
                            "qualification": row["new_record_qualification"],
                        }
                    ),
                    "```",
                ]
            )
        lines.extend(
            [
                "",
                "### Obecny katalog / niezależne różnice / historia",
                "",
                "```json",
                pretty_json(
                    {
                        k: row[k]
                        for k in (
                            "catalog_current",
                            "local_differences",
                            "history",
                            "conflicts",
                            "best_before",
                            "best_after",
                        )
                    }
                ),
                "```",
            ]
        )
    if report["deferred"]:
        lines.extend(
            ["", "## Zachowane odroczenia", "```json", pretty_json(report["deferred"]), "```"]
        )
    return "\n".join(lines) + "\n"
