"""Reader-facing cleanup cannot change measurements, decisions or selected points."""

import importlib
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from gps_kataster_obiektow_tatr.tpn_batch_actions import measurement

REPO = Path(__file__).resolve().parents[1]


def editorial():
    return importlib.import_module("gps_kataster_obiektow_tatr.tpn_editorial_notes")


def source_row():
    return {
        "globalid": "4bbef00c-a6c1-4706-9590-9dbc61b70ddd",
        "revision_hash": "7" * 64,
        "source_after": {
            "source_time": {
                "date_basis": "source_modified",
                "source_modified_at": "2026-06-16T11:29:06Z",
                "source_date": "2026-06-16",
            },
            "location": {"lat": 49.23207253551044, "lon": 19.904438168831337},
            "metadata": {"WER_LOK": "FF16062026", "UWAGI": None},
        },
    }


def test_new_measurement_has_tpn_tag_without_revision_in_reader_notes():
    value = measurement(
        source_row(), "m-001", {"reviewed_at": "2026-10-21T15:00:00Z", "reviewed_by": "human"}
    )
    assert value["tags"] == ["tpn"]
    assert "revision" not in value["notes"]
    assert "Data pomiaru terenowego nieznana" in value["notes"]
    assert "TPN WER_LOK: FF16062026" in value["notes"]


def test_legacy_measurement_is_reproducible():
    args = (source_row(), "m-001", {"reviewed_at": "2026-10-21T15:00:00Z", "reviewed_by": "human"})
    legacy = measurement(*args, legacy=True)
    current = measurement(*args)
    assert legacy["tags"] == []
    assert "TPN revision: " + "7" * 64 in legacy["notes"]
    for value in (legacy, current):
        value.pop("notes")
        value.pop("tags")
    assert legacy == current


def test_note_routing_preserves_location_context_and_separates_cave_and_opening():
    module = editorial()
    assert module.context_kind("lok. orientacyjnie na podstawie opisu") == "measurement"
    assert module.context_kind("Dane morfometr. orientacyjnie") == "cave"
    assert module.context_kind("zasypana, ale widoczne belkowanie stropu") == "object"
    notes = (
        "TPN source-record measurement imported after operator review; not "
        "field-verified.\nTPN WER_LOK: 2024 TZK\nTPN UWAGI: Dane morfometr. "
        "orientacyjnie"
    )
    assert module.measurement_notes(notes) == "TPN WER_LOK: 2024 TZK"
    assert module.measurement_notes("Własny ręczny komentarz") == "Własny ręczny komentarz"


def test_cleanup_is_idempotent_and_preserves_unrecognised_notes():
    module = editorial()
    for notes in [
        None,
        "TPN WER_LOK: 2024 TZK",
        "Data pomiaru terenowego nieznana; użyto daty modyfikacji rekordu TPN.",
        "Ręczna uwaga\nTPN UWAGI: niejednoznaczny kontekst",
    ]:
        assert module.measurement_notes(module.measurement_notes(notes)) == notes


def test_reconstruction_changes_only_notes_tpn_tags_and_audit():
    module = editorial()
    before = {
        "id": "KSW-0001",
        "notes": "Imported from TPN source record after operator review.",
        "measurements": [
            {
                "id": "m-001",
                "source": "TPN",
                "notes": "TPN revision: " + "7" * 64,
                "tags": ["custom"],
                "lat": 49.2,
            }
        ],
        "best_measurement": {"measurement_id": "m-001", "mode": "manual"},
    }
    after = module.clean_object(deepcopy(before))
    assert after["notes"] is None
    assert after["measurements"][0]["notes"] is None
    assert after["measurements"][0]["tags"] == ["custom", "tpn"]
    assert after["measurements"][0]["lat"] == before["measurements"][0]["lat"]
    assert after["best_measurement"] == before["best_measurement"]


@pytest.mark.parametrize(
    "note",
    [
        "TPN UWAGI: dane morfometryczne do poprawy",
        "TPN UWAGI: zasypana, ale widoczne belkowanie stropu",
    ],
)
def test_nonlocation_context_is_removed_only_by_known_semantic_class(note):
    assert editorial().measurement_notes(note) is None


def test_cave_routing_retains_morphometry_sources_absent_from_old_cave_notes():
    cave = {"id": "C-0001", "notes": "PIG source state year: 2014"}
    objects = [
        {
            "cave_id": "C-0001",
            "measurements": [{"notes": "TPN UWAGI: dane morf. wg listy J.Nowaka"}],
        }
    ]
    after = editorial().clean_cave(cave, objects)
    assert "PIG; stan źródła: 2014" in after["notes"]
    assert "wg listy J.Nowaka" in after["notes"]
    assert (
        editorial().cave_source_context("Dane morfometr. orentacyjne")
        == "Uwagi TPN: Dane morfometryczne orientacyjne."
    )


@pytest.fixture(scope="module")
def editorial_correction():
    from gps_kataster_obiektow_tatr.tpn_batch import base_checkout
    from gps_kataster_obiektow_tatr.tpn_changes import Catalog
    from gps_kataster_obiektow_tatr.tpn_editorial_correction import (
        BASE_COMMIT,
        build_editorial_files,
    )
    from gps_kataster_obiektow_tatr.tpn_snapshot import sha256

    with base_checkout(REPO, BASE_COMMIT) as base:
        receipt = {
            "format": "tpn-editorial-correction",
            "format_version": 1,
            "base_commit": BASE_COMMIT,
            "applied_at": "2026-10-21T16:00:00Z",
            "applied_by": "agent:codex",
            "authorization_quote": "Usuń hash z uwag i uzupełnij tagi; zachowaj historię i best.",
            "before_catalog_hash": Catalog(base).hash,
            "result_hashes": {},
        }
        files = build_editorial_files(base, receipt)
        receipt["result_hashes"] = {p: sha256(raw) for p, raw in files.items()}
        yield base, receipt, files


def test_full_correction_preserves_all_noneditorial_values(editorial_correction):
    import yaml

    base, _, files = editorial_correction
    for p, raw in files.items():
        if p.endswith("state.json"):
            before = json.loads((base / p).read_bytes())
            after = json.loads(raw)
            for state in (before, after):
                for resolution in state["resolutions"]:
                    resolution.pop("result_hashes")
                    resolution.pop("result_catalog_hash")
            assert before == after
            continue
        before = yaml.safe_load((base / p).read_bytes())
        after = yaml.safe_load(raw)
        for value in (before, after):
            for field in ("notes", "updated_at", "updated_by"):
                value.pop(field, None)
        for old, new in zip(
            before.get("measurements", []), after.get("measurements", []), strict=True
        ):
            assert new["tags"] == (
                old["tags"]
                if old["source"] != "TPN" or "tpn" in old["tags"]
                else [*old["tags"], "tpn"]
            )
            for value in (old, new):
                value.pop("notes", None)
                value.pop("tags", None)
        assert before == after, p


@pytest.fixture
def editorial_root(editorial_correction, tmp_path):
    from gps_kataster_obiektow_tatr.tpn_editorial_correction import RECEIPT
    from gps_kataster_obiektow_tatr.tpn_normalization import canonical

    base, receipt, files = editorial_correction
    root = tmp_path / "catalog"
    shutil.copytree(base, root)
    (root / ".git").write_text(f"gitdir: {REPO / '.git'}\n")
    for p, raw in files.items():
        (root / p).write_bytes(raw)
    (root / RECEIPT).write_bytes(canonical(receipt) + b"\n")
    return root, deepcopy(receipt)


def test_check_reconstructs_editorial_correction_and_original_apply_is_blocked(editorial_root):
    from gps_kataster_obiektow_tatr.tpn_batch import check_batch, load_batch, plan_batch

    root, _ = editorial_root
    assert check_batch(root, "pbi-101-20261019")["noop"]
    changes, decisions = load_batch(root, "pbi-101-20261019")
    reviewers = {d["reviewed_by"] for d in decisions["decisions"] if d["reviewed_by"]}
    with pytest.raises(ValueError, match="previous result/output changed"):
        plan_batch(root, changes, decisions, reviewers=reviewers)


@pytest.mark.parametrize("change", ["coordinate", "best", "reference", "tag", "binding", "receipt"])
def test_recomputed_editorial_hashes_do_not_authorize_foreign_edits(editorial_root, change):
    import yaml

    from gps_kataster_obiektow_tatr.tpn_editorial_correction import (
        RECEIPT,
        verified_editorial_files,
    )
    from gps_kataster_obiektow_tatr.tpn_normalization import canonical
    from gps_kataster_obiektow_tatr.tpn_snapshot import sha256

    root, receipt = editorial_root
    p = "data/objects/MLW/MLW-0050.yml"
    value = yaml.safe_load((root / p).read_bytes())
    if change == "coordinate":
        value["measurements"][0]["lat"] += 0.001
    elif change == "best":
        value["best_measurement"]["measurement_id"] = "m-002"
    elif change == "reference":
        value["external_refs"] = []
    elif change == "tag":
        value["measurements"][0]["tags"] = ["foreign"]
    elif change == "binding":
        p = "data/source_state/tpn/state.json"
        value = json.loads((root / p).read_bytes())
        value["bindings"][next(iter(value["bindings"]))] = "foreign"
    else:
        p = "docs/asdlc/verification/PBI-101-catalog-notes.json"
        value = json.loads((root / p).read_bytes())
        value["applied_by"] = "foreign"
    raw = canonical(value) + b"\n" if p.endswith(".json") else yaml.safe_dump(value).encode()
    (root / p).write_bytes(raw)
    receipt["result_hashes"][p] = sha256(raw)
    (root / RECEIPT).write_bytes(canonical(receipt) + b"\n")
    with pytest.raises(ValueError):
        verified_editorial_files(root, {})


@pytest.mark.parametrize(
    "path",
    [
        "docs/asdlc/verification/PBI-099-protection-manifest.json",
        "docs/asdlc/verification/PBI-101-review/remaining-26.json",
    ],
)
def test_current_historical_documents_cannot_be_hidden_by_editorial_preimage(editorial_root, path):
    from gps_kataster_obiektow_tatr.tpn_editorial_correction import verified_editorial_files

    root, _ = editorial_root
    target = root / path
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="historical"):
        verified_editorial_files(root, {})
