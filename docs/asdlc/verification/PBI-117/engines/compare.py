#!/usr/bin/env python3
"""Compare native Walls LST with the dump.txt produced by rebuild_network.py."""

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

ENTRANCES = (
    "Pawlikowskiego:Raptawicka:1.0",
    "Pawlikowskiego:Raptawicka:5.1",
    "Pawlikowskiego:Mylna:0",
    "Pawlikowskiego:Mylna:39",
    "Pawlikowskiego:Oblazkowa:0.0",
    "Pawlikowskiego:Mylna:52",
    "Pawlikowskiego:Mylna:53",
    "Pawlikowskiego:Mylna:333",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_survex(path):
    text = path.read_text()
    assert "CS EPSG:32634\n" in text
    nodes = {}
    for match in re.finditer(r"^NODE ([-.0-9]+) ([-.0-9]+) ([-.0-9]+) \[([^]]+)\]", text, re.M):
        name = match[4]
        assert name not in nodes, name
        nodes[name] = tuple(map(float, match.group(1, 2, 3)))
    assert len(nodes) == 601, len(nodes)
    return nodes


def read_walls(path, names):
    text = path.read_text()
    assert "UTM 34N" in text and "Datum: WGS 1984" in text
    # Walls prints eight ASCII characters per prefix component. Check bijection.
    short_names = {}
    for name in names:
        prefix, station = name.rsplit(":", 1)
        short = ":".join(part[:8] for part in prefix.split(":")) + ":" + station
        assert short not in short_names, ("prefix collision", short)
        short_names[short] = name
    nodes = {}
    for line in text.splitlines():
        fields = line.split("\t")
        if len(fields) < 5 or fields[0] == "PREFIX":
            continue
        name = short_names[fields[0] + ":" + fields[1]]
        assert name not in nodes, name
        nodes[name] = tuple(map(float, fields[2:5]))
    assert nodes.keys() == names.keys(), (nodes.keys() - names.keys(), names.keys() - nodes.keys())
    return nodes


def compare(survex, walls):
    assert survex.keys() == walls.keys()
    rows = {}
    for name, coordinates in survex.items():
        delta = [walls[name][axis] - coordinates[axis] for axis in range(3)]
        rows[name] = {
            "walls_minus_survex_m": delta,
            "horizontal_m": math.hypot(*delta[:2]),
            "distance_3d_m": math.sqrt(sum(value * value for value in delta)),
        }
    count = len(rows)
    max_xy = max(rows, key=lambda name: rows[name]["horizontal_m"])
    max_xyz = max(rows, key=lambda name: rows[name]["distance_3d_m"])
    return {
        "count": count,
        "rms_horizontal_m": math.sqrt(
            sum(row["horizontal_m"] ** 2 for row in rows.values()) / count
        ),
        "max_horizontal_m": rows[max_xy]["horizontal_m"],
        "max_horizontal_station": max_xy,
        "rms_3d_m": math.sqrt(sum(row["distance_3d_m"] ** 2 for row in rows.values()) / count),
        "max_3d_m": rows[max_xyz]["distance_3d_m"],
        "max_3d_station": max_xyz,
        "entrances": {name: rows[name] for name in ENTRANCES},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--walls-lst", type=Path, required=True)
    parser.add_argument("--survex-dump", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    survex = read_survex(args.survex_dump)
    result = compare(survex, read_walls(args.walls_lst, survex))
    result["sha256"] = {
        "walls_lst": digest(args.walls_lst),
        "survex_dump": digest(args.survex_dump),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {key: value for key, value in result.items() if key not in ("entrances", "sha256")}
        )
    )


if __name__ == "__main__":
    main()
