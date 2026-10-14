"""Join a frozen full capture with verified bounded replays into a durable ledger."""

import argparse
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

import mutmut.__main__ as mutmut


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    assert not args.out.exists()
    path = Path(__file__).with_name("PBI-054-final-replay.py")
    spec = importlib.util.spec_from_file_location("replay_helpers", path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    manifest = json.loads(args.manifest.read_text())
    helper.verify_capture(args.workspace, manifest)
    replay = json.loads(args.replay.read_text())
    fingerprint = manifest["workspace_fingerprint"]
    assert replay["fingerprint"] == fingerprint
    controls = replay["controls"]
    assert set(controls) == {"baseline", "forced-fail"}
    clean, forced = controls["baseline"], controls["forced-fail"]
    assert clean["pytest_exit_code"] == 0 and clean["forced_exceptions_seen"] == 0
    assert forced["pytest_exit_code"] == 1 and forced["forced_exceptions_seen"] > 0
    assert clean["selected_tests"] == forced["selected_tests"]
    assert set(clean["selected_tests"]) == set(manifest["durations"])
    for key, record in controls.items():
        assert record["id"] == key and record["exit_code"] == 0
        assert record["fingerprint"] == fingerprint
    expected_replays = {
        key
        for key, code in manifest["raw_exit_codes"].items()
        if code is None or mutmut.status_by_exit_code[code] == "timeout"
    }
    records = {record["id"]: record for record in replay["replays"]}
    assert len(records) == len(replay["replays"])
    assert set(records) == expected_replays
    outcomes = dict(manifest["raw_exit_codes"])
    for key, record in records.items():
        assert record["fingerprint"] == fingerprint
        assert record["raw_exit_code"] == outcomes[key]
        assert record["selected_tests"] == helper.selection(manifest, key)
        assert record["exit_code"] in {0, 1}
        assert record["pytest_exit_code"] == record["exit_code"]
        assert record["forced_exceptions_seen"] == 0
        outcomes[key] = record["exit_code"]
    modules = defaultdict(Counter)
    non_killed = []
    for key, code in outcomes.items():
        assert code in {0, 1, 33}, (key, code)
        status = mutmut.status_by_exit_code[code]
        module = key.rsplit(".x", 1)[0]
        modules[module][status] += 1
        if status != "killed":
            non_killed.append({"id": key, "status": status, "diff": manifest["diffs"][key]})
    report = {
        **manifest,
        "campaign_state": "complete: one fresh configured generation, CLI plus bounded replay",
        "replay_sha256": hashlib.sha256(args.replay.read_bytes()).hexdigest(),
        "capture_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "controls": controls,
        "replays": replay["replays"],
        "all_outcomes": outcomes,
        "final_module_totals": {module: dict(counts) for module, counts in modules.items()},
        "totals": dict(Counter(mutmut.status_by_exit_code[code] for code in outcomes.values())),
        "non_killed": non_killed,
        "analysis_ref": "PBI-054-final-mutation-analysis.md",
        "protocol_ref": "PBI-054.md",
    }
    helper.verify_capture(args.workspace, manifest)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"ids": len(outcomes), "totals": report["totals"]}))


if __name__ == "__main__":
    main()
