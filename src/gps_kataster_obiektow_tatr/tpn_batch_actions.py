"""Whole-batch domain planning. Existing history is append-only."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

from .coordinates import wgs84_to_1992
from .data_loader import load_dataset
from .prefix_resolver import PrefixResolver
from .staging_review import _dataset_with_review_changes
from .tpn_api import globalid, require
from .tpn_best_guard import plan_best_action
from .tpn_changes import Catalog, measurement_guid
from .tpn_editorial_notes import measurement_notes
from .tpn_normalization import distance
from .tpn_precision import projected_metres
from .validator import format_issue, has_errors, validate_dataset


def yaml_bytes(value):
    import yaml

    return yaml.safe_dump(value, allow_unicode=True, sort_keys=True).encode()


def next_id(prefix, used, width):
    numbers = [
        int(x[len(prefix) :]) for x in used if x.startswith(prefix) and x[len(prefix) :].isdigit()
    ]
    result = f"{prefix}{max(numbers, default=0) + 1:0{width}}"
    require(result not in used, "ID collision")
    used.add(result)
    return result


def measurement(row, identity, d, *, legacy=False):
    source = row["source_after"]
    require(source is not None, "missing source cannot create measurement")
    time = source["source_time"]
    require(time["date_basis"] == "source_modified", "missing modification date: defer measurement")
    point = source["location"]
    lat, lon = float(point["lat"]), float(point["lon"])
    xy = wgs84_to_1992(lat, lon)
    notes = [
        "Data pomiaru terenowego nieznana; użyto daty modyfikacji rekordu TPN.",
        "TPN LAST_EDITED_DATE: " + time["source_modified_at"],
    ]
    if legacy:
        notes.append("TPN revision: " + row["revision_hash"])
    for key in ("WER_LOK", "UWAGI"):
        if source["metadata"][key] is not None:
            notes.append(f"TPN {key}: {source['metadata'][key]}")
    return {
        "id": identity,
        "lat": lat,
        "lon": lon,
        "x_1992": projected_metres(xy.x_1992),
        "y_1992": projected_metres(xy.y_1992),
        "elevation_m": None,
        "elevation_datum": "unknown",
        "elevation_source": "source_record",
        "horizontal_accuracy_m": None,
        "vertical_accuracy_m": None,
        "source": "TPN",
        "source_ref": "TPN:" + row["globalid"],
        "observed_at": None,
        "observed_date": time["source_date"],
        "source_date": time["source_date"],
        "method": "source_record",
        "device": None,
        "tags": [] if legacy else ["tpn"],
        "verification_status": "nieweryfikowany",
        "verified_by": None,
        "verified_at": None,
        "notes": "\n".join(notes) if legacy else measurement_notes("\n".join(notes)),
        "created_at": d["reviewed_at"],
        "created_by": d["reviewed_by"],
    }


class DomainPlan:
    def __init__(self, root, changes, decisions):
        self.root, self.changes, self.decisions = root, changes, decisions
        self.legacy_measurements = changes["execution"]["format_version"] == 1
        self.catalog = Catalog(root)
        self.dataset = load_dataset(root / "data")
        self.resolver = PrefixResolver(
            config_path=root / "config/prefixes.yml", shapes_dir=root / "data/shapes"
        )
        self.validate(self.dataset)
        self.objects = deepcopy(self.catalog.objects)
        self.caves = deepcopy(self.catalog.caves)
        self.paths = dict(self.catalog.paths)
        self.used = set(self.catalog.records)
        self.keys, self.measurement_keys = {}, {}
        self.additions, self.best_actions = defaultdict(list), defaultdict(list)
        self.applied = defaultdict(list)
        self.dirty, self.claims = set(), set()
        self.row_targets = {}
        self.best_changes = []
        self.cave_owners = {}

    def proposal_time(self):
        from .tpn_normalization import exact_json

        for path in (self.root / "data/sources/tpn/snapshots").glob("*/manifest.json"):
            manifest = exact_json(path.read_bytes())
            if manifest["snapshot_hash"] == self.changes["snapshot_hash"]:
                return manifest["fetched_at"]
        raise ValueError("proposal snapshot missing")

    def validate(self, dataset):
        issues = validate_dataset(
            dataset,
            data_dir=self.root / "data",
            repo_root=self.root,
            schema_dir=self.root / "schema",
            prefix_resolver=self.resolver,
        )
        require(
            not has_errors(issues),
            "full catalog validation: "
            + "; ".join(format_issue(i) for i in issues if i.severity == "error"),
        )

    def touch(self, identity, d):
        entity = self.objects.get(identity, self.caves.get(identity))
        entity.update(updated_at=d["reviewed_at"], updated_by=d["reviewed_by"])
        self.dirty.add(identity)

    def preimages(self, p):
        identities = set()
        t = p["target"]
        if t:
            if t.get("object_id"):
                _, files, _ = self.catalog.context(t["object_id"])
                identities.update(files)
                require(
                    self.catalog.objects[t["object_id"]].get("cave_id") == t["cave_id"],
                    "target cave mismatch",
                )
            if t["cave_id"]:
                identities.add(self.catalog.paths[t["cave_id"]])
        for a in p["actions"]:
            if "object_id" in a:
                obj = a["object_id"]
                require(t and t.get("object_id") == obj, "action object outside reviewed target")
            if a["action"] == "link_cave":
                require(a["cave_id"] in self.catalog.caves, "missing destination cave")
                identities.add(self.catalog.paths[a["cave_id"]])
            if "target" in a:
                at = a["target"]
                require(t is not None, "action requires reviewed target")
                if at["kind"] == "cave":
                    require(at["id"] == t["cave_id"], "action cave outside reviewed target")
                else:
                    require(at["id"] == t.get("object_id"), "action object outside reviewed target")
                identities.add(self.catalog.paths[at["id"]])
        expected = {path: self.catalog.hashes[path] for path in sorted(identities)}
        require(p["preimage"] == expected, "incomplete/stale target preimage")

    def run(self):
        rows = {r["change_id"]: r for r in self.changes["records"]}
        proposals = {p["change_id"]: p for p in self.changes["execution"]["proposals"]}
        # Decision document order is intentional. IDs are allocated once for the complete plan.
        for d in self.decisions["decisions"]:
            row, p = rows[d["change_id"]], proposals[d["change_id"]]
            self.preimages(p)
            if row["target"] is not None:
                require(p["target"] == row["target"], "mapped source target cannot be changed")
            if d["status"] in ("reject", "defer"):
                continue
            automatic = d["status"] == "pending"
            if automatic:
                q = row.get("new_record_qualification", {})
                # Existing and uncertain proposals remain visible, without applying
                # any of their actions before an authorized human decision.
                if not p["actions"] or q.get("status") != "automatic_proposal":
                    continue
                require(row["proposal_origin"] == "automatic", "invalid automatic proposal origin")
                require(
                    p["target"] is None
                    and all(a["action"] in ("new_object", "create_cave") for a in p["actions"]),
                    "pending existing action forbidden",
                )
                d = {
                    **d,
                    "reviewed_by": "automatic:tpn-proposal",
                    "reviewed_at": self.proposal_time(),
                }
            source = row["source_after"]
            for a in p["actions"]:
                kind = a["action"]
                if source is None:
                    raise ValueError("source_missing permits acknowledgement only")
                if kind in ("append_measurement", "new_object"):
                    require(a["location_hash"] == row["location_hash"], "location hash mismatch")
                getattr(self, kind)(a, row, d)
            if p["target"] and p["target"].get("object_id"):
                self.row_targets[row["change_id"]] = p["target"]["object_id"]
            if automatic:
                # Technical proposal audit is separate from a human decision.
                continue
        for oid, additions in self.additions.items():
            base = self.catalog.objects[oid]
            choices = []
            for a, d in self.best_actions[oid]:
                choice = deepcopy(a)
                if choice["action"] == "select_new":
                    key = choice.pop("measurement_key")
                    require((oid, key) in self.measurement_keys, "unknown selected measurement key")
                    choice["measurement_id"] = self.measurement_keys[(oid, key)]
                choices.append((choice, d))
            require(
                all(c == choices[0][0] for c, _ in choices), "conflicting best actions for object"
            )
            choice, d = choices[0]
            # Joint planning includes notes just accepted in this batch: new
            # geodetic evidence must be visible to the guard before selecting best.
            guard_object = deepcopy(self.objects[oid])
            guard_object["measurements"] = guard_object["measurements"][: len(base["measurements"])]
            plan = plan_best_action(guard_object, additions, choice)
            require(plan["can_apply"], "best blocked: " + ",".join(plan["blockers"]))
            best = plan["after"]
            if best != base["best_measurement"]:
                best.update(updated_by=d["reviewed_by"], updated_at=d["reviewed_at"])
            self.objects[oid]["best_measurement"] = best
            self.best_changes.append(
                {"object_id": oid, "before": base["best_measurement"], "after": best, "guard": plan}
            )
        # Every new object must have an explicit, symmetric cave assignment if it is an opening.
        for oid in self.objects.keys() - self.catalog.objects.keys():
            obj = self.objects[oid]
            require(
                obj["category"] != "jaskinia_otwor" or obj.get("cave_id"),
                "new opening needs create_cave/link_cave",
            )
        future = _dataset_with_review_changes(
            self.dataset, data_dir=self.root / "data", objects=self.objects, caves=self.caves
        )
        self.validate(future)
        self.future = future
        files = {}
        for ident in self.dirty:
            data = self.objects.get(ident, self.caves.get(ident))
            files[self.paths[ident]] = yaml_bytes(data)
        return files

    def claim(self, key):
        require(key not in self.claims, "conflicting actions on same field/identity")
        self.claims.add(key)

    def update_metadata(self, a, row, d):
        t, field = a["target"], a["field"]
        source = self.caves if t["kind"] == "cave" else self.objects
        base_source = self.catalog.caves if t["kind"] == "cave" else self.catalog.objects
        current, base = source[t["id"]], base_source[t["id"]]
        if t["kind"] == "measurement":
            current = next(m for m in current["measurements"] if m["id"] == t["measurement_id"])
            base = next(m for m in base["measurements"] if m["id"] == t["measurement_id"])
        require(base.get(field) == a["before"], "metadata before mismatch")
        key = (t["kind"], t["id"], t.get("measurement_id"), field)
        if field == "notes":
            require(a["revision_hash"] == row["revision_hash"], "note revision mismatch")
            fragment = f"[TPN {row['revision_hash']}] {a['append_text']}"
            before = base.get(field) or ""
            already_present = f"\n{fragment}\n" in f"\n{before}\n"
            expected = before if already_present else before + ("\n" if before else "") + fragment
            require(a["after"] == expected, "note after must preserve or append exact fragment")
            self.claim((*key, fragment))
            if not already_present:
                current[field] = (
                    (current.get(field) or "") + ("\n" if current.get(field) else "") + fragment
                )
        else:
            self.claim(key)
            current[field] = a["after"]
        self.touch(t["id"], d)

    def attach_source(self, a, row, d):
        t, ref = a["target"], a["reference"]
        if t["kind"] == "object":
            require(ref["external_id"] == row["globalid"], "reference GUID outside revision")
            require(
                not self.catalog.guids.get(row["globalid"])
                or self.catalog.guids[row["globalid"]] == [t["id"]],
                "GUID already bound elsewhere",
            )
            entity = self.objects[t["id"]]
        else:
            require(
                ref["external_id"] == row["source_after"]["metadata"]["NR_INWENT"],
                "inventory value outside source",
            )
            entity = self.caves[t["id"]]
        existing = entity["external_refs"]
        identity = (ref["system"], ref["ref_type"], ref["external_id"])
        if not any(
            (
                r["system"],
                r["ref_type"],
                globalid(r["external_id"])
                if r["system"] == "TPN" and r["ref_type"] == "source_globalid"
                else r["external_id"],
            )
            == identity
            for r in existing
        ):
            existing.append({**ref, "scope": t["kind"], "notes": a["evidence"]})
            self.touch(t["id"], d)

    def append_measurement(self, a, row, d):
        oid = a["object_id"]
        obj = self.objects[oid]
        require(
            row["source_before"] is None or "location_changed" in row["classification"],
            "metadata/date-only revision cannot create measurement",
        )
        require(
            any(
                r["system"] == "TPN"
                and r["ref_type"] == "source_globalid"
                and globalid(r["external_id"]) == row["globalid"]
                for r in obj["external_refs"]
            ),
            "attach_source required before append",
        )
        require(
            (oid, a["measurement_key"]) not in self.measurement_keys, "duplicate measurement key"
        )
        if row["target"] is not None and row["target"].get("object_id") == oid:
            # Verified history includes accepted CSV/API associations even when
            # the historical YAML coordinates differ from the exact API floats.
            require(
                not row["history"]["current_matches"],
                "location already in history; acknowledge without append",
            )
        location = row["source_after"]["location"]
        for m in obj["measurements"]:
            if measurement_guid(m) is not None:
                # No duplicated source location across previously merged GUIDs.
                equal = float(location["lat"]) == m["lat"] and float(location["lon"]) == m["lon"]
                if self.changes["baseline"]["kind"] == "csv_bootstrap":
                    equal = distance(location, m) <= 0.1
                require(not equal, "location already in history; acknowledge without append")
        ids = {m["id"] for m in obj["measurements"]}
        mid = next_id("m-", ids, 3)
        new = measurement(row, mid, d, legacy=self.legacy_measurements)
        self.measurement_keys[(oid, a["measurement_key"])] = mid
        self.additions[oid].append(new)
        self.best_actions[oid].append((a["best_action"], d))
        obj["measurements"].append(new)
        self.applied[row["change_id"]].append(
            {
                "location_hash": row["location_hash"],
                "measurement_id": mid,
                "source_snapshot_hash": self.changes["snapshot_hash"],
                "csv_evidence": None,
            }
        )
        self.touch(oid, d)

    def create_cave(self, a, row, d):
        key = ("cave", a["cave_key"])
        require(key not in self.keys, "duplicate cave key")
        cid = next_id("C-", self.used, 4)
        self.keys[key] = cid
        self.cave_owners[a["cave_key"]] = row["change_id"]
        name = row["source_after"]["metadata"]["NAZWA"]
        require(isinstance(name, str) and bool(name.strip()), "new cave requires name")
        self.caves[cid] = {
            "schema_version": 1,
            "id": cid,
            "name": name,
            "system_name": None,
            "external_refs": [],
            "object_ids": [],
            "notes": None,
            "created_at": d["reviewed_at"],
            "created_by": d["reviewed_by"],
        }
        self.paths[cid] = f"data/caves/{cid}.yml"
        require(not (self.root / self.paths[cid]).exists(), "new cave path already exists")
        self.touch(cid, d)

    def new_object(self, a, row, d):
        require(
            "candidate_policy" in self.changes and "new_record_qualification" in row,
            "PBI-098 qualification report required for new object",
        )
        proposal = next(
            p for p in self.changes["execution"]["proposals"] if p["change_id"] == row["change_id"]
        )
        require(
            proposal["target"] is None or not proposal["target"].get("object_id"),
            "new object cannot target an existing object",
        )
        require(not self.catalog.guids.get(row["globalid"]), "GUID already mapped")
        self.claim(("new-guid", row["globalid"]))
        key = ("object", a["object_key"])
        require(key not in self.keys, "duplicate object key")
        location, meta = row["source_after"]["location"], row["source_after"]["metadata"]
        regions = self.resolver.qualification_regions(
            lat=float(location["lat"]), lon=float(location["lon"])
        )
        require(
            regions["inside_pl_sk"]
            and len(regions["valleys"]) == 1
            and regions["valleys"][0]["prefix"],
            "new object requires unambiguous valley prefix",
        )
        prefix = regions["valleys"][0]["prefix"]
        oid = next_id(prefix + "-", self.used, 4)
        self.keys[key] = oid
        category = a.get("category") or row.get("new_record_qualification", {}).get("category")
        require(category is not None, "uncertain category requires explicit category/evidence")
        require(meta["NAZWA"], "new object requires name")
        m = measurement(row, "m-001", d, legacy=self.legacy_measurements)
        self.objects[oid] = {
            "schema_version": 1,
            "id": oid,
            "category": category,
            "name_local": meta["OTWÓR"] or meta["NAZWA"],
            "cave_id": None,
            "id_assignment": {
                "method": "auto",
                "assigned_from_measurement_id": "m-001",
                "assigned_prefix": prefix,
                "prefix_override_reason": None,
            },
            "external_refs": [
                {
                    "system": "TPN",
                    "ref_type": "source_globalid",
                    "external_id": row["globalid"],
                    "scope": "object",
                }
            ],
            "measurements": [m],
            "best_measurement": {
                "mode": "auto",
                "measurement_id": "m-001",
                "reason": None,
                "updated_by": d["reviewed_by"],
                "updated_at": d["reviewed_at"],
            },
            "attachments": [],
            "notes": None,
            "created_at": d["reviewed_at"],
            "created_by": d["reviewed_by"],
        }
        self.paths[oid] = f"data/objects/{prefix}/{oid}.yml"
        require(not (self.root / self.paths[oid]).exists(), "new object path already exists")
        if d["reviewed_by"] == "automatic:tpn-proposal":
            require(
                category == row["new_record_qualification"]["category"],
                "automatic category must match qualification",
            )
            require(
                "cave_key" not in a or self.cave_owners.get(a["cave_key"]) == row["change_id"],
                "automatic proposal cannot group independent source rows",
            )
        if "cave_key" in a:
            require(("cave", a["cave_key"]) in self.keys, "create cave before new object")
            self.link(oid, self.keys[("cave", a["cave_key"])], d)
        self.row_targets[row["change_id"]] = oid
        self.applied[row["change_id"]].append(
            {
                "location_hash": row["location_hash"],
                "measurement_id": "m-001",
                "source_snapshot_hash": self.changes["snapshot_hash"],
                "csv_evidence": None,
            }
        )
        self.touch(oid, d)

    def link_cave(self, a, row, d):
        oid = a.get("object_id") or self.keys.get(("object", a.get("object_key")))
        require(oid in self.objects, "unknown link object/key")
        self.claim(("cave-link", oid))
        self.link(oid, a["cave_id"], d)

    def link(self, oid, cid, d):
        require(cid in self.caves, "missing link cave")
        obj = self.objects[oid]
        old = obj.get("cave_id")
        if old and old != cid:
            self.caves[old]["object_ids"].remove(oid)
            self.touch(old, d)
        obj["cave_id"] = cid
        if oid not in self.caves[cid]["object_ids"]:
            self.caves[cid]["object_ids"].append(oid)
        self.touch(oid, d)
        self.touch(cid, d)
