"""Capture one complete configured campaign, preserving raw results and every diff.

Run from its frozen workspace with the pinned project venv Python. The CLI
must have exited first. Do not regenerate instrumented files or statistics.
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import sys
import tomllib
from collections import Counter
from importlib.metadata import version
from pathlib import Path

import libcst as cst
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
        workspace / "mutants/mutmut-stats.json",
    }
    for directory in ("src", "tests", "config", "data/shapes", "schema", "scripts"):
        paths.update(
            path
            for path in (workspace / "mutants" / directory).rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
    for path in sorted(paths):
        digest.update(str(path.relative_to(workspace)).encode())
        digest.update(b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


class GeneratedNames(cst.CSTVisitor):
    def __init__(self, module):
        self.module = module
        self.names = set()

    def visit_FunctionDef(self, node):
        if re.search(r"__mutmut_\d+$", node.name.value):
            self.names.add(f"{self.module}.{node.name.value}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--base-sha", required=True)
    args = parser.parse_args()
    assert not args.out.exists()
    workspace = Path.cwd()
    assert not (workspace / "HARNESS-INVALID.jsonl").exists(), "Reject harness failures"
    before = fingerprint(workspace)
    config = tomllib.loads((workspace / "pyproject.toml").read_text())["tool"]["mutmut"]
    stats_path = workspace / "mutants/mutmut-stats.json"
    stats = json.loads(stats_path.read_text())
    codes, mapping, diffs, modules = {}, {}, {}, {}
    expected_paths = {workspace / "mutants" / path for path in config["paths_to_mutate"]}
    assert {path.with_suffix("") for path in (workspace / "mutants").rglob("*.meta")} == (
        expected_paths
    )
    for source in sorted(expected_paths):
        module = ".".join(source.relative_to(workspace / "mutants/src").with_suffix("").parts)
        meta = source.with_suffix(".py.meta")
        metadata = json.loads(meta.read_text())
        instrumented = mutmut.read_mutants_module(source)
        visitor = GeneratedNames(module)
        instrumented.visit(visitor)
        selected = metadata["exit_code_by_key"]
        assert all(code in {None, 0, 1, 33, -24, 24, 36, 152, 255} for code in selected.values()), (
            f"Reject setup/compiler/disk/crash outcomes: {module}"
        )
        assert set(selected) == visitor.names, f"Incomplete generated scope: {module}"
        modules[module] = {
            "source": str(source.relative_to(workspace)),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "meta_sha256": hashlib.sha256(meta.read_bytes()).hexdigest(),
            "complete_raw_meta": metadata,
        }
        for key, code in selected.items():
            assert key not in codes
            codes[key] = code
            name = mutmut.mangled_name_from_mutant_name(key)
            mapping[name] = sorted(stats["tests_by_mangled_function_name"].get(name, []))
            original = cst.Module([mutmut.read_original_function(instrumented, key)]).code.strip()
            mutant = cst.Module([mutmut.read_mutant_function(instrumented, key)]).code.strip()
            diffs[key] = "\n".join(
                difflib.unified_diff(original.splitlines(), mutant.splitlines(), n=2, lineterm="")
            )
            assert diffs[key]
    tests = {test for selected in mapping.values() for test in selected}
    result = {
        "baseline_sha": args.base_sha,
        "execution_context": {
            key: os.environ.get(key)
            for key in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA", "GITHUB_WORKFLOW_REF")
        },
        "runtime": runtime_identity(),
        "scope": config,
        "workspace_fingerprint": before,
        "stats_sha256": hashlib.sha256(stats_path.read_bytes()).hexdigest(),
        "modules": modules,
        "raw_exit_codes": codes,
        "raw_totals": dict(Counter(mutmut.status_by_exit_code[code] for code in codes.values())),
        "test_mapping": mapping,
        "durations": {test: stats["duration_by_test"][test] for test in sorted(tests)},
        "diffs": diffs,
        "input_sha256": {
            str(path.relative_to(workspace)): hashlib.sha256(path.read_bytes()).hexdigest()
            for directory in ("src", "tests", "scripts", "schema", "config", "data/shapes")
            for path in sorted((workspace / directory).rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
        },
    }
    assert before == fingerprint(workspace)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"ids": len(codes), "totals": result["raw_totals"]}))


if __name__ == "__main__":
    main()
