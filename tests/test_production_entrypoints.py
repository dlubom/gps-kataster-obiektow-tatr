"""Invalid candidates reach real public APIs/CLIs with an independent Git baseline."""

import shutil
import subprocess
import sys

import pytest
import yaml
from export_test_support import (
    REPO_ROOT,
    accept_source,
    cli_args,
    source,
    write_sample_data,
    write_yaml,
)

from gps_kataster_obiektow_tatr.best_measurements_export import export_best_measurements
from gps_kataster_obiektow_tatr.build_db import build_database
from gps_kataster_obiektow_tatr.postgres import restore_dump
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts

# Removing the strict YAML loader, source-field/layout guard or Git history gate
# must let the corresponding candidate through and fail this regression.
CASES = [
    ("yaml", "duplicate key", "SQL_CATALOG_INVALID"),
    ("directory", "required data directory", "DATA_DIRECTORY_INVALID"),
    ("manual", "best_policy_object_id_manual_measurement_id_fkey", "BEST_MEASUREMENT_MISSING"),
    ("coordinates", "derived coordinates", "SQL_CATALOG_INVALID"),
    ("membership", "computed membership", "SQL_CATALOG_INVALID"),
    ("measurement", "HISTORY_MEASUREMENT_DELETED", "HISTORY_MEASUREMENT_DELETED"),
    ("baseline", "HISTORY_BASELINE_UNAVAILABLE", "HISTORY_BASELINE_UNAVAILABLE"),
]


@pytest.mark.parametrize("damage,token,code", CASES, ids=[c[0] for c in CASES])
@pytest.mark.parametrize(
    "entry", ["dump", "best", "release", "validate-cli", "dump-cli", "best-cli", "release-cli"]
)
def test_invalid_source_reaches_public_entrypoint(tmp_path, damage, token, code, entry):
    data, baseline = source(tmp_path)
    object_path = data / "objects/KSW/KSW-0001.yml"
    path = object_path
    obj = yaml.safe_load(object_path.read_text())
    if damage == "yaml":
        object_path.write_text(object_path.read_text() + "notes: duplicate field\n")
    elif damage == "directory":
        path = data / "publications"
        shutil.rmtree(path)
    elif damage == "manual":
        obj["best_measurement"].update(
            mode="manual", measurement_id="m-999", reason="Invalid reference"
        )
        write_yaml(object_path, obj)
        # Deferred FK diagnostics currently identify the dataset and object/measurement IDs.
        path = None
    elif damage == "coordinates":
        obj["measurements"][0]["x_1992"] = 1.0
        write_yaml(object_path, obj)
    elif damage == "membership":
        path = data / "caves/C-0001.yml"
        cave = yaml.safe_load(path.read_text())
        cave["object_ids"] = []
        write_yaml(path, cave)
    elif damage == "measurement":
        obj["measurements"].pop()
        write_yaml(object_path, obj)
    else:
        baseline["base_ref"] = "unavailable-accepted-commit"
        path = None
    original = {p.relative_to(data): p.read_bytes() for p in data.rglob("*") if p.is_file()}
    output = tmp_path / "output"
    output.mkdir()
    dump = output / "katalog.dump"
    dump.write_bytes(b"accepted dump")
    exports = output / "exports"
    exports.mkdir()
    (exports / "previous").write_bytes(b"accepted exports")
    before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}

    if entry.endswith("-cli"):
        script, args = {
            "validate-cli": ("validate.py", []),
            "dump-cli": ("build_db.py", ["--output", str(dump)]),
            "best-cli": ("export_best_measurements.py", ["--output-dir", str(exports)]),
            "release-cli": ("build_release_artifacts.py", ["--output-dir", str(exports)]),
        }[entry]
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / script),
                "--data-dir",
                str(data),
                *args,
                *cli_args(baseline),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        diagnostic = result.stdout + result.stderr
        assert result.returncode == 1, diagnostic
        assert (code if entry == "validate-cli" else token) in diagnostic
        assert "Traceback" not in diagnostic
    else:
        api, kwargs = {
            "dump": (build_database, {"output_path": dump}),
            "best": (export_best_measurements, {"output_dir": exports}),
            "release": (build_release_artifacts, {"output_dir": exports}),
        }[entry]
        with pytest.raises(ValueError) as error:
            api(data_dir=data, **baseline, **kwargs)
        diagnostic = str(error.value)
        assert token in diagnostic
        if hasattr(error.value, "issues"):
            assert any(i.code == code and i.path == path for i in error.value.issues)
    if path is not None:
        assert str(path) in diagnostic
    assert {
        p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()
    } == before
    assert {p.relative_to(data): p.read_bytes() for p in data.rglob("*") if p.is_file()} == original


def test_canonical_manual_best_and_bibliography_survive_native_release(tmp_path):
    data = write_sample_data(tmp_path / "data", manual=True, bibliography=True)
    baseline = accept_source(data)
    result = build_release_artifacts(data_dir=data, output_dir=tmp_path / "exports", **baseline)
    with restore_dump(result.dump_path) as restored:
        db = restored.connection
        assert db.execute("SELECT id FROM v_best").fetchone() == {"id": "m-001"}
        assert db.execute("SELECT measurement_id FROM v_auto_best").fetchone() == {
            "measurement_id": "m-002"
        }
        assert db.execute("SELECT id,citation FROM publications").fetchall() == [
            {"id": "fixture-publication", "citation": "Fixture author (2026), Cave survey."}
        ]
        for table in ("cave_citations", "object_citations", "measurement_citations"):
            assert db.execute(f"SELECT publication_id,locator FROM {table}").fetchall() == [
                {"publication_id": "fixture-publication", "locator": "p. 7"}
            ]
