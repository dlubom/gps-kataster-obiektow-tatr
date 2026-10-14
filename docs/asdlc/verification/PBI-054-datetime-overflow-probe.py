# ruff: noqa: E402
"""Public original-code reproduction; no mutation, tests, or workspace writes."""

import hashlib
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
assert not os.environ.get("MUTANT_UNDER_TEST")
sys.path.insert(0, str(REPO / "src"))
import yaml

from gps_kataster_obiektow_tatr.build_db import build_sqlite_database
from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992
from gps_kataster_obiektow_tatr.data_loader import load_dataset
from gps_kataster_obiektow_tatr.staging_review import StagingReports, apply_review_decisions
from gps_kataster_obiektow_tatr.validator import validate_data_dir, validate_record_schemas


def snapshot(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def fixture(root, observed_at):
    data = root / "data"
    obj = yaml.safe_load((REPO / "tests/fixtures/valid-object.yml").read_text())
    cave = yaml.safe_load((REPO / "tests/fixtures/valid-cave.yml").read_text())
    cave["object_ids"] = ["KSW-0001"]
    measurement = obj["measurements"][0]
    coordinates = wgs84_to_1992(lat=49.23459299, lon=19.87589498)
    measurement.update(
        lat=49.23459299,
        lon=19.87589498,
        x_1992=coordinates.x_1992,
        y_1992=coordinates.y_1992,
        source_ref="own:overflow-probe",
        observed_at=observed_at,
    )
    for rel, record in [("objects/KSW/KSW-0001.yml", obj), ("caves/C-0001.yml", cave)]:
        path = data / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(record, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
    output = root / "build/catalog.sqlite"
    output.parent.mkdir()
    output.write_bytes(b"preserved existing artifact\n")
    return data, output


results = []
for timestamp, should_fail in [
    ("2026-05-16T13:30:00+02:00", False),
    ("9999-12-31T23:59:59-01:00", True),
    ("0001-01-01T00:00:00+01:00", True),
]:
    with tempfile.TemporaryDirectory(prefix="PBI054-datetime-overflow-", dir="/tmp") as dirname:
        root = Path(dirname)
        data, output = fixture(root, timestamp)
        before_data = snapshot(data)
        schema_issues = validate_record_schemas(load_dataset(data).records())
        assert schema_issues == (), schema_issues
        print(json.dumps({"timestamp": timestamp, "schema_errors": 0}, ensure_ascii=False))
        calls = {
            "validate_data_dir": lambda data=data: validate_data_dir(data),
            "build_sqlite_database": lambda data=data, output=output: build_sqlite_database(
                data_dir=data, output_path=output, generated_at="2026-10-14T12:00:00Z"
            ),
            "apply_review_decisions_write_false": lambda data=data: apply_review_decisions(
                {"decisions": []}, staging_reports=StagingReports(), data_dir=data, write=False
            ),
            "apply_review_decisions_write_true": lambda data=data: apply_review_decisions(
                {"decisions": []}, staging_reports=StagingReports(), data_dir=data, write=True
            ),
        }
        for name, call in calls.items():
            before = snapshot(root)
            row = {"timestamp": timestamp, "public_api": name, "schema_errors": 0}
            try:
                outcome = call()
            except Exception as exc:
                row.update(
                    exception_type=type(exc).__name__,
                    exception=str(exc),
                    traceback=traceback.format_exc(),
                )
                assert should_fail and isinstance(exc, OverflowError), row
            else:
                assert not should_fail, row
                if name == "validate_data_dir":
                    assert not [i for i in outcome if i.severity == "error"], outcome
                elif name.startswith("apply_review"):
                    assert not outcome.has_errors and outcome.written_paths == (), outcome
                row["exception_type"] = None
            row["data_unchanged"] = snapshot(data) == before_data
            row["all_input_and_output_bytes_unchanged"] = snapshot(root) == before
            assert row["data_unchanged"], row
            if should_fail:
                assert row["all_input_and_output_bytes_unchanged"], row
            print(json.dumps(row, ensure_ascii=False))
            results.append(row)

print(
    json.dumps(
        {
            "public_calls": len(results),
            "schema_valid_failures": sum(r["exception_type"] == "OverflowError" for r in results),
            "real_mutation_executed": False,
        }
    )
)
