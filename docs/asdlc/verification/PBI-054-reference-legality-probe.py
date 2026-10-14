# ruff: noqa: E402
"""Show schema-valid public reference pairs; no mutation or repository writes."""

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
assert not os.environ.get("MUTANT_UNDER_TEST")
sys.path.insert(0, str(REPO / "src"))
import yaml

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


for dimension, change in [
    ("system", "geoportal"),
    ("ref_type", "source_row"),
    ("url", "https://example.test/two"),
    ("external_id", "SECOND"),
]:
    with tempfile.TemporaryDirectory(prefix="PBI054-ref-legality-", dir="/tmp") as dirname:
        root = Path(dirname)
        obj = yaml.safe_load((REPO / "tests/fixtures/valid-object.yml").read_text())
        cave = yaml.safe_load((REPO / "tests/fixtures/valid-cave.yml").read_text())
        cave["object_ids"] = ["KSW-0001"]
        measurement = obj["measurements"][0]
        coords = wgs84_to_1992(lat=49.23459299, lon=19.87589498)
        measurement.update(
            lat=49.23459299,
            lon=19.87589498,
            x_1992=coords.x_1992,
            y_1992=coords.y_1992,
            source_ref="own:ref-probe",
        )
        first = {
            "system": "inne",
            "ref_type": "other",
            "external_id": "SHARED",
            "url": "https://example.test/one",
        }
        second = {**first, dimension: change}
        obj["external_refs"] = [first]
        object_path = root / "objects/KSW/KSW-0001.yml"
        cave_path = root / "caves/C-0001.yml"
        for path, record in [(object_path, obj), (cave_path, cave)]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
        assert validate_record_schemas(load_dataset(root).records()) == ()
        assert not [i for i in validate_data_dir(root) if i.severity == "error"]
        required = {"system": "TPN", "ref_type": "source_globalid", "external_id": "{ROW}"}
        proposal = {
            **measurement,
            "id": "m-002",
            "source": "TPN",
            "source_ref": "TPN:{ROW}",
            "observed_date": "2026-05-16",
            "verification_status": "nieweryfikowany",
        }
        reports = StagingReports(
            tpn={
                "rows": [
                    {
                        "record_number": 1,
                        "status": "matched",
                        "globalid": "{ROW}",
                        "nr_inwent": None,
                        "name": "Reference legality",
                    }
                ],
                "matched_measurements": [
                    {
                        "record_number": 1,
                        "target_object_id": "KSW-0001",
                        "target_cave_id": "C-0001",
                        "measurement": proposal,
                        "object_external_refs": [required, second],
                        "cave_external_refs": [],
                    }
                ],
            }
        )
        decisions = {
            "reviewed_at": "2026-10-14T12:00:00Z",
            "reviewed_by": "audit",
            "decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}],
        }
        before = snapshot(root)
        dry = apply_review_decisions(decisions, staging_reports=reports, data_dir=root, write=False)
        assert not dry.has_errors and dry.written_paths == ()
        assert snapshot(root) == before
        result = apply_review_decisions(
            decisions, staging_reports=reports, data_dir=root, write=True
        )
        assert not result.has_errors
        actual = yaml.safe_load(object_path.read_text())["external_refs"]
        assert actual == [first, required, second], actual
        schema = validate_record_schemas(load_dataset(root).records())
        issues = validate_data_dir(root)
        assert schema == () and not [i for i in issues if i.severity == "error"]
        print(
            json.dumps(
                {
                    "dimension": dimension,
                    "first": first,
                    "second": second,
                    "schema_errors": 0,
                    "review_errors": 0,
                    "final_validation_errors": 0,
                    "duplicate_typed_globalid_errors": sum(
                        i.code == "DUPLICATE_TPN_GLOBALID" for i in issues
                    ),
                    "both_refs_retained": True,
                    "dry_run_unchanged": True,
                },
                ensure_ascii=False,
            )
        )
print(json.dumps({"positive_public_cases": 4, "real_mutation_executed": False}))
