"""Require all disjoint complete shards, validate every control, then build ledger."""

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--shards", type=Path, required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    path = Path(__file__).with_name("PBI-054-final-replay.py")
    spec = importlib.util.spec_from_file_location("replay", path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    campaign = args.campaign.resolve()
    manifest = json.loads((campaign / "capture.json").read_text())
    helper.verify_capture(campaign / "workspace", manifest)
    keys = sorted(key for key, code in manifest["raw_exit_codes"].items() if code is None)
    assert all(code in {None, 33} for code in manifest["raw_exit_codes"].values())
    union = sorted(manifest["durations"], key=lambda key: (manifest["durations"][key], key))
    shards = {}
    for path in args.shards.rglob("summary.json"):
        shard = json.loads(path.read_text())
        index = shard["shard_index"]
        assert index not in shards and 0 <= index < args.count
        assert shard["shard_count"] == args.count
        assert shard["fingerprint"] == manifest["workspace_fingerprint"]
        assert shard["execution_context"] == manifest["execution_context"]
        assert shard["frozen_archive_sha256"] == os.environ["PBI054_ARCHIVE_SHA"]
        assert (
            shard["capture_sha256"]
            == hashlib.sha256((campaign / "capture.json").read_bytes()).hexdigest()
        )
        assert set(shard["controls"]) == {"baseline", "forced-fail"}
        for key, record in shard["controls"].items():
            assert record["id"] == key and record["exit_code"] == 0
            assert record["fingerprint"] == manifest["workspace_fingerprint"]
            assert record["selected_tests"] == union
            assert record["pytest_exit_code"] == (1 if key == "forced-fail" else 0)
            assert (
                record["forced_exceptions_seen"] > 0
                if key == "forced-fail"
                else (record["forced_exceptions_seen"] == 0)
            )
        actual = [record["id"] for record in shard["replays"]]
        assert len(actual) == len(set(actual))
        assert set(actual) == set(keys[index :: args.count])
        shards[index] = shard
    assert set(shards) == set(range(args.count))
    merged = {
        "fingerprint": manifest["workspace_fingerprint"],
        "controls": shards[0]["controls"],
        "replays": [record for index in range(args.count) for record in shards[index]["replays"]],
    }
    merge_path = campaign / "merged-replay.json"
    assert not merge_path.exists()
    merge_path.write_text(json.dumps(merged) + "\n")
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("PBI-054-final-ledger.py")),
            "--manifest",
            str(campaign / "capture.json"),
            "--workspace",
            str(campaign / "workspace"),
            "--replay",
            str(merge_path),
            "--out",
            str(args.out),
        ],
        check=True,
    )
    ledger = json.loads(args.out.read_text())
    ledger["shard_controls"] = {str(index): shards[index]["controls"] for index in shards}
    ledger["shard_partition"] = "sorted pending ID list, index::16; every ID checked once"
    ledger["frozen_archive_sha256"] = os.environ["PBI054_ARCHIVE_SHA"]
    args.out.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
