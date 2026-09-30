#!/usr/bin/env python3
"""Read-only-checkout reproductions for independent PBI-054 final review.

Run from the repository with its environment:
  uv run --frozen python docs/asdlc/verification/PBI-054-discoveries.py
All generated input/output resides in one TemporaryDirectory. No repository
files, index, branch, HEAD, or final catalog are written. Fixtures are imported
from this checkout; these are diagnostic reproductions, not a proposed repair.
"""
# ruff: noqa: E402

from __future__ import annotations

import io
import json
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path

import shapefile
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from test_review_validation import _two_source_rows
from test_staging_review import (
    TPN_GLOBALID,
    _cave_data,
    _object_data,
    _tpn_staging,
    _write_yaml,
)

from gps_kataster_obiektow_tatr.data_loader import DataKind, LoadedYamlRecord
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts
from gps_kataster_obiektow_tatr.staging_review import StagingReports, apply_review_decisions
from gps_kataster_obiektow_tatr.validator import validate_data_dir, validate_record_schemas

STAMP = "2026-09-30T08:00:00Z"


def errors(data_dir):
    return [i.code for i in validate_data_dir(data_dir) if i.severity == "error"]


def proposal_schema_errors(report):
    records = tuple(
        LoadedYamlRecord(kind=kind, path=Path("<staging>"), data=obj, raw_data=obj)
        for key, kind in (("proposed_objects", DataKind.OBJECT), ("proposed_caves", DataKind.CAVE))
        for obj in report.get(key, [])
    )
    return [i.code for i in validate_record_schemas(records) if i.severity == "error"]


def sample_target(data_dir):
    _write_yaml(data_dir / "objects/KSW/KSW-0001.yml", _object_data(cave_id="C-0001"))
    _write_yaml(data_dir / "caves/C-0001.yml", _cave_data(object_ids=["KSW-0001"]))
    assert errors(data_dir) == []


def source_row_selectors(root):
    observations = []
    # Native YAML float/bool must not be silently turned into source row 1.
    for raw, label in (("1.9", "fractional"), ("true", "boolean"), ("1", "valid-integer-control")):
        working = root / label
        working.mkdir(parents=True)
        data_dir = working / "data"
        report = _two_source_rows(working, "PIG", data_dir)
        assert proposal_schema_errors(report) == []
        (working / "pig.json").write_text(json.dumps(report), encoding="utf-8")
        (working / "decisions.yml").write_text(
            "decisions:\n"
            "  - action: create_cave\n    source: PIG\n    record_number: " + raw + "\n"
            "  - action: create_object\n    source: PIG\n    record_number: " + raw + "\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/importers/apply_review.py"),
                "--decisions",
                str(working / "decisions.yml"),
                "--pig-staging",
                str(working / "pig.json"),
                "--tpn-staging",
                str(working / "absent.json"),
                "--data-dir",
                str(data_dir),
                "--init-data-dir",
                "--output-dir",
                str(working / "reports"),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        applied = json.loads((working / "reports/staging-review.json").read_text())
        obj = yaml.safe_load(next((data_dir / "objects").rglob("*.yml")).read_text())
        observations.append(
            {
                "case": label,
                "decision_record_number_yaml": raw,
                "cli_exit_code": result.returncode,
                "has_errors": applied["has_errors"],
                "normalized_record_numbers": [d["record_number"] for d in applied["decisions"]],
                "written_count": len(applied["written_paths"]),
                "written_source_ref": obj["measurements"][0]["source_ref"],
                "final_validation_errors": errors(data_dir),
            }
        )
    return observations


def assigned_proposal_provenance(root):
    observations = []
    for source in ("PIG", "TPN"):
        for variant in (
            "object-source-ref-from-row-2",
            "cave-catalog-ref-from-row-2",
            "valid-control",
        ):
            working = root / (source + "-" + variant)
            working.mkdir(parents=True)
            data_dir = working / "data"
            report = _two_source_rows(working, source, data_dir)
            if variant == "object-source-ref-from-row-2":
                first = report["proposed_objects"][0]["measurements"][0]
                second = report["proposed_objects"][1]["measurements"][0]
                first["source_ref"] = second["source_ref"]
            elif variant == "cave-catalog-ref-from-row-2":
                system = "PIG" if source == "PIG" else "NR_INWENT"
                kind = "catalog_id" if source == "PIG" else "inventory_number"
                first = next(
                    r
                    for r in report["proposed_caves"][0]["external_refs"]
                    if r["system"] == system and r["ref_type"] == kind
                )
                second = next(
                    r
                    for r in report["proposed_caves"][1]["external_refs"]
                    if r["system"] == system and r["ref_type"] == kind
                )
                first["external_id"] = second["external_id"]
            assert proposal_schema_errors(report) == []
            original = deepcopy(report)
            decision = {
                "reviewed_at": STAMP,
                "decisions": [
                    {"action": "create_cave", "source": source, "record_number": 1},
                    {"action": "create_object", "source": source, "record_number": 1},
                ],
            }
            dry = apply_review_decisions(
                decision,
                staging_reports=StagingReports(**{source.lower(): report}),
                data_dir=data_dir,
                initialize_data_dir=True,
                write=False,
            )
            assert not data_dir.exists()
            result = apply_review_decisions(
                decision,
                staging_reports=StagingReports(**{source.lower(): report}),
                data_dir=data_dir,
                initialize_data_dir=True,
            )
            assert report == original
            obj = yaml.safe_load(next((data_dir / "objects").rglob("*.yml")).read_text())
            cave = yaml.safe_load(next((data_dir / "caves").rglob("*.yml")).read_text())
            observations.append(
                {
                    "source": source,
                    "case": variant,
                    "schema_errors": [],
                    "row_source_id": report["rows"][0].get(
                        "pig_id" if source == "PIG" else "globalid"
                    ),
                    "row_nr_inwent": report["rows"][0]["nr_inwent"],
                    "dry_run_has_errors": dry.has_errors,
                    "has_errors": result.has_errors,
                    "written_count": len(result.written_paths),
                    "written_source_ref": obj["measurements"][0]["source_ref"],
                    "written_cave_external_refs": [
                        {k: r[k] for k in ("system", "ref_type", "external_id")}
                        for r in cave["external_refs"]
                    ],
                    "final_validation_errors": errors(data_dir),
                }
            )
    return observations


def matched_tpn_provenance(root):
    observations = []
    for variant in (
        "replace-globalid",
        "remove-globalid",
        "replace-inventory-number",
        "remove-inventory-number",
        "wrong-measurement-source-control",
        "valid-extra-decision-globalid-control",
        "valid-extra-object-globalid-control",
    ):
        working = root / variant
        data_dir = working / "data"
        sample_target(data_dir)
        report = _tpn_staging()
        update = report["matched_measurements"][0]
        decision = {
            "reviewed_at": STAMP,
            "decisions": [{"action": "add_measurement", "source": "TPN", "record_number": 1}],
        }
        if variant == "replace-globalid":
            update["object_external_refs"][0]["external_id"] = "{WRONG-GLOBALID}"
        elif variant == "remove-globalid":
            update["object_external_refs"] = []
        elif variant == "replace-inventory-number":
            update["cave_external_refs"][0]["external_id"] = "WRONG-NR-INWENT"
        elif variant == "remove-inventory-number":
            update["cave_external_refs"] = []
        elif variant == "wrong-measurement-source-control":
            update["measurement"]["source_ref"] = "TPN:{WRONG-GLOBALID}"
        elif variant == "valid-extra-decision-globalid-control":
            decision["decisions"][0]["globalid"] = TPN_GLOBALID
        elif variant == "valid-extra-object-globalid-control":
            extra = deepcopy(update["object_external_refs"][0])
            extra["external_id"] = "{HISTORICAL-EXTRA-GLOBALID}"
            update["object_external_refs"].append(extra)
        dry = apply_review_decisions(
            decision, staging_reports=StagingReports(tpn=report), data_dir=data_dir, write=False
        )
        result = apply_review_decisions(
            decision, staging_reports=StagingReports(tpn=report), data_dir=data_dir
        )
        obj = yaml.safe_load((data_dir / "objects/KSW/KSW-0001.yml").read_text())
        cave = yaml.safe_load((data_dir / "caves/C-0001.yml").read_text())
        observations.append(
            {
                "case": variant,
                "dry_run_has_errors": dry.has_errors,
                "has_errors": result.has_errors,
                "issues": [i.code for i in result.issues],
                "written_count": len(result.written_paths),
                "row_globalid": report["rows"][0]["globalid"],
                "row_nr_inwent": report["rows"][0]["nr_inwent"],
                "object_external_refs": [
                    {k: r[k] for k in ("system", "ref_type", "external_id")}
                    for r in obj["external_refs"]
                ],
                "cave_external_refs": [
                    {k: r[k] for k in ("system", "ref_type", "external_id")}
                    for r in cave["external_refs"]
                ],
                "final_validation_errors": errors(data_dir),
            }
        )
    return observations


def finite_dbf_elevation(root):
    observations = []
    # 2**63 is a PBI-055 positive control; 1e50/-1e50 are finite valid
    # values that overflow the DBF *representation*, not the domain float.
    for n, value in enumerate((2**63, 1e49, 1e50, -1e50)):
        working = root / str(n)
        data_dir = working / "data"
        sample_target(data_dir)
        path = data_dir / "objects/KSW/KSW-0001.yml"
        obj = yaml.safe_load(path.read_text())
        obj["measurements"][0]["elevation_m"] = value
        _write_yaml(path, obj)
        before = path.read_bytes()
        assert errors(data_dir) == []
        result = build_release_artifacts(
            data_dir=data_dir,
            sqlite_path=working / "db/katalog.sqlite",
            output_dir=working / "exports",
            generated_at=STAMP,
        )
        with sqlite3.connect(result.sqlite_result.sqlite_path) as db:
            stored = db.execute("SELECT elevation_m FROM measurements").fetchone()[0]
        with zipfile.ZipFile(result.export_result.shapefile_zip_path) as archive:
            dbf_bytes = archive.read("best-measurements.dbf")
            with shapefile.Reader(
                shp=io.BytesIO(archive.read("best-measurements.shp")),
                shx=io.BytesIO(archive.read("best-measurements.shx")),
                dbf=io.BytesIO(dbf_bytes),
                encoding="utf-8",
                encodingErrors="strict",
            ) as reader:
                read_value = reader.record(0)["elev_m"]
                fields = [f for f in reader.fields if f.name != "DeletionFlag"]
                target = next(f for f in fields if f.name == "elev_m")
                offset = 1 + sum(f.size for f in fields[: fields.index(target)])
                header_length = int.from_bytes(dbf_bytes[8:10], "little")
                raw_field = dbf_bytes[
                    header_length + offset : header_length + offset + target.size
                ].decode("ascii")
        assert path.read_bytes() == before
        observations.append(
            {
                "input_elevation": value,
                "final_validation_errors": [],
                "sqlite_readback": stored,
                "dbf_field_width": target.size,
                "dbf_field_decimal": target.decimal,
                "dbf_raw_field": raw_field,
                "dbf_readback": read_value,
                "dbf_equals_input_float": float(value) == read_value,
                "formatted_input_before_pyshp_truncation": format(float(value), ".2f"),
            }
        )
    return observations


def main():
    with tempfile.TemporaryDirectory(prefix="pbi054-independent-review-") as td:
        root = Path(td)
        report = {
            "source_row_selectors": source_row_selectors(root / "selectors"),
            "assigned_proposal_provenance": assigned_proposal_provenance(root / "proposals"),
            "matched_tpn_provenance": matched_tpn_provenance(root / "matched"),
            "finite_dbf_elevation": finite_dbf_elevation(root / "numeric"),
        }
        print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
