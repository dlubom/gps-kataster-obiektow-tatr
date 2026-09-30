"""Probe exact validator survivors on schema-valid temporary YAML fixtures."""
# ruff: noqa: E402

import argparse
import inspect
import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
import test_validator as fixtures

import gps_kataster_obiektow_tatr.validator as validator
from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992
from gps_kataster_obiektow_tatr.data_loader import load_dataset

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--ledger", type=Path, default=Path(__file__).with_name("PBI-054-mutations.json")
)
ledger = json.loads(parser.parse_args().ledger.read_text())
by_id = {row["id"]: row for row in ledger["non_killed"]}


def mutated_function(name, number):
    key = f"gps_kataster_obiektow_tatr.validator.x_{name}__mutmut_{number}"
    entry = by_id[key]
    lines = inspect.getsource(getattr(validator, name)).splitlines()
    diff = entry["diff"].splitlines()
    hunks = [i for i, line in enumerate(diff) if line.startswith("@@")]
    for ordinal, start in reversed(list(enumerate(hunks))):
        end = hunks[ordinal + 1] if ordinal + 1 < len(hunks) else len(diff)
        match = re.match(r"@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@", diff[start])
        assert match
        offset = int(match.group(1)) - 1
        old_count = int(match.group(2) or 1)
        old, new = [], []
        for line in diff[start + 1 : end]:
            if line.startswith((" ", "-")):
                old.append(line[1:])
            if line.startswith((" ", "+")):
                new.append(line[1:])
        assert len(old) == old_count
        assert lines[offset : offset + old_count] == old, key
        lines[offset : offset + old_count] = new
    namespace = dict(validator.__dict__)
    exec(compile("\n".join(lines) + "\n", "<ledger mutant>", "exec"), namespace)
    return key, namespace[name]


def compare(data_dir, name, number, expected_code):
    assert not validator.validate_record_schemas(load_dataset(data_dir).records())

    def run():
        issues = validator.validate_data_dir(data_dir)
        return {
            "has_errors": validator.has_errors(issues),
            "issues": [
                {"code": issue.code, "severity": issue.severity.value if issue.severity else None}
                for issue in issues
            ],
        }

    original = run()
    assert any(issue["code"] == expected_code for issue in original["issues"])
    key, function = mutated_function(name, number)
    with patch.object(validator, name, function):
        changed = run()
    assert original != changed
    return {
        "id": key,
        "status": by_id[key]["status"],
        "schema_errors": 0,
        "original": original,
        "mutant": changed,
        "same": False,
    }


with TemporaryDirectory(prefix="pbi054-validator-probes-") as directory:
    temporary = Path(directory)
    results = []
    duplicate_dir = temporary / "duplicate-globalid"
    first = fixtures._valid_object()
    first["external_refs"] = [
        {"system": "TPN", "ref_type": "source_globalid", "external_id": "{DUPLICATE}"}
    ]
    second = deepcopy(first)
    second["id"] = "KSW-0002"
    for record in (first, second):
        fixtures._write_object(duplicate_dir, record)
    cave = fixtures._valid_cave()
    cave["object_ids"] = [first["id"], second["id"]]
    fixtures._write_yaml(duplicate_dir / "caves/C-0001.yml", cave)
    results.append(
        compare(duplicate_dir, "_validate_duplicate_tpn_globalids", 3, "DUPLICATE_TPN_GLOBALID")
    )

    attachment = {
        "id": "a-001",
        "kind": "inne",
        "path": "https://example.test/fixture",
        "measurement_id": "m-999",
        "created_at": "2026-09-30T12:00:00Z",
        "created_by": "reviewer",
    }
    attached = fixtures._valid_object()
    attached["attachments"] = [attachment]
    attachment_dir = temporary / "attachment-reference"
    fixtures._write_object(attachment_dir, attached)
    results.append(
        compare(attachment_dir, "_validate_cross_references", 145, "ATTACHMENT_MEASUREMENT_MISSING")
    )

    relation_dir = temporary / "relation-reference"
    fixtures._write_object(relation_dir, fixtures._valid_object())
    fixtures._write_yaml(
        relation_dir / "relations/R-0001.yml",
        {
            "schema_version": 1,
            "id": "R-0001",
            "from_object_id": "KSW-9999",
            "to_object_id": "KSW-0001",
            "relation_type": "sasiad",
        },
    )
    results.append(
        compare(
            relation_dir, "_validate_cross_references", 186, "RELATION_OBJECT_REFERENCE_MISSING"
        )
    )

    url_dir = temporary / "url"
    attachment.pop("measurement_id")
    attachment["path"] = "ftp://example.test/fixture"
    fixtures._write_object(url_dir, attached)
    results.append(compare(url_dir, "_valid_http_url", 3, "ATTACHMENT_URL_INVALID"))

    distance_dir = temporary / "distance"
    distant = fixtures._valid_object()
    observation = fixtures._valid_measurement()
    observation["id"] = "m-002"
    observation["lat"] += 0.005
    point = wgs84_to_1992(lat=observation["lat"], lon=observation["lon"])
    observation["x_1992"], observation["y_1992"] = point.x_1992, point.y_1992
    distant["measurements"].append(observation)
    fixtures._write_object(distance_dir, distant)
    results.append(
        compare(distance_dir, "_validate_measurement_distances", 33, "MEASUREMENT_DISTANCE_OUTLIER")
    )

    print(json.dumps({"baseline_sha": ledger["baseline_sha"], "probes": results}, indent=2))
