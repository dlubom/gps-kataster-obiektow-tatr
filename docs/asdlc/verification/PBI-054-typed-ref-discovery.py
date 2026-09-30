#!/usr/bin/env python3
"""Reproduce typed TPN reference misclassification without changing the checkout.

Run from the repository using .venv/bin/python. Each scenario uses a separate
TemporaryDirectory-derived subtree and current imported test fixtures. This is
an observation of the original code, not a patch or a passing regression test.
"""
# ruff: noqa: E402

import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
import test_tpn_staging as fixtures

from gps_kataster_obiektow_tatr.staging_review import StagingReports, apply_review_decisions
from gps_kataster_obiektow_tatr.tpn_staging import build_tpn_staging, write_staging_files
from gps_kataster_obiektow_tatr.validator import validate_data_dir

STAMP = "2026-09-30T12:00:00Z"


def validation_errors(path):
    return [issue.code for issue in validate_data_dir(path) if issue.severity == "error"]


def scenario(root, ref_type):
    root.mkdir()
    fixtures._globalid_matching_report(root, ambiguous=False, reverse_candidates=False)
    data = root / "data"
    # The second point has crossed a valley boundary. Preserve its historical ID
    # with the documented prefix reason so the complete input catalog is valid.
    for path in sorted((data / "objects").rglob("*.yml")):
        obj = yaml.safe_load(path.read_text())
        obj["id_assignment"]["prefix_override_reason"] = (
            "Preserve historical ID after source correction."
        )
        if obj["id"] == "KSW-0001":
            if ref_type is None:
                obj["external_refs"] = []
            else:
                obj["external_refs"][0]["ref_type"] = ref_type
        path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False))
    initial_errors = validation_errors(data)
    assert initial_errors == [], initial_errors
    initial = {p.relative_to(data).as_posix(): p.read_bytes() for p in data.rglob("*.yml")}
    report = build_tpn_staging(
        root / "tpn.csv",
        generated_at=STAMP,
        data_dir=data,
        pig_staging_path=None,
        prefix_resolver=fixtures.StubResolver(),
    )
    assert initial == {p.relative_to(data).as_posix(): p.read_bytes() for p in data.rglob("*.yml")}
    staging_path, _ = write_staging_files(report, output_dir=root / "staging")
    staging = json.loads(staging_path.read_text())
    decisions = [{"action": "add_measurement", "source": "TPN", "record_number": 1}]
    dry = apply_review_decisions(
        {"decisions": decisions, "reviewed_at": STAMP, "reviewed_by": "dl"},
        staging_reports=StagingReports(pig=None, tpn=staging),
        data_dir=data,
        write=False,
    )
    assert initial == {p.relative_to(data).as_posix(): p.read_bytes() for p in data.rglob("*.yml")}
    decision_path = root / "decisions.yml"
    decision_path.write_text(
        yaml.safe_dump({"reviewed_at": STAMP, "reviewed_by": "dl", "decisions": decisions})
    )
    cli = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/importers/apply_review.py"),
            "--decisions",
            str(decision_path),
            "--no-pig-staging",
            "--tpn-staging",
            str(staging_path),
            "--data-dir",
            str(data),
            "--output-dir",
            str(root / "review"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    result = json.loads((root / "review/staging-review.json").read_text())
    objects = {
        obj["id"]: obj
        for path in sorted((data / "objects").rglob("*.yml"))
        for obj in [yaml.safe_load(path.read_text())]
    }
    return {
        "ref_type_on_first_object": ref_type,
        "input_validation_errors": initial_errors,
        "staging_row": asdict(report.rows[0]),
        "staging_update_target": report.matched_measurements[0]["target_object_id"],
        "dry_run_has_errors": dry.has_errors,
        "cli_exit_code": cli.returncode,
        "review_has_errors": result["has_errors"],
        "written_count": len(result["written_paths"]),
        "applied_decisions": result["decisions"],
        "object_measurement_counts": {
            key: len(value["measurements"]) for key, value in objects.items()
        },
        "object_measurement_source_refs": {
            key: [item.get("source_ref") for item in value["measurements"]]
            for key, value in objects.items()
        },
        "final_validation_errors": validation_errors(data),
        "changed_paths": [
            p.relative_to(data).as_posix()
            for p in sorted(data.rglob("*.yml"))
            if p.read_bytes() != initial[p.relative_to(data).as_posix()]
        ],
    }


with TemporaryDirectory(prefix="pbi054-typed-ref-") as directory:
    root = Path(directory)
    results = [
        scenario(root / label, ref_type)
        for label, ref_type in [
            ("legal-other-ref", "other"),
            ("source-globalid-control", "source_globalid"),
            ("no-unrelated-ref-control", None),
        ]
    ]
    print(
        json.dumps(
            {"source_sha": "827a2f86f215080acda3317d4542ef6ebba8d0ae", "observations": results},
            ensure_ascii=False,
            indent=2,
        )
    )
