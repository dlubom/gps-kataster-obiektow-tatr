#!/usr/bin/env python3
"""Translate a pinned network; write derived results, never catalogue YAML.

Run: .venv/bin/python docs/asdlc/verification/PBI-117/recalculate.py OUTPUT_DIR
Dependencies: standard library and the project's pyproj.
"""

import csv
import hashlib
import itertools
import json
import math
import sys
from decimal import Decimal
from pathlib import Path

from pyproj import Transformer

HERE = Path(__file__).resolve().parent
ENTRANCES = {
    "Pawlikowskiego:Raptawicka:1.0": ("Raptawicka główna", "KSZ-0047"),
    "Pawlikowskiego:Raptawicka:5.1": ("Raptawicka górna", None),
    "Pawlikowskiego:Mylna:0": ("Mylna główna", "KSZ-0064"),
    "Pawlikowskiego:Mylna:39": ("Mylna północna", "KSZ-0113"),
    "Pawlikowskiego:Oblazkowa:0.0": ("Obłazkowa", "KSZ-0090"),
    "Pawlikowskiego:Mylna:52": ("Mylna — stacja przy I Oknie", None),
    "Pawlikowskiego:Mylna:53": ("Mylna — stacja przy II Oknie", None),
    "Pawlikowskiego:Mylna:333": ("Mylna — stacja 333 w rejonie okien", None),
}


def main():
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    source = json.loads((HERE / "network-before.json").read_text())
    anchor = json.loads((HERE / "anchor.json").read_text())
    nodes = {n["station"]: n for n in source["nodes"] if n["station"]}
    assert len(source["nodes"]) == 692
    assert len(nodes) == sum(bool(n["station"]) for n in source["nodes"])
    old_anchor = nodes[anchor["station"]]
    de = anchor["easting"] - old_anchor["easting"]
    dn = anchor["northing"] - old_anchor["northing"]
    anchor_height = Decimal(str(anchor["elevation_m"]))
    old_anchor_height = Decimal(str(old_anchor["elevation"]))
    dz = float(anchor_height - old_anchor_height)

    def height(old_height):
        # Only a relative network height is used; the old absolute GPS anchor cancels.
        return float(anchor_height + Decimal(str(old_height)) - old_anchor_height)

    geo = Transformer.from_crs(2180, 4326, always_xy=True)
    translated = []
    for index, old in enumerate(source["nodes"]):
        e, n = old["easting"] + de, old["northing"] + dn
        lon, lat = geo.transform(e, n)
        translated.append(
            dict(
                node_index=index,
                station=old["station"],
                easting=e,
                northing=n,
                elevation=height(old["elevation"]),
                lon=lon,
                lat=lat,
            )
        )
    moved = {n["station"]: n for n in translated if n["station"]}
    errors = []
    for a, b in itertools.combinations(range(len(translated)), 2):
        before = [
            source["nodes"][a][k] - source["nodes"][b][k]
            for k in ("easting", "northing", "elevation")
        ]
        after = [translated[a][k] - translated[b][k] for k in ("easting", "northing", "elevation")]
        assert max(abs(x - y) for x, y in zip(before, after, strict=True)) < 1e-8
        errors.append(abs(math.dist(before, (0, 0, 0)) - math.dist(after, (0, 0, 0))))
    assert all(
        Decimal(str(n["elevation"])) - anchor_height
        == Decimal(str(old["elevation"])) - old_anchor_height
        for old, n in zip(source["nodes"], translated, strict=True)
    )
    legs = []
    for leg in source["legs"]:
        legs.append(
            {
                **leg,
                "start": [leg["start"][0] + de, leg["start"][1] + dn, height(leg["start"][2])],
                "end": [leg["end"][0] + de, leg["end"][1] + dn, height(leg["end"][2])],
            }
        )
    result = {
        "source_revision": source["revision"],
        "network_before_sha256": hashlib.sha256(
            (HERE / "network-before.json").read_bytes()
        ).hexdigest(),
        "anchor_sha256": hashlib.sha256((HERE / "anchor.json").read_bytes()).hexdigest(),
        "crs": "EPSG:2180",
        "vertical_datum": anchor["elevation_datum"],
        "translation": {
            "delta_e": de,
            "delta_n": dn,
            "delta_z": dz,
            "distance_xy": math.hypot(de, dn),
            "rotation_deg": 0.0,
            "scale": 1.0,
        },
        "nodes": translated,
        "legs": legs,
    }
    (output / "network-after.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    rows = [
        {"station": station, "name": name, "object_id": oid, **moved[station]}
        for station, (name, oid) in ENTRANCES.items()
    ]
    (output / "entrances.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    with (output / "entrances.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    check = {
        "nodes": len(translated),
        "named_stations": len(nodes),
        "drawing_legs": len(legs),
        "pairwise_checks": len(errors),
        "max_pairwise_distance_difference_m": max(errors),
        "all_relative_elevations_unchanged": True,
        "vertical_anchor_replaced": True,
        "translation": result["translation"],
    }
    (output / "geometry-check.json").write_text(json.dumps(check, indent=2) + "\n")
    print(json.dumps(check, indent=2))


if __name__ == "__main__":
    main()
