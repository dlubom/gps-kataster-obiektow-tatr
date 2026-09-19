"""Both YAML extensions reserve IDs and review updates the original files."""

from copy import deepcopy

import pytest
import yaml
from test_cave_membership import _sample, _snapshot, _write

from gps_kataster_obiektow_tatr import pig_staging, tpn_staging
from gps_kataster_obiektow_tatr.data_loader import iter_yaml_paths, load_dataset
from gps_kataster_obiektow_tatr.staging_review import StagingReports, apply_review_decisions
from gps_kataster_obiektow_tatr.validator import validate_data_dir


@pytest.mark.parametrize("module", [pig_staging, tpn_staging])
@pytest.mark.parametrize("prefix", ["KSW", "C"])
@pytest.mark.parametrize("number", [1, 9999, 10000])
def test_importer_numbering_matches_recursive_loader(tmp_path, module, prefix, number):
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / f"{prefix}-{number:04d}.yaml").touch()
    (tmp_path / f"{prefix}-0001.yml").touch()
    (tmp_path / f"{prefix}-99999.yml").mkdir()  # A directory cannot reserve an ID.
    (tmp_path / "OTHER-99999.yaml").touch()
    (tmp_path / f"{prefix}-invalid.yaml").touch()
    (tmp_path / f"{prefix}-99999.yml.bak").touch()
    assert module._max_existing_number(tmp_path, prefix=prefix) == number
    assert iter_yaml_paths(tmp_path) == tuple(
        sorted(
            [
                nested / f"{prefix}-{number:04d}.yaml",
                tmp_path / f"{prefix}-0001.yml",
                tmp_path / "OTHER-99999.yaml",
                tmp_path / f"{prefix}-invalid.yaml",
            ]
        )
    )


@pytest.mark.parametrize("action", ["link_cave", "add_measurement"])
@pytest.mark.parametrize("layout", ["yaml", "mixed", "nested"])
def test_review_preserves_original_paths_and_history(tmp_path, action, layout):
    records = _sample(tmp_path)
    paths = {}
    for index, (relative, data) in enumerate(records.items()):
        original = tmp_path / relative
        path = original
        if layout != "mixed" or index % 2 == 0:
            path = path.with_suffix(".yaml")
        if layout == "nested":
            path = (
                path.parent.parent / "retained" / path.parent.name / path.name
                if relative.startswith("objects/")
                else path.parent / "retained" / path.name
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        original.rename(path)
        paths[data["id"]] = path
    obj = records["objects/KSW/KSW-0001.yml"]
    update = {**deepcopy(obj["measurements"][0]), "id": "m-002", "source": "TPN"}
    reports = StagingReports(
        tpn={
            "matched_measurements": [
                {
                    "record_number": 1,
                    "target_object_id": "KSW-0001",
                    "target_cave_id": "C-0001",
                    "measurement": update,
                }
            ]
        }
    )
    decision = (
        {"action": action, "object_id": "KSW-0001", "cave_id": "C-0002"}
        if action == "link_cave"
        else {"action": action, "source": "TPN", "record_number": 1}
    )
    decisions = {
        "reviewed_at": "2026-09-19T12:00:00Z",
        "reviewed_by": "reviewer",
        "decisions": [decision],
    }
    initial_errors = {
        (i.code, i.path) for i in validate_data_dir(tmp_path) if i.severity == "error"
    }
    before = _snapshot(tmp_path)
    dry = apply_review_decisions(decisions, staging_reports=reports, data_dir=tmp_path, write=False)
    if layout == "nested":
        assert dry.has_errors and dry.written_paths == ()
        result = apply_review_decisions(decisions, staging_reports=reports, data_dir=tmp_path)
        assert result.has_errors and result.written_paths == ()
        assert all(code == "FILE_ID_MISMATCH" for code, _ in initial_errors)
        assert all(str(path) in result.issues[0].description for path in paths.values())
        assert _snapshot(tmp_path) == before
        return
    assert not dry.has_errors and dry.written_paths == ()
    assert _snapshot(tmp_path) == before
    result = apply_review_decisions(decisions, staging_reports=reports, data_dir=tmp_path)
    assert not result.has_errors
    touched = {"KSW-0001", "C-0001"} | ({"C-0002"} if action == "link_cave" else set())
    assert set(result.written_paths) == {paths[id_] for id_ in touched}
    assert _snapshot(tmp_path).keys() == before.keys()
    loaded = load_dataset(tmp_path)
    assert {r.data["id"]: r.path for r in loaded.records()} == paths
    actual = yaml.safe_load(paths["KSW-0001"].read_text())
    assert actual["measurements"][0] == obj["measurements"][0]
    assert actual["id_assignment"] == obj["id_assignment"]
    if action == "add_measurement":
        assert actual["measurements"] == [*obj["measurements"], update]
    else:
        assert actual["measurements"] == obj["measurements"]
        assert actual["cave_id"] == "C-0002"
        assert yaml.safe_load(paths["C-0001"].read_text())["object_ids"] == ["KSW-0002"]
        assert yaml.safe_load(paths["C-0002"].read_text())["object_ids"] == ["KSW-0001"]
    for id_, path in paths.items():
        if id_ not in touched:
            assert path.read_bytes() == before[str(path.relative_to(tmp_path))]
    final_errors = {(i.code, i.path) for i in validate_data_dir(tmp_path) if i.severity == "error"}
    assert not final_errors


@pytest.mark.parametrize("relative", ["objects/KSW/KSW-0001.yml", "caves/C-0001.yml"])
@pytest.mark.parametrize("different", [False, True])
@pytest.mark.parametrize("write", [False, True])
def test_conflicting_extensions_block_entire_review(tmp_path, relative, different, write):
    records = _sample(tmp_path)
    duplicate = deepcopy(records[relative])
    if different:
        duplicate["notes"] = "different content must never be chosen implicitly"
    alternate = (tmp_path / relative).with_suffix(".yaml")
    _write(alternate, duplicate)
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        {"decisions": [{"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0002"}]},
        staging_reports=StagingReports(),
        data_dir=tmp_path,
        write=write,
    )
    assert result.has_errors
    assert result.written_paths == () and result.applied_decisions == ()
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert (issue.code, issue.severity.value, issue.decision_index) == (
        "FINAL_DATA_INVALID",
        "error",
        None,
    )
    assert str(alternate) in issue.description
    assert str(tmp_path / relative) in issue.description
    assert duplicate["id"] in issue.description
    assert _snapshot(tmp_path) == before


def test_new_records_use_yml_in_mixed_catalog(tmp_path):
    records = _sample(tmp_path)
    for relative in records:
        path = tmp_path / relative
        path.rename(path.with_suffix(".yaml"))
    before = _snapshot(tmp_path)
    obj = {**deepcopy(records["objects/KSW/KSW-0001.yml"]), "id": "KSW-0003", "cave_id": "C-0004"}
    cave = {**deepcopy(records["caves/C-0001.yml"]), "id": "C-0004", "object_ids": ["KSW-0003"]}
    reports = StagingReports(
        pig={
            "rows": [{"record_number": 1, "object_id": "KSW-0003", "cave_id": "C-0004"}],
            "proposed_objects": [obj],
            "proposed_caves": [cave],
        }
    )
    result = apply_review_decisions(
        {
            "decisions": [
                {"action": action, "source": "PIG", "record_number": 1}
                for action in ["create_cave", "create_object"]
            ]
        },
        staging_reports=reports,
        data_dir=tmp_path,
    )
    assert not result.has_errors
    assert result.written_paths == (
        tmp_path / "caves/C-0004.yml",
        tmp_path / "objects/KSW/KSW-0003.yml",
    )
    assert (
        yaml.safe_load(result.written_paths[1].read_text())["measurements"] == obj["measurements"]
    )
    after = _snapshot(tmp_path)
    assert {path: after[path] for path in before} == before
    assert after.keys() == before.keys() | {"caves/C-0004.yml", "objects/KSW/KSW-0003.yml"}
    assert not [i for i in validate_data_dir(tmp_path) if i.severity == "error"]
