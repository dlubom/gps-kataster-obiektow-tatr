"""Read-only comparison, history, accepted state and consecutive cycles."""

import csv
import io
import json
from pathlib import Path

import pytest
import yaml

from gps_kataster_obiektow_tatr import tpn_changes as changes
from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992
from gps_kataster_obiektow_tatr.tpn_normalization import CSV_COLUMNS, CSV_PATH, canonical, digest
from gps_kataster_obiektow_tatr.tpn_snapshot import make_manifest, publish

REPO = Path(__file__).resolve().parents[1]
GUID = "11111111-1111-4111-8111-111111111111"
GUID2 = "22222222-2222-4222-8222-222222222222"
GUID3 = "33333333-3333-4333-8333-333333333333"


def feature(guid=GUID, *, lon=19.8, name="Otwór I", oid=1):
    attrs = json.loads((REPO / "tests/fixtures/tpn_api/page-0.json").read_bytes())["features"][0][
        "attributes"
    ]
    attrs.update(
        GLOBALID=guid,
        NAZWA=name,
        OTWÓR=None,
        SYSTEM=None,
        NR_INWENT=None,
        WER_LOK="opis źródła",
        UWAGI=None,
        OBJECTID=oid,
    )
    return {"attributes": attrs, "geometry": {"x": lon, "y": 49.2}}


def snapshot(repo, name, features):
    layer = json.loads((REPO / "tests/fixtures/tpn_api/layer.json").read_bytes())
    layer["maxRecordCount"] = 100
    page = json.loads((REPO / "tests/fixtures/tpn_api/page-0.json").read_bytes())
    page.update(features=features, exceededTransferLimit=False)
    ids = [f["attributes"]["OBJECTID"] for f in features]
    raw = {
        "layer.json": canonical(layer),
        "layer-after.json": canonical(layer),
        "page-0.json": canonical(page),
        "policy.md": (repo / "docs/asdlc/tpn_sync_contract.md").read_bytes(),
    }
    for side in ("before", "after"):
        raw[f"ids-{side}.json"] = canonical({"objectIdFieldName": "OBJECTID", "objectIds": ids})
        raw[f"count-{side}.json"] = canonical({"count": len(ids)})
    manifest = make_manifest(raw, name, 100, "2026-10-19T00:00:00Z", "2026-10-19T00:00:01Z")
    parent = repo / "data/sources/tpn/snapshots"
    parent.mkdir(parents=True, exist_ok=True)
    return publish(parent, name, raw, manifest)


def csv_source(repo, features):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=sorted(CSV_COLUMNS))
    writer.writeheader()
    for f in features:
        point = wgs84_to_1992(f["geometry"]["y"], f["geometry"]["x"])
        row = {k: f["attributes"].get(k, "") for k in CSV_COLUMNS}
        row.update(X1992=point.x_1992, Y1992=point.y_1992, Z=1234, LAST_EDI_1="1970-01-01 00:00:00")
        writer.writerow(row)
    path = repo / CSV_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output.getvalue())


def object_data(guids=(GUID,)):
    return {
        "id": "KSW-9001",
        "name_local": "Otwór I",
        "cave_id": "C-9001",
        "notes": "Ręczna notatka o scaleniu",
        "category": "jaskinia_otwor",
        "external_refs": [
            {"system": "TPN", "ref_type": "source_globalid", "external_id": "{" + g.upper() + "}"}
            for g in guids
        ],
        "measurements": [
            {
                "id": f"m-{i:03}",
                "lat": 49.2,
                "lon": 19.8,
                "source": "TPN",
                "source_ref": "TPN:{" + g.upper() + "}",
                "elevation_m": 1234,
                "verification_status": "odrzucony",
                "notes": "TPN WER_LOK: opis źródła\nMoja uwaga",
                "observed_date": "1970-01-01",
            }
            for i, g in enumerate(guids, 1)
        ],
        "best_measurement": {"mode": "manual", "measurement_id": "m-001", "reason": "Moja decyzja"},
    }


def save_object(repo, obj):
    path = repo / f"data/objects/KSW/{obj['id']}.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True))


@pytest.fixture
def repo(tmp_path):
    for folder in (
        "data/objects",
        "data/caves",
        "data/relations",
        "config",
        "data/shapes",
        "docs/asdlc",
    ):
        (tmp_path / folder).mkdir(parents=True)
    (tmp_path / "config/prefixes.yml").write_text("{}\n")
    (tmp_path / "docs/asdlc/tpn_sync_contract.md").write_bytes(
        (REPO / "docs/asdlc/tpn_sync_contract.md").read_bytes()
    )
    (tmp_path / "data/caves/C-9001.yml").write_text(
        yaml.safe_dump(
            {
                "id": "C-9001",
                "name": "Otwór I",
                "system_name": None,
                "object_ids": ["KSW-9001"],
                "notes": "Notatka jaskini",
                "external_refs": [],
            }
        )
    )
    save_object(tmp_path, object_data())
    csv_source(tmp_path, [feature()])
    return tmp_path


def compare(repo, snap, state=None):
    return changes.compare(repo, snap, batch_id="test", base_commit="a" * 40, state=state)


def state_for(report, status, *, deferred=False):
    row = report["records"][0]
    resolution = {
        "globalid": row["globalid"],
        "revision_hash": row["revision_hash"],
        "snapshot_hash": report["snapshot_hash"],
        "status": status,
        "target": row["target"],
        "preimage": row["preimage"],
        "catalog_hash": report["catalog_hash"],
        "policy_hash": report["policy_hash"],
        "reviewed_by": "operator",
        "reviewed_at": "2026-10-19T00:01:00Z",
        "reason": "Decyzja testowa",
        "batch_id": report["batch_id"],
        "changes_hash": digest(report),
        "applied_locations": [],
        "absence": None,
        "result_hashes": row["preimage"],
        "result_catalog_hash": report["catalog_hash"],
    }
    return {
        "format": "tpn-source-state",
        "format_version": 1,
        "accepted_snapshot_hash": report["snapshot_hash"],
        "policy_hash": report["policy_hash"],
        "bindings": {GUID: "KSW-9001"},
        "resolutions": [resolution],
        "deferred": [
            {
                "globalid": GUID,
                "revision_hash": row["revision_hash"],
                "snapshot_hash": report["snapshot_hash"],
            }
        ]
        if deferred
        else [],
    }


def test_bootstrap_keeps_multiple_merged_guids_notes_best_and_history(repo):
    save_object(repo, object_data((GUID, GUID2)))
    old = [feature(), feature(GUID2, oid=2)]
    csv_source(repo, old)
    snap = snapshot(repo, "first", old)
    before = {str(p): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    report = compare(repo, snap)
    assert len(report["records"]) == 2
    for row in report["records"]:
        assert row["target"] == {"object_id": "KSW-9001", "cave_id": "C-9001"}
        assert row["history"]["baseline_matches"]
        assert row["history"]["current_matches"]
        assert row["proposed_actions"] == []
        assert row["best_before"] == row["best_after"]
        assert row["catalog_current"]["object"]["notes"] == "Ręczna notatka o scaleniu"
        assert row["bootstrap_binding"]["accepted"] is False
    assert report == compare(repo, snap)
    assert before == {str(p): p.read_bytes() for p in repo.rglob("*") if p.is_file()}


@pytest.mark.parametrize("wrong_ref", ["other", "source_row", "inventory_number", "url"])
def test_identity_does_not_fall_back_to_name_xy_or_untyped_reference(repo, wrong_ref):
    obj = object_data()
    obj["external_refs"][0]["ref_type"] = wrong_ref
    save_object(repo, obj)
    row = compare(repo, snapshot(repo, "first", [feature()]))["records"][0]
    assert row["target"] is None
    assert "unmapped_guid" in row["classification"]
    assert row["history"]["current_matches"] == []


def test_duplicate_typed_guid_is_conflict_not_first_match(repo):
    obj = object_data()
    obj["id"] = "KSW-9002"
    save_object(repo, obj)
    row = compare(repo, snapshot(repo, "first", [feature()]))["records"][0]
    assert row["target"] is None
    assert "local_conflict" in row["classification"]
    assert "ambiguous_typed_globalid" in row["conflicts"]


def test_source_and_local_changes_are_separate_and_before_after_is_readable(repo):
    new = feature(lon=19.81, name="Otwór nowa nazwa")
    new["attributes"]["UWAGI"] = "Nowa uwaga"
    obj = object_data()
    obj["name_local"] = "Moja nazwa"
    obj["measurements"][0]["lon"] = 19.79
    save_object(repo, obj)
    report = compare(repo, snapshot(repo, "first", [new]))
    row = report["records"][0]
    assert set(row["classification"]) == {"metadata_changed", "location_changed", "local_conflict"}
    assert row["distance_m"] > 700
    assert row["source_before"]["metadata"]["NAZWA"] == "Otwór I"
    assert row["source_after"]["metadata"]["NAZWA"] == "Otwór nowa nazwa"
    assert row["local_differences"]
    markdown = changes.render_markdown(report)
    for value in (
        "Otwór I",
        "Otwór nowa nazwa",
        "Moja nazwa",
        "Nowa uwaga",
        "WER_LOK",
        "UWAGI",
        "Ręczna notatka",
        "19.79",
    ):
        assert value in markdown


def test_foreign_measurement_and_ambiguous_history_cannot_confirm_bootstrap(repo):
    obj = object_data()
    obj["measurements"][0]["source"] = "PIG"
    save_object(repo, obj)
    row = compare(repo, snapshot(repo, "foreign", [feature()]))["records"][0]
    assert row["history"]["baseline_matches"] == []
    assert row["bootstrap_binding"] is None
    obj = object_data()
    obj["measurements"].append({**obj["measurements"][0], "id": "m-999"})
    save_object(repo, obj)
    row = compare(repo, repo / "data/sources/tpn/snapshots/foreign")["records"][0]
    assert "ambiguous_history" in row["conflicts"]
    assert row["bootstrap_binding"] is None


def test_source_missing_requires_complete_snapshot_and_does_not_delete(repo):
    snap = snapshot(repo, "empty", [])
    report = compare(repo, snap)
    assert report["records"][0]["classification"] == ["source_missing"]
    assert report["records"][0]["source_after"] is None
    assert report["records"][0]["location_hash"] is None
    assert report["requires_pr"] is True
    (snap / "page-0.json").chmod(0o644)
    (snap / "page-0.json").write_text("{}")
    with pytest.raises(ValueError):
        compare(repo, snap)


def test_two_cycles_reject_new_revision_and_stale_target(repo):
    first = snapshot(repo, "first", [feature(name="Inna nazwa")])
    initial = compare(repo, first)
    state = state_for(initial, "reject")
    second = snapshot(repo, "second", [feature(name="Inna nazwa")])
    report = compare(repo, second, state)
    assert report["baseline"]["snapshot_hash"] == initial["snapshot_hash"]
    assert report["records"][0]["review_status"] == "reject"
    assert report["requires_pr"] is False
    third = snapshot(repo, "third", [feature(name="Jeszcze inna")])
    assert compare(repo, third, state)["requires_pr"] is True
    obj = object_data()
    obj["notes"] += " zmiana operatora"
    save_object(repo, obj)
    stale = compare(repo, second, state)
    assert stale["requires_pr"] is True
    assert "stale_resolution" in stale["records"][0]["conflicts"]


def test_defer_survives_accepted_baseline_without_duplicate_pr_and_keeps_old_evidence(repo):
    first = snapshot(repo, "first", [feature(name="Do wyjaśnienia")])
    initial = compare(repo, first)
    state = state_for(initial, "defer", deferred=True)
    second = snapshot(repo, "second", [feature(name="Do wyjaśnienia")])
    report = compare(repo, second, state)
    assert report["records"][0]["review_status"] == "defer"
    assert report["requires_pr"] is False
    assert report["deferred"][0]["status"] == "active"
    third = snapshot(repo, "third", [feature(name="Nowa rewizja")])
    next_report = compare(repo, third, state)
    assert next_report["requires_pr"] is True
    assert next_report["deferred"][0]["status"] == "superseded"
    assert next_report["deferred"][0]["source"]["metadata"]["NAZWA"] == "Do wyjaśnienia"


def test_accepted_noop_technical_and_tiny_api_movement(repo):
    first = snapshot(repo, "first", [feature()])
    initial = compare(repo, first)
    state = state_for(initial, "approve")
    unchanged = compare(repo, first, state)
    assert unchanged["records"][0]["classification"] == ["unchanged"]
    assert unchanged["requires_pr"] is False
    new = feature()
    new["attributes"].update(FIELD=None, LAST_EDITED_DATE=10)
    technical = compare(repo, snapshot(repo, "technical", [new]), state)
    assert technical["records"][0]["classification"] == ["technical_only"]
    assert technical["requires_pr"] is False
    new["geometry"]["x"] += 0.000000001
    moved = compare(repo, snapshot(repo, "moved", [new]), state)
    assert "location_changed" in moved["records"][0]["classification"]
    assert moved["requires_pr"] is True


def test_return_to_old_location_recognizes_history_even_with_renumbered_id(repo):
    first = snapshot(repo, "first", [feature(lon=19.81)])
    state = state_for(compare(repo, first), "approve")
    obj = object_data()
    obj["measurements"][0]["id"] = "m-900"
    obj["best_measurement"]["measurement_id"] = "m-900"
    save_object(repo, obj)
    row = compare(repo, snapshot(repo, "returned", [feature()]), state)["records"][0]
    assert "location_changed" in row["classification"]
    assert row["history"]["current_matches"][0]["measurement_id"] == "m-900"
    assert row["measurement_needed"] is False


@pytest.mark.parametrize(
    "fault", ["version", "policy", "extra", "duplicate", "unknown_defer", "baseline_missing"]
)
def test_invalid_state_never_suppresses_changes(repo, fault):
    snap = snapshot(repo, "first", [feature()])
    state = state_for(compare(repo, snap), "reject")
    if fault == "version":
        state["format_version"] = 2
    elif fault == "policy":
        state["policy_hash"] = "0" * 64
    elif fault == "extra":
        state["accept_all"] = True
    elif fault == "duplicate":
        state["resolutions"] *= 2
    elif fault == "unknown_defer":
        state["deferred"] = [
            {
                "globalid": GUID,
                "revision_hash": "0" * 64,
                "snapshot_hash": state["accepted_snapshot_hash"],
            }
        ]
    else:
        state["accepted_snapshot_hash"] = "0" * 64
    with pytest.raises(ValueError):
        compare(repo, snap, state)


def test_applied_bootstrap_fingerprint_survives_api_conversion_difference(repo):
    new = feature(lon=19.80000001)
    snap = snapshot(repo, "first", [new])
    initial = compare(repo, snap)
    state = state_for(initial, "approve")
    state["resolutions"][0]["applied_locations"] = [
        {
            "location_hash": initial["records"][0]["location_hash"],
            "measurement_id": "m-001",
            "source_snapshot_hash": initial["snapshot_hash"],
            "csv_evidence": initial["baseline"],
        }
    ]
    report = compare(repo, snap, state)
    row = report["records"][0]
    assert row["history"]["current_matches"][0]["measurement_id"] == "m-001"
    assert row["history"]["current_matches"][0]["basis"] == "accepted_csv_bootstrap"
    assert report["requires_pr"] is False
    state["resolutions"][0]["applied_locations"][0]["location_hash"] = "0" * 64
    with pytest.raises(ValueError):
        compare(repo, snap, state)


def test_same_guid_without_matching_history_is_explicit_conflict(repo):
    obj = object_data()
    obj["measurements"][0]["source_ref"] = "TPN:row-1"
    save_object(repo, obj)
    row = compare(repo, snapshot(repo, "first", [feature()]))["records"][0]
    assert "missing_source_history" in row["conflicts"]
    assert row["review_status"] == "pending"


def test_deferred_revision_remains_when_absent_from_both_later_snapshots(repo):
    first = snapshot(repo, "first", [feature(name="Odroczone")])
    initial = compare(repo, first)
    state = state_for(initial, "defer", deferred=True)
    empty = snapshot(repo, "empty", [])
    state["accepted_snapshot_hash"] = json.loads((empty / "manifest.json").read_bytes())[
        "snapshot_hash"
    ]
    next_empty = snapshot(repo, "next-empty", [])
    report = compare(repo, next_empty, state)
    assert report["deferred"][0]["source"]["metadata"]["NAZWA"] == "Odroczone"
    assert "source_missing" in report["records"][0]["classification"]
    assert report["requires_pr"] is True


def test_bootstrap_tolerance_boundary_and_cross_guid_history(repo):
    from gps_kataster_obiektow_tatr.tpn_normalization import GEOD

    save_object(repo, object_data((GUID, GUID2)))
    for index, meters in enumerate((0.09, 0.11)):
        lon, lat, _ = GEOD.fwd(19.8, 49.2, 90, meters)
        new = feature()
        new["geometry"] = {"x": lon, "y": lat}
        row = compare(repo, snapshot(repo, f"threshold-{index}", [new]))["records"][0]
        assert ("location_changed" in row["classification"]) == (meters > 0.1)
        if meters < 0.1:
            assert {m["source_globalid"] for m in row["history"]["current_matches"]} == {
                GUID,
                GUID2,
            }


def test_catalog_relation_and_configuration_changes_invalidate_resolution(repo):
    snap = snapshot(repo, "first", [feature(name="Inna")])
    state = state_for(compare(repo, snap), "reject")
    (repo / "data/relations/R-0001.yml").write_text(
        yaml.safe_dump(
            {
                "id": "R-0001",
                "from_object_id": "KSW-9001",
                "to_object_id": "KSW-9001",
                "relation_type": "inne",
            }
        )
    )
    report = compare(repo, snap, state)
    assert "stale_resolution" in report["records"][0]["conflicts"]
    assert "data/relations/R-0001.yml" in report["records"][0]["preimage"]
    state = state_for(report, "reject")
    (repo / "config/prefixes.yml").write_text("changed: true\n")
    assert "stale_resolution" in compare(repo, snap, state)["records"][0]["conflicts"]


def test_cli_reads_state_only_from_main_and_writes_new_report_directory(repo):
    import subprocess

    from gps_kataster_obiektow_tatr.tpn_source_state import STATE_PATH

    snap = snapshot(repo, "first", [feature(name="Zmiana")])
    initial = compare(repo, snap)

    def git(*args):
        return (
            subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
            .stdout.decode()
            .strip()
        )

    git("init", "-b", "main")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.invalid")
    git("add", ".")
    git("commit", "-m", "base")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    state_path = repo / STATE_PATH
    state_path.parent.mkdir(parents=True)
    state_path.write_bytes(canonical(state_for(initial, "reject")))
    git("switch", "-c", "candidate")
    git("add", ".")
    git("commit", "-m", "candidate resolution")
    command = [
        str(REPO / ".venv/bin/python"),
        str(REPO / "scripts/compare_tpn_snapshot.py"),
        "--repo-root",
        str(repo),
        "--snapshot",
        str(snap),
        "--batch-id",
        "cli",
    ]

    def run(output):
        return subprocess.run(
            [*command, "--output-dir", str(output)], capture_output=True, text=True
        )

    output = repo / "build/first"
    result = run(output)
    assert result.returncode == 0, result.stderr
    assert json.loads((output / "changes.json").read_bytes())["requires_pr"] is True
    assert run(output).returncode == 1
    git("update-ref", "refs/remotes/origin/main", "HEAD")  # Simulated human merge accepted state.
    second = repo / "build/second"
    result = run(second)
    assert result.returncode == 0, result.stderr
    assert json.loads((second / "changes.json").read_bytes())["requires_pr"] is False
    assert run(repo / "data/objects/forbidden").returncode == 1
    assert not (repo / "data/objects/forbidden").exists()


def test_absence_decision_needs_real_baseline_and_defer_does_not_repeat_pr(repo):
    first = snapshot(repo, "first", [feature()])
    accepted = state_for(compare(repo, first), "approve")
    missing = snapshot(repo, "missing", [])
    report = compare(repo, missing, accepted)
    deferred = state_for(report, "defer", deferred=True)
    deferred["resolutions"][0]["absence"] = {
        "baseline": report["baseline"],
        "previous_revision_hash": report["records"][0]["source_before"]["revision_hash"],
    }
    second_empty = snapshot(repo, "still-missing", [])
    result = compare(repo, second_empty, deferred)
    assert result["records"][0]["review_status"] == "defer"
    assert result["requires_pr"] is False
    assert result["deferred"][0]["source"]["metadata"]["NAZWA"] == "Otwór I"
    deferred["resolutions"][0]["absence"]["previous_revision_hash"] = "0" * 64
    with pytest.raises(ValueError):
        compare(repo, second_empty, deferred)


def test_applied_api_fingerprint_prevents_duplicate_after_yaml_float_projection(repo):
    from decimal import Decimal

    original = feature(lon=Decimal("19.800000000000001"))
    first = snapshot(repo, "first", [original])
    initial = compare(repo, first)
    state = state_for(initial, "approve")
    state["resolutions"][0]["applied_locations"] = [
        {
            "location_hash": initial["records"][0]["location_hash"],
            "measurement_id": "m-001",
            "source_snapshot_hash": initial["snapshot_hash"],
            "csv_evidence": None,
        }
    ]
    elsewhere = snapshot(repo, "elsewhere", [feature(lon=19.81)])
    state["accepted_snapshot_hash"] = json.loads((elsewhere / "manifest.json").read_bytes())[
        "snapshot_hash"
    ]
    row = compare(repo, first, state)["records"][0]
    assert row["measurement_needed"] is False
    assert row["history"]["current_matches"][0]["basis"] == "accepted_api_location"
    # A changed YAML point must not be recognized solely through its old ID.
    obj = object_data()
    obj["measurements"][0]["lon"] = 19.7
    save_object(repo, obj)
    assert compare(repo, first, state)["records"][0]["measurement_needed"] is True


def test_opening_metadata_before_after_uses_opening_not_cave_name(repo):
    old, new = feature(), feature()
    old["attributes"]["OTWÓR"] = "I"
    new["attributes"]["OTWÓR"] = "II"
    csv_source(repo, [old])
    row = compare(repo, snapshot(repo, "first", [new]))["records"][0]
    change = next(x for x in row["local_differences"] if x["field"] == "object.name_local")
    assert change["source_field"] == "OTWÓR"
    assert change["source_before"] == "I"
    assert change["source_after"] == "II"


def absence_state(report, status, deferred=False):
    state = state_for(report, status, deferred=deferred)
    state["resolutions"][0]["absence"] = {
        "baseline": report["baseline"],
        "previous_revision_hash": report["records"][0]["source_before"]["revision_hash"],
    }
    return state


def test_rejected_absence_reopens_after_local_edit(repo):
    absent = snapshot(repo, "absent", [])
    state = absence_state(compare(repo, absent), "reject")
    later = snapshot(repo, "later", [])
    assert compare(repo, later, state)["requires_pr"] is False
    obj = object_data()
    obj["notes"] += " zmiana"
    save_object(repo, obj)
    report = compare(repo, later, state)
    assert report["requires_pr"] is True
    assert "stale_resolution" in report["records"][0]["conflicts"]


def test_two_absence_events_retain_correct_old_deferred_evidence(repo):
    absent = snapshot(repo, "absent", [])
    state = absence_state(compare(repo, absent), "defer", deferred=True)
    reappeared = snapshot(repo, "reappeared", [feature(name="B")])
    state["accepted_snapshot_hash"] = json.loads((reappeared / "manifest.json").read_bytes())[
        "snapshot_hash"
    ]
    absent_again = snapshot(repo, "absent-again", [])
    newer = absence_state(compare(repo, absent_again, state), "reject")
    state["resolutions"].extend(newer["resolutions"])
    state["accepted_snapshot_hash"] = newer["accepted_snapshot_hash"]
    latest = snapshot(repo, "latest", [])
    report = compare(repo, latest, state)
    assert report["deferred"][0]["source"]["metadata"]["NAZWA"] == "Otwór I"
    assert report["records"][0]["source_before"]["metadata"]["NAZWA"] == "B"


def test_committed_snapshot_and_merged_objects_work_without_build_inputs():
    from gps_kataster_obiektow_tatr.tpn_snapshot import sha256, verify_snapshot

    snap = REPO / "data/sources/tpn/snapshots/pbi-096-live-20261019"
    manifest = verify_snapshot(snap)
    protected = {
        str(p): sha256(p.read_bytes())
        for folder in ("data", "config")
        for p in (REPO / folder).rglob("*")
        if p.is_file()
    }
    report = compare(REPO, snap)
    assert (
        sum(r["source_after"] is not None for r in report["records"])
        == manifest["checks"]["feature_count"]
    )
    merged = [
        r for r in report["records"] if r["target"] and r["target"]["object_id"] == "MLZ-0087"
    ]
    assert len(merged) == 2
    assert {r["bootstrap_binding"]["measurement_id"] for r in merged} == {"m-001", "m-002"}
    assert all(not r["proposed_actions"] and not r["candidates"] for r in report["records"])
    assert protected == {
        str(p): sha256(p.read_bytes())
        for folder in ("data", "config")
        for p in (REPO / folder).rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("status", ["reject", "defer"])
def test_return_after_accepted_absence_requires_review_even_if_content_is_identical(repo, status):
    gone = snapshot(repo, "gone", [])
    state = absence_state(compare(repo, gone), status, deferred=status == "defer")
    returned = snapshot(repo, "returned", [feature()])
    report = compare(repo, returned, state)
    row = report["records"][0]
    assert row["source_before"] is None
    assert "new_guid" in row["classification"]
    assert row["review_status"] == "pending"
    assert report["requires_pr"] is True


def test_optional_best_protection_covers_unmapped_history_without_changing_best(repo):
    obj = object_data()
    obj["best_measurement"] = {"mode": "auto", "measurement_id": "m-001", "reason": None}
    obj["measurements"].append(
        {
            "id": "m-099",
            "lat": 49.1,
            "lon": 19.1,
            "source": "inne",
            "method": "gnss",
            "verification_status": "odrzucony",
            "horizontal_accuracy_m": None,
        }
    )
    save_object(repo, obj)
    # Object with no typed GUID must also be audited: KSZ-0112 has no TPN mapping.
    other = object_data(guids=())
    other["id"] = "KSW-9002"
    other["cave_id"] = None
    other["measurements"] = [
        {"id": "m-001", "source": "inne", "method": "gnss", "lat": 49.2, "lon": 19.8}
    ]
    other["best_measurement"] = {"mode": "auto", "measurement_id": "m-001", "reason": None}
    save_object(repo, other)
    snap = snapshot(repo, "guard", [feature(lon=19.9)])
    plain = compare(repo, snap)
    report = changes.compare(
        repo, snap, batch_id="test", base_commit="a" * 40, state=None, protect_best=True
    )
    assert report["records"] == plain["records"]
    assert {p["object_id"] for p in report["best_protection"]["migration_proposals"]} == {
        "KSW-9001",
        "KSW-9002",
    }
    protected = report["best_protection"]["objects"][0]
    assert any(e["measurement_id"] == "m-099" for e in protected["protection"]["evidence"])
    row = report["records"][0]
    assert row["best_before"] == row["best_after"] == obj["best_measurement"]
    markdown = changes.render_markdown(report)
    assert "Ochrona best" in markdown
    assert "KSW-9002" in markdown and "m-001" in markdown
