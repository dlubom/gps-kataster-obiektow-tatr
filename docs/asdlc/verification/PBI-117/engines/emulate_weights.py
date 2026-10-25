#!/usr/bin/env python3
"""Research-only weight controls, using an untouched rebuild_network.py output."""

import argparse
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

from compare import compare, digest, read_survex, read_walls


def copy_inputs(source, target):
    target.mkdir()
    paths = sorted(path for path in source.rglob("*") if path.suffix.upper() in (".SRV", ".WPJ"))
    assert len(paths) == 18, len(paths)
    for path in paths:
        destination = target / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)


def compile_case(path):
    result = subprocess.run(
        ["cavern", "-o", str(path / "KATASTER.3d"), str(path / "KATASTER.wpj")],
        capture_output=True,
        text=True,
    )
    log = result.stdout + result.stderr
    (path / "compile.log").write_text(log)
    assert result.returncode == 0 and not re.search(r"\b(?:warning|error):", log, re.I), log
    dump = subprocess.check_output(["dump3d", str(path / "KATASTER.3d")], text=True)
    (path / "dump.txt").write_text(dump)
    return read_survex(path / "dump.txt")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network", type=Path, required=True)
    parser.add_argument("--walls-lst", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    version = subprocess.check_output(["cavern", "--version"], text=True).splitlines()[0]
    assert version == "cavern - Survex 1.4.24", version
    args.output.mkdir(parents=True, exist_ok=False)
    original = read_survex(args.network / "dump.txt")
    walls = read_walls(args.walls_lst, original)
    alternating = args.output / "alternating"
    copy_inputs(args.network, alternating)
    surface = alternating / "Powierzchnia/POW_ORM.SRV"
    lines = surface.read_text().splitlines()
    indices = [
        i
        for i, line in enumerate(lines)
        if line.startswith("p1.") and line.split()[1].startswith("p1.")
    ]
    assert len(indices) == 66
    readings = [lines[i] for i in indices]
    reordered = []
    for first in range(0, 66, 6):
        forward, backward = readings[first : first + 3], readings[first + 3 : first + 6]
        assert all(line.split()[:2] == forward[0].split()[:2] for line in forward)
        assert all(line.split()[:2] == list(reversed(forward[0].split()[:2])) for line in backward)
        for offset in range(3):
            reordered.extend([forward[offset], backward[offset]])
    for offset, index in enumerate(indices):
        lines[index] = reordered[offset]
    surface.write_text("\n".join(lines) + "\n")
    alternated = compile_case(alternating)

    weighted = args.output / "walls-variance"
    copy_inputs(alternating, weighted)
    changed = 0
    for path in weighted.rglob("*.SRV"):
        lines, depth, updated = path.read_text().splitlines(), 0, []
        for line in lines:
            fields = line.strip().split()
            if fields and fields[0] == "#[":
                depth += 1
            if fields and fields[0] == "#]":
                depth -= 1
            if not depth and len(fields) >= 5 and not fields[0].startswith(("#", ";")):
                distance = float(fields[2])
                assert "(" not in line, "Unexpected existing variance override"
                if distance > 0:
                    variance = 0.003048 * distance  # Native Walls variance per Cartesian component.
                    line += f" (R{math.sqrt(2 * variance):.14f},R{math.sqrt(variance):.14f})"
                    changed += 1
            updated.append(line)
        assert depth == 0
        path.write_text("\n".join(updated) + "\n")
    assert changed == 792, changed
    emulated = compile_case(weighted)
    result = {
        "compiler": version,
        "changed_variance_rows": changed,
        "original_walls_minus_survex": compare(original, walls),
        "alternating_walls_minus_survex": compare(alternated, walls),
        "emulated_walls_minus_survex": compare(emulated, walls),
        "input_sha256": {
            "walls_lst": digest(args.walls_lst),
            "survex_dump": digest(args.network / "dump.txt"),
        },
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: value
                for key, value in result["emulated_walls_minus_survex"].items()
                if key != "entrances"
            }
        )
    )


if __name__ == "__main__":
    main()
