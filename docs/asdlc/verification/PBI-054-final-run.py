"""Run official mutmut with bounded, isolated temporary files for each pytest invocation.

Use a new copied workspace without mutants/. All generation, test mapping,
selection, activation and raw outcomes remain mutmut's implementation.
Only temporary-file lifetime and the macOS setproctitle workaround change.
"""

import argparse
import errno
import json
import os
import shutil
import tempfile
from pathlib import Path

import mutmut.__main__ as mutmut


class DiskFailureProbe:
    def __init__(self):
        self.failed = False

    def pytest_runtest_makereport(self, item, call):
        if call.excinfo is not None:
            self.failed |= disk_error(call.excinfo.value)

    def pytest_internalerror(self, excrepr, excinfo):
        self.failed |= disk_error(excinfo.value)


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


class TemporaryRunner(mutmut.PytestRunner):
    scratch = None

    def invalidate(self, reason):
        marker = self.scratch.parent / "HARNESS-INVALID.jsonl"
        record = json.dumps({"pid": os.getpid(), "reason": reason}) + "\n"
        try:
            with marker.open("a") as stream:
                stream.write(record)
        except OSError:
            pass  # Exit 35 remains durable in raw metadata if the disk cannot hold a marker.
        print("HARNESS_INVALID: " + record, flush=True)
        if os.environ.get("MUTANT_UNDER_TEST") == "fail":
            raise SystemExit(35)  # Never let a harness failure satisfy the forced-fail control.
        return 35

    def execute_pytest(self, params, **kwargs):
        assert self.scratch is not None
        previous_env, previous_cache = os.environ.get("TMPDIR"), tempfile.tempdir
        directory, code, reason, forced_exception = None, 35, None, None
        probe = DiskFailureProbe()
        try:
            if shutil.disk_usage(self.scratch).free <= 128 * 1024**2:
                reason = "low disk space before pytest"
            else:
                directory = Path(
                    tempfile.mkdtemp(prefix=f"pytest-case-{os.getpid()}-", dir=self.scratch)
                )
                os.environ["TMPDIR"] = str(directory)
                tempfile.tempdir = None
                kwargs["plugins"] = [*kwargs.get("plugins", []), probe]
                code = super().execute_pytest(params, **kwargs)
                if shutil.disk_usage(self.scratch).free <= 128 * 1024**2:
                    reason = "low disk space after pytest, before cleanup"
        except mutmut.MutmutProgrammaticFailException as error:
            forced_exception = error
        except Exception as error:
            reason = f"pytest harness exception: {type(error).__name__}: {error}"
        finally:
            if previous_env is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = previous_env
            tempfile.tempdir = previous_cache
            if directory is not None:
                try:
                    shutil.rmtree(directory)
                except OSError as error:
                    reason = f"temporary cleanup failed: {error}"
        if probe.failed:
            reason = "ENOSPC during pytest (including chained exceptions)"
        if reason is not None:
            return self.invalidate(reason)  # suspicious, never killed/survived
        if forced_exception is not None:
            raise forced_exception
        return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-children", type=int, default=6)
    args = parser.parse_args()
    workspace = Path.cwd()
    assert not (workspace / "mutants").exists(), "Fresh generations only"
    assert not (workspace / "HARNESS-INVALID.jsonl").exists()
    assert shutil.disk_usage(workspace).free > 512 * 1024**2
    scratch = workspace / "campaign-tmp"
    scratch.mkdir(exist_ok=False)
    TemporaryRunner.scratch = scratch
    os.environ["TMPDIR"] = str(scratch)
    tempfile.tempdir = None
    mutmut.PytestRunner = TemporaryRunner
    mutmut.setproctitle = lambda *_: None
    original_register = mutmut.SourceFileMutationData.register_result

    def register_result_with_cleanup(metadata, *, pid, exit_code):
        # wait() has confirmed this worker is dead; reclaim SIGXCPU/SIGKILL leftovers too.
        for directory in scratch.glob(f"pytest-case-{pid}-*"):
            try:
                shutil.rmtree(directory)
            except OSError as error:
                exit_code = TemporaryRunner().invalidate(f"dead worker cleanup failed: {error}")
        return original_register(metadata, pid=pid, exit_code=exit_code)

    mutmut.SourceFileMutationData.register_result = register_result_with_cleanup
    mutmut.cli.main(args=["run", "--max-children", str(args.max_children)])


if __name__ == "__main__":
    main()
