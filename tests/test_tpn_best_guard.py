"""TPN protection is independent of source priority and never mutates history."""

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from gps_kataster_obiektow_tatr import tpn_best_guard as guard
from gps_kataster_obiektow_tatr.best_measurement import select_default_best_measurement_id

REPO = Path(__file__).resolve().parents[1]


def measurement(identity="m-001", **changes):
    return {
        "id": identity,
        "source": "inne",
        "method": "source_record",
        "verification_status": "nieweryfikowany",
        "horizontal_accuracy_m": None,
        "elevation_source": "unknown",
        "observed_date": "2020-01-01",
        "lat": 49.2,
        "lon": 19.8,
        "tags": [],
    } | changes


def obj(**changes):
    return {
        "id": "KSW-9001",
        "measurements": [measurement()],
        "attachments": [],
        "best_measurement": {"mode": "auto", "measurement_id": "m-001", "reason": None},
    } | changes


def action(kind="keep", identity="m-001", mode="manual", reason="Zachować punkt eksportu."):
    return {"action": kind, "measurement_id": identity, "resulting_mode": mode, "reason": reason}


def addition(identity="m-002", **changes):
    return measurement(identity, source="TPN", observed_date="2026-10-19", **changes)


@pytest.mark.parametrize("source", ["inne", "TPN", "PIG", "wlasne", "geoportal", "publikacja"])
@pytest.mark.parametrize("status", ["nieweryfikowany", "odrzucony", "zweryfikowany"])
def test_gnss_in_history_protects_even_if_unselected_rejected_and_unknown_accuracy(source, status):
    old = obj(
        measurements=[
            measurement(source="TPN"),
            measurement("m-009", source=source, method="gnss", verification_status=status),
        ]
    )
    saved = deepcopy(old)
    evidence = guard.assess_protection(old)
    assert evidence["protected"] is True
    assert any(
        e["measurement_id"] == "m-009" and e["basis"] == "method_gnss" for e in evidence["evidence"]
    )
    with pytest.raises(ValueError, match="TPN_BEST_PROTECTED"):
        guard.plan_best_action(old, [addition()], action("select_new", "m-002", "auto"))
    assert old == saved


@pytest.mark.parametrize(
    "change,basis",
    [
        ({"method": "gnss"}, "method_gnss"),
        ({"elevation_source": "gnss"}, "elevation_gnss"),
        ({"tags": ["gnss"]}, "tag_gnss"),
        ({"tags": ["gnss_anchor"]}, "tag_gnss_anchor"),
        ({"source": "wlasne", "verification_status": "zweryfikowany"}, "own_verified"),
    ],
)
def test_each_structured_basis_independently_protects(change, basis):
    result = guard.assess_protection(obj(measurements=[measurement(**change)]))
    assert result["protected"]
    assert basis in {e["basis"] for e in result["evidence"]}


def test_manual_and_object_level_report_protect_the_whole_object():
    manual = obj(
        best_measurement={"mode": "manual", "measurement_id": "m-001", "reason": "Operator"}
    )
    assert guard.assess_protection(manual)["protected"]
    with pytest.raises(ValueError, match="TPN_BEST_PROTECTED"):
        guard.plan_best_action(manual, [addition()], action("select_new", "m-002"))
    report = obj(
        attachments=[
            {
                "id": "a-001",
                "kind": "raport_gnss",
                "measurement_id": None,
                "path": "https://example.com/report.pdf",
            }
        ]
    )
    result = guard.assess_protection(report)
    assert result["protected"]
    assert any(
        e["basis"] == "gnss_report" and e["attachment_id"] == "a-001" for e in result["evidence"]
    )


def test_keep_explicitly_pins_best_without_mutating_inputs():
    old, new = obj(), [addition()]
    saved = deepcopy((old, new))
    with pytest.raises(ValueError, match="manual"):
        guard.plan_best_action(old, new, action(mode="auto", reason=None))
    result = guard.plan_best_action(old, new, action())
    assert result["before"] == old["best_measurement"]
    assert result["after"]["measurement_id"] == "m-001"
    assert result["after"]["mode"] == "manual"
    assert result["mode_change"] == {"before": "auto", "after": "manual"}
    assert result["can_apply"] is True
    assert result["default_after"] == "m-002"
    assert (old, new) == saved


def test_protected_keep_migration_remains_blocked_until_manifest_approval():
    old = obj(measurements=[measurement(method="gnss")])
    result = guard.plan_best_action(old, [addition()], action())
    assert result["after"]["measurement_id"] == "m-001"
    assert result["can_apply"] is False
    assert "migration_manifest_approval_required" in result["blockers"]
    assert old["best_measurement"]["mode"] == "auto"


def test_keep_can_preserve_auto_when_algorithm_preserves_the_same_id():
    old = obj(measurements=[measurement(source="wlasne", verification_status="zweryfikowany")])
    result = guard.plan_best_action(old, [addition()], action(mode="auto", reason=None))
    assert result["can_apply"]
    assert result["after"] == old["best_measurement"]
    assert result["mode_change"] is None


def test_unprotected_auto_select_new_and_explicit_manual_exception():
    result = guard.plan_best_action(
        obj(), [addition()], action("select_new", "m-002", "auto", "Porównano źródła.")
    )
    assert result["can_apply"] and result["after"]["measurement_id"] == "m-002"
    older = addition(observed_at="1900-01-01T00:00:00Z")
    old = obj(measurements=[measurement(source="TPN", observed_date="2025-01-01")])
    with pytest.raises(ValueError, match="manual"):
        guard.plan_best_action(old, [older], action("select_new", "m-002", "auto"))
    assert (
        guard.plan_best_action(old, [older], action("select_new", "m-002"))["after"]["mode"]
        == "manual"
    )


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {},
        action("other"),
        action(identity="m-002"),
        action(reason=" "),
        action(mode="invalid"),
        action() | {"unknown": True},
    ],
)
def test_invalid_or_implicit_actions_are_rejected(bad):
    with pytest.raises(ValueError):
        guard.plan_best_action(obj(), [addition()], bad)


def test_invalid_histories_and_non_tpn_additions_cannot_reach_guard():
    for new in ([addition("m-001")], [measurement("m-002")], [addition(lat=float("nan"))], []):
        with pytest.raises(ValueError):
            guard.plan_best_action(obj(), new, action())


def test_ksz_0112_regression_preserves_the_point_and_general_auto_algorithm():
    old = yaml.safe_load((REPO / "data/objects/KSZ/KSZ-0112.yml").read_text())
    saved = deepcopy(old)
    assert select_default_best_measurement_id(old["measurements"] + [addition()]) == "m-002"
    result = guard.plan_best_action(old, [addition()], action())
    assert result["after"]["measurement_id"] == "m-001"
    assert not result["can_apply"]
    with pytest.raises(ValueError, match="TPN_BEST_PROTECTED"):
        guard.plan_best_action(old, [addition()], action("select_new", "m-002", "auto"))
    assert old == saved


def test_catalog_audit_lists_exact_proposals_with_preimages_and_unchanged_best():
    from gps_kataster_obiektow_tatr.tpn_changes import Catalog
    from gps_kataster_obiektow_tatr.tpn_normalization import digest

    catalog = Catalog(REPO)
    saved = deepcopy(catalog.objects)
    report = guard.audit_catalog(catalog)
    assert report == guard.audit_catalog(catalog)
    assert report["approval_status"] == "pending"
    assert report["catalog_hash"] == catalog.hash
    assert report["policy"]["hash"] == digest(report["policy"]["rules"])
    proposals = {p["object_id"]: p for p in report["migration_proposals"]}
    assert set(proposals) == {"KSZ-0112", "KSW-0201", "KSW-0240"}
    for identity, proposal in proposals.items():
        assert proposal["before"] == saved[identity]["best_measurement"]
        assert proposal["after"]["measurement_id"] == proposal["before"]["measurement_id"]
        assert proposal["after"]["mode"] == "manual"
        assert proposal["after"]["reason"]
        assert proposal["preimage_sha256"] == catalog.hashes[catalog.paths[identity]]
        assert proposal["evidence"]
    assert len(report["objects"]) == 9
    assert catalog.objects == saved


def test_audit_cli_writes_readable_manifest_exclusively_without_touching_catalog(tmp_path):
    import json
    import subprocess
    import sys
    import uuid

    # Only reports may be written; the executable does not expose apply/migrate.
    output = REPO / "build" / "test-best-guard" / uuid.uuid4().hex
    command = [
        sys.executable,
        str(REPO / "scripts/audit_tpn_best.py"),
        "--repo-root",
        str(REPO),
        "--output-dir",
        str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    manifest = json.loads((output / "manifest.json").read_bytes())
    assert manifest["approval_status"] == "pending"
    assert len(manifest["migration_proposals"]) == 3
    markdown = (output / "report.md").read_text()
    for p in manifest["migration_proposals"]:
        assert p["object_id"] in markdown and p["before"]["measurement_id"] in markdown
        assert p["after"]["reason"] in markdown
    payload = (output / "manifest.json").read_bytes()
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode != 0
    assert (output / "manifest.json").read_bytes() == payload
    outside = subprocess.run(
        command[:-1] + [str(tmp_path / "not-a-report")], capture_output=True, text=True
    )
    assert outside.returncode != 0
    assert not (tmp_path / "not-a-report").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("notes", "Raport z pomiaru geodezyjnego, kwalifikacja niejasna."),
        ("device", "GNSS receiver"),
        ("source_ref", "archive:RTK:2020"),
        ("tags", ["GEODEZJA_DO_SPRAWDZENIA"]),
    ],
)
def test_unqualified_text_is_review_evidence_and_cannot_allow_tpn_replacement(field, value):
    old = obj(measurements=[measurement(**{field: value})])
    result = guard.assess_protection(old)
    assert not result["protected"]
    assert result["requires_review"]
    assert result["review_evidence"][0]["measurement_id"] == "m-001"
    with pytest.raises(ValueError, match="TPN_BEST_PROTECTED"):
        guard.plan_best_action(old, [addition()], action("select_new", "m-002", "auto"))
    assert not guard.plan_best_action(old, [addition()], action())["can_apply"]


def test_object_and_attachment_geodetic_text_require_review_even_for_history():
    for changes in (
        {"notes": "Dokumentacja geodezyjna do sprawdzenia"},
        {
            "attachments": [
                {
                    "id": "a-001",
                    "kind": "inne",
                    "measurement_id": "m-001",
                    "path": "https://example.com/gnss/report.pdf",
                }
            ]
        },
        {
            "attachments": [
                {
                    "id": "a-001",
                    "kind": "inne",
                    "measurement_id": None,
                    "path": "report.pdf",
                    "caption": "Geodetic report",
                }
            ]
        },
    ):
        result = guard.assess_protection(obj(**changes))
        assert result["requires_review"] and not result["protected"]


@pytest.mark.parametrize("tag", ["geodetic", "geodezja"])
def test_operator_geodetic_marker_protects_without_status_or_accuracy_inference(tag):
    old = obj(
        measurements=[measurement(tags=[tag], notes="Operator kwalifikuje pomiar jako geodezyjny.")]
    )
    saved = deepcopy(old)
    result = guard.assess_protection(old)
    assert result["protected"]
    assert any(e["basis"] == "tag_" + tag for e in result["evidence"])
    assert old == saved


def test_unknown_accuracy_alone_and_ordinary_gps_do_not_invent_geodetic_protection():
    result = guard.assess_protection(
        obj(
            measurements=[measurement(method="gps_receiver", notes="Zwykły GPS, brak dokładności.")]
        )
    )
    assert not result["protected"] and not result["requires_review"]


def test_best_proposals_do_not_attribute_new_reason_to_the_previous_author():
    old = obj()
    old["best_measurement"].update(updated_at="2020-01-01T00:00:00Z", updated_by="old-author")
    proposal = guard.plan_best_action(old, [addition()], action())
    assert "updated_by" not in proposal["after"] and "updated_at" not in proposal["after"]
    assert proposal["before"]["updated_by"] == "old-author"


def test_manual_keep_preserves_the_original_choice_rationale_and_audit():
    best = {
        "mode": "manual",
        "measurement_id": "m-001",
        "reason": "Decyzja operatora",
        "updated_by": "old-author",
        "updated_at": "2020-01-01T00:00:00Z",
    }
    old = obj(best_measurement=best)
    assert guard.plan_best_action(old, [addition()], action())["after"] == best


@pytest.mark.parametrize("value", ["pomiar_geodezyjny", "survey_gnss", "archive/report_rtk.pdf"])
def test_unclear_terms_after_underscores_cannot_bypass_review(value):
    old = obj(measurements=[measurement(tags=[value])])
    assert guard.assess_protection(old)["requires_review"]
    with pytest.raises(ValueError, match="TPN_BEST_PROTECTED"):
        guard.plan_best_action(old, [addition()], action("select_new", "m-002", "auto"))


def test_human_audit_shows_review_status_and_the_actual_unclear_evidence():
    from types import SimpleNamespace

    catalog = SimpleNamespace(
        objects={"KSW-9001": obj(notes="Wzmianka: pomiar geodezyjny")},
        paths={"KSW-9001": "data/objects/KSW/KSW-9001.yml"},
        hashes={"data/objects/KSW/KSW-9001.yml": "a" * 64},
        hash="b" * 64,
    )
    report = guard.audit_catalog(catalog)
    markdown = guard.render_audit(report)
    assert "review" in markdown
    assert "unqualified_geodetic_text" in markdown
    assert "Wzmianka: pomiar geodezyjny" in markdown
    assert report["migration_proposals"] == []
