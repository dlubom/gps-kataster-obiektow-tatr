"""Replay pending/timeouts in one frozen PBI-067 mutmut workspace.

The input is the captured stage JSON (raw_exit_codes/test_mapping/durations).
A baseline workspace can be archived separately from the new campaign.
Never regenerate its instrumented code or stats between capture and replay.
"""

import argparse
import hashlib
import importlib
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mutmut.__main__ as mutmut


def fingerprint(workspace):
    digest = hashlib.sha256()
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
    assert fingerprint(workspace) == manifest["workspace_fingerprint"]
    stats = json.loads((workspace / "mutants/mutmut-stats.json").read_text())
    scope = {
        "validator": (
            "_validate_duplicate_tpn_globalids",
            "_validate_cross_references",
            "_validate_object_attachments",
            "_valid_http_url",
            "_validate_measurement_distances",
        )
    }
    names = {
        f"gps_kataster_obiektow_tatr.{module}.x_{name}"
        for module, funcs in scope.items()
        for name in funcs
    }
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
    for module in scope:
        path = workspace / f"mutants/src/gps_kataster_obiektow_tatr/{module}.py.meta"
        codes = json.loads(path.read_text())["exit_code_by_key"]
        actual_codes.update(
            {
                key: code
                for key, code in codes.items()
                if any(key.startswith(name + "__mutmut_") for name in names)
            }
        )
    assert actual_codes == manifest["raw_exit_codes"]


class ForcedFailureProbe:
    def __init__(self):
        self.seen = 0

    def pytest_runtest_makereport(self, item, call):
        if call.excinfo is not None and isinstance(
            call.excinfo.value, mutmut.MutmutProgrammaticFailException
        ):
            self.seen += 1


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
        "gps_kataster_obiektow_tatr.validator.x__valid_http_url__mutmut_1" if control else key
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
    run_code = ControlledRunner(probe).run_tests(mutant_name=test_key, tests=tests)
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
        "gps_kataster_obiektow_tatr.validator.x__valid_http_url__mutmut_1" if control else key
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
    with (args.out / (key + ".log")).open("w") as log:
        result = subprocess.run(
            command,
            cwd=args.workspace,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=limit,
            check=False,
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
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--worker")
    parser.add_argument("--expected-fingerprint")
    args = parser.parse_args()
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
    keys = [
        key
        for key, code in manifest["raw_exit_codes"].items()
        if code is None or mutmut.status_by_exit_code[code] == "timeout"
    ]
    records = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(run_case, args, manifest, expected_fingerprint, key) for key in keys]
        for job in as_completed(jobs):
            record = job.result()
            records.append(record)
            print(json.dumps({k: record[k] for k in ("id", "exit_code", "seconds")}), flush=True)
    assert fingerprint(args.workspace) == expected_fingerprint
    (args.out / "summary.json").write_text(
        json.dumps(
            {"fingerprint": expected_fingerprint, "controls": controls, "replays": records},
            indent=2,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
