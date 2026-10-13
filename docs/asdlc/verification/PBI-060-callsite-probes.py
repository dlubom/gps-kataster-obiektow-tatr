"""Remove each new provenance guard only in memory and require a failing regression."""

import argparse
import ast
import hashlib
from pathlib import Path

import pytest

import gps_kataster_obiektow_tatr.staging_review as review

SELECTORS = {
    "_apply_create_object": "proposal_provenance_blocks_whole_batch and measurement_source",
    "_apply_create_cave": "proposal_provenance_blocks_whole_batch and inventory_wrong",
    "_apply_add_measurement": "matched_provenance_blocks_whole_batch and object_external_refs",
    "_apply_cave_references": "matched_provenance_blocks_whole_batch and cave_external_refs",
}

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("function", choices=SELECTORS)
parser.add_argument("--baseline", action="store_true")
args = parser.parse_args()
path = Path(review.__file__)
raw = path.read_bytes()
tree = ast.parse(raw, filename=str(path))
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == args.function)


class RemoveGuard(ast.NodeTransformer):
    def __init__(self):
        self.removed = 0

    def visit_If(self, node):
        if (
            isinstance(node.test, ast.UnaryOp)
            and isinstance(node.test.op, ast.Not)
            and isinstance(node.test.operand, ast.Call)
            and isinstance(node.test.operand.func, ast.Name)
            and node.test.operand.func.id == "_check_staging_provenance"
        ):
            self.removed += 1
            return None
        return self.generic_visit(node)


remover = RemoveGuard()
if not args.baseline:
    function = remover.visit(function)
    assert remover.removed == (2 if args.function == "_apply_cave_references" else 1)
    patched = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    exec(compile(patched, str(path), "exec"), review.__dict__)
print(f"source_sha256={hashlib.sha256(raw).hexdigest()}, removed_guards={remover.removed}")
code = pytest.main(
    ["-q", "tests/test_review_validation.py", "-k", SELECTORS[args.function], "--tb=short", "-x"]
)
assert path.read_bytes() == raw
raise SystemExit(code)
