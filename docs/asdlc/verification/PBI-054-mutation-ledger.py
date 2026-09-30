"""Collect complete CLI/replay outcomes and exact non-killed mutation diffs."""

import difflib
import hashlib
import json
import runpy
from collections import Counter
from pathlib import Path

import libcst as cst
import mutmut.__main__ as mutmut

ROOT = Path(__file__).resolve().parents[3]
assert Path.cwd() == ROOT
RUN = ROOT / "build/verification/PBI-054-20260930"
manifest = json.loads((RUN / "campaign-before-replay/manifest.json").read_text())
stats_bytes = (ROOT / "mutants/mutmut-stats.json").read_bytes()
stats = json.loads(stats_bytes)
summary = json.loads((RUN / "completion/summary.json").read_text())
assert not summary["errors"]
fingerprint = summary["fingerprint"]
completion = runpy.run_path(
    str(Path(__file__).with_name("PBI-054-mutation-completion.py")),
    run_name="completion_helpers",
)
assert completion["fingerprint"](manifest) == fingerprint
controls = {}
for name in ("baseline", "forced-fail"):
    controls[name] = json.loads((RUN / "completion" / (name + ".json")).read_text())
    assert controls[name]["exit_code"] == 0
    assert controls[name]["fingerprint"] == fingerprint

all_outcomes = {}
replays = []
non_killed = []
modules = {}
for source, record in sorted(manifest["modules"].items()):
    counts = Counter()
    tree = mutmut.read_mutants_module(Path(source))
    functions = {}
    for node in tree.body:
        if isinstance(node, cst.FunctionDef):
            functions[node.name.value] = node
        if isinstance(node, cst.ClassDef):
            for function in node.body.body:
                if isinstance(function, cst.FunctionDef):
                    functions[function.name.value] = function
    for key, raw_code in sorted(record["codes"].items()):
        code = raw_code
        if code is None or mutmut.status_by_exit_code[code] == "timeout":
            replay = json.loads((RUN / "completion" / (key + ".json")).read_text())
            assert replay["fingerprint"] == fingerprint
            assert replay["raw_exit_code"] == raw_code
            tests = stats["tests_by_mangled_function_name"][
                mutmut.mangled_name_from_mutant_name(key)
            ]
            expected_tests = sorted(tests, key=lambda test: (stats["duration_by_test"][test], test))
            assert replay["selected_tests"] == expected_tests
            code = replay["exit_code"]
            replays.append(
                {field: value for field, value in replay.items() if field != "selected_tests"}
            )
        assert code in {0, 1, 5, 33}, (key, code)
        assert key not in all_outcomes
        all_outcomes[key] = code
        status = mutmut.status_by_exit_code[code]
        counts[status] += 1
        if status == "killed":
            continue
        name = mutmut.orig_function_and_class_names_from_key(key)[0]
        original = (mutmut.mangled_name_from_mutant_name(key) + "__mutmut_orig").split(".")[-1]
        mutant = key.split(".")[-1]
        before = cst.Module([functions[original].with_changes(name=cst.Name(name))]).code.strip()
        after = cst.Module([functions[mutant].with_changes(name=cst.Name(name))]).code.strip()
        diff = "\n".join(difflib.unified_diff(before.splitlines(), after.splitlines(), n=1))
        assert diff
        non_killed.append(
            {"id": key, "status": status, "function": name, "source": source, "diff": diff}
        )
    modules[source] = dict(counts)

assert len(all_outcomes) == 8962
assert len(modules) == 15
assert len(replays) == summary["replayed"] == 1370
tests = sorted(stats["duration_by_test"])
test_index = {test: i for i, test in enumerate(tests)}
mapping = {
    name: [test_index[test] for test in sorted(selected)]
    for name, selected in sorted(stats["tests_by_mangled_function_name"].items())
}
report = {
    "baseline_sha": manifest["baseline_sha"],
    "campaign_state": "complete: one fresh generation, CLI plus bounded direct replay",
    "analysis_ref": "PBI-054-mutation-analysis.md",
    "protocol_ref": "PBI-054.md",
    "modules": modules,
    "totals": dict(sum((Counter(values) for values in modules.values()), Counter())),
    "raw_cli_totals": manifest["totals"],
    "raw_meta": {
        source: {
            "sha256": record["meta_sha256"],
            "complete_json": record["meta_complete_json"],
        }
        for source, record in manifest["modules"].items()
    },
    "fingerprint": fingerprint,
    "stats_sha256": hashlib.sha256(stats_bytes).hexdigest(),
    "controls": controls,
    "test_selection": {
        "tests": tests,
        "duration_seconds": [stats["duration_by_test"][test] for test in tests],
        "indices_by_mangled_function": mapping,
    },
    "all_outcomes": all_outcomes,
    "replays": replays,
    "non_killed": non_killed,
}
destination = Path(__file__).with_name("PBI-054-mutations.json")
assert completion["fingerprint"](manifest) == fingerprint
destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(
    json.dumps(
        {
            "report": str(destination.relative_to(ROOT)),
            "totals": report["totals"],
            "unique_ids": len(all_outcomes),
            "non_killed": len(non_killed),
            "replays": len(replays),
            "bytes": destination.stat().st_size,
        }
    )
)
