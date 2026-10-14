"""Replay pending/timeouts in one frozen PBI-054 final mutmut workspace.

The input is the captured stage JSON (raw_exit_codes/test_mapping/durations).
A baseline workspace can be archived separately from the new campaign.
Never regenerate its instrumented code or stats between capture and replay.
"""

import argparse
import errno
import hashlib
import importlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from importlib.metadata import version
from pathlib import Path

import mutmut.__main__ as mutmut


def runtime_identity():
    return {
        "python": sys.version,
        "executable": sys.executable,
        "packages": {
            name: version(name)
            for name in ("mutmut", "pytest", "libcst", "pyproj", "pyshp", "PyYAML", "jsonschema")
        },
    }


def fingerprint(workspace):
    digest = hashlib.sha256()
    digest.update(json.dumps(runtime_identity(), sort_keys=True).encode())
    paths = {
        workspace / "pyproject.toml",
        workspace / "uv.lock",
        workspace / "mutants/pyproject.toml",
    }
    paths.add(workspace / "mutants/mutmut-stats.json")
    for directory in ("src", "tests", "config", "data/shapes", "schema", "scripts"):
        paths.update(
            path
            for path in (workspace / "mutants" / directory).rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
    for path in sorted(paths):
        digest.update(str(path.relative_to(workspace)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def selection(manifest, key):
    name = mutmut.mangled_name_from_mutant_name(key)
    return sorted(
        manifest["test_mapping"][name], key=lambda test: (manifest["durations"][test], test)
    )


def verify_capture(workspace, manifest):
    assert not (workspace / "HARNESS-INVALID.jsonl").exists(), "Reject harness failures"
    assert runtime_identity() == manifest["runtime"]
    assert fingerprint(workspace) == manifest["workspace_fingerprint"]
    stats = json.loads((workspace / "mutants/mutmut-stats.json").read_text())
    names = {mutmut.mangled_name_from_mutant_name(key) for key in manifest["raw_exit_codes"]}
    assert set(manifest["test_mapping"]) == names
    for name in names:
        assert sorted(manifest["test_mapping"][name]) == sorted(
            stats["tests_by_mangled_function_name"].get(name, [])
        )
    tests = {test for selected in manifest["test_mapping"].values() for test in selected}
    assert set(manifest["durations"]) == tests
    for test in tests:
        assert stats["duration_by_test"][test] == manifest["durations"][test]
    actual_codes = {}
    for record in manifest["modules"].values():
        path = workspace / record["source"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["source_sha256"]
        meta = path.with_suffix(".py.meta")
        assert hashlib.sha256(meta.read_bytes()).hexdigest() == record["meta_sha256"]
        actual_codes.update(json.loads(meta.read_text())["exit_code_by_key"])
    assert actual_codes == manifest["raw_exit_codes"]


class ForcedFailureProbe:
    def __init__(self):
        self.seen = 0
        self.disk_failed = False

    def pytest_runtest_makereport(self, item, call):
        if call.excinfo is not None:
            self.disk_failed |= disk_error(call.excinfo.value)
        if call.excinfo is not None and isinstance(
            call.excinfo.value, mutmut.MutmutProgrammaticFailException
        ):
            self.seen += 1

    def pytest_internalerror(self, excrepr, excinfo):
        self.disk_failed |= disk_error(excinfo.value)


def disk_error(error, seen=None):
    seen = set() if seen is None else seen
    if error is None or id(error) in seen:
        return False
    seen.add(id(error))
    return (
        isinstance(error, OSError)
        and error.errno == errno.ENOSPC
        or disk_error(error.__cause__, seen)
        or disk_error(error.__context__, seen)
        or any(disk_error(child, seen) for child in getattr(error, "exceptions", []))
    )


class ControlledRunner(mutmut.PytestRunner):
    def __init__(self, probe):
        super().__init__()
        self.probe = probe

    def execute_pytest(self, params, **kwargs):
        return super().execute_pytest(params, plugins=[self.probe], **kwargs)


def worker(args, manifest, expected_fingerprint):
    verify_capture(args.workspace, manifest)
    assert fingerprint(args.workspace) == expected_fingerprint
    assert not (args.out / (args.worker + ".json")).exists()
    mutmut.ensure_config_loaded()
    mutmut.setup_source_paths()
    assert mutmut.load_stats()
    key = args.worker
    control = key in {"baseline", "forced-fail"}
    test_key = (
        next(key for key in manifest["raw_exit_codes"] if selection(manifest, key))
        if control
        else key
    )
    tests = (
        sorted(manifest["durations"], key=lambda test: (manifest["durations"][test], test))
        if control
        else selection(manifest, test_key)
    )
    assert tests
    os.environ["MUTANT_UNDER_TEST"] = "fail" if key == "forced-fail" else "" if control else key
    module = importlib.import_module(test_key.rsplit(".x", 1)[0])
    assert Path(module.__file__).resolve().is_relative_to(args.workspace / "mutants")
    start = time.monotonic()
    probe = ForcedFailureProbe()
    assert shutil.disk_usage(args.workspace).free > 128 * 1024**2
    run_code = ControlledRunner(probe).run_tests(mutant_name=test_key, tests=tests)
    assert shutil.disk_usage(args.workspace).free > 128 * 1024**2
    assert not probe.disk_failed, "Do not classify ENOSPC as killed"
    if key == "forced-fail":
        assert run_code == 1 and probe.seen > 0
        code = 0  # Effective control success; actual pytest exit remains recorded.
    else:
        code = run_code
        assert code == 0 if control else code in {0, 1}
    assert probe.seen == 0 if key != "forced-fail" else probe.seen > 0
    assert fingerprint(args.workspace) == expected_fingerprint
    record = {
        "id": key,
        "exit_code": code,
        "pytest_exit_code": run_code,
        "forced_exceptions_seen": probe.seen,
        "seconds": time.monotonic() - start,
        "selected_tests": tests,
        "fingerprint": expected_fingerprint,
        "instrumented_module": str(Path(module.__file__).relative_to(args.workspace)),
    }
    if key == "forced-fail":
        record["control_selection"] = (
            "Same union of mapped tests as clean control; fail trampoline observed"
        )
    (args.out / (key + ".json")).write_text(json.dumps(record, indent=2) + "\n")
    return code


def run_case(args, manifest, expected_fingerprint, key):
    control = key in {"baseline", "forced-fail"}
    test_key = (
        next(key for key in manifest["raw_exit_codes"] if selection(manifest, key))
        if control
        else key
    )
    tests = (
        sorted(manifest["durations"], key=lambda test: (manifest["durations"][test], test))
        if control
        else selection(manifest, test_key)
    )
    assert not (args.out / (key + ".json")).exists()
    estimate = sum(manifest["durations"][test] for test in tests)
    limit = math.ceil((estimate + 1) * 15)
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--manifest",
        str(args.manifest),
        "--workspace",
        str(args.workspace),
        "--out",
        str(args.out),
        "--worker",
        key,
        "--expected-fingerprint",
        expected_fingerprint,
    ]
    with (
        tempfile.TemporaryDirectory(prefix="pytest-replay-", dir=args.out) as temporary,
        (args.out / (key + ".log")).open("w") as log,
    ):
        result = subprocess.run(
            command,
            cwd=args.workspace,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=limit,
            check=False,
            env={**os.environ, "TMPDIR": temporary},
        )
    record = json.loads((args.out / (key + ".json")).read_text())
    assert record["exit_code"] == result.returncode
    assert record["id"] == key
    assert record["exit_code"] in ({0} if control else {0, 1})
    assert record["fingerprint"] == expected_fingerprint
    assert record["selected_tests"] == tests
    record.update(
        raw_exit_code=None if control else manifest["raw_exit_codes"][key],
        estimate_seconds=estimate,
        wall_limit_seconds=limit,
    )
    (args.out / (key + ".json")).write_text(json.dumps(record, indent=2) + "\n")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-workers", type=int, default=6)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--worker")
    parser.add_argument("--expected-fingerprint")
    args = parser.parse_args()
    assert args.max_workers > 0
    assert 0 <= args.shard_index < args.shard_count
    args.manifest, args.workspace, args.out = (
        path.resolve() for path in (args.manifest, args.workspace, args.out)
    )
    if args.worker:
        assert args.out.is_dir()
    else:
        args.out.mkdir(exist_ok=False, parents=True)
    os.chdir(args.workspace)
    manifest = json.loads(args.manifest.read_text())
    if args.worker:
        assert args.expected_fingerprint
        return worker(args, manifest, args.expected_fingerprint)
    verify_capture(args.workspace, manifest)
    expected_fingerprint = fingerprint(args.workspace)
    controls = {
        key: run_case(args, manifest, expected_fingerprint, key)
        for key in ("baseline", "forced-fail")
    }
    keys = sorted(
        key
        for key, code in manifest["raw_exit_codes"].items()
        if code is None or mutmut.status_by_exit_code[code] == "timeout"
    )[args.shard_index :: args.shard_count]
    records = []
    with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
        # Keep only a bounded active window: a harness error must not enqueue
        # the rest of the campaign while executor.__exit__ waits for workers.
        remaining = iter(keys)
        jobs = set()
        for _ in range(args.max_workers):
            key = next(remaining, None)
            if key is not None:
                jobs.add(pool.submit(run_case, args, manifest, expected_fingerprint, key))
        while jobs:
            done, jobs = wait(jobs, return_when=FIRST_COMPLETED)
            completed = [job.result() for job in done]  # fail before submitting any more
            for record in completed:
                records.append(record)
                print(
                    json.dumps({k: record[k] for k in ("id", "exit_code", "seconds")}), flush=True
                )
                key = next(remaining, None)
                if key is not None:
                    jobs.add(pool.submit(run_case, args, manifest, expected_fingerprint, key))
    assert fingerprint(args.workspace) == expected_fingerprint
    (args.out / "summary.json").write_text(
        json.dumps(
            {
                "fingerprint": expected_fingerprint,
                "shard_index": args.shard_index,
                "shard_count": args.shard_count,
                "frozen_archive_sha256": os.environ.get("PBI054_ARCHIVE_SHA"),
                "capture_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
                "execution_context": {
                    key: os.environ.get(key) for key in manifest.get("execution_context", {})
                },
                "controls": controls,
                "replays": records,
            },
            indent=2,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
