"""Capture the exact seven-function PBI-065 campaign before moving/regenerating mutants.

Run with the pinned project venv Python, from the campaign workspace root:
    python /path/to/PBI-065-mutation-capture.py --out /new/stage.json
The archived workspace needs its original pyproject.toml, uv.lock and mutants/.
"""

import argparse
import difflib
import hashlib
import json
from collections import Counter
from pathlib import Path

import libcst as cst
import mutmut.__main__ as mutmut

FUNCTIONS = {
    "staging_review": ("_finalize_staging_record", "_append_unique_dicts"),
    "pig_staging": ("_parse_pig_point", "_format_morphometry", "_pig_cave_notes", "_date_part"),
    "tpn_staging": ("_tpn_cave_notes",),
}


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
        digest.update(b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    assert not args.out.exists()
    workspace = Path.cwd()
    before = fingerprint(workspace)
    stats_path = workspace / "mutants/mutmut-stats.json"
    stats = json.loads(stats_path.read_text())
    codes, mapping, diffs, modules = {}, {}, {}, {}
    for module, names in FUNCTIONS.items():
        source = workspace / f"mutants/src/gps_kataster_obiektow_tatr/{module}.py"
        meta = source.with_suffix(".py.meta")
        metadata = json.loads(meta.read_text())
        instrumented = mutmut.read_mutants_module(source)
        modules[module] = {
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "meta_sha256": hashlib.sha256(meta.read_bytes()).hexdigest(),
            "complete_raw_meta": metadata,
        }
        for name in names:
            mangled = f"gps_kataster_obiektow_tatr.{module}.x_{name}"
            mapping[mangled] = sorted(stats["tests_by_mangled_function_name"].get(mangled, []))
            selected = {
                key: code
                for key, code in metadata["exit_code_by_key"].items()
                if key.startswith(mangled + "__mutmut_")
            }
            assert selected, f"Missing generated scope: {mangled}"
            generated = {
                f"gps_kataster_obiektow_tatr.{module}.{node.name.value}"
                for node in instrumented.body
                if isinstance(node, cst.FunctionDef)
                and node.name.value.startswith(f"x_{name}__mutmut_")
                and node.name.value.rsplit("__mutmut_", 1)[1].isdigit()
            }
            assert set(selected) == generated, f"Incomplete generated scope: {mangled}"
            for key, code in selected.items():
                assert key not in codes
                codes[key] = code
                original = cst.Module(
                    [mutmut.read_original_function(instrumented, key)]
                ).code.strip()
                mutant = cst.Module([mutmut.read_mutant_function(instrumented, key)]).code.strip()
                diffs[key] = "\n".join(
                    difflib.unified_diff(
                        original.splitlines(), mutant.splitlines(), n=2, lineterm=""
                    )
                )
                assert diffs[key]
    tests = {test for selected in mapping.values() for test in selected}
    result = {
        "workspace_fingerprint": before,
        "stats_sha256": hashlib.sha256(stats_path.read_bytes()).hexdigest(),
        "modules": modules,
        "raw_exit_codes": codes,
        "raw_totals": dict(Counter(mutmut.status_by_exit_code[code] for code in codes.values())),
        "test_mapping": mapping,
        "durations": {test: stats["duration_by_test"][test] for test in sorted(tests)},
        "diffs": diffs,
        "test_sha256": {
            str(path.relative_to(workspace / "mutants")): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted((workspace / "mutants/tests").glob("*.py"))
        },
    }
    assert before == fingerprint(workspace)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"ids": len(codes), "totals": result["raw_totals"]}))


if __name__ == "__main__":
    main()
