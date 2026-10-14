from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / "docs/asdlc/verification"
passed = []


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, DOC / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


GEN = load("cloud_generate", "PBI-054-cloud-generate.py")
JOIN = load("cloud_join", "PBI-054-cloud-join.py")
REP = load("frozen_replay", "PBI-054-final-replay.py")
LED = load("frozen_ledger", "PBI-054-final-ledger.py")


def report(label):
    passed.append(label)
    print(label + ": PASS", flush=True)


class Meta:
    def __init__(self):
        self.exit_code_by_key = {}
        self.saved = 0

    def save(self):
        self.saved += 1


with tempfile.TemporaryDirectory(prefix="PBI054-gen-stub-", dir="/tmp") as td:
    cwd = Path.cwd()
    root = Path(td).resolve()
    events = []
    metas = [Meta() for _ in range(17)]
    mutants = []
    mapping = {}
    for i in range(10218):
        j = i % 17
        k = f"audit.module{j}.x_f__mutmut_{i + 1}"
        metas[j].exit_code_by_key[k] = None
        mutants.append((metas[j], k, None))
        if j != 16:
            mapping[GEN.mutmut.mangled_name_from_mutant_name(k)] = ["tests/t.py::test_case"]

    def event(label):
        def f(*args, **kwargs):
            events.append(label)

        return f

    def create(children):
        assert children == 2
        events.append("create")
        return SimpleNamespace(mutated=17, unmodified=0)

    def collect(*, mutant_names):
        assert mutant_names == []
        events.append("collect")
        return mutants, {str(i): meta for i, meta in enumerate(metas)}

    def stats(runner):
        assert isinstance(runner, GEN.mutmut.PytestRunner)
        assert runner.scratch == root / "campaign-tmp"
        events.append("stats")

    def capture(command, **kwargs):
        assert kwargs == {"check": True}
        assert command[0] == sys.executable
        assert command[1] == str(DOC / "PBI-054-final-capture.py")
        assert command[-1] == "audit-sha"
        events.append("capture")
        assert all(meta.saved == 1 for meta in metas)
        for meta, key, _ in mutants:
            assert meta.exit_code_by_key[key] == (33 if key.startswith("audit.module16.") else None)
        return SimpleNamespace(returncode=0)

    try:
        os.chdir(root)
        with (
            patch.object(
                GEN.mutmut.mutmut,
                "config",
                SimpleNamespace(
                    type_check_command=None,
                    pytest_add_cli_args=[],
                    pytest_add_cli_args_test_selection=[],
                    tests_dir=[],
                ),
            ),
            patch.object(GEN.mutmut.mutmut, "tests_by_mangled_function_name", mapping),
            patch.object(GEN.mutmut, "PytestRunner", GEN.mutmut.PytestRunner),
            patch.object(GEN.mutmut, "ensure_config_loaded", event("config")),
            patch.object(GEN.mutmut, "copy_src_dir", event("copy_src")),
            patch.object(GEN.mutmut, "copy_also_copy_files", event("copy_other")),
            patch.object(GEN.mutmut, "setup_source_paths", event("paths")),
            patch.object(GEN.mutmut, "store_lines_covered_by_tests", event("covered")),
            patch.object(GEN.mutmut, "create_mutants", create),
            patch.object(GEN.mutmut, "run_stats_collection", stats),
            patch.object(GEN.mutmut, "collect_source_file_mutation_data", collect),
            patch("subprocess.run", capture),
            patch.object(sys, "argv", ["audit", "--base-sha", "audit-sha"]),
            patch.dict(os.environ, {}, clear=False),
        ):
            GEN.main()
        assert events == [
            "config",
            "copy_src",
            "copy_other",
            "paths",
            "covered",
            "create",
            "stats",
            "collect",
            "capture",
        ]
        report("generation_stub_exact_API_order_scope33_and_capture")
    finally:
        os.chdir(cwd)


def fixture(root, mode=None):
    campaign = root / "campaign"
    workspace = campaign / "workspace"
    shards = root / "shards"
    out = root / "ledger.json"
    for name in ("pyproject.toml", "uv.lock", "mutants/pyproject.toml"):
        p = workspace / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("frozen")
    module = "gps_kataster_obiektow_tatr.audit"
    keys = [f"{module}.x_f__mutmut_{i}" for i in range(1, 17)] + [
        f"{module}.x_g__mutmut_{i}" for i in range(1, 17)
    ]
    empty = f"{module}.x_empty__mutmut_1"
    raw = {**{k: None for k in keys}, empty: 33}
    tf, tg = "tests/a.py::test_f", "tests/b.py::test_g"
    mapping = {module + ".x_f": [tf], module + ".x_g": [tg], module + ".x_empty": []}
    if mode == "bad33":
        mapping[module + ".x_empty"] = [tf]
    if mode == "empty_pending":
        mapping[module + ".x_f"] = []
    durations = {tf: 0.1, tg: 0.2}
    durations = {t: durations[t] for t in {t for ts in mapping.values() for t in ts}}
    stats = {
        "tests_by_mangled_function_name": mapping,
        "duration_by_test": durations,
        "stats_time": 0.3,
    }
    (workspace / "mutants/mutmut-stats.json").write_text(json.dumps(stats))
    source = workspace / "mutants/src/gps_kataster_obiektow_tatr/audit.py"
    source.parent.mkdir(parents=True)
    source.write_text("def audit_marker():\n    pass\n")
    meta = source.with_suffix(".py.meta")
    meta.write_text(json.dumps({"exit_code_by_key": raw}))
    context = {
        k: "audit"
        for k in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA", "GITHUB_WORKFLOW_REF")
    }
    manifest = {
        "baseline_sha": "audit",
        "execution_context": context,
        "runtime": REP.runtime_identity(),
        "scope": {},
        "workspace_fingerprint": REP.fingerprint(workspace),
        "raw_exit_codes": raw,
        "test_mapping": mapping,
        "durations": durations,
        "diffs": {k: "--- original\n+++ mutant\n-pass\n+None" for k in raw},
        "modules": {
            module: {
                "source": str(source.relative_to(workspace)),
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "meta_sha256": hashlib.sha256(meta.read_bytes()).hexdigest(),
            }
        },
    }
    capture = campaign / "capture.json"
    capture.write_text(json.dumps(manifest))
    cap_sha = hashlib.sha256(capture.read_bytes()).hexdigest()
    union = sorted(durations, key=lambda t: (durations[t], t))
    fp = manifest["workspace_fingerprint"]

    def record(key, control=False):
        tests = union if control else REP.selection(manifest, key)
        estimate = sum(durations[t] for t in tests)
        code = 0 if control or ".x_f__" in key else 1
        return {
            "id": key,
            "exit_code": code,
            "pytest_exit_code": 1 if key == "forced-fail" else code,
            "forced_exceptions_seen": int(key == "forced-fail"),
            "selected_tests": tests,
            "fingerprint": fp,
            "raw_exit_code": None,
            "estimate_seconds": estimate,
            "wall_limit_seconds": math.ceil((estimate + 1) * 15),
            "seconds": 0.01,
            "instrumented_module": str(source.relative_to(workspace)),
        }

    summaries = []
    for index in range(16):
        p = shards / str(index) / "summary.json"
        p.parent.mkdir(parents=True)
        summary = {
            "shard_index": index,
            "shard_count": 16,
            "fingerprint": fp,
            "execution_context": context,
            "frozen_archive_sha256": "archive-sha",
            "capture_sha256": cap_sha,
            "controls": {k: record(k, True) for k in ("baseline", "forced-fail")},
            "replays": [record(k) for k in sorted(keys)[index::16]],
        }
        p.write_text(json.dumps(summary))
        summaries.append(p)
    return campaign, shards, out, summaries


def join(campaign, shards, out):
    def ledger(command, **kwargs):
        assert command[1] == str(DOC / "PBI-054-final-ledger.py") and kwargs == {"check": True}
        with patch.object(sys, "argv", command[1:]):
            LED.main()
        return SimpleNamespace(returncode=0)

    with (
        patch("subprocess.run", ledger),
        patch.dict(os.environ, {"PBI054_ARCHIVE_SHA": "archive-sha"}),
        patch.object(
            sys,
            "argv",
            [
                "audit",
                "--campaign",
                str(campaign),
                "--shards",
                str(shards),
                "--count",
                "16",
                "--out",
                str(out),
            ],
        ),
    ):
        JOIN.main()


def change(summary, transform):
    obj = json.loads(summary.read_text())
    transform(obj)
    summary.write_text(json.dumps(obj))


with tempfile.TemporaryDirectory(prefix="PBI054-collector-audit-", dir="/tmp") as td:
    root = Path(td).resolve()
    campaign, shards, out, summaries = fixture(root / "valid")
    join(campaign, shards, out)
    ledger = json.loads(out.read_text())
    assert (
        ledger["totals"] == {"survived": 16, "killed": 16, "no tests": 1}
        and len(ledger["all_outcomes"]) == 33
        and len(ledger["shard_controls"]) == 16
    )
    assert all(
        "selected_tests" not in r and r["selected_test_count"] == 1 for r in ledger["replays"]
    )
    report("collector16_and_ledger_positive_exact33_outcomes_compaction")
    probes = {
        "missing_shard": lambda ps: ps[15].unlink(),
        "duplicate_shard": lambda ps: (
            (ps[0].parent / "duplicate/summary.json").parent.mkdir(parents=True)
            or (ps[0].parent / "duplicate/summary.json").write_bytes(ps[0].read_bytes())
        ),
        "wrong_shard_count": lambda ps: change(ps[0], lambda d: d.__setitem__("shard_count", 15)),
        "wrong_context": lambda ps: change(ps[0], lambda d: d.__setitem__("execution_context", {})),
        "wrong_archiveSHA": lambda ps: change(
            ps[0], lambda d: d.__setitem__("frozen_archive_sha256", "wrong")
        ),
        "wrong_captureSHA": lambda ps: change(
            ps[0], lambda d: d.__setitem__("capture_sha256", "wrong")
        ),
        "wrong_fingerprint": lambda ps: change(
            ps[0], lambda d: d.__setitem__("fingerprint", "wrong")
        ),
        "bad_clean_pytest": lambda ps: change(
            ps[0], lambda d: d["controls"]["baseline"].__setitem__("pytest_exit_code", 1)
        ),
        "bad_forced_pytest": lambda ps: change(
            ps[0], lambda d: d["controls"]["forced-fail"].__setitem__("pytest_exit_code", 0)
        ),
        "unobserved_forced": lambda ps: change(
            ps[0], lambda d: d["controls"]["forced-fail"].__setitem__("forced_exceptions_seen", 0)
        ),
        "wrong_control_selection": lambda ps: change(
            ps[0], lambda d: d["controls"]["baseline"].__setitem__("selected_tests", [])
        ),
        "duplicate_case": lambda ps: change(
            ps[0], lambda d: d["replays"].append(deepcopy(d["replays"][0]))
        ),
        "missing_case": lambda ps: change(ps[0], lambda d: d["replays"].pop()),
        "misrouted_case": lambda ps: change(
            ps[0],
            lambda d: d["replays"][0].__setitem__(
                "id", json.loads(ps[1].read_text())["replays"][0]["id"]
            ),
        ),
        "wrong_case_fp": lambda ps: change(
            ps[0], lambda d: d["replays"][0].__setitem__("fingerprint", "wrong")
        ),
        "wrong_raw_code": lambda ps: change(
            ps[0], lambda d: d["replays"][0].__setitem__("raw_exit_code", 0)
        ),
        "wrong_selected_tests": lambda ps: change(
            ps[0], lambda d: d["replays"][0].__setitem__("selected_tests", [])
        ),
        "wrong_estimate": lambda ps: change(
            ps[0], lambda d: d["replays"][0].__setitem__("estimate_seconds", 999)
        ),
        "wrong_wall_limit": lambda ps: change(
            ps[0], lambda d: d["replays"][0].__setitem__("wall_limit_seconds", 999)
        ),
        "setup35_never_killed": lambda ps: change(
            ps[0], lambda d: d["replays"][0].update(exit_code=35, pytest_exit_code=35)
        ),
        "no_collect5_never_killed": lambda ps: change(
            ps[0], lambda d: d["replays"][0].update(exit_code=5, pytest_exit_code=5)
        ),
        "mismatched_pytest_exit": lambda ps: change(
            ps[0], lambda d: d["replays"][0].__setitem__("pytest_exit_code", 9)
        ),
        "unexpected_forced_exception": lambda ps: change(
            ps[0], lambda d: d["replays"][0].__setitem__("forced_exceptions_seen", 1)
        ),
    }
    for label, transform in probes.items():
        campaign, shards, out, ps = fixture(root / label)
        transform(ps)
        try:
            join(campaign, shards, out)
        except (AssertionError, KeyError):
            assert not out.exists()
            report(label + "_rejected")
        else:
            raise AssertionError(label + " ACCEPTED")
    for label, mode in [
        ("no_tests33_with_nonempty_mapping", "bad33"),
        ("pending_with_empty_mapping", "empty_pending"),
    ]:
        campaign, shards, out, ps = fixture(root / label, mode)
        try:
            join(campaign, shards, out)
        except AssertionError:
            assert not out.exists()
            report(label + "_rejected")
        else:
            raise AssertionError(label + " ACCEPTED")
print(json.dumps({"passed": passed, "count": len(passed), "real_mutation_executed": False}))
