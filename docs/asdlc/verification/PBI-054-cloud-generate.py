"""Generate and map one fresh full campaign using the pinned mutmut APIs.

No mutation result is executed here. The official empty-mapping rule sets 33;
every other ID remains pending for controlled shards. This avoids mutmut 3.5's
module/PID timeout mismatch without changing instrumentation or selection.
"""

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import mutmut.__main__ as mutmut


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-sha", required=True)
    args = parser.parse_args()
    workspace = Path.cwd()
    assert not (workspace / "mutants").exists()
    path = Path(__file__).with_name("PBI-054-final-run.py")
    spec = importlib.util.spec_from_file_location("temporary_runner", path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    scratch = workspace / "campaign-tmp"
    scratch.mkdir(exist_ok=False)
    helper.TemporaryRunner.scratch = scratch
    mutmut.PytestRunner = helper.TemporaryRunner
    os.environ["MUTANT_UNDER_TEST"] = "mutant_generation"
    mutmut.ensure_config_loaded()
    assert not mutmut.mutmut.config.type_check_command
    (workspace / "mutants").mkdir()
    mutmut.copy_src_dir()
    mutmut.copy_also_copy_files()
    mutmut.setup_source_paths()
    mutmut.store_lines_covered_by_tests()
    stats = mutmut.create_mutants(2)
    assert stats.mutated == 17 and stats.unmodified == 0
    runner = helper.TemporaryRunner()
    runner.prepare_main_test_run()
    mutmut.run_stats_collection(runner)
    mutants, modules = mutmut.collect_source_file_mutation_data(mutant_names=[])
    assert len(mutants) == 10218 and len(modules) == 17
    for metadata, key, result in mutants:
        assert result is None
        tests = mutmut.mutmut.tests_by_mangled_function_name.get(
            mutmut.mangled_name_from_mutant_name(key), []
        )
        if not tests:
            metadata.exit_code_by_key[key] = 33
    for metadata in modules.values():
        metadata.save()
    os.environ.pop("MUTANT_UNDER_TEST", None)
    assert not (workspace / "HARNESS-INVALID.jsonl").exists()
    subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("PBI-054-final-capture.py")),
            "--out",
            str(workspace.parent / "capture.json"),
            "--base-sha",
            args.base_sha,
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
