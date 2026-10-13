"""Remove each DBF preflight call in memory; regressions must fail."""

import argparse
import ast
import hashlib
from pathlib import Path

import pytest

from gps_kataster_obiektow_tatr import best_measurements_export as export
from gps_kataster_obiektow_tatr import release_artifacts as release

TARGETS = {
    "export_best_measurements": (export, "_validate_shapefile_rows", "overflow_blocks_entire_export"),
    "_write_shapefile_zip": (export, "_validate_shapefile_rows", "each_numeric_field_rejects"),
    "validate_best_measurements_dbf": (export, "_validate_shapefile_rows", "overflow_blocks_entire_export"),
    "build_release_artifacts": (release, "validate_best_measurements_dbf", "overflow_blocks_entire_export"),
}

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("function", choices=TARGETS)
parser.add_argument("--baseline", action="store_true")
args = parser.parse_args()
module, guard, selector = TARGETS[args.function]
path = Path(module.__file__)
raw = path.read_bytes()
tree = ast.parse(raw, filename=str(path))
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == args.function)


class RemoveGuard(ast.NodeTransformer):
    def __init__(self):
        self.removed = 0

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == guard:
            self.removed += 1
            return None
        return self.generic_visit(node)

    def visit_Try(self, node):
        node = self.generic_visit(node)
        if not node.body:
            node.body = [ast.Pass()]
        return node


remover = RemoveGuard()
if not args.baseline:
    function = remover.visit(function)
    assert remover.removed == 1
    patched = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    exec(compile(patched, str(path), "exec"), module.__dict__)
    if args.function == "validate_best_measurements_dbf":
        # release imports this function before the in-memory replacement.
        release.validate_best_measurements_dbf = export.validate_best_measurements_dbf
print(f"source_sha256={hashlib.sha256(raw).hexdigest()}, removed_guards={remover.removed}")
code = pytest.main(["-q", "tests/test_dbf_numeric.py", "-k", selector, "--tb=short", "-x"])
assert path.read_bytes() == raw
raise SystemExit(code)
