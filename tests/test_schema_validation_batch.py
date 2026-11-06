"""Prepare legacy schemas once per operation, including Git history reads."""

from copy import deepcopy
from pathlib import Path

import yaml

from gps_kataster_obiektow_tatr import validator
from gps_kataster_obiektow_tatr.data_loader import load_yaml_dataset


def count_preparations(monkeypatch):
    calls = []
    original = validator._load_schema_validators

    def prepare(schema_dir):
        calls.append(schema_dir)
        return original(schema_dir)

    monkeypatch.setattr(validator, "_load_schema_validators", prepare)
    return calls


def test_proposal_batch_prepares_schemas_once_without_changing_diagnostics(
    tmp_path, make_data_dir, monkeypatch
):
    make_data_dir(tmp_path)
    fixtures = Path(__file__).parent / "fixtures"
    obj = yaml.safe_load((fixtures / "valid-object.yml").read_text())
    obj["category"] = "bad-category"
    cave = yaml.safe_load((fixtures / "valid-cave.yml").read_text())
    cave["object_ids"] = ["KSW-0001", "KSW-0002"]
    (tmp_path / "caves/C-0001.yml").write_text(yaml.safe_dump(cave))
    (tmp_path / "objects/KSW").mkdir()
    for oid in cave["object_ids"]:
        data = deepcopy(obj)
        data["id"] = oid
        (tmp_path / f"objects/KSW/{oid}.yml").write_text(yaml.safe_dump(data))
    calls = count_preparations(monkeypatch)
    issues = validator.validate_proposal(load_yaml_dataset(tmp_path), data_dir=tmp_path)
    assert [(issue.code, issue.path.stem) for issue in issues] == [
        ("SCHEMA_VALIDATION", "KSW-0001"),
        ("SCHEMA_VALIDATION", "KSW-0002"),
    ]
    assert len(calls) == 1


def test_git_baseline_prepares_schemas_once(tmp_path, monkeypatch):
    from sql_test_support import make_legacy_history_baseline

    from gps_kataster_obiektow_tatr.history import _git_baseline

    root, sha, original = make_legacy_history_baseline(tmp_path)
    calls = count_preparations(monkeypatch)
    actual = _git_baseline(sha, root, "data")
    assert [r.data for r in actual.objects] == [r.data for r in original.objects]
    assert len(calls) == 1
