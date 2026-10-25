#!/usr/bin/env python3
"""Rebuild the isolated Pawlikowski network from a full JKTZ commit SHA.

Requires Survex 1.4.24 and pyproj. Output includes compiler inputs and logs.
An optional --anchor replaces only the Raptawicka fix for the consumer check.
"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from pyproj import Transformer

BASE = "Poligony/D_Koscieliska/Kom_Wierch/Rapt_Turnia/Syst_Pawlikowskiego/"
STATION = "Pawlikowskiego:Raptawicka:1.0"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jktz", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--anchor", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        parser.error("--revision must be a full commit SHA")
    args.output.mkdir(parents=True, exist_ok=False)

    def git(*arguments):
        return subprocess.check_output(["git", "-C", str(args.jktz), *arguments])

    manifest = []

    def blob(path):
        content = git("show", f"{args.revision}:{path}")
        manifest.append({"path": path, "sha256": hashlib.sha256(content).hexdigest()})
        return content

    paths = git("ls-tree", "-r", "--name-only", args.revision, "--", BASE).decode().splitlines()
    for path in paths:
        if not path.endswith(".SRV") or "/_RAW/" in path:
            continue
        target = args.output / path.removeprefix(BASE)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob(path))
    assert len(manifest) == 16, "Unexpected active survey file count"

    wpj = blob("KATASTER.wpj").decode().splitlines()
    start = wpj.index(".BOOK\tSystem Jaskin Pawlikowskiego")
    depth, block = 0, []
    for line in wpj[start:]:
        depth += line.startswith(".BOOK") - line.startswith(".ENDBOOK")
        if line != ".PATH\tSyst_Pawlikowskiego":
            block.append(line)
        if depth == 0:
            break
    header = wpj[:5] + [".SURVEY\tOtwory", ".NAME\tOTWORY", ".STATUS\t8"]
    (args.output / "KATASTER.wpj").write_text("\n".join(header + block + [".ENDBOOK"]) + "\n")
    otwory = blob("Poligony/OTWORY.SRV").decode().splitlines()
    lines = otwory[:2] + [line for line in otwory[2:] if "Pawlikowskiego:" in line]
    fixes = [line for line in lines if line.startswith("#fix")]
    assert len(fixes) == 1 and fixes[0].split()[1] == STATION
    assert sum(line.endswith("/ENTRANCE") for line in lines) == 8
    if args.anchor:
        anchor = json.loads(args.anchor.read_text())
        lon, lat = Transformer.from_crs(2180, 4326, always_xy=True).transform(
            anchor["easting"], anchor["northing"]
        )
        replacement = f"#fix\t{STATION}\tE{lon:.10f}\tN{lat:.10f}\t{anchor['elevation_m']}m"
        lines[lines.index(fixes[0])] = replacement
    (args.output / "OTWORY.SRV").write_text("\n".join(lines) + "\n")

    compiler = subprocess.check_output(["cavern", "--version"], text=True).splitlines()[0]
    assert compiler == "cavern - Survex 1.4.24", compiler
    result = subprocess.run(
        ["cavern", "-o", str(args.output / "KATASTER.3d"), str(args.output / "KATASTER.wpj")],
        capture_output=True,
        text=True,
        check=False,
    )
    log = result.stdout + result.stderr
    (args.output / "compile.log").write_text(log)
    assert result.returncode == 0 and not re.search(r"\b(?:warning|error):", log, re.I), log
    dump = subprocess.check_output(["dump3d", str(args.output / "KATASTER.3d")], text=True)
    (args.output / "dump.txt").write_text(dump)
    assert "CS EPSG:32634\n" in dump
    to_1992 = Transformer.from_crs(32634, 2180, always_xy=True)
    to_geo = Transformer.from_crs(32634, 4326, always_xy=True)

    def xyz(values):
        x, y, z = map(float, values)
        return [*to_1992.transform(x, y), z]

    nodes, legs, current = [], [], None
    for line in dump.splitlines():
        parts = line.split()
        if line.startswith("NODE "):
            match = re.fullmatch(r"NODE ([-\d.]+) ([-\d.]+) ([-\d.]+) \[(.*?)\](.*)", line)
            x, y, z = map(float, match.group(1, 2, 3))
            e, n = to_1992.transform(x, y)
            lon, lat = to_geo.transform(x, y)
            nodes.append(
                dict(
                    station=match[4],
                    easting=e,
                    northing=n,
                    elevation=z,
                    lon=lon,
                    lat=lat,
                    utm_e=x,
                    utm_n=y,
                    flags=match[5].strip(),
                )
            )
        elif line.startswith("MOVE "):
            current = xyz(parts[1:4])
        elif line.startswith("LINE "):
            target = xyz(parts[1:4])
            assert current is not None
            legs.append({"start": current, "end": target, "source": " ".join(parts[4:])})
            current = target
    assert len(nodes) == 704 and sum(bool(n["station"]) for n in nodes) == 601
    assert len(legs) == 748
    network = dict(
        source_repository="https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich",
        revision=args.revision,
        compiler=compiler,
        crs="EPSG:2180",
        vertical_datum="Kronstadt86" if args.anchor else "unknown",
        manifest=manifest,
        nodes=nodes,
        legs=legs,
    )
    if args.anchor:
        network["anchor_override_sha256"] = hashlib.sha256(args.anchor.read_bytes()).hexdigest()
    (args.output / "network-before.json").write_text(
        json.dumps(network, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({"revision": args.revision, "nodes": len(nodes), "legs": len(legs)}))


if __name__ == "__main__":
    main()
