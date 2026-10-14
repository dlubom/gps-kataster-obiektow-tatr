"""Independently check the durable full Linux ledger using only its data.

Run with --ledger PATH. No product or mutant executes. The function/test
mapping is stored once; exact ordered selections are reconstructed here.
Requires CPython 3.12, matching the campaign's floating-point sum semantics.
"""

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path


def critical_ids(directory):
    result = {}

    def add(pbi, keys):
        for key in keys:
            result.setdefault(key, []).append(pbi)

    def read(pbi):
        return json.loads((directory / f"PBI-{pbi}-mutations.json").read_text())

    add("059", (key for key in read("059")["all_outcomes"] if ".x__parse_positive_int__" in key))
    for pbi in ("062", "067"):
        add(pbi, read(pbi)["critical_transitions"])
    for pbi, field in (
        ("063", "before_after"),
        ("064", "critical_before_after"),
        ("065", "critical_comparisons"),
    ):
        add(pbi, (record["id"] for record in read(pbi)[field]))
    add("066", read("066")["critical_ids"])
    add(
        "058",
        [
            f"gps_kataster_obiektow_tatr.tpn_staging.x__match_tpn_row__mutmut_{i}"
            for i in range(1, 20)
        ]
        + [
            f"gps_kataster_obiektow_tatr.tpn_staging.x__unique_candidate_outcome__mutmut_{i}"
            for i in range(1, 18)
        ],
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()
    if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 12):
        parser.error("Use the frozen project environment with CPython 3.12 for exact time sums.")
    ledger = json.loads(args.ledger.read_text())
    outcomes = ledger["all_outcomes"]
    raw = ledger["raw_exit_codes"]
    assert len(outcomes) == len(raw) == 10218
    assert len(ledger["modules"]) == 17
    assert set(outcomes) == set(raw) == set(ledger["diffs"])
    assert set(raw.values()) == {None, 33}
    assert set(outcomes.values()) == {0, 1, 33}
    names = {key.rsplit("__mutmut_", 1)[0] for key in raw}
    assert set(ledger["test_mapping"]) == names
    union = {test for selected in ledger["test_mapping"].values() for test in selected}
    assert set(ledger["durations"]) == union
    assert len(union) == 1595

    def order(tests):
        return sorted(tests, key=lambda test: (ledger["durations"][test], test))

    union_ordered = order(union)
    replay = {record["id"]: record for record in ledger["replays"]}
    assert len(replay) == len(ledger["replays"]) == 10193
    assert set(replay) == {key for key, code in raw.items() if code is None}
    fingerprint = ledger["workspace_fingerprint"]
    for key, code in raw.items():
        name = key.rsplit("__mutmut_", 1)[0]
        selected = order(ledger["test_mapping"][name])
        if code == 33:
            assert selected == [] and outcomes[key] == 33
            continue
        assert selected
        record = replay[key]
        assert record["mapped_function"] == name
        assert record["selected_test_count"] == len(selected)
        estimate = sum(ledger["durations"][test] for test in selected)
        assert record["estimate_seconds"] == estimate
        assert record["wall_limit_seconds"] == math.ceil((estimate + 1) * 15)
        assert record["raw_exit_code"] is None
        assert record["fingerprint"] == fingerprint
        assert record["exit_code"] == record["pytest_exit_code"] == outcomes[key]
        assert record["forced_exceptions_seen"] == 0
        assert record["seconds"] >= 0
        module = key.rsplit(".x", 1)[0].replace(".", "/")
        assert record["instrumented_module"] == f"mutants/src/{module}.py"
    assert set(ledger["shard_controls"]) == {str(i) for i in range(16)}
    for controls in ledger["shard_controls"].values():
        assert set(controls) == {"baseline", "forced-fail"}
        for key, record in controls.items():
            assert record["id"] == key and record["exit_code"] == 0
            assert record["selected_tests"] == union_ordered
            assert record["fingerprint"] == fingerprint
            assert record["pytest_exit_code"] == (1 if key == "forced-fail" else 0)
            assert (
                record["forced_exceptions_seen"] > 0
                if key == "forced-fail"
                else (record["forced_exceptions_seen"] == 0)
            )
    status = {0: "survived", 1: "killed", 33: "no tests"}
    totals = Counter(status[code] for code in outcomes.values())
    assert dict(totals) == ledger["totals"]
    actual_non_killed = {record["id"]: record for record in ledger["non_killed"]}
    assert len(actual_non_killed) == len(ledger["non_killed"]) == 1746
    assert set(actual_non_killed) == {key for key, code in outcomes.items() if code != 1}
    for key, record in actual_non_killed.items():
        assert record["status"] == status[outcomes[key]]
        assert record["diff"] == ledger["diffs"][key]
    critical = critical_ids(Path(__file__).parent)
    assert len(critical) == 243 and sum(map(len, critical.values())) == 245
    assert all(outcomes[key] == 1 for key in critical)
    reviewed_count = None
    if args.review:
        review = json.loads(args.review.read_text())
        assert review["raw_ledger_sha256"] == ledger["raw_ci_ledger_sha256"]
        assert review["fingerprint"] == fingerprint
        assert review["runtime"] == ledger["runtime"]
        assert review["execution_context"] == ledger["execution_context"]
        assert review["totals"] == ledger["totals"]
        assessed = {record["id"]: record for record in review["assessments"]}
        assert len(assessed) == len(review["assessments"]) == 1746
        assert set(assessed) == set(actual_non_killed)
        for key, record in assessed.items():
            diff = ledger["diffs"][key]
            assert record["diff"] == diff
            assert record["diff_sha256"] == hashlib.sha256(diff.encode()).hexdigest()
            assert record["status"] == status[outcomes[key]]
            assert record["classification"] and record["assessment"]
            assert record["ref"]["source"] and record["ref"]["family_or_pbi"]
            assert record["original_product_defect_inferred_from_mutant"] is False
        assert (
            dict(Counter(record["classification"] for record in assessed.values()))
            == review["classification_counts"]
        )
        reviewed_count = len(assessed)
    print(
        json.dumps(
            {
                "ledger_sha256": hashlib.sha256(args.ledger.read_bytes()).hexdigest(),
                "ids": len(outcomes),
                "totals": dict(totals),
                "critical_unique": len(critical),
                "critical_references": sum(map(len, critical.values())),
                "critical_all_killed": True,
                "all_10193_replays_valid": True,
                "controls": 16,
                "non_killed_assessments_checked": reviewed_count,
                "real_mutant_or_product_execution": False,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
