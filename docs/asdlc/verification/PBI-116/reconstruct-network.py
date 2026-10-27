#!/usr/bin/env python3
"""Read pinned JKTZ sources and compile isolated research copies, never the checkout."""

import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

import yaml
from pyproj import Transformer

SHA = "773c8e2e6aa910c8ba78192ae6741d107c6598e2"
BASE = "Poligony/D_Koscieliska/Kom_Wierch/Rapt_Turnia/Syst_Pawlikowskiego/"


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def parse_dump(text, projected):
    transformer = Transformer.from_crs(32634, 2180, always_xy=True) if projected else None
    geographic = Transformer.from_crs(32634, 4326, always_xy=True) if projected else None
    nodes, legs, previous = [], [], None
    for line in text.splitlines():
        match = re.match(r"NODE ([\d.-]+) ([\d.-]+) ([\d.-]+) \[([^\]]*)\](.*)", line)
        if match:
            x, y, z = map(float, match.group(1, 2, 3))
            if projected:
                e, n = transformer.transform(x, y)
                lon, lat = geographic.transform(x, y)
                node = dict(
                    station=match[4],
                    easting=e,
                    northing=n,
                    elevation=z,
                    lon=lon,
                    lat=lat,
                    utm_e=x,
                    utm_n=y,
                )
            else:
                node = dict(station=match[4], local_x=x, local_y=y, local_z=z)
            node["flags"] = match[5].strip()
            nodes.append(node)
        match = re.match(r"(MOVE|LINE) ([\d.-]+) ([\d.-]+) ([\d.-]+)(.*)", line)
        if match:
            x, y, z = map(float, match.group(2, 3, 4))
            e, n = transformer.transform(x, y) if projected else (x, y)
            point = [e, n, z]
            if match[1] == "LINE" and previous:
                legs.append(dict(start=previous, end=point, source=match[5].strip()))
            previous = point
    return nodes, legs


def compile_copy(directory, wpj, name):
    output = directory / (name + ".3d")
    result = subprocess.run(["cavern", "-o", str(output), str(wpj)], capture_output=True, text=True)
    (directory / "compile.log").write_text(result.stdout + result.stderr)
    result.check_returncode()
    dump = subprocess.check_output(["dump3d", str(output)], text=True)
    (directory / (name + ".dump.txt")).write_text(dump)
    return dump


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jktz", type=Path, required=True)
    parser.add_argument("--catalogue", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    historical = args.output / "historical"
    raw = args.output / "raw"
    historical.mkdir(exist_ok=True)
    raw.mkdir(exist_ok=True)
    files = git(args.jktz, "ls-tree", "-rz", "--name-only", SHA, BASE).decode().split("\0")
    manifest = []
    for name in filter(None, files):
        relative = name.removeprefix(BASE)
        if "/_RAW/" not in name:
            destination = historical / relative
        elif relative.startswith("_RAW/SJP/"):
            destination = raw / relative.removeprefix("_RAW/SJP/")
        else:
            continue
        content = git(args.jktz, "show", SHA + ":" + name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        manifest.append(dict(path=name, sha256=hashlib.sha256(content).hexdigest()))
    project = git(args.jktz, "show", SHA + ":KATASTER.wpj")
    manifest.append(dict(path="KATASTER.wpj", sha256=hashlib.sha256(project).hexdigest()))
    lines = project.decode().splitlines()
    start = next(i for i, line in enumerate(lines) if line == ".BOOK\tSystem Jaskin Pawlikowskiego")
    depth = 0
    for index in range(start, len(lines)):
        depth += int(lines[index].startswith(".BOOK"))
        depth -= int(lines[index].startswith(".ENDBOOK"))
        if depth == 0:
            end = index + 1
            break
    subtree = [line for line in lines[start:end] if line != ".PATH\tSyst_Pawlikowskiego"]
    wpj = historical / "system.wpj"
    wpj.write_text("\n".join(lines[:5] + subtree + [".ENDBOOK"]) + "\n")
    nodes, legs = parse_dump(compile_copy(historical, wpj, "system"), True)
    raw_nodes, raw_legs = parse_dump(compile_copy(raw, raw / "SJ PAWLIKOWSKIEGO.wpj", "raw"), False)
    exact_fixes = []
    for path, prefix in [
        ("Dane/Mylna/CG.SRV", "Mylna"),
        ("Dane/OBLAZK.SRV", "Oblazkowa"),
        ("Dane/RAPTAW.SRV", "Raptawicka"),
    ]:
        for line in (raw / path).read_text(errors="replace").splitlines():
            match = re.match(r"#fix\s+(\S+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)", line, re.I)
            if match:
                exact_fixes.append(
                    dict(
                        station=prefix + ":" + match[1],
                        local_x=float(match[2]),
                        local_y=float(match[3]),
                        local_z=float(match[4]),
                        source=path,
                    )
                )
    objects = {
        key: yaml.safe_load((args.catalogue / "data/objects/KSZ" / (key + ".yml")).read_text())
        for key in ["KSZ-0064", "KSZ-0090", "KSZ-0047", "KSZ-0113"]
    }
    anchor = objects["KSZ-0064"]["measurements"][2]
    scenarios = []
    for candidate in objects["KSZ-0064"]["measurements"]:
        dn = candidate["x_1992"] - anchor["x_1992"]
        de = candidate["y_1992"] - anchor["y_1992"]
        records = []
        for key, station in [
            ("KSZ-0090", "Oblazkowa:0.0"),
            ("KSZ-0047", "Raptawicka:1.0"),
            ("KSZ-0113", "Mylna:39"),
        ]:
            node = next(node for node in nodes if node["station"] == "Pawlikowskiego:" + station)
            tpn = next(m for m in objects[key]["measurements"] if m["source"] == "TPN")
            n, e = node["northing"] + dn, node["easting"] + de
            records.append(
                dict(
                    object_id=key,
                    station=station,
                    northing=n,
                    easting=e,
                    distance_to_tpn_m=math.hypot(n - tpn["x_1992"], e - tpn["y_1992"]),
                )
            )
        scenarios.append(
            dict(
                anchor_measurement_id=candidate["id"],
                delta_n=dn,
                delta_e=de,
                historical_rigid_translation=records,
                raw_parallel_axes_diagnostic=[
                    dict(
                        station=f["station"],
                        hypothetical_easting=candidate["y_1992"] + f["local_x"],
                        hypothetical_northing=candidate["x_1992"] + f["local_y"],
                    )
                    for f in exact_fixes
                    if f["station"] in ["Mylna:0", "Mylna:39", "Oblazkowa:0.0", "Raptawicka:1.0"]
                ],
            )
        )
    result = dict(
        provenance=dict(
            repo="https://github.com/dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich",
            commit=SHA,
            compiler=subprocess.check_output(["cavern", "--version"], text=True).splitlines()[0],
            input="Original system subtree with original top-level REF. Source survey bytes unchanged.",
            horizontal_crs="EPSG:2180; easting then northing",
            vertical_datum="unknown",
            historical_warnings="2 original compass-on-plumb warnings in WSZCZCB.SRV.",
            raw_warnings="2 compass-on-plumb and 1 decimal-comma warning; no raw source edits.",
            raw_registration="Unknown north reference: raw WPJ has no REF and SRV has no date/DECL. Local axes cannot be assigned an EPSG CRS. Parallel-axis scenarios below are diagnostic assumptions, not transformations.",
            source_manifest=manifest,
        ),
        nodes=nodes,
        legs=legs,
        raw_local_nodes=raw_nodes,
        raw_local_legs=raw_legs,
        raw_exact_fixes=exact_fixes,
        scenarios=scenarios,
    )
    target = args.output / "system-network.json"
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(target)


if __name__ == "__main__":
    main()
