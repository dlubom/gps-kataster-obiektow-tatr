"""Contracts at source, proposal, SQL state and accepted-history boundaries."""

import importlib.util
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest
import yaml
from sql_test_support import history_cli_args

from gps_kataster_obiektow_tatr import history as history_checks
from gps_kataster_obiektow_tatr import postgres, validator
from gps_kataster_obiektow_tatr.data_loader import load_yaml_dataset
from gps_kataster_obiektow_tatr.staging_review import StagingReports, apply_review_decisions

ROOT = Path(__file__).resolve().parents[1]


def source(root, *, canonical=True):
    for directory in ("objects/KSW", "caves", "relations", "publications"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    obj = yaml.safe_load((ROOT / "tests/fixtures/valid-object.yml").read_text())
    obj["measurements"][0].update(input_srid=2180, input_x=562729.5, input_y=152838.5)
    for key in ("lat", "lon", "x_1992", "y_1992"):
        obj["measurements"][0].pop(key)
    cave = yaml.safe_load((ROOT / "tests/fixtures/valid-cave.yml").read_text())
    cave["object_ids"] = ["KSW-0001"]
    if canonical:
        (root / "catalog.json").write_text('{"format":"postgresql-yaml","schema_version":2}')
        obj["membership_ordinal"] = 1
        obj["best_measurement"].pop("measurement_id")
        cave.pop("object_ids")
    (root / "objects/KSW/KSW-0001.yml").write_text(yaml.safe_dump(obj))
    (root / "caves/C-0001.yml").write_text(yaml.safe_dump(cave))
    return root


def snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("canonical", [False, True], ids=["legacy", "canonical"])
@pytest.mark.parametrize("change", [False, True], ids=["unchanged", "changed"])
def test_review_loads_each_distinct_catalogue_state_once(tmp_path, monkeypatch, canonical, change):
    data = source(tmp_path / "data", canonical=canonical)
    history = history_cli_args(data)
    opened = []
    history_connections = []
    original = postgres._open_rows
    compare_history = history_checks.compare_history

    @contextmanager
    def counted(*args, **kwargs):
        with original(*args, **kwargs) as catalog:
            opened.append(catalog.connection)
            yield catalog

    monkeypatch.setattr(postgres, "_open_rows", counted)

    def compare(*args, connection=None):
        history_connections.append(connection)
        return compare_history(*args, connection=connection)

    monkeypatch.setattr(history_checks, "compare_history", compare)
    result = apply_review_decisions(
        {
            "reviewed_at": "2026-11-05T14:00:00Z",
            "decisions": [{"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"}]
            if change
            else [],
        },
        staging_reports=StagingReports(),
        data_dir=data,
        write=False,
        base_ref=history[3],
        repo_root=Path(history[1]),
    )
    assert not result.has_errors, result.issues
    assert len(opened) == (2 if change else 1)
    assert history_connections == [opened[-1], opened[-1]]


@pytest.mark.parametrize("write", [False, True], ids=["dry-run", "write"])
@pytest.mark.parametrize("stage", ["input", "final"])
def test_review_invalid_state_preserves_all_existing_files(tmp_path, write, stage):
    data = source(tmp_path / "data")
    (data / "operator-note.txt").write_bytes(b"keep source asset\n")
    reports = StagingReports()
    decisions = []
    if stage == "input":
        path = data / "objects/KSW/KSW-0001.yml"
        obj = yaml.safe_load(path.read_text())
        obj["measurements"] = [42]
        path.write_text(yaml.safe_dump(obj))
        expected = "FINAL_DATA_INVALID"
    else:
        proposal = yaml.safe_load((data / "objects/KSW/KSW-0001.yml").read_text())
        proposal["id"] = "KSW-0002"
        proposal["cave_id"] = "C-9999"
        proposal["best_measurement"]["measurement_id"] = "m-001"
        reports = StagingReports(
            pig={
                "rows": [{"record_number": 1, "object_id": "KSW-0002"}],
                "proposed_objects": [proposal],
            }
        )
        decisions = [{"action": "create_object", "source": "PIG", "record_number": 1}]
        expected = "REVIEW_DATA_INVALID"
    before = snapshot(data)
    result = apply_review_decisions(
        {"decisions": decisions}, staging_reports=reports, data_dir=data, write=write
    )
    assert result.has_errors and result.written_paths == ()
    assert expected in {i.code for i in result.issues}, result.issues
    if stage == "final":
        assert any("CAVE_REFERENCE_MISSING" in i.description for i in result.issues)
    assert snapshot(data) == before


@pytest.mark.parametrize("canonical", [False, True])
@pytest.mark.parametrize("nested", [None, 42, [42]])
def test_invalid_source_shape_is_reported_before_database_use(
    tmp_path, monkeypatch, canonical, nested
):
    data = source(tmp_path / "data", canonical=canonical)
    path = data / "objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(path.read_text())
    obj["measurements"] = nested
    path.write_text(yaml.safe_dump(obj))

    def unexpected(*args, **kwargs):
        pytest.fail("Malformed nested source reached PostgreSQL")

    monkeypatch.setattr(postgres, "_open_rows", unexpected)
    issues = validator.validate_data_dir(data)
    assert [(i.code, i.severity, i.path) for i in issues] == [
        ("SQL_CATALOG_INVALID" if canonical else "SCHEMA_VALIDATION", "error", path)
    ]
    assert "measurements" in issues[0].description


def test_source_and_projection_have_separate_input_contracts(tmp_path):
    data = source(tmp_path / "data")
    raw = load_yaml_dataset(data)
    assert "object_ids" not in raw.caves[0].raw_data
    assert "lat" not in raw.objects[0].raw_data["measurements"][0]
    with postgres.open_catalog(data, validate=False) as catalog:
        projection = catalog.dataset()
    assert projection.caves[0].data["object_ids"] == ["KSW-0001"]
    measurement = projection.objects[0].data["measurements"][0]
    assert (measurement["input_srid"], measurement["input_x"], measurement["input_y"]) == (
        2180,
        562729.5,
        152838.5,
    )
    assert {"lat", "lon", "x_1992", "y_1992"} <= measurement.keys()
    validate_proposal = getattr(validator, "validate_proposal", None)
    assert callable(validate_proposal), "Proposal validation must be an explicit entry point"
    assert not validator.has_errors(validate_proposal(projection, data_dir=data))
    for record in projection.records():
        record.path.write_text(yaml.safe_dump(record.data))
    issues = validator.validate_data_dir(data)
    assert [(i.code, i.severity, i.path) for i in issues] == [
        ("SQL_CATALOG_INVALID", "error", data / "objects/KSW/KSW-0001.yml")
    ]
    assert "computed" in issues[0].description


@pytest.mark.parametrize("ref", ["", "unavailable-accepted-ref"])
def test_missing_history_baseline_blocks_cli_and_build_without_replacing_files(tmp_path, ref):
    from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts

    data = source(tmp_path / "data")
    history = history_cli_args(data)
    output = tmp_path / "exports"
    output.mkdir()
    (output / "katalog.dump").write_bytes(b"previous valid output")
    before = snapshot(output)
    with pytest.raises(ValueError, match="HISTORY_BASELINE_UNAVAILABLE"):
        build_release_artifacts(
            data_dir=data, output_dir=output, base_ref=ref, history_repo=Path(history[1])
        )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate.py"),
            "--data-dir",
            str(data),
            "--history-repo",
            history[1],
            "--base-ref",
            ref,
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "HISTORY_BASELINE_UNAVAILABLE\terror\t<dataset>" in result.stdout
    assert "Traceback" not in result.stderr
    assert snapshot(output) == before


def test_existing_catalogue_validation_never_reloads_source_or_projection(tmp_path, monkeypatch):
    data = source(tmp_path / "data")
    with postgres.open_catalog(data, validate=False) as catalog:

        def unexpected(*args, **kwargs):
            pytest.fail("Existing SQL validation must use its existing connection")

        monkeypatch.setattr(postgres, "_read_snapshots", unexpected)
        monkeypatch.setattr(postgres, "_open_rows", unexpected)
        monkeypatch.setattr(postgres.Catalog, "dataset", unexpected)
        issues = validator.validate_catalog(catalog)
        assert not validator.has_errors(issues)
        assert all(i.path is not None for i in issues)


def test_proposal_cleanup_failure_retains_sql_diagnostic(tmp_path, monkeypatch):
    data = source(tmp_path / "data", canonical=False)
    original = postgres.open_proposal

    @contextmanager
    def broken_cleanup(*args, **kwargs):
        with original(*args, **kwargs) as catalog:
            yield catalog
        raise postgres.CatalogLoadError("owned proposal cleanup failed")

    monkeypatch.setattr(postgres, "open_proposal", broken_cleanup)
    issues = validator.validate_proposal(load_yaml_dataset(data), data_dir=data)
    errors = [i for i in issues if i.severity == "error"]
    assert [(i.code, i.path, i.description) for i in errors] == [
        ("SQL_CATALOG_INVALID", None, "owned proposal cleanup failed")
    ]


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize("boundary", ["input", "final"])
def test_review_closes_catalogues_before_any_write(tmp_path, monkeypatch, write, boundary):
    data = source(tmp_path / "data")
    entry = "open_catalog" if boundary == "input" else "open_source_proposal"
    original = getattr(postgres, entry)

    @contextmanager
    def broken_cleanup(*args, **kwargs):
        with original(*args, **kwargs) as catalog:
            yield catalog
        raise postgres.CatalogLoadError(f"owned {boundary} cleanup failed")

    monkeypatch.setattr(postgres, entry, broken_cleanup)
    before = snapshot(data)
    result = apply_review_decisions(
        {"decisions": [{"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"}]},
        staging_reports=StagingReports(),
        data_dir=data,
        write=write,
    )
    assert result.has_errors and result.written_paths == ()
    assert any(
        i.code == ("FINAL_DATA_INVALID" if boundary == "input" else "REVIEW_DATA_INVALID")
        and f"owned {boundary} cleanup failed" in i.description
        for i in result.issues
    )
    assert snapshot(data) == before


def test_proposal_consumer_exception_is_not_reclassified(tmp_path):
    data = source(tmp_path / "data", canonical=False)
    error = ValueError("failure in the context consumer")
    with (
        pytest.raises(ValueError) as raised,
        validator.validated_proposal(load_yaml_dataset(data), data_dir=data),
    ):
        raise error
    assert raised.value is error


@pytest.mark.parametrize("write", [False, True])
@pytest.mark.parametrize("ref", ["", "unavailable-accepted-ref"])
def test_review_unavailable_git_baseline_preserves_files(tmp_path, write, ref):
    data = source(tmp_path / "data")
    history = history_cli_args(data)
    before = snapshot(data)
    result = apply_review_decisions(
        {"decisions": [{"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"}]},
        staging_reports=StagingReports(),
        data_dir=data,
        write=write,
        base_ref=ref,
        repo_root=Path(history[1]),
    )
    assert result.has_errors and result.written_paths == ()
    assert any(
        i.code == "HISTORY_INVALID"
        and "HISTORY_BASELINE_UNAVAILABLE\terror\t<dataset>" in i.description
        for i in result.issues
    )
    assert snapshot(data) == before


@pytest.mark.parametrize("kind", ["missing", "file"])
def test_cli_keeps_default_source_failure_diagnostic(tmp_path, monkeypatch, capsys, kind):
    from gps_kataster_obiektow_tatr import data_loader

    data = tmp_path / "data"
    if kind == "file":
        data.write_text("broken data root")
    monkeypatch.setattr(data_loader, "DEFAULT_DATA_DIR", data)
    monkeypatch.setattr(postgres, "DEFAULT_DATA_DIR", data)
    spec = importlib.util.spec_from_file_location("validate_cli", ROOT / "scripts/validate.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    assert cli.main(["--data-dir", str(data)]) == 1
    text = capsys.readouterr().out
    assert text.startswith(f"SQL_CATALOG_INVALID\terror\t{data / 'catalog.json'}\t")
    assert "Canonical YAML catalogue format marker is missing" in text


@pytest.mark.parametrize("kind", ["missing", "file"])
@pytest.mark.parametrize("operation", ["database", "release", "best"])
def test_build_keeps_invalid_default_directory_contract(tmp_path, monkeypatch, kind, operation):
    from gps_kataster_obiektow_tatr import data_loader
    from gps_kataster_obiektow_tatr.best_measurements_export import export_best_measurements
    from gps_kataster_obiektow_tatr.build_db import build_database
    from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts

    data = tmp_path / "data"
    if kind == "file":
        data.write_text("broken data root")
    monkeypatch.setattr(data_loader, "DEFAULT_DATA_DIR", data)
    monkeypatch.setattr(postgres, "DEFAULT_DATA_DIR", data)
    output = tmp_path / "exports"
    output.mkdir()
    (output / "katalog.dump").write_bytes(b"previous release")
    before = snapshot(output)
    kwargs = {"data_dir": data}
    function = {
        "database": build_database,
        "release": build_release_artifacts,
        "best": export_best_measurements,
    }[operation]
    kwargs["output_path" if operation == "database" else "output_dir"] = (
        output / "katalog.dump" if operation == "database" else output
    )
    with pytest.raises(data_loader.DataDirectoryError) as raised:
        function(**kwargs)
    assert raised.value.path == data
    assert snapshot(output) == before


@pytest.mark.parametrize("directory", ["objects", "caves", "relations", "publications"])
@pytest.mark.parametrize("damage", ["missing", "file"])
@pytest.mark.parametrize("operation", ["database", "release", "best", "review", "review-dry-run"])
def test_incomplete_source_never_opens_database_or_changes_data_and_outputs(
    tmp_path, monkeypatch, directory, damage, operation
):
    from gps_kataster_obiektow_tatr.best_measurements_export import export_best_measurements
    from gps_kataster_obiektow_tatr.build_db import build_database
    from gps_kataster_obiektow_tatr.data_loader import DataDirectoryError
    from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts

    data = source(tmp_path / "data")
    history = history_cli_args(data)  # Accept the complete source, then damage only the candidate.
    path = data / directory
    shutil.rmtree(path)
    if damage == "file":
        path.write_bytes(b"not a directory")
    output = tmp_path / "exports"
    output.mkdir()
    (output / "katalog.dump").write_bytes(b"accepted dump")
    (output / "best-measurements.csv").write_bytes(b"accepted CSV")
    before = snapshot(tmp_path)

    def unexpected(*args, **kwargs):
        pytest.fail("Incomplete source reached PostgreSQL before layout rejection")

    monkeypatch.setattr(postgres, "_open_rows", unexpected)
    with pytest.raises(DataDirectoryError) as raised:
        if operation.startswith("review"):
            apply_review_decisions(
                {
                    "decisions": [
                        {"action": "link_cave", "object_id": "KSW-0001", "cave_id": "C-0001"}
                    ]
                },
                staging_reports=StagingReports(),
                data_dir=data,
                write=operation == "review",
                base_ref=history[3],
                repo_root=Path(history[1]),
            )
        else:
            function = {
                "database": build_database,
                "release": build_release_artifacts,
                "best": export_best_measurements,
            }[operation]
            destination = (
                {"output_path": output / "katalog.dump"}
                if operation == "database"
                else {"output_dir": output}
            )
            function(
                data_dir=data, base_ref=history[3], history_repo=Path(history[1]), **destination
            )
    assert raised.value.path == path
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("marker", [None, "{broken", '{"format":"unsupported"}'])
def test_marker_error_precedes_incomplete_default_source_layout(
    tmp_path, monkeypatch, capsys, marker
):
    from gps_kataster_obiektow_tatr import data_loader

    data = tmp_path / "data"
    data.mkdir()
    if marker is not None:
        (data / "catalog.json").write_text(marker)
    monkeypatch.setattr(data_loader, "DEFAULT_DATA_DIR", data)
    monkeypatch.setattr(postgres, "DEFAULT_DATA_DIR", data)

    def unexpected(*args, **kwargs):
        pytest.fail("Broken format marker reached PostgreSQL")

    monkeypatch.setattr(postgres, "_open_rows", unexpected)
    spec = importlib.util.spec_from_file_location("validate_cli_u03", ROOT / "scripts/validate.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    assert cli.main(["--data-dir", str(data)]) == 1
    output = capsys.readouterr().out
    assert output.startswith(f"SQL_CATALOG_INVALID\terror\t{data / 'catalog.json'}\t")
    expected = (
        "format marker is missing"
        if marker is None
        else (
            "Invalid catalogue format marker"
            if marker == "{broken"
            else "Unsupported catalogue storage format"
        )
    )
    assert expected in output
