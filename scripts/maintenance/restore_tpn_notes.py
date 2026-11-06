#!/usr/bin/env python3
"""One-time, identity-only restoration of measurement notes from preserved TPN CSV."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from gps_kataster_obiektow_tatr.data_loader import (  # noqa: E402
    is_canonical_source,
    load_yaml_dataset,
)
from gps_kataster_obiektow_tatr.postgres import read_catalog_projection  # noqa: E402
from gps_kataster_obiektow_tatr.report_formatting import utc_timestamp  # noqa: E402
from gps_kataster_obiektow_tatr.tpn_notes import (  # noqa: E402
    CONTEXT_FIELDS,
    append_tpn_context,
)

AUTHOR = "maintenance:PBI-082"


def restore_notes(
    *,
    source: Path,
    data_dir: Path,
    report: Path,
    apply: bool,
    generated_at: str,
    base_ref: str | None = None,
    history_repo: Path = REPO_ROOT,
):
    """Write a reviewable manifest before applying only unambiguous note changes."""

    if report.resolve() == source.resolve() or report.resolve().is_relative_to(data_dir.resolve()):
        raise ValueError("Report must be outside the dataset and must not overwrite the source.")
    source_bytes = source.read_bytes()
    reader = csv.DictReader(io.StringIO(source_bytes.decode("utf-8-sig")))
    headers = reader.fieldnames or []
    if not {"GLOBALID", *CONTEXT_FIELDS}.issubset(headers) or len(set(headers)) != len(headers):
        raise ValueError("CSV requires unique headers including GLOBALID, WER_LOK and UWAGI.")
    rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError("CSV contains a row with missing or extra columns.")
    counts = Counter(row["GLOBALID"].strip() for row in rows)
    dataset = (
        read_catalog_projection(data_dir)
        if is_canonical_source(data_dir)
        else load_yaml_dataset(data_dir)
    )
    owners = defaultdict(list)
    measurements = defaultdict(list)
    object_ids = Counter(
        rec.data["id"] for rec in dataset.objects if isinstance(rec.data.get("id"), str)
    )
    for rec in dataset.objects:
        for ref in rec.data["external_refs"]:
            if ref.get("system") == "TPN" and ref.get("ref_type") == "source_globalid":
                owners[ref.get("external_id")].append(rec)
        for index, measurement in enumerate(rec.data["measurements"]):
            if measurement.get("source") == "TPN":
                measurements[measurement.get("source_ref")].append((rec, index))

    changes, issues = [], []
    updated = {}
    before_bytes = {}
    missing = Counter()
    for number, row in enumerate(rows, 1):
        if not any(row[field].strip() for field in CONTEXT_FIELDS):
            continue
        globalid = row["GLOBALID"].strip()
        candidates = owners[globalid]
        targets = measurements[f"TPN:{globalid}"]
        reason = None
        if not globalid or counts[globalid] != 1:
            reason = "Missing or ambiguous source GLOBALID."
        elif len(candidates) != 1:
            reason = "Missing or ambiguous TPN/source_globalid object reference."
        elif len(targets) != 1 or targets[0][0].path != candidates[0].path:
            reason = "Missing, ambiguous or differently owned TPN measurement.source_ref."
        if reason:
            issues.append({"record_number": number, "globalid": globalid, "reason": reason})
            continue
        rec, index = targets[0]
        measurement = rec.raw_data["measurements"][index]
        object_id = rec.data.get("id")
        measurement_id = measurement.get("id")
        if (
            not isinstance(object_id, str)
            or not object_id.strip()
            or not isinstance(measurement_id, str)
            or not measurement_id.strip()
        ):
            issues.append(
                {"globalid": globalid, "reason": "Missing or invalid local object/measurement ID."}
            )
            continue
        if (
            object_ids[rec.data["id"]] != 1
            or sum(m.get("id") == measurement.get("id") for m in rec.data["measurements"]) != 1
        ):
            issues.append({"globalid": globalid, "reason": "Ambiguous object/measurement ID."})
            continue
        notes = measurement.get("notes")
        if notes is not None and not isinstance(notes, str):
            issues.append({"globalid": globalid, "reason": "Existing notes are not text/null."})
            continue
        after = append_tpn_context(notes, row)
        for field in CONTEXT_FIELDS:
            value = row[field].strip()
            if value and f"\nTPN {field}: {value}\n" not in f"\n{notes or ''}\n":
                missing[field] += 1
        if after == notes:
            continue
        if rec.path not in updated:
            updated[rec.path] = deepcopy(rec.raw_data)
            before_bytes[rec.path] = rec.path.read_bytes()
        obj = updated[rec.path]
        obj["measurements"][index]["notes"] = after
        obj["updated_at"] = generated_at
        obj["updated_by"] = AUTHOR
        changes.append(
            {
                "path": str(rec.path.relative_to(data_dir)),
                "object_id": obj["id"],
                "measurement_id": measurement["id"],
                "globalid": globalid,
                "record_number": number,
                "source_values": {f: row[f].strip() for f in CONTEXT_FIELDS},
                "file_sha256_before": sha256(before_bytes[rec.path]).hexdigest(),
                "before": {
                    "notes": notes,
                    "updated_at": rec.raw_data.get("updated_at"),
                    "updated_by": rec.raw_data.get("updated_by"),
                },
                "after": {"notes": after, "updated_at": generated_at, "updated_by": AUTHOR},
                "reason": "Restore labelled TPN context at its uniquely identified measurement.",
            }
        )
    prospective = replace(
        dataset,
        objects=tuple(
            replace(
                rec,
                data=updated.get(rec.path, rec.data),
                raw_data=updated.get(rec.path, rec.raw_data),
            )
            for rec in dataset.objects
        ),
    )
    from gps_kataster_obiektow_tatr.catalog_records import write_dataset
    from gps_kataster_obiektow_tatr.history import check_history, compare_history
    from gps_kataster_obiektow_tatr.validator import format_issue, has_errors, validate_proposal

    validation = validate_proposal(prospective, data_dir=data_dir)
    if not has_errors(validation):
        validation = (*validation, *compare_history(dataset, prospective))
    if base_ref is not None and not has_errors(validation):
        validation = (*validation, *check_history(base_ref, prospective, repo_root=history_repo))
    issues.extend({"reason": format_issue(i)} for i in validation if i.severity == "error")
    if source.read_bytes() != source_bytes or any(
        p.read_bytes() != b for p, b in before_bytes.items()
    ):
        raise ValueError("Input changed during restoration; no final writes attempted.")
    result = {
        "mode": "blocked" if apply and issues else "pending" if apply else "dry-run",
        "generated_at": generated_at,
        "source_path": str(source),
        "source_sha256": sha256(source_bytes).hexdigest(),
        "source_rows": len(rows),
        "changed_files": len(updated),
        "missing_context_fields": {field: missing[field] for field in CONTEXT_FIELDS},
        "changes": changes,
        "issues": issues,
    }
    report.parent.mkdir(parents=True, exist_ok=True)

    def persist_report():
        # Readers keep a complete pending/failed manifest until success is durable.
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=report.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            try:
                stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
                os.replace(temporary, report)
            finally:
                temporary.unlink(missing_ok=True)

    persist_report()
    if apply and not issues:
        try:
            if updated:
                write_dataset(prospective, data_dir, changed={("object", p.stem) for p in updated})
        except Exception as exc:
            result["mode"] = "failed"
            result["issues"].append({"reason": f"Catalogue write failed: {exc}"})
            persist_report()
            raise
        result["mode"] = "apply"
        persist_report()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument(
        "--apply", action="store_true", help="Apply the manifest; default is dry-run."
    )
    parser.add_argument("--generated-at", help="Override audit timestamp for reproducible runs.")
    parser.add_argument(
        "--history-repo",
        type=Path,
        default=REPO_ROOT,
        help="Git repository containing the accepted baseline.",
    )
    parser.add_argument(
        "--base-ref",
        default="origin/main",
        help="Accepted Git baseline for immutable source history.",
    )
    args = parser.parse_args(argv)
    timestamp = args.generated_at or utc_timestamp()
    try:
        result = restore_notes(
            source=args.source,
            data_dir=args.data_dir,
            report=args.report,
            apply=args.apply,
            generated_at=timestamp,
            base_ref=args.base_ref,
            history_repo=args.history_repo,
        )
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        f"{result['mode']}: {len(result['changes'])} measurements, "
        f"{result['changed_files']} files, {len(result['issues'])} unresolved; "
        f"report: {args.report}"
    )
    return 1 if args.apply and result["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
