"""Finish an interrupted mutmut campaign without regenerating its mutants.

Run from the repository after freezing exit_code_by_key in manifest.json.
The manifest retains raw CLI outcomes; this script writes separate replay
outcomes for pending/timeout cases, using mutmut's existing test mapping.
"""
# ruff: noqa: E402

import argparse
import hashlib
import importlib
import json
import math
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mutmut.__main__ as mutmut

ROOT = Path(__file__).resolve().parents[3]
DEFAULT = ROOT / "build/verification/PBI-054-20260930"


def write_json(path, data):
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


def freeze_manifest(destination):
    """Capture metadata only after the mutmut CLI and its children have exited."""
    assert not destination.exists(), "Keep the original frozen raw outcomes"
    modules = {}
    for path in sorted((ROOT / "mutants").rglob("*.meta")):
        raw = path.read_bytes()
        text = raw.decode()
        complete_json = True
        try:
            codes = json.loads(text)["exit_code_by_key"]
        except json.JSONDecodeError:
            # Accept only a COMPLETE first object, never salvage individual keys.
            start = text.index("{", text.index('"exit_code_by_key"') + 18)
            codes, _ = json.JSONDecoder().raw_decode(text, start)
            complete_json = False
        source = str(path.relative_to(ROOT / "mutants").with_suffix(""))
        modules[source] = {
            "codes": codes,
            "meta_sha256": hashlib.sha256(raw).hexdigest(),
            "meta_complete_json": complete_json,
        }
        (destination.parent / path.name).write_bytes(raw)
    manifest = {
        "baseline_sha": "827a2f86f215080acda3317d4542ef6ebba8d0ae",
        "modules": modules,
    }
    counts = {}
    for module in modules.values():
        for code in module["codes"].values():
            label = str(code)
            counts[label] = counts.get(label, 0) + 1
    manifest["totals"] = counts
    write_json(destination, manifest)


def fingerprint(manifest):
    paths = {ROOT / "pyproject.toml", ROOT / "uv.lock"}
    paths.update((ROOT / "src").rglob("*.py"))
    paths.update((ROOT / "tests").rglob("*.py"))
    paths.add(ROOT / "mutants/mutmut-stats.json")
    paths.update(ROOT / "mutants" / name for name in manifest["modules"])
    result = hashlib.sha256()
    for path in sorted(paths):
        result.update(str(path.relative_to(ROOT)).encode())
        result.update(b"\0")
        result.update(path.read_bytes())
        result.update(b"\0")
    result.update(json.dumps(manifest, sort_keys=True).encode())
    return result.hexdigest()


def selected_tests(stats, key):
    tests = stats["tests_by_mangled_function_name"][mutmut.mangled_name_from_mutant_name(key)]
    return sorted(tests, key=lambda test: (stats["duration_by_test"][test], test))


def worker(args):
    manifest = json.loads(args.manifest.read_text())
    stats = json.loads((ROOT / "mutants/mutmut-stats.json").read_text())
    key = args.worker
    control = key in {"baseline", "forced-fail"}
    test_key = (
        "gps_kataster_obiektow_tatr.staging_review.x__selected_proposal_ids__mutmut_4"
        if control
        else key
    )
    tests = selected_tests(stats, test_key)
    assert tests
    mutmut.ensure_config_loaded()
    mutmut.setup_source_paths()
    assert mutmut.load_stats()
    os.environ["MUTANT_UNDER_TEST"] = "" if control else key
    module = importlib.import_module(test_key.rsplit(".x", 1)[0])
    assert Path(module.__file__).resolve().is_relative_to(ROOT / "mutants")
    started = time.monotonic()
    if key == "forced-fail":
        mutmut.run_forced_fail_test(mutmut.PytestRunner())
        code = 0  # Official control raises/exits on an undetected forced failure.
        tests = []  # Official control uses the configured suite, not test_key's map.
    else:
        code = mutmut.PytestRunner().run_tests(mutant_name=test_key, tests=tests)
    result = {
        "id": key,
        "exit_code": code,
        "seconds": time.monotonic() - started,
        "selected_tests": tests,
        "instrumented_module": str(Path(module.__file__).relative_to(ROOT)),
        "fingerprint": fingerprint(manifest),
    }
    if key == "forced-fail":
        result["control_selection"] = "PytestRunner.run_forced_fail: configured suite"
    write_json(args.out / (key + ".json"), result)
    return code


def run_case(args, stats, campaign_fingerprint, key, raw_code):
    destination = args.out / (key + ".json")
    test_key = (
        "gps_kataster_obiektow_tatr.staging_review.x__selected_proposal_ids__mutmut_4"
        if key in {"baseline", "forced-fail"}
        else key
    )
    tests = selected_tests(stats, test_key)
    estimate = sum(stats["duration_by_test"][test] for test in tests)
    limit = math.ceil((estimate + 1) * 15)
    expected_tests = [] if key == "forced-fail" else tests
    if destination.exists():
        cached = json.loads(destination.read_text())
        if (
            cached.get("fingerprint") == campaign_fingerprint
            and cached.get("exit_code") in {0, 1}
            and cached.get("selected_tests") == expected_tests
        ):
            return cached
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--manifest",
        str(args.manifest),
        "--out",
        str(args.out),
        "--worker",
        key,
    ]
    with (args.out / (key + ".log")).open("w") as log:
        try:
            process = subprocess.run(
                command,
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=limit,
                check=False,
            )
            result = json.loads(destination.read_text()) if destination.exists() else {}
            assert process.returncode == result["exit_code"]
            assert result["fingerprint"] == campaign_fingerprint
            assert result["selected_tests"] == expected_tests
        except subprocess.TimeoutExpired:
            result = {"id": key, "timeout": True, "fingerprint": campaign_fingerprint}
        except (KeyError, AssertionError):
            result = {"id": key, "tool_error": True, "fingerprint": campaign_fingerprint}
    result.update(
        {
            "raw_exit_code": raw_code,
            "estimate_seconds": estimate,
            "wall_limit_seconds": limit,
        }
    )
    write_json(destination, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=DEFAULT / "campaign-before-replay/manifest.json"
    )
    parser.add_argument("--out", type=Path, default=DEFAULT / "completion")
    parser.add_argument("--max-workers", type=int, default=6)
    parser.add_argument("--worker")
    parser.add_argument("--freeze-manifest", action="store_true")
    args = parser.parse_args()
    args.manifest = args.manifest.resolve()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    assert Path.cwd() == ROOT
    if args.freeze_manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        freeze_manifest(args.manifest)
    if args.worker:
        return worker(args)
    assert 1 <= args.max_workers <= 6
    manifest = json.loads(args.manifest.read_text())
    stats = json.loads((ROOT / "mutants/mutmut-stats.json").read_text())
    for source, record in manifest["modules"].items():
        names = set(
            re.findall(
                r"^\s*def (x[^\s(]*__mutmut_\d+)\(",
                (ROOT / "mutants" / source).read_text(),
                re.MULTILINE,
            )
        )
        assert names == {key.split(".")[-1] for key in record["codes"]}
    assert sum(len(m["codes"]) for m in manifest["modules"].values()) == 8962
    campaign_fingerprint = fingerprint(manifest)
    for control in ("baseline", "forced-fail"):
        result = run_case(args, stats, campaign_fingerprint, control, None)
        assert result.get("exit_code") == 0, result
        print(json.dumps({k: v for k, v in result.items() if k != "selected_tests"}), flush=True)
    cases = {
        key: code
        for module in manifest["modules"].values()
        for key, code in module["codes"].items()
        if code is None or mutmut.status_by_exit_code[code] == "timeout"
    }
    print(f"Replaying {len(cases)} pending/timeout cases", flush=True)
    errors = []
    with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
        jobs = {
            pool.submit(run_case, args, stats, campaign_fingerprint, key, code): key
            for key, code in sorted(cases.items())
        }
        for ordinal, job in enumerate(as_completed(jobs), 1):
            result = job.result()
            if result.get("exit_code") not in {0, 1, 5}:
                errors.append(result)
            print(
                json.dumps(
                    {"done": ordinal, **{k: v for k, v in result.items() if k != "selected_tests"}}
                ),
                flush=True,
            )
    assert fingerprint(manifest) == campaign_fingerprint
    write_json(
        args.out / "summary.json",
        {"fingerprint": campaign_fingerprint, "replayed": len(cases), "errors": errors},
    )
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
