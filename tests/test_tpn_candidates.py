"""Conservative new-record qualification, without catalog writes."""

from decimal import Decimal

import pytest
from test_tpn_batch import batch_repo as batch_repo

from gps_kataster_obiektow_tatr.tpn_candidates import (
    CandidatePolicy,
    name_similarity,
    normalize_name,
    pair_evidence,
    qualify,
)


def side(key="source:a", name="Otwór Próbny I", *, lon=19.8, accuracy=None):
    return {
        "key": key,
        "target": {"globalid": key.removeprefix("source:")},
        "names": [{"field": "NAZWA", "value": name}],
        "inventories": [],
        "systems": [],
        "positions": [{"lat": 49.2, "lon": lon, "horizontal_accuracy_m": accuracy}],
        "revision_hash": "a" * 64,
        "preimage": {},
    }


def test_normalization_retains_opening_markers():
    assert normalize_name("  GÓRNY\t Otwór  II ") == "górny otwór ii"
    assert normalize_name("Nyz\u0307a") == normalize_name("Nyża")
    for a, b in [("I", "II"), ("II", "III"), ("górny", "dolny"), ("1", "2")]:
        assert normalize_name("Otwór " + a) != normalize_name("Otwór " + b)


def test_similarity_and_threshold_boundary():
    assert name_similarity("abcdefghij", "abcdefghiX") == Decimal("0.9")
    a, b = side(name="abcdefghij"), side("source:b", "abcdefghiX", lon=20.2)
    assert pair_evidence(a, b, CandidatePolicy())[0]["code"] == "similar_name"
    assert not pair_evidence(a, b, CandidatePolicy(name_similarity_threshold=Decimal("0.90001")))
    assert name_similarity("", "") == 0


@pytest.mark.parametrize("radius", [99, 0, float("nan"), float("inf"), True])
def test_unsafe_radius_rejected(radius):
    with pytest.raises(ValueError):
        CandidatePolicy(radius_m=radius)


@pytest.mark.parametrize("threshold", [0, -1, 1.01, float("nan"), True])
def test_unsafe_threshold_rejected(threshold):
    with pytest.raises(ValueError):
        CandidatePolicy(name_similarity_threshold=threshold)


def test_distance_boundary_and_accuracy(monkeypatch):
    import gps_kataster_obiektow_tatr.tpn_candidates as candidates

    a, b = side(name="X"), side("source:b", "Y", lon=20.2)
    monkeypatch.setattr(candidates, "distance", lambda *args: 100)
    assert pair_evidence(a, b, CandidatePolicy())[0]["code"] == "nearby_position"
    monkeypatch.setattr(candidates, "distance", lambda *args: 100.00001)
    assert not pair_evidence(a, b, CandidatePolicy())
    b["positions"][0]["horizontal_accuracy_m"] = 200
    evidence = pair_evidence(a, b, CandidatePolicy())[0]
    assert evidence["radius_m"] == 200
    assert evidence["left_position"]["horizontal_accuracy_m"] is None
    monkeypatch.setattr(candidates, "distance", lambda *args: 200)
    assert pair_evidence(a, b, CandidatePolicy())
    monkeypatch.setattr(candidates, "distance", lambda *args: 200.00001)
    assert not pair_evidence(a, b, CandidatePolicy())


def test_distance_display_precision_does_not_expand_candidate_radius(monkeypatch):
    import gps_kataster_obiektow_tatr.tpn_candidates as candidates

    a, b = side(name="X"), side("source:b", "Y", lon=20.2)
    monkeypatch.setattr(candidates, "distance", lambda *args: 99.99999)
    assert pair_evidence(a, b, CandidatePolicy())[0]["distance_m"] == 100
    monkeypatch.setattr(candidates, "distance", lambda *args: 100.00001)
    assert not pair_evidence(a, b, CandidatePolicy())


def test_each_independent_signal_has_evidence():
    a, b = side(), side("source:b", lon=20.2)
    for field, code in [("inventories", "shared_inventory"), ("systems", "shared_system")]:
        a[field] = [{"field": "test", "value": " T.A-01 "}]
        b[field] = [{"field": "test", "value": "t.a-01"}]
        assert code in {e["code"] for e in pair_evidence(a, b, CandidatePolicy())}
    assert "exact_name" in {e["code"] for e in pair_evidence(a, b, CandidatePolicy())}
    a["names"], b["names"] = [], []
    a["inventories"], b["inventories"] = [], []
    a["systems"], b["systems"] = [], []
    assert not pair_evidence(a, b, CandidatePolicy())


def test_qualification_positive_and_each_missing_condition():
    checks = dict(
        new_unique_guid=True,
        geometry=True,
        category=True,
        region=True,
        measurement=True,
        name=True,
        standalone=True,
        comparison_complete=True,
        source_review_clear=True,
    )
    assert qualify(checks, []) == "automatic_proposal"
    for key in checks:
        incomplete = {**checks, key: False}
        assert qualify(incomplete, []) == "review", key
    assert qualify(checks, [{"key": "collision"}]) == "review"
    assert qualify({}, []) == "review"


@pytest.mark.parametrize(
    "case",
    __import__("json").loads(
        (
            __import__("pathlib").Path(__file__).parent / "fixtures/tpn_api/candidate_cases.json"
        ).read_text()
    ),
    ids=lambda case: case["case"],
)
def test_required_candidate_fixtures(case):
    for i, name in enumerate(case["names"]):
        for j in range(i + 1, len(case["names"])):
            a = side("source:a", name, lon=case["longitudes"][i])
            b = side("source:b", case["names"][j], lon=case["longitudes"][j])
            if case["case"] == "unselected_rejected_history_only":
                b["positions"][0].update(id="m-002", is_best=False, verification_status="odrzucony")
                b["positions"].insert(0, {"id": "m-001", "lat": 49.3, "lon": 20.2, "is_best": True})
            evidence = pair_evidence(a, b, CandidatePolicy())
            assert case["expected"] in {e["code"] for e in evidence}
            if case["case"] == "unselected_rejected_history_only":
                assert evidence[0]["right_position"]["id"] == "m-002"


def test_remembered_resolution_and_each_changed_basis():
    from gps_kataster_obiektow_tatr.tpn_candidates import resolution_status
    from gps_kataster_obiektow_tatr.tpn_duplicate_state import validate_resolutions
    from gps_kataster_obiektow_tatr.tpn_normalization import digest

    a, b, policy = side(), side("source:b"), CandidatePolicy()
    basis = {
        "sides": [a, b],
        "policy": policy.document(),
        "catalog_hash": "a" * 64,
        "source_set_hash": digest([]),
    }
    for outcome in (
        "same_opening",
        "different_openings_same_cave",
        "different_objects",
        "unresolved",
    ):
        memory = dict(
            pair=[a["key"], b["key"]],
            outcome=outcome,
            basis=basis,
            basis_hash=digest(basis),
            evidence="Plan z oznaczeniami",
            reviewed_by="operator",
            reviewed_at="2026-10-19T00:00:00Z",
        )
        validate_resolutions([memory])
        assert resolution_status(a, b, policy, "a" * 64, [memory])["status"] == "valid"
        for field, new in [
            ("names", [{"field": "NAZWA", "value": "Inny otwór"}]),
            ("inventories", [{"field": "NR_INWENT", "value": "T.A-02"}]),
            ("systems", [{"field": "SYSTEM", "value": "Inny system"}]),
            ("target", {"object_id": "KSW-9999"}),
            ("positions", [{"lat": 49.2, "lon": 20.2}]),
            ("preimage", {"data/objects/KSW/KSW-9001.yml": "b" * 64}),
            ("revision_hash", "b" * 64),
        ]:
            changed = {**a, field: new}
            result = resolution_status(changed, b, policy, "a" * 64, [memory])
            assert result["status"] == "stale", field
            assert result["outcome"] == "unresolved"
        assert resolution_status(a, b, policy, "b" * 64, [memory])["status"] == "stale"
        assert (
            resolution_status(a, b, CandidatePolicy(radius_m=200), "a" * 64, [memory])["status"]
            == "stale"
        )
        bad = {**memory, "basis_hash": "b" * 64}
        with pytest.raises(ValueError, match="basis hash"):
            validate_resolutions([bad])


def test_catalog_local_cave_names_refs_and_all_measurements():
    from types import SimpleNamespace

    from gps_kataster_obiektow_tatr.tpn_candidates import catalog_sides

    obj = {
        "id": "KSW-9001",
        "cave_id": "C-9001",
        "name_local": "Nazwa lokalna",
        "external_refs": [],
        "measurements": [
            {"id": "m-001", "lat": 49.2, "lon": 19.8},
            {"id": "m-002", "lat": 49.3, "lon": 20.1, "verification_status": "odrzucony"},
        ],
        "best_measurement": {"measurement_id": "m-001"},
    }
    cave = {
        "id": "C-9001",
        "name": "Jaskinia Próba",
        "system_name": "System Próba",
        "external_refs": [
            {"system": "NR_INWENT", "ref_type": "inventory_number", "external_id": "T.A-01"}
        ],
    }
    catalog = SimpleNamespace(
        records={obj["id"]: obj, cave["id"]: cave},
        objects={obj["id"]: obj},
        caves={cave["id"]: cave},
        paths={obj["id"]: "object.yml", cave["id"]: "cave.yml"},
        hashes={"object.yml": "a" * 64, "cave.yml": "b" * 64},
    )
    sides = catalog_sides(catalog)
    candidate = next(s for s in sides if s["key"].startswith("object:"))
    assert len(candidate["positions"]) == 2
    assert candidate["positions"][1]["is_best"] is False
    assert candidate["positions"][1]["verification_status"] == "odrzucony"
    assert {n["value"] for n in candidate["names"]} == {"Nazwa lokalna", "Jaskinia Próba"}
    assert candidate["inventories"][0]["value"] == "T.A-01"
    assert candidate["systems"][0]["value"] == "System Próba"


@pytest.fixture
def tiny_repo(tmp_path):
    import shutil
    from pathlib import Path

    import yaml
    from test_tpn_changes import csv_source, feature, object_data, save_object

    original = Path(__file__).resolve().parents[1]
    for folder in (
        "data/objects",
        "data/caves",
        "data/relations",
        "docs/asdlc",
        "data/sources/pig",
    ):
        (tmp_path / folder).mkdir(parents=True)
    shutil.copytree(original / "config", tmp_path / "config")
    shutil.copytree(original / "data/shapes", tmp_path / "data/shapes")
    shutil.copy(
        original / "docs/asdlc/tpn_sync_contract.md", tmp_path / "docs/asdlc/tpn_sync_contract.md"
    )
    obj = object_data()
    obj["name_local"] = "Wyjątkowa Nazwa Dawnego Punktu"
    obj["measurements"][0]["lon"] = 19.7
    save_object(tmp_path, obj)
    (tmp_path / "data/caves/C-9001.yml").write_text(
        yaml.safe_dump(
            {
                "id": "C-9001",
                "name": "Stara Pozycja Katalogowa",
                "external_refs": [],
                "object_ids": [obj["id"]],
            }
        )
    )
    csv_source(tmp_path, [feature()])
    (tmp_path / "data/sources/pig/pig_otwory_jaskin_.xlsx.-.Export.csv").write_text(
        "ID,Nazwa,Inne nazwy,Nr inw.\n"
    )
    return tmp_path


def clean_feature(
    guid="44444444-4444-4444-8444-444444444444", name="Niezależny Unikatowy Punkt", oid=2
):
    from test_tpn_changes import feature

    f = feature(guid, lon=19.86, name=name, oid=oid)
    f["geometry"]["y"] = 49.24
    f["attributes"].update(GENEZA="jaskinia", WER_LOK=None, UWAGI=None, OPIS=None, TATER=None)
    return f


def compare_tiny(root, features, label="one", **kwargs):
    from test_tpn_changes import snapshot

    from gps_kataster_obiektow_tatr.tpn_changes import compare

    return compare(
        root,
        snapshot(root, label, features),
        batch_id="fixture",
        base_commit="a" * 40,
        candidate_policy=CandidatePolicy(),
        **kwargs,
    )


def test_full_gate_positive_and_no_catalog_write(tiny_repo):
    before = {str(p): p.read_bytes() for p in tiny_repo.glob("data/**/*.yml")}
    report = compare_tiny(tiny_repo, [clean_feature()])
    row = active_row(report)
    assert row["new_record_qualification"]["status"] == "automatic_proposal"
    assert row["new_record_qualification"]["regions"]["valleys"]
    assert row["target"] is None and row["proposed_actions"] == []
    assert row["new_record_qualification"]["proposed_actions"] == []
    assert before == {str(p): p.read_bytes() for p in tiny_repo.glob("data/**/*.yml")}


@pytest.mark.parametrize(
    "change,condition",
    [
        ({"NAZWA": None}, "name"),
        ({"LAST_EDITED_DATE": None}, "measurement"),
        ({"GENEZA": None}, "category"),
        ({"GENEZA": "jaskinia/sztolnia"}, "category"),
        ({"SYSTEM": "Nieznany system"}, "standalone"),
        ({"OTWÓR": "górny"}, "standalone"),
        ({"WER_LOK": "Pozycja przybliżona"}, "source_review_clear"),
        ({"UWAGI": "Sprawdzić"}, "source_review_clear"),
        ({"TATER": "1"}, "source_review_clear"),
    ],
)
def test_full_gate_missing_or_uncertain_data(tiny_repo, change, condition):
    f = clean_feature()
    f["attributes"].update(change)
    report = compare_tiny(tiny_repo, [f])
    row = active_row(report)
    assert row["new_record_qualification"]["status"] == "review"
    assert row["new_record_qualification"]["checks"][condition] is False
    assert any(
        b.get("condition") == condition and b["evidence"]
        for b in row["new_record_qualification"]["blocks"]
    )


def test_batch_is_symmetric_and_order_independent(tiny_repo, monkeypatch):
    a = clean_feature(name="Okno w Ciemniaku")
    b = clean_feature("55555555-5555-4555-8555-555555555555", "Okno w Ciemniaku", 3)
    b["geometry"]["x"] = 19.9
    report = compare_tiny(tiny_repo, [a, b])
    rows = [r for r in report["records"] if r["source_after"]]
    for r in rows:
        assert r["new_record_qualification"]["status"] == "review"
        peer = next(c for c in r["candidates"] if c["target"].get("globalid") != r["globalid"])
        assert any(e["code"] == "exact_name" for e in peer["evidence"])
    from gps_kataster_obiektow_tatr import tpn_changes

    read = tpn_changes.read_snapshot

    def reversed_read(*args):
        manifest, current = read(*args)
        return manifest, dict(reversed(list(current.items())))

    monkeypatch.setattr(tpn_changes, "read_snapshot", reversed_read)
    other = tpn_changes.compare(
        tiny_repo,
        tiny_repo / "data/sources/tpn/snapshots/one",
        batch_id="fixture",
        base_commit="a" * 40,
        candidate_policy=CandidatePolicy(),
    )
    assert rows == [r for r in other["records"] if r["source_after"]]


def test_unmapped_historical_guid_is_not_automatic_new_object(tiny_repo):
    from test_tpn_changes import feature

    f = feature()
    f["attributes"].update(GENEZA="jaskinia", WER_LOK=None)
    # Remove typed mapping, preserve historical source identity.
    import yaml

    path = tiny_repo / "data/objects/KSW/KSW-9001.yml"
    obj = yaml.safe_load(path.read_text())
    obj["external_refs"] = []
    path.write_text(yaml.safe_dump(obj))
    r = next(r for r in compare_tiny(tiny_repo, [f])["records"] if r["source_after"])
    assert r["new_record_qualification"]["checks"]["new_unique_guid"] is False
    assert r["new_record_qualification"]["status"] == "review"


def test_missing_source_names_block_auto(tiny_repo):
    path = tiny_repo / "data/sources/pig/pig_otwory_jaskin_.xlsx.-.Export.csv"
    path.unlink()
    report = compare_tiny(tiny_repo, [clean_feature()])
    assert active_row(report)["new_record_qualification"]["checks"]["comparison_complete"] is False


def test_source_names_inventory_and_system_conflicts(tiny_repo):
    import yaml

    path = tiny_repo / "data/caves/C-9001.yml"
    cave = yaml.safe_load(path.read_text())
    cave.update(
        system_name="System Unikalny",
        external_refs=[
            {"system": "NR_INWENT", "ref_type": "inventory_number", "external_id": "T.A-77"}
        ],
    )
    path.write_text(yaml.safe_dump(cave))
    (tiny_repo / "data/sources/pig/pig_otwory_jaskin_.xlsx.-.Export.csv").write_text(
        "ID,Nazwa,Inne nazwy,Nr inw.\n123,Dawna Nazwa,Inna Nazwa Źródłowa,T.A-55\n"
    )
    f = clean_feature(name="Inna Nazwa Źródłowa")
    f["attributes"].update(NR_INWENT="T.A-77", SYSTEM="System Unikalny")
    r = active_row(compare_tiny(tiny_repo, [f]))
    codes = {e["code"] for c in r["candidates"] for e in c["evidence"]}
    assert {"exact_name", "shared_inventory", "shared_system"} <= codes
    assert any(c["key"].startswith("pig:") for c in r["candidates"])


def test_region_fallback_outside_country_and_overlap(tiny_repo, monkeypatch):
    from gps_kataster_obiektow_tatr.prefix_resolver import PrefixResolver

    for i, regions in enumerate(
        [
            {"inside_pl_sk": True, "valleys": []},
            {"inside_pl_sk": False, "valleys": []},
            {"inside_pl_sk": True, "valleys": [{"prefix": "KSW"}, {"prefix": "MTW"}]},
        ]
    ):
        monkeypatch.setattr(
            PrefixResolver, "qualification_regions", lambda *a, _r=regions, **kw: _r
        )
        report = compare_tiny(tiny_repo, [clean_feature()], f"region-{i}")
        assert active_row(report)["new_record_qualification"]["status"] == "review"


def active_row(report):
    return next(r for r in report["records"] if "new_record_qualification" in r)


def test_stale_resolution_when_name_collision_disappears(tiny_repo):
    import yaml

    from gps_kataster_obiektow_tatr.tpn_normalization import digest

    f = clean_feature(name="Wyjątkowa Nazwa Dawnego Punktu")
    report = compare_tiny(tiny_repo, [f])
    candidate = next(c for c in active_row(report)["candidates"] if c["key"] == "object:KSW-9001")
    basis = candidate["resolution"]["current_basis"]
    memory = {
        "pair": [s["key"] for s in basis["sides"]],
        "basis": basis,
        "basis_hash": digest(basis),
        "outcome": "different_objects",
        "evidence": "Sprawdzony plan otworów",
        "reviewed_by": "operator",
        "reviewed_at": "2026-10-19T00:00:00Z",
    }
    unchanged = compare_tiny(tiny_repo, [f], "two", duplicate_resolutions=[memory])
    assert unchanged["duplicate_resolution_checks"][0]["status"] == "valid"
    assert active_row(unchanged)["new_record_qualification"]["status"] == "review"
    path = tiny_repo / "data/objects/KSW/KSW-9001.yml"
    obj = yaml.safe_load(path.read_text())
    obj["name_local"] = "Całkiem Zmieniony Dawny Punkt"
    path.write_text(yaml.safe_dump(obj))
    updated = compare_tiny(tiny_repo, [f], "three", duplicate_resolutions=[memory])
    assert updated["duplicate_resolution_checks"][0]["status"] == "stale"
    row = active_row(updated)
    assert row["candidates"] == []
    assert row["new_record_qualification"]["status"] == "review"
    assert row["new_record_qualification"]["checks"]["source_review_clear"] is False


def test_historical_unselected_measurement_is_the_only_collision(tiny_repo):
    import yaml

    f = clean_feature()
    path = tiny_repo / "data/objects/KSW/KSW-9001.yml"
    obj = yaml.safe_load(path.read_text())
    obj["measurements"].append(
        {
            "id": "m-002",
            "lat": f["geometry"]["y"],
            "lon": f["geometry"]["x"],
            "source": "inne",
            "verification_status": "odrzucony",
        }
    )
    path.write_text(yaml.safe_dump(obj))
    row = active_row(compare_tiny(tiny_repo, [f]))
    assert len(row["candidates"]) == 1
    evidence = row["candidates"][0]["evidence"]
    assert len(evidence) == 1 and evidence[0]["code"] == "nearby_position"
    assert evidence[0]["right_position"]["id"] == "m-002"
    assert evidence[0]["right_position"]["is_best"] is False


def test_missing_typed_ref_with_same_guid_history_is_still_blocked(tiny_repo):
    import yaml

    f = clean_feature()
    path = tiny_repo / "data/objects/KSW/KSW-9001.yml"
    obj = yaml.safe_load(path.read_text())
    obj["external_refs"] = []
    obj["measurements"][0]["source_ref"] = "TPN:" + f["attributes"]["GLOBALID"]
    path.write_text(yaml.safe_dump(obj))
    row = active_row(compare_tiny(tiny_repo, [f]))
    assert row["new_record_qualification"]["status"] == "review"
    assert any(e["code"] == "shared_source_guid" for c in row["candidates"] for e in c["evidence"])


def test_cli_accepted_duplicate_state_only_from_main(tiny_repo):
    import json
    import subprocess
    import sys
    from pathlib import Path

    from gps_kataster_obiektow_tatr.tpn_duplicate_state import read_accepted_duplicates
    from gps_kataster_obiektow_tatr.tpn_normalization import digest

    report = compare_tiny(tiny_repo, [clean_feature(name="Wyjątkowa Nazwa Dawnego Punktu")])
    basis = active_row(report)["candidates"][0]["resolution"]["current_basis"]
    memory = {
        "pair": [s["key"] for s in basis["sides"]],
        "basis": basis,
        "basis_hash": digest(basis),
        "outcome": "same_opening",
        "evidence": "Plan",
        "reviewed_by": "operator",
        "reviewed_at": "2026-10-19T00:00:00Z",
    }

    def git(*args):
        return subprocess.check_output(["git", "-C", str(tiny_repo), *args]).decode().strip()

    git("init", "-q")
    git("add", ".")
    git(
        "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "baseline"
    )
    baseline = git("rev-parse", "HEAD")
    git("update-ref", "refs/remotes/origin/main", baseline)
    path = tiny_repo / "data/source_state/tpn/duplicates.json"
    path.parent.mkdir(parents=True)
    from gps_kataster_obiektow_tatr.tpn_normalization import canonical

    path.write_bytes(
        canonical({"format": "tpn-duplicate-state", "format_version": 1, "resolutions": [memory]})
    )
    assert read_accepted_duplicates(tiny_repo, baseline) == []
    git("add", ".")
    git(
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        "candidate state",
    )
    assert read_accepted_duplicates(tiny_repo, baseline) == []
    accepted = git("rev-parse", "HEAD")
    git("update-ref", "refs/remotes/origin/main", accepted)
    assert read_accepted_duplicates(tiny_repo, accepted)[0]["outcome"] == "same_opening"
    path.write_text("INVALID branch input")
    snapshot_path = tiny_repo / "data/sources/tpn/snapshots/one"
    command = [
        sys.executable,
        str(Path(__file__).resolve().parents[1] / "scripts/compare_tpn_snapshot.py"),
        "--repo-root",
        str(tiny_repo),
        "--snapshot",
        str(snapshot_path),
        "--batch-id",
        "cli",
        "--qualify-new",
        "--output-dir",
        str(tiny_repo / "build/report"),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    output = json.loads((tiny_repo / "build/report/changes.json").read_text())
    assert output["accepted_state_commit"] == accepted
    assert output["duplicate_resolution_checks"][0]["status"] == "valid"
    assert "Kandydaci i blokady" in (tiny_repo / "build/report/report.md").read_text()
    assert path.read_text() == "INVALID branch input"
    repeat = subprocess.run(command, capture_output=True, text=True)
    assert repeat.returncode == 1 and "already exists" in repeat.stderr


def test_pig_comma_alias_is_a_source_name_signal(tiny_repo):
    path = tiny_repo / "data/sources/pig/pig_otwory_jaskin_.xlsx.-.Export.csv"
    path.write_text('ID,Nazwa,Inne nazwy,Nr inw.\n123,Dawna,"Pierwsza, Druga II; Trzecia",\n')
    row = active_row(compare_tiny(tiny_repo, [clean_feature(name="Druga II")]))
    candidate = next(c for c in row["candidates"] if c["key"].startswith("pig:"))
    evidence = next(e for e in candidate["evidence"] if e["code"] == "exact_name")
    assert evidence["right"]["raw_field"] == "Pierwsza, Druga II; Trzecia"


def test_new_third_source_invalidates_remembered_pair(tiny_repo):
    from gps_kataster_obiektow_tatr.tpn_normalization import digest

    f = clean_feature(name="Wyjątkowa Nazwa Dawnego Punktu")
    report = compare_tiny(tiny_repo, [f])
    basis = active_row(report)["candidates"][0]["resolution"]["current_basis"]
    memory = {
        "pair": [s["key"] for s in basis["sides"]],
        "basis": basis,
        "basis_hash": digest(basis),
        "outcome": "different_objects",
        "evidence": "Plan",
        "reviewed_by": "operator",
        "reviewed_at": "2026-10-19T00:00:00Z",
    }
    third = clean_feature("55555555-5555-4555-8555-555555555555", f["attributes"]["NAZWA"], 3)
    result = compare_tiny(tiny_repo, [f, third], "two", duplicate_resolutions=[memory])
    assert result["duplicate_resolution_checks"][0]["status"] == "stale"
    assert result["requires_pr"] is True


def test_historical_csv_names_remain_after_accepted_snapshot(tiny_repo):
    from test_tpn_changes import feature

    old = feature(name="Całkowicie Inna Nazwa Źródła")
    first = compare_tiny(tiny_repo, [old])
    state = {
        "format": "tpn-source-state",
        "format_version": 1,
        "accepted_snapshot_hash": first["snapshot_hash"],
        "policy_hash": first["policy_hash"],
        "bindings": {},
        "resolutions": [],
        "deferred": [],
    }
    report = compare_tiny(tiny_repo, [old, clean_feature(name="Otwór I")], "two", state=state)
    row = active_row(report)
    assert row["new_record_qualification"]["status"] == "review"
    assert any(
        c["target"].get("globalid") == old["attributes"]["GLOBALID"]
        and any(e["code"] == "exact_name" for e in c["evidence"])
        for c in row["candidates"]
    )


def test_category_contradiction_in_name_requires_review(tiny_repo):
    row = active_row(compare_tiny(tiny_repo, [clean_feature(name="Sztolnia w Testowym Miejscu")]))
    assert row["new_record_qualification"]["checks"]["category"] is False
    assert row["new_record_qualification"]["status"] == "review"


def test_returning_historical_guid_is_not_new(tiny_repo):
    import yaml
    from test_tpn_changes import GUID, feature

    objpath = tiny_repo / "data/objects/KSW/KSW-9001.yml"
    obj = yaml.safe_load(objpath.read_text())
    obj["external_refs"] = []
    obj["measurements"][0]["source"] = "inne"
    objpath.write_text(yaml.safe_dump(obj))
    accepted = feature("77777777-7777-4777-8777-777777777777", name="Stan Pośredni", lon=20.1)
    first = compare_tiny(tiny_repo, [accepted])
    state = {
        "format": "tpn-source-state",
        "format_version": 1,
        "accepted_snapshot_hash": first["snapshot_hash"],
        "policy_hash": first["policy_hash"],
        "bindings": {},
        "resolutions": [],
        "deferred": [],
    }
    f = clean_feature(guid=GUID)
    report = compare_tiny(tiny_repo, [accepted, f], "two", state=state)
    row = next(r for r in report["records"] if r["globalid"] == GUID)
    assert row["new_record_qualification"]["checks"]["new_unique_guid"] is False
    assert row["new_record_qualification"]["status"] == "review"
    assert any(
        b.get("condition") == "new_unique_guid" and b["evidence"]["historical_guid"]
        for b in row["new_record_qualification"]["blocks"]
    )


@pytest.mark.parametrize("bad_basis", [None, [], "invalid"])
def test_malformed_duplicate_basis_has_controlled_error(bad_basis):
    from gps_kataster_obiektow_tatr.tpn_duplicate_state import validate_resolutions

    with pytest.raises(ValueError):
        validate_resolutions(
            [
                {
                    "pair": ["a", "b"],
                    "outcome": "unresolved",
                    "basis": bad_basis,
                    "basis_hash": "a" * 64,
                    "evidence": "Plan",
                    "reviewed_by": "operator",
                    "reviewed_at": "2026-10-19T00:00:00Z",
                }
            ]
        )


def test_missing_existing_measurement_blocks_comparison_completeness(tiny_repo):
    import yaml

    path = tiny_repo / "data/objects/KSW/KSW-9001.yml"
    obj = yaml.safe_load(path.read_text())
    obj["measurements"] = []
    path.write_text(yaml.safe_dump(obj))
    row = active_row(compare_tiny(tiny_repo, [clean_feature()]))
    assert row["new_record_qualification"]["checks"]["comparison_complete"] is False
    assert row["new_record_qualification"]["status"] == "review"


@pytest.mark.parametrize("candidate_kind", ["object", "source"])
def test_accepted_duplicate_decision_survives_identical_next_batch(batch_repo, candidate_kind):
    import yaml
    from test_tpn_batch import git
    from test_tpn_changes import GUID, feature, snapshot

    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch, check_batch, prepare_batch
    from gps_kataster_obiektow_tatr.tpn_changes import compare
    from gps_kataster_obiektow_tatr.tpn_duplicate_state import read_accepted_duplicates
    from gps_kataster_obiektow_tatr.tpn_normalization import canonical, digest
    from gps_kataster_obiektow_tatr.tpn_source_state import read_accepted_state

    root, initial_snapshot = batch_repo

    def accept(message):
        git(root, "add", ".")
        git(root, "commit", "-qm", message)
        git(root, "update-ref", "refs/remotes/origin/main", "HEAD")

    def report_for(snap, label, *, qualify=False):
        state, accepted = read_accepted_state(root)
        report = compare(
            root,
            snap,
            batch_id=label,
            base_commit=git(root, "rev-parse", "HEAD"),
            state=state,
            candidate_policy=CandidatePolicy() if qualify else None,
            duplicate_resolutions=read_accepted_duplicates(root, accepted) if qualify else None,
        )
        report["accepted_state_commit"] = accepted
        return report

    def reject_and_check(report):
        changes, decisions = prepare_batch(root, report)
        for decision in decisions["decisions"]:
            decision.update(
                status="reject",
                reviewed_by="human",
                reviewed_at="2026-10-21T00:01:00Z",
                reason="Fixture explicit rejection",
            )
        apply_batch(root, changes, decisions, reviewers={"human"})
        check_batch(root, report["batch_id"])

    reject_and_check(report_for(initial_snapshot, "base-batch"))
    accept("fixture: accept first batch")
    pig = root / "data/sources/pig/pig_otwory_jaskin_.xlsx.-.Export.csv"
    pig.parent.mkdir(parents=True)
    pig.write_text("ID,Nazwa,Inne nazwy,Nr inw.\n")
    obj = yaml.safe_load((root / "data/objects/KSW/KSW-0001.yml").read_text())
    old = feature(lon=19.801)
    new = clean_feature(
        name=obj["name_local"] if candidate_kind == "object" else old["attributes"]["NAZWA"]
    )
    # The second case remembers a source that disappears from the accepted
    # baseline but remains in the immutable evidence for its absence decision.
    features = [old, new] if candidate_kind == "object" else [new]
    review_snapshot = snapshot(root, "review", features)
    accept("fixture: retain snapshot for review")
    report = report_for(review_snapshot, "review-batch", qualify=True)
    new_guid = new["attributes"]["GLOBALID"]
    row = next(r for r in report["records"] if r["globalid"] == new_guid)
    candidate = next(
        c
        for c in row["candidates"]
        if (
            c["target"].get("object_id") == "KSW-0001"
            if candidate_kind == "object"
            else c["target"].get("globalid") == GUID
            and c["candidate_basis"]["positions"][0]["lon"] == Decimal("19.801")
        )
    )
    basis = candidate["resolution"]["current_basis"]
    memory = {
        "pair": [s["key"] for s in basis["sides"]],
        "basis": basis,
        "basis_hash": digest(basis),
        "outcome": "different_objects",
        "evidence": "Fixture reviewed cave plan",
        "reviewed_by": "human",
        "reviewed_at": "2026-10-21T00:00:00Z",
    }
    # PBI-098 only reads duplicate memory; explicitly accept it in fixture main.
    (root / "data/source_state/tpn/duplicates.json").write_bytes(
        canonical({"format": "tpn-duplicate-state", "format_version": 1, "resolutions": [memory]})
        + b"\n"
    )
    accept("fixture: accept duplicate decision")
    report = report_for(review_snapshot, "review-batch", qualify=True)
    assert report["duplicate_resolution_checks"][0]["status"] == "valid"
    reject_and_check(report)
    accept("fixture: accept source rejection batch")
    result = report_for(snapshot(root, "next", features), "next-batch", qualify=True)
    result_row = next(r for r in result["records"] if r["globalid"] == new_guid)
    assert result["catalog_hash"] == report["catalog_hash"]
    assert result_row["revision_hash"] == row["revision_hash"]
    assert result["duplicate_resolution_checks"][0]["status"] == "valid"
    assert result_row["review_status"] == "reject"
    assert not result_row["actionable"] and not result["requires_pr"]


@pytest.mark.parametrize("version", ["tpn-candidates-v0", "tpn-candidates-v3", None])
def test_unknown_candidate_policy_version_cannot_generate_report(version):
    with pytest.raises(ValueError, match="candidate policy version"):
        CandidatePolicy(version=version)


def test_legacy_candidate_report_replays_through_public_batch_api(batch_repo):
    from test_tpn_batch import git

    from gps_kataster_obiektow_tatr.tpn_batch import apply_batch, check_batch, prepare_batch
    from gps_kataster_obiektow_tatr.tpn_changes import compare

    root, snap = batch_repo
    head = git(root, "rev-parse", "HEAD")
    report = compare(
        root,
        snap,
        batch_id="legacy-batch",
        base_commit=head,
        candidate_policy=CandidatePolicy(version="tpn-candidates-v1"),
    )
    report["accepted_state_commit"] = head
    changes, decisions = prepare_batch(root, report)
    for decision in decisions["decisions"]:
        decision.update(
            status="reject",
            reviewed_by="human",
            reviewed_at="2026-10-21T00:01:00Z",
            reason="Legacy decision replay",
        )
    apply_batch(root, changes, decisions, reviewers={"human"})
    check_batch(root, "legacy-batch")


def test_legacy_duplicate_memory_requires_review_under_new_policy(tiny_repo):
    from test_tpn_changes import snapshot, state_for

    from gps_kataster_obiektow_tatr.tpn_changes import compare
    from gps_kataster_obiektow_tatr.tpn_normalization import digest

    snap = snapshot(tiny_repo, "legacy", [clean_feature(name="Wyjątkowa Nazwa Dawnego Punktu")])
    report = compare(
        tiny_repo,
        snap,
        batch_id="legacy",
        base_commit="a" * 40,
        candidate_policy=CandidatePolicy(version="tpn-candidates-v1"),
    )
    row = active_row(report)
    candidate = next(c for c in row["candidates"] if c["key"] == "object:KSW-9001")
    basis = candidate["resolution"]["current_basis"]
    memory = {
        "pair": [s["key"] for s in basis["sides"]],
        "basis": basis,
        "basis_hash": digest(basis),
        "outcome": "different_objects",
        "evidence": "Legacy reviewed pair",
        "reviewed_by": "human",
        "reviewed_at": "2026-10-21T00:00:00Z",
    }
    state = state_for({**report, "records": [row]}, "reject")
    state["bindings"] = {}
    result = compare(
        tiny_repo,
        snap,
        batch_id="new-policy",
        base_commit="a" * 40,
        state=state,
        candidate_policy=CandidatePolicy(),
        duplicate_resolutions=[memory],
    )
    assert result["duplicate_resolution_checks"][0]["status"] == "stale"
    assert active_row(result)["review_status"] == "pending"
    assert active_row(result)["new_record_qualification"]["checks"]["source_review_clear"] is False
    assert result["requires_pr"]


def test_changed_source_revision_without_collision_reopens_historical_reject(tiny_repo):
    from test_tpn_changes import state_for

    from gps_kataster_obiektow_tatr.tpn_normalization import digest

    original = clean_feature()
    first = compare_tiny(tiny_repo, [original])
    state = state_for({**first, "records": [active_row(first)]}, "reject")
    state["bindings"] = {}
    conflicting = clean_feature(name="Wyjątkowa Nazwa Dawnego Punktu")
    second = compare_tiny(tiny_repo, [conflicting], "second", state=state)
    row = active_row(second)
    candidate = next(c for c in row["candidates"] if c["key"] == "object:KSW-9001")
    basis = candidate["resolution"]["current_basis"]
    memory = {
        "pair": [s["key"] for s in basis["sides"]],
        "basis": basis,
        "basis_hash": digest(basis),
        "outcome": "different_objects",
        "evidence": "Review of the later source name",
        "reviewed_by": "human",
        "reviewed_at": "2026-10-21T00:00:00Z",
    }
    state["accepted_snapshot_hash"] = second["snapshot_hash"]
    state["resolutions"].extend(state_for({**second, "records": [row]}, "reject")["resolutions"])
    control = compare_tiny(tiny_repo, [original], "control", state=state)
    assert active_row(control)["review_status"] == "reject" and not control["requires_pr"]
    result = compare_tiny(
        tiny_repo, [original], "returned", state=state, duplicate_resolutions=[memory]
    )
    assert active_row(result)["candidates"] == []
    assert result["duplicate_resolution_checks"][0]["status"] == "stale"
    assert active_row(result)["review_status"] == "pending"
    assert active_row(result)["new_record_qualification"]["checks"]["source_review_clear"] is False
    assert result["requires_pr"]


@pytest.mark.parametrize("field", ["NAZWA", "NR_INWENT", "SYSTEM", "WER_LOK", "geometry"])
def test_changed_competitor_evidence_invalidates_duplicate_memory(tiny_repo, field):
    from copy import deepcopy

    from gps_kataster_obiektow_tatr.tpn_normalization import digest

    new = clean_feature(name="Wyjątkowa Nazwa Dawnego Punktu")
    other = clean_feature("55555555-5555-4555-8555-555555555555", "Odrębny punkt", 3)
    other["geometry"]["x"] = 20.1
    report = compare_tiny(tiny_repo, [new, other])
    candidate = next(c for c in active_row(report)["candidates"] if c["key"] == "object:KSW-9001")
    basis = candidate["resolution"]["current_basis"]
    memory = {
        "pair": [s["key"] for s in basis["sides"]],
        "basis": basis,
        "basis_hash": digest(basis),
        "outcome": "different_objects",
        "evidence": "Reviewed comparison set",
        "reviewed_by": "human",
        "reviewed_at": "2026-10-21T00:00:00Z",
    }
    changed = deepcopy(other)
    if field == "geometry":
        changed["geometry"]["x"] = 20.1000000001
    else:
        changed["attributes"][field] = "Nowy dowód"
    result = compare_tiny(tiny_repo, [new, changed], "next", duplicate_resolutions=[memory])
    assert result["duplicate_resolution_checks"][0]["status"] == "stale"
    assert result["requires_pr"]
