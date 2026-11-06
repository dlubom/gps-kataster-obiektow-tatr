import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml
from sql_test_support import history_cli_args, read_record

from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992
from gps_kataster_obiektow_tatr.data_loader import load_yaml_dataset
from gps_kataster_obiektow_tatr.postgres import read_catalog_projection
from gps_kataster_obiektow_tatr.staging_review import (
    ReviewDecisionError,
    ReviewSeverity,
    StagingReports,
    _dataset_with_review_changes,
    apply_review_decisions,
    load_review_decisions,
    load_staging_reports,
    render_review_markdown,
    write_review_report_files,
)
from gps_kataster_obiektow_tatr.validator import has_errors, validate_data_dir

REPO_ROOT = Path(__file__).resolve().parents[1]
APPLY_REVIEW_PATH = REPO_ROOT / "scripts" / "importers" / "apply_review.py"
VALIDATE_SCRIPT = REPO_ROOT / "scripts" / "validate.py"
KSW_LAT = 49.23459299
KSW_LON = 19.87589498
TPN_GLOBALID = "{38626571-CAA6-4317-8900-D61A995020E9}"


def _seed_review_data(data_dir):
    _write_yaml(data_dir / "objects/KSW/KSW-0001.yml", _object_data(cave_id="C-0001"))
    other = _object_data(cave_id="C-0001")
    other["id"] = "KSW-0002"
    _write_yaml(data_dir / "objects/KSW/KSW-0002.yml", other)
    _write_yaml(data_dir / "caves/C-0001.yml", _cave_data(object_ids=["KSW-0001", "KSW-0002"]))
    _write_yaml(
        data_dir / "relations/R-0001.yml",
        {
            "schema_version": 1,
            "id": "R-0001",
            "from_object_id": "KSW-0001",
            "to_object_id": "KSW-0002",
            "relation_type": "sasiad",
        },
    )
    assert not has_errors(validate_data_dir(data_dir))


def _tree_snapshot(data_dir):
    return {
        p.relative_to(data_dir): p.read_bytes() if p.is_file() else None
        for p in data_dir.rglob("*")
    }


def _source_review_data(data_dir, *, canonical):
    """Hand-authored source fixture; no production conversion before the tested API."""
    for name in ("objects/KSW", "caves", "relations", "publications"):
        (data_dir / name).mkdir(parents=True, exist_ok=True)
    for object_id, ordinal in (("KSW-0001", 2), ("KSW-0002", 7)):
        obj = _object_data(cave_id="C-0001")
        obj["id"] = object_id
        if canonical:
            obj["membership_ordinal"] = ordinal
            obj["best_measurement"].pop("measurement_id")
            for measurement in obj["measurements"]:
                measurement.pop("x_1992")
                measurement.pop("y_1992")
        _write_yaml(data_dir / f"objects/KSW/{object_id}.yml", obj)
    cave = _cave_data(object_ids=["KSW-0001", "KSW-0002"])
    if canonical:
        cave.pop("object_ids")
        (data_dir / "catalog.json").write_text(
            '{\n  "format": "postgresql-yaml",\n  "schema_version": 2\n}\n'
        )
    _write_yaml(data_dir / "caves/C-0001.yml", cave)
    return data_dir


@pytest.mark.parametrize("canonical", [False, True], ids=["legacy", "canonical"])
@pytest.mark.parametrize("write", [False, True], ids=["dry-run", "write"])
def test_review_reports_actual_written_paths_without_scanning_after_swap(
    tmp_path, monkeypatch, canonical, write
):
    from gps_kataster_obiektow_tatr import catalog_records

    data = _source_review_data(tmp_path / "data", canonical=canonical)
    before = _tree_snapshot(data)
    published = False
    scans, reads = [], []
    exchange = catalog_records._exchange_directories
    read_bytes, rglob = Path.read_bytes, Path.rglob

    def publish(*args):
        nonlocal published
        exchange(*args)
        published = True

    def track_read(path):
        if path.is_relative_to(data) and path.suffix in {".yml", ".yaml"}:
            assert not published, "Review must use the writer result, without YAML readback"
            reads.append(path)
        return read_bytes(path)

    def track_scan(path, pattern, *args, **kwargs):
        if path.is_relative_to(data) and pattern == "*.y*ml":
            scans.append(path)
        return rglob(path, pattern, *args, **kwargs)

    def unexpected_write(*args, **kwargs):
        pytest.fail("Dry-run must not call the writer")

    with monkeypatch.context() as patch:
        patch.setattr(catalog_records, "_exchange_directories", publish)
        patch.setattr(Path, "read_bytes", track_read)
        patch.setattr(Path, "rglob", track_scan)
        if not write:
            patch.setattr(catalog_records, "write_dataset", unexpected_write)
        result = apply_review_decisions(
            {
                "reviewed_at": "2026-11-05T12:00:00Z",
                "decisions": [
                    {"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"},
                ],
            },
            staging_reports=StagingReports(),
            data_dir=data,
            write=write,
        )
    assert not result.has_errors, result.issues
    after = _tree_snapshot(data)
    expected = tuple(
        p
        for name in ("caves", "objects", "relations", "publications")
        for p in sorted((data / name).rglob("*"))
        if p.is_file()
        and p.suffix in {".yml", ".yaml"}
        and before.get(p.relative_to(data)) != after[p.relative_to(data)]
    )
    assert result.written_paths == expected
    assert scans == []
    if write:
        assert published
        assert len(reads) == (2 if canonical else 3)
        assert len(expected) == (2 if canonical else 3)
        if not canonical:
            assert data / "objects/KSW/KSW-0002.yml" in expected
    else:
        assert after == before and not reads


@pytest.mark.parametrize("canonical", [False, True], ids=["legacy", "canonical"])
@pytest.mark.parametrize("write", [False, True], ids=["dry-run", "write"])
def test_create_object_into_existing_cave_appends_after_source_ordinals(tmp_path, canonical, write):
    data = _source_review_data(tmp_path / "data", canonical=canonical)
    pig = _pig_staging()
    pig["proposed_objects"][0]["id"] = "KSW-0003"
    pig["rows"][0]["object_id"] = "KSW-0003"
    before = _tree_snapshot(data)
    result = apply_review_decisions(
        {"decisions": [{"action": "create_object", "source": "PIG", "record_number": 1}]},
        staging_reports=StagingReports(pig=pig),
        data_dir=data,
        write=write,
    )
    assert not result.has_errors, result.issues
    if not write:
        assert result.written_paths == () and _tree_snapshot(data) == before
        return
    obj = yaml.safe_load((data / "objects/KSW/KSW-0003.yml").read_text())
    assert obj["cave_id"] == "C-0001"
    assert obj["membership_ordinal"] == (8 if canonical else 3)
    assert "measurement_id" not in obj["best_measurement"]
    assert "x_1992" not in obj["measurements"][0]
    assert next(r.data for r in read_catalog_projection(data).caves)["object_ids"] == [
        "KSW-0001",
        "KSW-0002",
        "KSW-0003",
    ]
    if canonical:
        assert all(
            (data / path).read_bytes() == contents
            for path, contents in before.items()
            if contents is not None
        )


@pytest.mark.parametrize("canonical", [False, True], ids=["legacy", "canonical"])
@pytest.mark.parametrize("write", [False, True], ids=["dry-run", "write"])
def test_repeated_link_keeps_nonmaximal_ordinal_without_legacy_revalidation(
    tmp_path, monkeypatch, canonical, write
):
    from gps_kataster_obiektow_tatr import validator

    data = _source_review_data(tmp_path / "data", canonical=canonical)
    before = _tree_snapshot(data)
    calls = []
    original = validator.validate_records_schema

    def counted(records, **kwargs):
        calls.append(tuple(records))
        return original(records, **kwargs)

    monkeypatch.setattr(validator, "validate_records_schema", counted)
    result = apply_review_decisions(
        {
            "reviewed_at": "2026-11-05T18:00:00Z",
            "reviewed_by": "reviewer",
            "decisions": [
                {"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"},
                {"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"},
            ],
        },
        staging_reports=StagingReports(),
        data_dir=data,
        write=write,
    )
    assert not result.has_errors, result.issues
    assert len(calls) == (0 if canonical else 1)
    if not write:
        assert result.written_paths == () and _tree_snapshot(data) == before
        return
    obj = yaml.safe_load((data / "objects/KSW/KSW-0001.yml").read_text())
    cave = yaml.safe_load((data / "caves/C-0001.yml").read_text())
    assert obj["membership_ordinal"] == (2 if canonical else 1)
    assert obj["updated_by"] == cave["updated_by"] == "reviewer"
    assert obj["updated_at"] == cave["updated_at"] == "2026-11-05T18:00:00Z"
    assert "object_ids" not in cave
    if canonical:
        untouched = Path("objects/KSW/KSW-0002.yml")
        assert (data / untouched).read_bytes() == before[untouched]


@pytest.mark.parametrize("write", [False, True], ids=["dry-run", "write"])
def test_link_cannot_repair_contradictory_staging_membership_before_adaptation(
    tmp_path, make_canonical_data_dir, write
):
    data = make_canonical_data_dir(tmp_path / "data")
    pig = _pig_staging()
    pig["proposed_caves"][0]["object_ids"] = []
    before = _tree_snapshot(data)
    result = apply_review_decisions(
        {
            "decisions": [
                {"action": "create_cave", "source": "PIG", "record_number": 1},
                {"action": "create_object", "source": "PIG", "record_number": 1},
                {"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"},
            ]
        },
        staging_reports=StagingReports(pig=pig),
        data_dir=data,
        write=write,
    )
    assert result.has_errors and result.written_paths == ()
    assert any("OBJECT_CAVE_MEMBERSHIP_MISSING" in i.description for i in result.issues)
    assert _tree_snapshot(data) == before


@pytest.mark.parametrize("canonical", [False, True], ids=["legacy", "canonical"])
@pytest.mark.parametrize("write", [False, True], ids=["dry-run", "write"])
def test_all_actions_use_source_proposal_and_existing_connection_for_declarations(
    tmp_path, monkeypatch, canonical, write
):
    from contextlib import contextmanager

    from gps_kataster_obiektow_tatr import postgres, staging_review
    from gps_kataster_obiektow_tatr.catalog_records import SourceDataset

    data = _source_review_data(tmp_path / "data", canonical=canonical)
    path = data / "objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(path.read_text())
    obj["best_measurement"].update(
        mode="manual", measurement_id="m-001", reason="Keep field choice"
    )
    m = obj["measurements"][0]
    m.update(input_srid=2180, input_x=562729.5, input_y=152838.5)
    for key in ("lat", "lon", "x_1992", "y_1992"):
        m.pop(key, None)
    m.pop("vertical_accuracy_m")
    m["elevation_m"] = None
    _write_yaml(path, obj)
    history = history_cli_args(data)
    before = _tree_snapshot(data)
    pig = _pig_staging()
    pig["proposed_caves"][0].update(id="C-0002", object_ids=["KSW-0003"])
    pig["proposed_objects"][0].update(id="KSW-0003", cave_id="C-0002")
    pig["rows"][0].update(cave_id="C-0002", object_id="KSW-0003")
    opened, declaration_connections = [], []
    open_rows, open_source = postgres._open_rows, postgres.open_source_proposal
    coordinates = staging_review.validate_coordinate_declarations

    @contextmanager
    def counted(*args, **kwargs):
        with open_rows(*args, **kwargs) as catalog:
            opened.append(catalog.connection)
            yield catalog

    @contextmanager
    def source_only(proposal, **kwargs):
        assert isinstance(proposal, SourceDataset)
        for record in proposal.caves:
            assert "object_ids" not in record.data
        for record in proposal.objects:
            assert "computed_best_measurement_id" not in record.data
            if record.data["best_measurement"]["mode"] == "auto":
                assert "measurement_id" not in record.data["best_measurement"]
            for measurement in record.data["measurements"]:
                assert not {"x_1992", "y_1992"} & measurement.keys()
                if "input_srid" in measurement:
                    assert not {"lat", "lon"} & measurement.keys()
        with open_source(proposal, **kwargs) as catalog:
            yield catalog

    def check_coordinates(records, connection):
        declaration_connections.append(connection)
        return coordinates(records, connection)

    monkeypatch.setattr(postgres, "_open_rows", counted)
    monkeypatch.setattr(postgres, "open_source_proposal", source_only)
    monkeypatch.setattr(staging_review, "validate_coordinate_declarations", check_coordinates)
    result = apply_review_decisions(
        {
            "reviewed_at": "2026-11-05T18:00:00Z",
            "decisions": [
                {"action": "create_cave", "source": "PIG", "record_number": 1},
                {"action": "create_object", "source": "PIG", "record_number": 1},
                {"action": "add_measurement", "source": "TPN", "record_number": 1},
                {"action": "link_cave", "object_id": "KSW-0003", "cave_id": "C-0001"},
            ],
        },
        staging_reports=StagingReports(pig=pig, tpn=_tpn_staging()),
        data_dir=data,
        write=write,
        base_ref=history[3],
        repo_root=Path(history[1]),
    )
    assert not result.has_errors, result.issues
    assert len(result.applied_decisions) == 4
    assert len(opened) == 2 and all(c.closed for c in opened)
    assert declaration_connections == [opened[0], opened[0]]
    if not write:
        assert result.written_paths == () and _tree_snapshot(data) == before
        return
    written = yaml.safe_load(path.read_text())
    assert written["best_measurement"] == obj["best_measurement"]
    assert written["measurements"][0] == m
    assert [m["id"] for m in written["measurements"]] == ["m-001", "m-002"]
    new = yaml.safe_load((data / "objects/KSW/KSW-0003.yml").read_text())
    assert new["membership_ordinal"] == (8 if canonical else 3)
    assert "Imported from PIG source record after operator review." in new["notes"]


@pytest.mark.parametrize("write", [False, True], ids=["dry-run", "write"])
@pytest.mark.parametrize("damage", ["coordinates", "measurement", "object_refs", "cave_refs"])
def test_staging_diagnostics_keep_existing_yaml_suffix(tmp_path, write, damage):
    data = _source_review_data(tmp_path / "data", canonical=True)
    for name in ("objects/KSW/KSW-0001", "caves/C-0001"):
        (data / f"{name}.yml").rename(data / f"{name}.yaml")
    tpn = _tpn_staging()
    update = tpn["matched_measurements"][0]
    if damage == "coordinates":
        update["measurement"]["x_1992"] += 1000
    elif damage == "measurement":
        update["measurement"]["lat"] = "bad"
    else:
        update["cave_external_refs" if damage == "cave_refs" else "object_external_refs"] = [None]
    expected = data / (
        "caves/C-0001.yaml" if damage == "cave_refs" else "objects/KSW/KSW-0001.yaml"
    )
    before = _tree_snapshot(data)
    result = apply_review_decisions(
        {"decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}]},
        staging_reports=StagingReports(tpn=tpn),
        data_dir=data,
        write=write,
    )
    assert result.has_errors and result.written_paths == ()
    assert any(str(expected) in i.description for i in result.issues), result.issues
    assert _tree_snapshot(data) == before


@pytest.mark.parametrize("write", [False, True], ids=["dry-run", "write"])
@pytest.mark.parametrize("action", ["create_object", "add_measurement"])
def test_declared_coordinate_sql_failure_is_reported_without_poisoning_input(
    tmp_path, monkeypatch, write, action
):
    from gps_kataster_obiektow_tatr import staging_review

    data = _source_review_data(tmp_path / "data", canonical=True)
    if action == "create_object":
        pig = _pig_staging()
        pig["proposed_objects"][0]["id"] = "KSW-0003"
        pig["rows"][0]["object_id"] = "KSW-0003"
        m = pig["proposed_objects"][0]["measurements"][0]
        reports, source, oid = StagingReports(pig=pig), "PIG", "KSW-0003"
    else:
        tpn = _tpn_staging()
        m = tpn["matched_measurements"][0]["measurement"]
        reports, source, oid = StagingReports(tpn=tpn), "TPN", "KSW-0001"
    m.update(lat=0, lon=109)
    original = staging_review.validate_coordinate_declarations
    checked = []

    def check_connection(records, connection):
        result = original(records, connection)
        checked.append(connection.execute("SELECT 1 AS usable").fetchone()["usable"])
        return result

    monkeypatch.setattr(staging_review, "validate_coordinate_declarations", check_connection)
    before = _tree_snapshot(data)
    result = apply_review_decisions(
        {"decisions": [{"action": action, "source": source, "record_number": 1}]},
        staging_reports=reports,
        data_dir=data,
        write=write,
    )
    assert result.has_errors and result.written_paths == ()
    assert checked == [1]
    assert any(
        "SQL_CATALOG_INVALID" in i.description and oid in i.description for i in result.issues
    ), result.issues
    assert _tree_snapshot(data) == before


@pytest.mark.parametrize("history_size", [1, 3])
def test_appended_measurement_diagnostic_keeps_history_index(tmp_path, history_size):
    data = _source_review_data(tmp_path / "data", canonical=True)
    path = data / "objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(path.read_text())
    for number in range(3, history_size + 2):
        obj["measurements"].append(obj["measurements"][0] | {"id": f"m-{number:03d}"})
    _write_yaml(path, obj)
    tpn = _tpn_staging()
    tpn["matched_measurements"][0]["measurement"]["lat"] = "bad"
    result = apply_review_decisions(
        {"decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}]},
        staging_reports=StagingReports(tpn=tpn),
        data_dir=data,
    )
    assert result.has_errors and result.written_paths == ()
    assert any(f"measurements.{history_size}.lat" in i.description for i in result.issues)


def _seed_relink_data(data_dir):
    _seed_review_data(data_dir)
    for object_id in ("KSW-0001", "KSW-0002"):
        path = data_dir / f"objects/KSW/{object_id}.yml"
        obj = _read_yaml(path)
        obj["cave_id"] = "C-0002"
        _write_yaml(path, obj)
    old = _cave_data(object_ids=["KSW-0002", "KSW-0001"])
    old["id"] = "C-0002"
    _write_yaml(data_dir / "caves/C-0002.yaml", old)
    other = _object_data(cave_id="C-0001")
    other["id"] = "KSW-0003"
    _write_yaml(data_dir / "objects/KSW/KSW-0003.yml", other)
    _write_yaml(data_dir / "caves/C-0001.yml", _cave_data(object_ids=["KSW-0003"]))
    assert not has_errors(validate_data_dir(data_dir))


def test_relink_appends_after_explicit_ordinals_without_reindexing(tmp_path, make_data_dir):
    from gps_kataster_obiektow_tatr.catalog_records import write_dataset

    data_dir = make_data_dir(tmp_path / "data")
    _seed_relink_data(data_dir)
    write_dataset(load_yaml_dataset(data_dir), data_dir)
    target_path = data_dir / "objects/KSW/KSW-0003.yml"
    target = yaml.safe_load(target_path.read_text())
    target["membership_ordinal"] = 7
    _write_yaml(target_path, target)
    untouched = target_path.read_bytes()
    result = apply_review_decisions(
        {"decisions": [{"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"}]},
        staging_reports=StagingReports(),
        data_dir=data_dir,
    )
    assert not result.has_errors, result.issues
    moved = yaml.safe_load((data_dir / "objects/KSW/KSW-0001.yml").read_text())
    assert moved["membership_ordinal"] == 8
    assert target_path.read_bytes() == untouched
    assert not has_errors(validate_data_dir(data_dir))


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize("sequence", ["move", "repeat", "round-trip"])
def test_link_cave_preserves_membership_symmetry(tmp_path, make_data_dir, write, sequence):
    data_dir = make_data_dir(tmp_path / "data")
    _seed_relink_data(data_dir)
    from gps_kataster_obiektow_tatr.catalog_records import write_dataset

    write_dataset(load_yaml_dataset(data_dir), data_dir)
    before_records = {r.data["id"]: r.data for r in read_catalog_projection(data_dir).records()}
    before = _tree_snapshot(data_dir)
    targets = ["C-0001"]
    if sequence == "repeat":
        targets.append("C-0001")
    elif sequence == "round-trip":
        targets.extend(["C-0002", "C-0001"])
    decisions = [{"action": "link_cave", "object_id": "KSW-0001", "cave_id": c} for c in targets]
    result = apply_review_decisions(
        {"reviewed_by": "reviewer", "reviewed_at": "2026-10-15T00:00:00Z", "decisions": decisions},
        staging_reports=StagingReports(),
        data_dir=data_dir,
        write=write,
    )
    assert not result.has_errors, result.issues
    if not write:
        assert result.written_paths == ()
        assert _tree_snapshot(data_dir) == before
        return
    object_path = data_dir / "objects/KSW/KSW-0001.yml"
    old_path = data_dir / "caves/C-0002.yaml"
    new_path = data_dir / "caves/C-0001.yml"
    assert set(result.written_paths) == {object_path, old_path, new_path}
    assert _read_yaml(object_path)["cave_id"] == "C-0001"
    assert "object_ids" not in _read_yaml(old_path)
    assert "object_ids" not in _read_yaml(new_path)
    # Compare the database projections as well as the YAML file changes.
    after_records = {r.data["id"]: r.data for r in read_catalog_projection(data_dir).records()}
    for path, field, value in (
        (object_path, "cave_id", "C-0001"),
        (old_path, "object_ids", ["KSW-0002"]),
        (new_path, "object_ids", ["KSW-0003", "KSW-0001"]),
    ):
        expected = deepcopy(before_records[path.stem])
        expected.update(
            {field: value, "updated_by": "reviewer", "updated_at": "2026-10-15T00:00:00Z"}
        )
        assert after_records[path.stem] == expected
    after = _tree_snapshot(data_dir)
    changed = {p for p in before if before[p] != after[p]}
    assert set(after) == set(before)
    assert changed == {p.relative_to(data_dir) for p in (object_path, old_path, new_path)}
    assert not has_errors(validate_data_dir(data_dir))
    # A separate retry also cannot duplicate membership or touch the old cave.
    retry = apply_review_decisions(
        {"decisions": decisions[:1]},
        staging_reports=StagingReports(),
        data_dir=data_dir,
    )
    assert not retry.has_errors
    assert old_path not in retry.written_paths
    assert old_path.read_bytes() == after[old_path.relative_to(data_dir)]
    assert next(
        r.data for r in read_catalog_projection(data_dir).caves if r.data["id"] == "C-0001"
    )["object_ids"] == ["KSW-0003", "KSW-0001"]


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize("old_cave_id", [None, "C-9998"])
def test_link_cave_can_finalize_earlier_object_proposal(
    tmp_path, make_data_dir, write, old_cave_id
):
    data_dir = make_data_dir(tmp_path / "data")
    _seed_relink_data(data_dir)
    pig = _pig_staging()
    pig["proposed_objects"][0].update(id="KSW-0004", cave_id=old_cave_id)
    pig["rows"][0]["object_id"] = "KSW-0004"
    before = _tree_snapshot(data_dir)
    result = apply_review_decisions(
        {
            "decisions": [
                {"action": "create_object", "source": "PIG", "record_number": 1},
                {"action": "link_cave", "object_id": "KSW-0004", "cave_id": "C-0001"},
            ]
        },
        staging_reports=StagingReports(pig=pig),
        data_dir=data_dir,
        write=write,
    )
    assert not result.has_errors, result.issues
    if write:
        assert _read_yaml(data_dir / "objects/KSW/KSW-0004.yml")["cave_id"] == "C-0001"
        assert next(
            r.data for r in read_catalog_projection(data_dir).caves if r.data["id"] == "C-0001"
        )["object_ids"] == ["KSW-0003", "KSW-0004"]
        assert not has_errors(validate_data_dir(data_dir))
    else:
        assert result.written_paths == ()
        assert _tree_snapshot(data_dir) == before


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize(
    "failure", ["missing-cave", "missing-object", "last-decision", "asymmetric-input"]
)
def test_link_cave_error_blocks_entire_batch(tmp_path, make_data_dir, write, failure):
    data_dir = make_data_dir(tmp_path / "data")
    _seed_relink_data(data_dir)
    decisions = [{"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"}]
    if failure == "missing-cave":
        decisions[0]["cave_id"] = "C-9999"
    elif failure == "missing-object":
        decisions[0]["object_id"] = "KSW-9999"
    elif failure == "last-decision":
        decisions.append({"action": "link_cave", "object_id": "KSW-0002", "cave_id": "C-9999"})
    else:
        path = data_dir / "caves/C-0002.yaml"
        cave = _read_yaml(path)
        cave["object_ids"].remove("KSW-0001")
        _write_yaml(path, cave)
    before = _tree_snapshot(data_dir)
    result = apply_review_decisions(
        {"decisions": decisions},
        staging_reports=StagingReports(),
        data_dir=data_dir,
        write=write,
    )
    assert result.has_errors
    assert result.written_paths == ()
    assert _tree_snapshot(data_dir) == before
    if failure == "asymmetric-input":
        assert any("OBJECT_CAVE_MEMBERSHIP_MISSING" in i.description for i in result.issues)


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize("origin", ["existing", "proposal", "added", "earlier-proposal"])
def test_duplicate_local_measurement_id_blocks_review_without_writes(
    tmp_path, make_data_dir, monkeypatch, write, origin
):
    data_dir = make_data_dir(tmp_path / "data")
    _seed_review_data(data_dir)
    path = data_dir / "objects/KSW/KSW-0001.yml"
    staging = StagingReports()
    decisions = [{"action": "link_cave", "object_id": "KSW-0002", "cave_id": "C-0001"}]
    if origin == "existing":
        obj = _read_yaml(path)
        obj["measurements"].append(deepcopy(obj["measurements"][0]))
        _write_yaml(path, obj)
    elif origin == "added":
        tpn = _tpn_staging()
        tpn["matched_measurements"][0]["measurement"]["id"] = "m-001"
        staging = StagingReports(tpn=tpn)
        decisions.append({"action": "add_measurement", "source": "TPN", "record_number": 1})
    else:
        pig = _pig_staging()
        obj = pig["proposed_objects"][0]
        obj["id"] = "KSW-0003"
        pig["rows"][0]["object_id"] = "KSW-0003"
        obj["measurements"].append(deepcopy(obj["measurements"][0]))
        staging = StagingReports(pig=pig, tpn=_tpn_staging())
        decisions.append({"action": "create_object", "source": "PIG", "record_number": 1})
        path = data_dir / "objects/KSW/KSW-0003.yml"
        if origin == "earlier-proposal":
            decisions.append(
                {
                    "action": "add_measurement",
                    "source": "TPN",
                    "record_number": 1,
                    "target_object_id": "KSW-0003",
                }
            )
    before = _tree_snapshot(data_dir)
    staging_before = deepcopy(staging)

    def ambiguous_best_used(*args, **kwargs):
        pytest.fail("Review selected best before checking measurement identity")

    monkeypatch.setattr(
        "gps_kataster_obiektow_tatr.staging_review._touch_auto_best_policy_audit",
        ambiguous_best_used,
    )
    result = apply_review_decisions(
        {"decisions": decisions}, staging_reports=staging, data_dir=data_dir, write=write
    )
    assert result.has_errors
    assert result.written_paths == ()
    rule = "MEASUREMENT_ALREADY_EXISTS" if origin == "added" else "DUPLICATE_MEASUREMENT_ID"
    assert any(rule in i.code or rule in i.description for i in result.issues)
    if origin != "added":
        assert any(str(path) in i.description and "m-001" in i.description for i in result.issues)
    assert _tree_snapshot(data_dir) == before
    assert staging == staging_before


def test_review_finalization_keeps_tpn_context_and_manual_notes(tmp_path, make_data_dir):
    data_dir = make_data_dir(tmp_path / "data")
    _seed_review_data(data_dir)
    staging = _tpn_staging()
    notes = (
        "TPN source-record measurement imported into staging; not field-verified."
        "\nRęczna uwaga.\nTPN WER_LOK: niepewna\nTPN UWAGI: Trzeba uściślić położenie"
    )
    staging["matched_measurements"][0]["measurement"]["notes"] = notes
    before = deepcopy(staging)
    result = apply_review_decisions(
        {"decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}]},
        staging_reports=StagingReports(tpn=staging),
        data_dir=data_dir,
    )
    assert not result.has_errors
    obj = _read_yaml(data_dir / "objects/KSW/KSW-0001.yml")
    assert obj["measurements"][-1]["notes"] == notes.replace(
        "imported into staging", "imported after operator review", 1
    )
    assert obj["measurements"][-1]["verification_status"] == "nieweryfikowany"
    assert staging == before


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize(
    ("damage", "rule"),
    [
        ("coordinates", "COORDINATE_MISMATCH"),
        ("object-schema", "SCHEMA_VALIDATION"),
        ("cave-schema", "SCHEMA_VALIDATION"),
        ("relation", "RELATION_OBJECT_REFERENCE_MISSING"),
        ("relation-schema", "SCHEMA_VALIDATION"),
        ("cave", "CAVE_OBJECT_MEMBERSHIP_MISMATCH"),
        ("duplicate", "DUPLICATE_OBJECT_ID"),
        ("path", "FILE_ID_MISMATCH"),
    ],
)
def test_invalid_existing_dataset_blocks_review_before_decisions(
    tmp_path, make_data_dir, write, damage, rule
):
    data_dir = make_data_dir(tmp_path / "data")
    _seed_review_data(data_dir)
    path = data_dir / "objects/KSW/KSW-0001.yml"
    obj = _read_yaml(path)
    if damage == "coordinates":
        obj["measurements"][0]["lat"] = 0
    elif damage == "object-schema":
        obj["measurements"] = None
    elif damage.startswith("relation"):
        path = data_dir / "relations/R-0001.yml"
        obj = _read_yaml(path)
        obj["to_object_id"] = "KSW-9999" if damage == "relation" else []
    elif damage == "cave-schema":
        path = data_dir / "caves/C-0001.yml"
        obj = _read_yaml(path)
        obj["object_ids"] = None
    elif damage == "cave":
        obj["cave_id"] = "C-9999"
    elif damage == "duplicate":
        path = data_dir / "objects/KSW/copy.yml"
    elif damage == "path":
        path.rename(data_dir / "objects/KSW/wrong.yml")
        path = data_dir / "objects/KSW/wrong.yml"
    _write_yaml(path, obj)
    before = _tree_snapshot(data_dir)
    result = apply_review_decisions(
        {"decisions": [{"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"}]},
        staging_reports=StagingReports(),
        data_dir=data_dir,
        write=write,
    )
    assert result.has_errors
    assert result.written_paths == ()
    assert result.applied_decisions == ()
    expected_path = data_dir / "caves/C-0001.yml" if damage == "cave" else path
    assert any(
        rule in issue.description and str(expected_path) in issue.description
        for issue in result.issues
    )
    assert _tree_snapshot(data_dir) == before


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize(
    ("damage", "rule"),
    [
        ("r3", "COORDINATE_MISMATCH"),
        ("schema", "SCHEMA_VALIDATION"),
        ("missing-measurement", "STAGING_MEASUREMENT_INVALID"),
        ("missing-object", "TARGET_OBJECT_MISSING"),
        ("missing-cave", "TARGET_CAVE_MISSING"),
        ("globalid", "DUPLICATE_TPN_GLOBALID"),
        ("cave-payload", "SCHEMA_VALIDATION"),
        ("last-decision", "DECISION_ACTION_INVALID"),
    ],
)
def test_invalid_last_update_blocks_entire_review_batch(
    tmp_path, make_data_dir, write, damage, rule
):
    data_dir = make_data_dir(tmp_path / "data")
    _seed_review_data(data_dir)
    staging = _tpn_staging()
    update = staging["matched_measurements"][0]
    measurement = update["measurement"]
    decision_data = {
        "reviewed_at": "2026-10-15T00:00:00Z",
        "reviewed_by": "dl",
        "decisions": [
            {"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"},
            {"action": "add_measurement", "source": "TPN", "record_number": 1},
        ],
    }
    if damage == "r3":
        measurement["lat"] = 0
    elif damage == "schema":
        measurement["lat"] = "broken"
    elif damage == "missing-measurement":
        update["measurement"] = None
    elif damage == "missing-object":
        update["target_object_id"] = "KSW-9999"
    elif damage == "missing-cave":
        update["target_cave_id"] = "C-9999"
    elif damage == "globalid":
        other_path = data_dir / "objects/KSW/KSW-0002.yml"
        other = _read_yaml(other_path)
        other["external_refs"] = deepcopy(update["object_external_refs"])
        _write_yaml(other_path, other)
    elif damage == "cave-payload":
        update["cave_external_refs"][0]["scope"] = "invalid"
    elif damage == "last-decision":
        decision_data["decisions"].append({"action": "unknown"})
    before = _tree_snapshot(data_dir)
    input_before = deepcopy((decision_data, staging))
    result = apply_review_decisions(
        decision_data,
        staging_reports=StagingReports(tpn=staging),
        data_dir=data_dir,
        write=write,
    )
    assert result.has_errors
    assert result.written_paths == ()
    assert any(rule in (issue.code + issue.description) for issue in result.issues)
    if damage == "r3":
        assert any("MEASUREMENT_OUTSIDE_PL_SK" in issue.description for issue in result.issues)
    assert _tree_snapshot(data_dir) == before
    assert (decision_data, staging) == input_before


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize("damage", ["object", "cave", "missing-cave"])
def test_invalid_new_proposal_blocks_earlier_create(tmp_path, make_data_dir, write, damage):
    data_dir = make_data_dir(tmp_path / "data")
    staging = _pig_staging()
    if damage == "object":
        staging["proposed_objects"][0]["measurements"] = None
    elif damage == "cave":
        staging["proposed_caves"][0]["name"] = None
    else:
        staging["proposed_objects"][0]["cave_id"] = "C-9999"
    before = _tree_snapshot(data_dir)
    result = apply_review_decisions(
        {
            "decisions": [
                {"action": "create_cave", "source": "PIG", "record_number": 1},
                {"action": "create_object", "source": "PIG", "record_number": 1},
            ]
        },
        staging_reports=StagingReports(pig=staging),
        data_dir=data_dir,
        write=write,
    )
    assert result.has_errors
    assert result.written_paths == ()
    assert _tree_snapshot(data_dir) == before


def test_valid_review_dry_run_matches_write_and_preserves_unmodified_records(
    tmp_path, make_data_dir
):
    from gps_kataster_obiektow_tatr.catalog_records import write_dataset

    data_dir = make_data_dir(tmp_path / "data")
    _seed_review_data(data_dir)
    write_dataset(load_yaml_dataset(data_dir), data_dir)
    before_records = {r.data["id"]: r.data for r in read_catalog_projection(data_dir).records()}
    before = _tree_snapshot(data_dir)
    staging = StagingReports(tpn=_tpn_staging())
    decisions = {
        "reviewed_at": "2026-10-15T00:00:00Z",
        "decisions": [
            {"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"},
            {"action": "add_measurement", "source": "TPN", "record_number": 1},
        ],
    }
    dry = apply_review_decisions(decisions, staging_reports=staging, data_dir=data_dir, write=False)
    assert not dry.has_errors
    assert dry.written_paths == ()
    assert _tree_snapshot(data_dir) == before
    written = apply_review_decisions(decisions, staging_reports=staging, data_dir=data_dir)
    assert not written.has_errors
    assert written.issues == dry.issues
    assert written.applied_decisions == dry.applied_decisions
    assert written.written_paths == (
        data_dir / "caves/C-0001.yml",
        data_dir / "objects/KSW/KSW-0001.yml",
    )
    assert not has_errors(validate_data_dir(data_dir))
    after_records = {r.data["id"]: r.data for r in read_catalog_projection(data_dir).records()}
    assert after_records["R-0001"] == before_records["R-0001"]
    assert after_records["KSW-0002"] == before_records["KSW-0002"]
    obj = after_records["KSW-0001"]
    assert [m["id"] for m in obj["measurements"]] == ["m-001", "m-002"]
    assert obj["best_measurement"]["measurement_id"] == "m-002"


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize("damage", ["measurements", "external_refs", "object_ids", "cave_id"])
def test_malformed_created_record_used_by_later_decision_returns_report(
    tmp_path, make_data_dir, write, damage
):
    data_dir = make_data_dir(tmp_path / "data")
    staging = _pig_staging()
    key = "proposed_caves" if damage == "object_ids" else "proposed_objects"
    staging[key][0][damage] = {} if damage == "cave_id" else None
    before = _tree_snapshot(data_dir)
    result = apply_review_decisions(
        {
            "decisions": [
                {"action": "create_cave", "source": "PIG", "record_number": 1},
                {"action": "create_object", "source": "PIG", "record_number": 1},
                {"action": "add_measurement", "source": "TPN", "record_number": 1},
                {"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"},
            ]
        },
        staging_reports=StagingReports(pig=staging, tpn=_tpn_staging()),
        data_dir=data_dir,
        write=write,
    )
    assert result.has_errors
    assert result.written_paths == ()
    assert any("SCHEMA_VALIDATION" in issue.description for issue in result.issues)
    assert _tree_snapshot(data_dir) == before


@pytest.mark.parametrize("dry_run", [False, True])
def test_r3_review_cli_reports_error_without_final_writes(tmp_path, make_data_dir, dry_run):
    data_dir = make_data_dir(tmp_path / "data")
    _seed_review_data(data_dir)
    staging = _tpn_staging()
    staging["matched_measurements"][0]["measurement"]["lat"] = 0
    _write_json(tmp_path / "tpn.json", staging)
    _write_yaml(
        tmp_path / "decisions.yml",
        {"decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}]},
    )
    before = _tree_snapshot(data_dir)
    command = [
        sys.executable,
        str(APPLY_REVIEW_PATH),
        "--decisions",
        str(tmp_path / "decisions.yml"),
        "--data-dir",
        str(data_dir),
        "--no-pig-staging",
        "--tpn-staging",
        str(tmp_path / "tpn.json"),
        "--output-dir",
        str(tmp_path / "review"),
    ]
    if dry_run:
        command.append("--dry-run")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert "COORDINATE_MISMATCH" in result.stderr
    assert str(data_dir / "objects/KSW/KSW-0001.yml") in result.stderr
    assert "Traceback" not in result.stderr
    report = json.loads((tmp_path / "review/staging-review.json").read_text())
    assert report["has_errors"] is True
    assert report["written_paths"] == []
    assert _tree_snapshot(data_dir) == before


def test_review_adopts_legacy_yaml_without_renaming_sources(tmp_path, make_data_dir):
    data_dir = make_data_dir(tmp_path / "data")
    _seed_review_data(data_dir)
    for name in ("objects/KSW/KSW-0001", "caves/C-0001"):
        (data_dir / f"{name}.yml").rename(data_dir / f"{name}.yaml")
    result = apply_review_decisions(
        {"decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}]},
        staging_reports=StagingReports(tpn=_tpn_staging()),
        data_dir=data_dir,
    )
    assert not result.has_errors
    preserved = {data_dir / f"{name}.yaml" for name in ("objects/KSW/KSW-0001", "caves/C-0001")}
    assert preserved <= set(result.written_paths)
    assert all(p.is_file() and not p.with_suffix(".yml").exists() for p in preserved)
    assert not has_errors(validate_data_dir(data_dir))


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize("field", ["object_external_refs", "cave_external_refs"])
@pytest.mark.parametrize("payload", [{"system": "TPN"}, [None], None])
def test_malformed_selected_references_are_not_silently_dropped(
    tmp_path, make_data_dir, write, field, payload
):
    data_dir = make_data_dir(tmp_path / "data")
    _seed_review_data(data_dir)
    staging = _tpn_staging()
    staging["matched_measurements"][0][field] = payload
    before = _tree_snapshot(data_dir)
    result = apply_review_decisions(
        {"decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}]},
        staging_reports=StagingReports(tpn=staging),
        data_dir=data_dir,
        write=write,
    )
    assert result.has_errors
    assert result.written_paths == ()
    assert any(field in issue.description for issue in result.issues)
    assert _tree_snapshot(data_dir) == before


@pytest.mark.parametrize("write", [False, True])
def test_unhashable_reference_type_in_selected_payload_returns_schema_report(
    tmp_path, make_data_dir, write
):
    data_dir = make_data_dir(tmp_path / "data")
    _seed_review_data(data_dir)
    staging = _tpn_staging()
    staging["matched_measurements"][0]["object_external_refs"] = [
        {"system": "PIG", "ref_type": [], "external_id": "test"}
    ]
    before = _tree_snapshot(data_dir)
    result = apply_review_decisions(
        {"decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}]},
        staging_reports=StagingReports(tpn=staging),
        data_dir=data_dir,
        write=write,
    )
    assert result.has_errors
    assert result.written_paths == ()
    assert any("SCHEMA_VALIDATION" in issue.description for issue in result.issues)
    assert _tree_snapshot(data_dir) == before


@pytest.mark.parametrize("write", [False, True])
def test_malformed_duplicate_reference_is_validated_before_deduplication(
    tmp_path, make_data_dir, write
):
    data_dir = make_data_dir(tmp_path / "data")
    _seed_review_data(data_dir)
    staging = _tpn_staging()
    update = staging["matched_measurements"][0]
    path = data_dir / "objects/KSW/KSW-0001.yml"
    obj = _read_yaml(path)
    obj["external_refs"] = deepcopy(update["object_external_refs"])
    _write_yaml(path, obj)
    update["object_external_refs"][0]["scope"] = "invalid"
    before = _tree_snapshot(data_dir)
    result = apply_review_decisions(
        {"decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}]},
        staging_reports=StagingReports(tpn=staging),
        data_dir=data_dir,
        write=write,
    )
    assert result.has_errors
    assert result.written_paths == ()
    assert any("SCHEMA_VALIDATION" in issue.description for issue in result.issues)
    assert _tree_snapshot(data_dir) == before


def test_duplicate_cave_id_is_preserved_for_report_and_blocks_review(tmp_path, make_data_dir):
    data_dir = make_data_dir(tmp_path / "data")
    _seed_review_data(data_dir)
    extra = _cave_data(object_ids=["KSW-0001", "KSW-0002"])
    extra["name"] = "Separate source file"
    extra_path = data_dir / "caves/C-0001.yaml"
    _write_yaml(extra_path, extra)
    assert has_errors(validate_data_dir(data_dir))
    dataset = load_yaml_dataset(data_dir)
    objects = {r.data["id"]: deepcopy(r.raw_data) for r in dataset.objects}
    caves = {r.data["id"]: deepcopy(r.raw_data) for r in dataset.caves}
    caves["C-0001"]["notes"] = "review update"
    prospective = _dataset_with_review_changes(
        dataset, data_dir=data_dir, objects=objects, caves=caves
    )
    assert len(prospective.caves) == 2
    assert {r.path for r in prospective.records()} == {r.path for r in dataset.records()}
    assert next(r.raw_data for r in prospective.caves if r.path == extra_path) == extra
    canonical = next(r.raw_data for r in prospective.caves if r.path.suffix == ".yml")
    assert canonical["notes"] == "review update"
    before = _tree_snapshot(data_dir)
    result = apply_review_decisions(
        {"decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}]},
        staging_reports=StagingReports(tpn=_tpn_staging()),
        data_dir=data_dir,
    )
    assert result.has_errors
    assert result.written_paths == ()
    assert extra_path not in result.written_paths
    assert _tree_snapshot(data_dir)[Path("caves/C-0001.yaml")] == before[Path("caves/C-0001.yaml")]
    assert has_errors(validate_data_dir(data_dir))
    assert _tree_snapshot(data_dir) == before


def test_apply_review_directly_materializes_pig_and_tpn_decisions(
    tmp_path: Path, make_data_dir
) -> None:
    data_dir = make_data_dir(tmp_path / "data")

    result = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:00:00Z",
            "reviewed_by": "dl",
            "decisions": [
                {"action": "create_cave", "source": "PIG", "record_number": 1},
                {"action": "create_object", "source": "PIG", "record_number": 1},
                {"action": "add_measurement", "source": "TPN", "record_number": 1},
            ],
        },
        staging_reports=StagingReports(pig=_pig_staging(), tpn=_tpn_staging()),
        data_dir=data_dir,
    )

    object_path = data_dir / "objects" / "KSW" / "KSW-0001.yml"
    cave_path = data_dir / "caves" / "C-0001.yml"
    dataset = read_catalog_projection(data_dir)
    object_data = dataset.objects[0].data
    cave_data = dataset.caves[0].data

    assert result.has_errors is False
    assert result.written_paths == (cave_path.with_suffix(".yml"), object_path.with_suffix(".yml"))
    assert [decision.status for decision in result.applied_decisions] == [
        "materialized",
        "materialized",
        "materialized",
    ]
    assert [measurement["id"] for measurement in object_data["measurements"]] == [
        "m-001",
        "m-002",
    ]
    assert object_data["best_measurement"] == {
        "mode": "auto",
        "measurement_id": "m-002",
        "reason": None,
        "updated_at": "2026-05-16T10:00:00Z",
        "updated_by": "dl",
    }
    assert object_data["measurements"][0]["tags"] == ["pig"]
    assert object_data["measurements"][1]["tags"] == ["tpn"]
    assert object_data["external_refs"] == [
        {
            "system": "TPN",
            "ref_type": "source_globalid",
            "external_id": TPN_GLOBALID,
            "scope": "object",
            "notes": "TPN GLOBALID belongs to the object/source feature.",
        }
    ]
    assert cave_data["external_refs"] == [
        _nr_inwent_ref(),
        {
            "system": "PIG",
            "ref_type": "catalog_id",
            "external_id": "1692",
            "url": "https://jaskiniepolski.pgi.gov.pl/Details/Information/1692",
            "scope": "cave",
            "notes": "PIG catalog record identifier.",
        },
    ]


def test_write_review_report_files_serializes_decisions_issues_and_paths(
    tmp_path: Path, make_data_dir
) -> None:
    result = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:15:00Z",
            "reviewed_by": "dl",
            "decisions": [
                {"action": "unresolved", "source": "TPN", "record_number": 3},
            ],
        },
        staging_reports=StagingReports(tpn=_tpn_review_only_staging()),
        data_dir=make_data_dir(tmp_path / "data"),
        write=False,
    )

    json_path, markdown_path = write_review_report_files(result, output_dir=tmp_path / "review")
    json_data = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")

    assert json_data["has_errors"] is False
    assert json_data["decision_count"] == 1
    assert json_data["issue_count"] == 1
    assert json_data["decisions"][0]["description"] == "No reason provided."
    assert json_data["issues"][0]["code"] == "DECISION_REASON_MISSING"
    assert "| `warning` | `DECISION_REASON_MISSING` |" in markdown
    assert "No reason provided." in markdown


def test_load_review_decisions_rejects_invalid_yaml_and_non_mapping(tmp_path: Path) -> None:
    invalid_yaml = tmp_path / "invalid.yml"
    invalid_yaml.write_text("decisions: [\n", encoding="utf-8")
    non_mapping = tmp_path / "non-mapping.yml"
    non_mapping.write_text("- action: reject\n", encoding="utf-8")

    with pytest.raises(ReviewDecisionError, match="invalid YAML"):
        load_review_decisions(invalid_yaml)
    with pytest.raises(ReviewDecisionError, match="decision file must be a mapping"):
        load_review_decisions(non_mapping)


def test_load_review_decisions_rejects_yaml_key_collisions(tmp_path, yaml_key_collision):
    content, key, line = yaml_key_collision
    path = tmp_path / "decisions.yml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ReviewDecisionError) as error:
        load_review_decisions(path)
    message = str(error.value)
    assert str(path) in message
    assert "duplicate key" in message
    assert key in message
    assert f"line {line}, column" in message
    assert path.read_bytes() == content.encode("utf-8")


def test_review_aliases_and_disjoint_merges_keep_decisions_and_order(tmp_path):
    path = tmp_path / "decisions.yml"
    content = """\
reviewed_by: dl
decisions:
  - &decision {action: unresolved, source: TPN, record_number: 2}
  - *decision
  - <<: [{action: reject}, {source: PIG}]
    record_number: 1
"""
    path.write_text(content, encoding="utf-8")
    assert load_review_decisions(path) == {
        "reviewed_by": "dl",
        "decisions": [
            {"action": "unresolved", "source": "TPN", "record_number": 2},
            {"action": "unresolved", "source": "TPN", "record_number": 2},
            {"action": "reject", "source": "PIG", "record_number": 1},
        ],
    }
    assert path.read_bytes() == content.encode("utf-8")


@pytest.mark.parametrize("bad_input", ["decision", "record"])
@pytest.mark.parametrize("dry_run", [False, True])
def test_duplicate_yaml_blocks_review_cli_writes(tmp_path, make_data_dir, bad_input, dry_run):
    data_dir = make_data_dir(tmp_path / "data")
    object_path = data_dir / "objects" / "KSW" / "KSW-0001.yml"
    _write_yaml(object_path, _object_data(cave_id="C-0001"))
    _write_yaml(data_dir / "caves" / "C-0001.yml", _cave_data(object_ids=["KSW-0001"]))
    decisions = tmp_path / "decisions.yml"
    content = "decisions: [{action: link_cave, object_id: KSW-0001, cave_id: C-0001}]\n"
    if bad_input == "decision":
        content += "decisions: []\n"
        bad_path, key = decisions, "decisions"
    else:
        object_path.write_text(
            object_path.read_text(encoding="utf-8") + "measurements: []\n", encoding="utf-8"
        )
        bad_path, key = object_path, "measurements"
    decisions.write_text(content, encoding="utf-8")
    before = {p.relative_to(data_dir): p.read_bytes() for p in data_dir.rglob("*") if p.is_file()}
    output = tmp_path / "review"
    output.mkdir()
    (output / "staging-review.json").write_bytes(b"existing report")
    command = [
        sys.executable,
        str(APPLY_REVIEW_PATH),
        "--decisions",
        str(decisions),
        "--data-dir",
        str(data_dir),
        "--no-pig-staging",
        "--no-tpn-staging",
        "--output-dir",
        str(output),
    ]
    if dry_run:
        command.append("--dry-run")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 1
    message = result.stdout + result.stderr
    assert str(bad_path) in message
    assert "duplicate key" in message
    assert key in message
    assert "Traceback" not in message
    assert {
        p.relative_to(data_dir): p.read_bytes() for p in data_dir.rglob("*") if p.is_file()
    } == before
    if bad_input == "decision":
        assert (output / "staging-review.json").read_bytes() == b"existing report"
        assert not (output / "staging-review.md").exists()


@pytest.mark.parametrize("content", ["? [not, a, scalar]\n: value\n", "!!python/tuple [1, 2]\n"])
def test_review_loader_keeps_safe_yaml_errors(tmp_path, content):
    path = tmp_path / "decisions.yml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ReviewDecisionError, match="invalid YAML") as error:
        load_review_decisions(path)
    assert str(path) in str(error.value)


def test_load_staging_reports_handles_missing_paths_and_rejects_non_objects(
    tmp_path: Path,
) -> None:
    bad_json = tmp_path / "bad-staging.json"
    bad_json.write_text("[]\n", encoding="utf-8")

    assert load_staging_reports(pig_staging_path=None, tpn_staging_path=tmp_path / "missing") == (
        StagingReports()
    )
    with pytest.raises(ReviewDecisionError, match="staging report must be a JSON object"):
        load_staging_reports(pig_staging_path=bad_json, tpn_staging_path=None)


def test_cli_applies_sample_decisions_and_final_yaml_passes_validate_py(
    tmp_path: Path,
    make_data_dir,
) -> None:
    pig_staging_path = tmp_path / "pig-staging.json"
    tpn_staging_path = tmp_path / "tpn-staging.json"
    decisions_path = tmp_path / "decisions.yml"
    data_dir = make_data_dir(tmp_path / "data")
    review_dir = tmp_path / "build" / "review"
    _write_json(pig_staging_path, _pig_staging())
    _write_json(tpn_staging_path, _tpn_staging())
    _write_yaml(
        decisions_path,
        {
            "reviewed_at": "2026-05-16T10:00:00Z",
            "reviewed_by": "dl",
            "decisions": [
                {"action": "create_cave", "source": "PIG", "record_number": 1},
                {"action": "create_object", "source": "PIG", "record_number": 1},
                {"action": "add_measurement", "source": "TPN", "record_number": 1},
            ],
        },
    )

    result = subprocess.run(
        [
            sys.executable,
            str(APPLY_REVIEW_PATH),
            *history_cli_args(data_dir),
            "--decisions",
            str(decisions_path),
            "--data-dir",
            str(data_dir),
            "--pig-staging",
            str(pig_staging_path),
            "--tpn-staging",
            str(tpn_staging_path),
            "--output-dir",
            str(review_dir),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    validation = subprocess.run(
        [
            sys.executable,
            str(VALIDATE_SCRIPT),
            "--data-dir",
            str(data_dir),
            *history_cli_args(data_dir),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    dataset = read_catalog_projection(data_dir)
    object_data = dataset.objects[0].data
    cave_data = dataset.caves[0].data
    report = json.loads((review_dir / "staging-review.json").read_text(encoding="utf-8"))

    assert "staging review: 3 decisions, 2 final YAML files" in result.stdout
    assert validation.returncode == 0, validation.stdout + validation.stderr
    assert [measurement["id"] for measurement in object_data["measurements"]] == [
        "m-001",
        "m-002",
    ]
    assert object_data["notes"] == "Imported from PIG source record after operator review."
    assert object_data["measurements"][0]["tags"] == ["pig"]
    assert (
        object_data["measurements"][0]["notes"]
        == "PIG source-record measurement imported after operator review; not field-verified."
    )
    assert object_data["measurements"][1]["tags"] == ["tpn"]
    assert (
        object_data["measurements"][1]["notes"]
        == "TPN source-record measurement imported after operator review; not field-verified."
    )
    assert object_data["best_measurement"]["measurement_id"] == "m-002"
    assert object_data["external_refs"][0]["external_id"] == TPN_GLOBALID
    assert cave_data["object_ids"] == ["KSW-0001"]
    assert report["has_errors"] is False
    assert report["decision_count"] == 3


def test_link_reject_and_unresolved_decisions_are_reported(tmp_path: Path, make_data_dir) -> None:
    data_dir = make_data_dir(tmp_path / "data")
    _write_yaml(data_dir / "objects" / "KSW" / "KSW-0001.yml", _object_data(cave_id=None))
    _write_yaml(data_dir / "caves" / "C-0001.yml", _cave_data(object_ids=[]))

    result = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:15:00Z",
            "reviewed_by": "dl",
            "decisions": [
                {"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"},
                {
                    "action": "reject",
                    "source": "TPN",
                    "record_number": 2,
                    "reason": "Duplicated source row.",
                },
                {
                    "action": "unresolved",
                    "source": "TPN",
                    "record_number": 3,
                    "reason": "Needs field review.",
                },
            ],
        },
        staging_reports=StagingReports(tpn=_tpn_review_only_staging()),
        data_dir=data_dir,
    )

    object_data = _read_yaml(data_dir / "objects" / "KSW" / "KSW-0001.yml")
    cave_data = read_catalog_projection(data_dir).caves[0].data
    markdown = render_review_markdown(result)

    assert result.has_errors is False
    assert result.issues == ()
    assert object_data["cave_id"] == "C-0001"
    assert cave_data["object_ids"] == ["KSW-0001"]
    assert [decision.status for decision in result.applied_decisions] == [
        "materialized",
        "skipped",
        "skipped",
    ]
    assert "Duplicated source row." in markdown
    assert "Needs field review." in markdown


def test_invalid_decision_blocks_all_final_yaml_writes(tmp_path: Path, make_data_dir) -> None:
    data_dir = make_data_dir(tmp_path / "data")
    result = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:30:00Z",
            "reviewed_by": "dl",
            "decisions": [
                {"action": "create_cave", "source": "PIG", "record_number": 1},
                {"action": "create_object", "source": "PIG", "record_number": 99},
            ],
        },
        staging_reports=StagingReports(pig=_pig_staging()),
        data_dir=data_dir,
    )

    assert result.has_errors is True
    assert result.written_paths == ()
    assert not (data_dir / "caves" / "C-0001.yml").exists()


def test_invalid_decision_shapes_and_non_materialized_warnings_are_reported(
    tmp_path: Path,
    make_data_dir,
) -> None:
    invalid_list = apply_review_decisions(
        {"reviewed_at": "2026-05-16T10:30:00Z", "reviewed_by": "dl", "decisions": "bad"},
        staging_reports=StagingReports(),
        data_dir=make_data_dir(tmp_path / "data-invalid-list"),
    )
    mixed = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:31:00Z",
            "reviewed_by": "dl",
            "decisions": [
                None,
                {"action": "unknown"},
                {"action": "reject", "source": "bad", "record_number": 0},
                {"action": "reject", "source": "TPN", "record_number": 2},
            ],
        },
        staging_reports=StagingReports(tpn=_tpn_review_only_staging()),
        data_dir=make_data_dir(tmp_path / "data-mixed"),
        write=False,
    )

    assert _issue_codes(invalid_list) == ["DECISIONS_INVALID"]
    assert _issue_codes(mixed) == [
        "DECISION_INVALID",
        "DECISION_ACTION_INVALID",
        "DECISION_SOURCE_INVALID",
        "DECISION_RECORD_INVALID",
        "DECISION_REASON_MISSING",
    ]
    assert mixed.issues[-1].severity == ReviewSeverity.WARNING
    assert mixed.applied_decisions[0].description == "No reason provided."


def test_duplicate_create_decisions_report_existing_final_records(
    tmp_path: Path, make_data_dir
) -> None:
    data_dir = make_data_dir(tmp_path / "data")
    _write_yaml(data_dir / "objects" / "KSW" / "KSW-0001.yml", _object_data(cave_id="C-0001"))
    _write_yaml(data_dir / "caves" / "C-0001.yml", _cave_data(object_ids=["KSW-0001"]))

    result = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:32:00Z",
            "reviewed_by": "dl",
            "decisions": [
                {"action": "create_cave", "source": "PIG", "record_number": 1},
                {"action": "create_object", "source": "PIG", "record_number": 1},
            ],
        },
        staging_reports=StagingReports(pig=_pig_staging()),
        data_dir=data_dir,
        write=False,
    )

    assert _issue_codes(result) == ["CAVE_ALREADY_EXISTS", "OBJECT_ALREADY_EXISTS"]
    assert result.applied_decisions == ()


def test_add_measurement_reports_blocking_edge_cases(tmp_path: Path, make_data_dir) -> None:
    unsupported_source = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:33:00Z",
            "reviewed_by": "dl",
            "decisions": [{"action": "add_measurement", "source": "PIG", "record_number": 1}],
        },
        staging_reports=StagingReports(pig=_pig_staging()),
        data_dir=make_data_dir(tmp_path / "data-unsupported"),
        write=False,
    )
    missing_update = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:34:00Z",
            "reviewed_by": "dl",
            "decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 2}],
        },
        staging_reports=StagingReports(tpn=_tpn_review_only_staging()),
        data_dir=make_data_dir(tmp_path / "data-missing-update"),
        write=False,
    )
    target_missing = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:35:00Z",
            "reviewed_by": "dl",
            "decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}],
        },
        staging_reports=StagingReports(tpn=_tpn_staging()),
        data_dir=make_data_dir(tmp_path / "data-target-missing"),
        write=False,
    )

    invalid_measurement_dir = make_data_dir(tmp_path / "data-invalid-measurement")
    _write_yaml(
        invalid_measurement_dir / "objects" / "KSW" / "KSW-0001.yml",
        _object_data(cave_id="C-0001"),
    )
    _write_yaml(invalid_measurement_dir / "caves/C-0001.yml", _cave_data(object_ids=["KSW-0001"]))
    invalid_tpn = deepcopy(_tpn_staging())
    invalid_tpn["matched_measurements"][0]["measurement"] = None
    invalid_measurement = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:36:00Z",
            "reviewed_by": "dl",
            "decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}],
        },
        staging_reports=StagingReports(tpn=invalid_tpn),
        data_dir=invalid_measurement_dir,
        write=False,
    )

    duplicate_dir = make_data_dir(tmp_path / "data-duplicate-measurement")
    duplicate_object = _object_data(
        cave_id="C-0001", measurement=_measurement("m-002", source="TPN", source_ref="")
    )
    duplicate_object["best_measurement"]["measurement_id"] = "m-002"
    duplicate_object["id_assignment"]["assigned_from_measurement_id"] = "m-002"
    _write_yaml(duplicate_dir / "objects/KSW/KSW-0001.yml", duplicate_object)
    _write_yaml(duplicate_dir / "caves/C-0001.yml", _cave_data(object_ids=["KSW-0001"]))
    duplicate = apply_review_decisions(
        {
            "reviewed_at": "2026-05-16T10:37:00Z",
            "reviewed_by": "dl",
            "decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}],
        },
        staging_reports=StagingReports(tpn=_tpn_staging()),
        data_dir=duplicate_dir,
        write=False,
    )

    assert _issue_codes(unsupported_source) == ["MEASUREMENT_SOURCE_UNSUPPORTED"]
    assert _issue_codes(missing_update) == ["STAGING_MEASUREMENT_UPDATE_MISSING"]
    assert _issue_codes(target_missing) == ["TARGET_OBJECT_MISSING"]
    assert _issue_codes(invalid_measurement) == ["STAGING_MEASUREMENT_INVALID"]
    assert _issue_codes(duplicate) == ["MEASUREMENT_ALREADY_EXISTS"]


def _pig_staging() -> dict[str, Any]:
    cave = _cave_data(
        object_ids=["KSW-0001"],
        external_refs=[
            _nr_inwent_ref(),
            {
                "system": "PIG",
                "ref_type": "catalog_id",
                "external_id": "1692",
                "url": "https://jaskiniepolski.pgi.gov.pl/Details/Information/1692",
                "scope": "cave",
                "notes": "PIG catalog record identifier.",
            },
        ],
        created_by="importer:pig",
    )
    obj = _object_data(
        cave_id="C-0001",
        created_by="importer:pig",
        measurement=_measurement("m-001", source="PIG", source_ref="PIG:1692"),
        notes="Staging proposal from PIG; requires operator review before final YAML.",
    )
    return {
        "generated_at": "2026-05-16T08:00:00Z",
        "rows": [
            {
                "record_number": 1,
                "pig_id": "1692",
                "nr_inwent": "T.F-09.33",
                "name": "Szczelina pod Gankowa II",
                "cave_id": "C-0001",
                "object_id": "KSW-0001",
                "status": "object_proposed",
            }
        ],
        "proposed_caves": [cave],
        "proposed_objects": [obj],
    }


def _tpn_staging() -> dict[str, Any]:
    measurement = _measurement("m-002", source="TPN", source_ref=f"TPN:{TPN_GLOBALID}")
    return {
        "generated_at": "2026-05-16T09:00:00Z",
        "rows": [
            {
                "record_number": 1,
                "globalid": TPN_GLOBALID,
                "nr_inwent": "T.F-09.33",
                "name": "Szczelina pod Gankowa II",
                "status": "matched",
                "cave_id": "C-0001",
                "object_id": "KSW-0001",
                "match_strategy": "nr_inwent",
                "distance_m": 0.0,
            }
        ],
        "matched_measurements": [
            {
                "status": "matched",
                "record_number": 1,
                "target_object_id": "KSW-0001",
                "target_cave_id": "C-0001",
                "object_external_refs": [
                    {
                        "system": "TPN",
                        "ref_type": "source_globalid",
                        "external_id": TPN_GLOBALID,
                        "scope": "object",
                        "notes": "TPN GLOBALID belongs to the object/source feature.",
                    }
                ],
                "cave_external_refs": [_nr_inwent_ref()],
                "measurement": measurement,
            }
        ],
        "proposed_caves": [],
        "proposed_objects": [],
    }


def _tpn_review_only_staging() -> dict[str, Any]:
    return {
        "rows": [
            {"record_number": 2, "status": "rejected"},
            {"record_number": 3, "status": "unresolved"},
        ],
        "matched_measurements": [],
        "proposed_caves": [],
        "proposed_objects": [],
    }


def _object_data(
    *,
    cave_id: str | None,
    created_by: str = "dl",
    measurement: dict[str, Any] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    measurement_data = measurement or _measurement(
        "m-001",
        source="wlasne",
        source_ref="teren:2026-05-15:gps",
        horizontal_accuracy_m=5.0,
    )
    return {
        "schema_version": 1,
        "id": "KSW-0001",
        "category": "jaskinia_otwor",
        "name_local": "Szczelina pod Gankowa II",
        "cave_id": cave_id,
        "id_assignment": {
            "method": "auto",
            "assigned_from_measurement_id": "m-001",
            "assigned_prefix": "KSW",
            "prefix_override_reason": None,
        },
        "external_refs": [],
        "measurements": [measurement_data],
        "best_measurement": {
            "mode": "auto",
            "measurement_id": "m-001",
            "reason": None,
            "updated_at": "2026-05-16T08:00:00Z",
            "updated_by": created_by,
        },
        "attachments": [],
        "notes": notes,
        "created_at": "2026-05-16T08:00:00Z",
        "created_by": created_by,
        "updated_at": "2026-05-16T08:00:00Z",
        "updated_by": created_by,
    }


def _cave_data(
    *,
    object_ids: list[str],
    external_refs: list[dict[str, Any]] | None = None,
    created_by: str = "dl",
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": "C-0001",
        "name": "Szczelina pod Gankowa II",
        "system_name": None,
        "external_refs": external_refs or [],
        "object_ids": object_ids,
        "notes": None,
        "created_at": "2026-05-16T08:00:00Z",
        "created_by": created_by,
        "updated_at": "2026-05-16T08:00:00Z",
        "updated_by": created_by,
    }


def _measurement(
    measurement_id: str,
    *,
    source: str,
    source_ref: str,
    horizontal_accuracy_m: float | None = None,
) -> dict[str, Any]:
    pl_1992 = wgs84_to_1992(lat=KSW_LAT, lon=KSW_LON)
    return {
        "id": measurement_id,
        "lat": KSW_LAT,
        "lon": KSW_LON,
        "x_1992": pl_1992.x_1992,
        "y_1992": pl_1992.y_1992,
        "elevation_m": 1266.0,
        "elevation_datum": "unknown",
        "elevation_source": "source_record" if source in {"PIG", "TPN"} else "gps",
        "horizontal_accuracy_m": horizontal_accuracy_m,
        "vertical_accuracy_m": None,
        "source": source,
        "source_ref": source_ref,
        "observed_date": "2026-05-16",
        "source_date": "2026-05-16",
        "method": "source_record" if source in {"PIG", "TPN"} else "gps_receiver",
        "device": None,
        "tags": [source.lower(), "staging"] if source in {"PIG", "TPN"} else [source.lower()],
        "verification_status": "nieweryfikowany",
        "verified_by": None,
        "verified_at": None,
        "notes": (
            f"{source} source-record measurement imported into staging; not field-verified."
            if source in {"PIG", "TPN"}
            else f"{source} review fixture measurement."
        ),
        "created_at": "2026-05-16T08:00:00Z",
        "created_by": f"importer:{source.lower()}",
    }


def _nr_inwent_ref() -> dict[str, Any]:
    return {
        "system": "NR_INWENT",
        "ref_type": "inventory_number",
        "external_id": "T.F-09.33",
        "scope": "cave",
        "notes": "Inventory number belongs to the cave/catalog entry, not the object.",
    }


def _issue_codes(result: Any) -> list[str]:
    return [issue.code for issue in result.issues]


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _read_yaml(path: Path) -> dict[str, Any]:
    return read_record(path)


def test_yaml_review_is_atomic_and_preserves_native_sources_and_publications(
    tmp_path, make_data_dir
):
    from dataclasses import replace

    from gps_kataster_obiektow_tatr.catalog_records import write_dataset
    from gps_kataster_obiektow_tatr.data_loader import DataKind, LoadedYamlRecord

    data_dir = make_data_dir(tmp_path / "data")
    _seed_review_data(data_dir)
    dataset = load_yaml_dataset(data_dir)
    obj = dataset.objects[0].data
    m = obj["measurements"][0]
    m.update(input_srid=2180, input_x=m["y_1992"], input_y=m["x_1992"])
    obj["citations"] = [{"publication_id": "test", "locator": "s. 1", "purpose": "identity"}]
    publication = {"id": "test", "citation": "Author, Full source, 2026."}
    dataset = replace(
        dataset,
        publications=(
            LoadedYamlRecord(
                DataKind.PUBLICATION, data_dir / "publications/test.yml", publication, publication
            ),
        ),
    )
    write_dataset(dataset, data_dir)
    before = _tree_snapshot(data_dir)
    valid = {"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"}
    bad = apply_review_decisions(
        {"decisions": [valid, {"action": "invalid"}]},
        staging_reports=StagingReports(),
        data_dir=data_dir,
    )
    assert bad.has_errors and _tree_snapshot(data_dir) == before
    good = apply_review_decisions(
        {"decisions": [valid]}, staging_reports=StagingReports(), data_dir=data_dir
    )
    assert not good.has_errors, good.issues
    assert all(p.suffix == ".yml" for p in good.written_paths)
    result = read_catalog_projection(data_dir)
    assert result.publications[0].data == publication
    assert result.objects[0].data["citations"] == obj["citations"]
    native = result.objects[0].data["measurements"][0]
    assert tuple(native[k] for k in ("input_srid", "input_x", "input_y")) == tuple(
        m[k] for k in ("input_srid", "input_x", "input_y")
    )


@pytest.mark.parametrize(
    "field",
    [
        "lat",
        "lon",
        "x_1992",
        "y_1992",
        "elevation_m",
        "horizontal_accuracy_m",
        "vertical_accuracy_m",
    ],
)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize("source", ["PIG", "TPN"])
def test_non_finite_staging_blocks_review_before_best_and_writes(
    tmp_path,
    make_data_dir,
    monkeypatch,
    field,
    value,
    write,
    source,
):
    data_dir = make_data_dir(tmp_path / "data")
    pig = _pig_staging()
    tpn = _tpn_staging()
    if source == "PIG":
        pig["proposed_objects"][0]["measurements"][0][field] = value
        decisions = [
            {"action": "create_cave", "source": "PIG", "record_number": 1},
            {"action": "create_object", "source": "PIG", "record_number": 1},
        ]
    else:
        _write_yaml(data_dir / "objects/KSW/KSW-0001.yml", _object_data(cave_id="C-0001"))
        _write_yaml(data_dir / "caves/C-0001.yml", _cave_data(object_ids=["KSW-0001"]))
        tpn["matched_measurements"][0]["measurement"][field] = value
        decisions = [{"action": "add_measurement", "source": "TPN", "record_number": 1}]

    from contextlib import contextmanager

    from gps_kataster_obiektow_tatr import postgres

    original_open = postgres.open_proposal

    @contextmanager
    def check_dataset(dataset, **kwargs):
        from math import isfinite

        assert all(
            isfinite(m[field])
            for r in dataset.objects
            for m in r.data["measurements"]
            if m.get(field) is not None
        )
        with original_open(dataset, **kwargs) as catalog:
            yield catalog

    monkeypatch.setattr(postgres, "open_proposal", check_dataset)
    before = {p.relative_to(data_dir): p.read_bytes() for p in data_dir.rglob("*") if p.is_file()}
    result = apply_review_decisions(
        {"reviewed_at": "2026-10-15T00:00:00Z", "reviewed_by": "test", "decisions": decisions},
        staging_reports=StagingReports(pig=pig, tpn=tpn),
        data_dir=data_dir,
        write=write,
    )
    assert result.has_errors and result.written_paths == ()
    assert any(
        "MEASUREMENT_NON_FINITE" in i.description and field in i.description for i in result.issues
    )
    assert {
        p.relative_to(data_dir): p.read_bytes() for p in data_dir.rglob("*") if p.is_file()
    } == before
