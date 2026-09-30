"""Read-only probes of selected ledger survivors; all source artifacts are temporary."""
# ruff: noqa: E402

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
import test_pig_staging as pig_fixtures
import test_staging_review as review_fixtures
import test_tpn_staging as tpn_fixtures

import gps_kataster_obiektow_tatr.pig_staging as pig
import gps_kataster_obiektow_tatr.staging_review as review
import gps_kataster_obiektow_tatr.tpn_staging as tpn

ledger = json.loads((Path(__file__).with_name("PBI-054-mutations.json")).read_text())
by_id = {m["id"]: m for m in ledger["non_killed"]}


def mutated_function(module, name, number):
    mutant_id = (
        f"gps_kataster_obiektow_tatr.{module.__name__.rsplit('.', 1)[1]}.x_{name}__mutmut_{number}"
    )
    entry = by_id[mutant_id]
    lines = inspect.getsource(getattr(module, name)).splitlines()
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
        assert len(old) == old_count, (mutant_id, old_count, old)
        assert lines[offset : offset + old_count] == old, mutant_id
        lines[offset : offset + old_count] = new
    namespace = dict(module.__dict__)
    exec(compile("\n".join(lines) + "\n", "<ledger mutant>", "exec"), namespace)
    return mutant_id, namespace[name]


def compare(module, name, number, run):
    mutant_id, function = mutated_function(module, name, number)
    original = run()
    with patch.object(module, name, function):
        try:
            changed = run()
        except Exception as exc:
            changed = {"exception": type(exc).__name__, "message": str(exc)}
    return {
        "id": mutant_id,
        "ledger_status": by_id[mutant_id]["status"],
        "original": original,
        "mutant": changed,
        "same": original == changed,
    }


with TemporaryDirectory(prefix="pbi054-mutation-probes-") as directory:
    tmp = Path(directory)
    source = tmp / "tpn.csv"
    candidates = tmp / "pig.json"
    tpn_fixtures._write_pig_staging(
        candidates,
        object_id="KSW-0001",
        cave_id="C-0001",
        nr_inwent="OTHER-INVENTORY",
        name="Distinct matching name",
        x_1992=152267.23,
        y_1992=563744.25,
    )
    tpn_fixtures._write_tpn_csv(
        source,
        [
            tpn_fixtures._tpn_row(
                nr_inwent="",
                name="Distinct matching name",
                globalid="{NEW-GLOBALID}",
                x_1992="152267.23",
                y_1992="563744.25",
            )
        ],
    )

    def match_run():
        report = tpn.build_tpn_staging(
            source,
            generated_at="2026-09-30T12:00:00Z",
            data_dir=tmp / "empty-data",
            pig_staging_path=candidates,
            prefix_resolver=tpn_fixtures.StubResolver(),
        )
        row = report.rows[0]
        return {
            "status": row.status,
            "object_id": row.object_id,
            "strategy": row.match_strategy,
            "measurements": len(report.matched_measurements),
            "new_objects": len(report.proposed_objects),
        }

    probes = [compare(tpn, "_match_tpn_row", 89, match_run)]
    refs = {
        "external_refs": [
            {"system": "PIG", "ref_type": "catalog_id", "external_id": "{OTHER-SYSTEM}"},
            {"system": "TPN", "ref_type": "source_globalid", "external_id": "{CURRENT-SYSTEM}"},
        ]
    }
    probes.append(
        compare(
            tpn,
            "_external_ref_ids",
            11,
            lambda: tpn._external_ref_ids(deepcopy(refs), system="TPN"),
        )
    )
    record = review_fixtures._object_data(cave_id="C-0001")
    record["notes"] = (
        "Staging proposal from PIG; requires operator review before final YAML.\n"
        "Original alias / source note"
    )
    probes.append(
        compare(
            review,
            "_finalize_staging_record",
            4,
            lambda: review._finalize_staging_record(deepcopy(record), source="PIG")["notes"],
        )
    )
    ref_a = {"system": "TPN", "ref_type": "source_globalid", "external_id": "{A}"}
    ref_b = {"system": "TPN", "ref_type": "source_globalid", "external_id": "{B}"}
    ref_c = {"system": "NR_INWENT", "ref_type": "inventory_number", "external_id": "C"}

    def refs_run():
        target = [deepcopy(ref_a)]
        review._append_unique_dicts(
            target, [deepcopy(ref_a), deepcopy(ref_b), deepcopy(ref_b), deepcopy(ref_c)]
        )
        return target

    probes.extend([compare(review, "_append_unique_dicts", number, refs_run) for number in (9, 13)])
    pig_source = tmp / "pig.csv"
    pig_fixtures._write_text(
        pig_source,
        "\n".join(
            [
                pig_fixtures._pig_header(),
                pig_fixtures._pig_row(
                    pig_id="1692",
                    name="Source name",
                    nr_inwent="T.F-09.33",
                    x_1992="152267,23",
                    y_1992="563744,25",
                    lat="49,23459299",
                    lon="19,87589498",
                    source_year="2010",
                ),
            ]
        ),
    )

    def pig_run():
        report = pig.build_pig_staging(
            pig_source,
            generated_at="2026-09-30T12:00:00Z",
            data_dir=tmp / "empty-data",
            prefix_resolver=pig_fixtures.StubResolver(),
        )
        return {
            "cave_notes": report.proposed_caves[0]["notes"],
            "observed_date": report.proposed_objects[0]["measurements"][0]["observed_date"],
            "source_date": report.proposed_objects[0]["measurements"][0]["source_date"],
            "issues": [issue.code for issue in report.issues],
        }

    probes.extend(
        [
            compare(pig, name, number, pig_run)
            for name, number in [("_format_morphometry", 23), ("_parse_pig_point", 116)]
        ]
    )
    text = pig_source.read_text().replace(",2010,", ",,")
    pig_source.write_text(text)
    probes.append(compare(pig, "_date_part", 1, pig_run))
    print(
        json.dumps(
            {
                "baseline_sha": ledger["baseline_sha"],
                "snapshot_totals": ledger["totals"],
                "probes": probes,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
