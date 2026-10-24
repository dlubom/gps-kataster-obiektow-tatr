#!/usr/bin/env python3
"""Independently decode LAS1.2/type3 bytes and check issue36 evidence.

No laspy or analyze.py import. Header and selected records use struct; bulk
counts use an explicit LAS format3 dtype. Verifies completeness as well as
values, with integer-centimetre selection rather than plotting routines.
Run from repository root. Optional args: analysis_dir output_json.
"""

import collections
import csv
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
import yaml

root = Path.cwd()
here = Path(__file__).resolve().parent
d = root / (sys.argv[1] if len(sys.argv) > 1 else "docs/asdlc/verification/PBI-116")
out = Path(sys.argv[2] if len(sys.argv) > 2 else "/private/tmp/issue36-independent-readback.json")
a = json.loads((d / "analysis.json").read_text())
p = root / a["input"]
blob = p.read_bytes()
checks = 0


def check(ok, label):
    global checks
    checks += 1
    if not ok:
        raise AssertionError(label)


def close(a, b, label):
    check(math.isclose(float(a), float(b), abs_tol=1e-9, rel_tol=0), label)


check(blob[:4] == b"LASF", "LAS magic")
check(tuple(blob[24:26]) == (1, 2), "LAS1.2")
off = struct.unpack_from("<I", blob, 96)[0]
fmt = blob[104]
recsize = struct.unpack_from("<H", blob, 105)[0]
count = struct.unpack_from("<I", blob, 107)[0]
scales = struct.unpack_from("<3d", blob, 131)
offsets = struct.unpack_from("<3d", blob, 155)
check(fmt == 3 and recsize == 34, "LAS format3,34-byte record")
check(len(blob) == off + recsize * count, "Complete LAS exact byte length")
check(count == a["count"], "JSON count")
check(hashlib.sha256(blob).hexdigest() == a["sha256"], "Input SHA")
check(list(scales) == a["scales"], "scales")
# LAS1.2 format3 layouts: coordinates=0,4,8; classification+flags=15;
# source ID=18. LAS stores E first, while YAML uses y_1992 for E.
dtype = np.dtype(
    {
        "names": ["X", "Y", "Z", "class_flags", "source_id"],
        "formats": ["<i4", "<i4", "<i4", "u1", "<u2"],
        "offsets": [0, 4, 8, 15, 18],
        "itemsize": 34,
    }
)
raw = np.frombuffer(blob, dtype=dtype, count=count, offset=off)
cl = raw["class_flags"] & 31
withheld = (raw["class_flags"] & 128) != 0
ok = (cl != 7) & (cl != 18) & (~withheld)
ground = (cl == 2) & ok
check(int(ok.sum()) == a["accepted"], "accepted count")
check(int(ground.sum()) == a["ground"], "ground count")
check(dict(sorted(collections.Counter(map(str, cl)).items())) == a["classes"], "class counts")
check(
    dict(sorted(collections.Counter(map(str, raw["source_id"])).items())) == a["source_ids"],
    "PSID counts",
)
xyz = np.column_stack([raw[k] * scales[i] + offsets[i] for i, k in enumerate(["X", "Y", "Z"])])
markers = {}
yamlcount = 0
for oid, entry in a["catalogue"].items():
    fp = root / "data/objects/KSZ" / f"{oid}.yml"
    obj = yaml.safe_load(fp.read_text())
    check(hashlib.sha256(fp.read_bytes()).hexdigest() == entry["sha256"], oid + " SHA")
    check(entry["best"] == obj["best_measurement"], oid + " best")
    for m in obj["measurements"]:
        markers[(oid, m["id"])] = m
        yamlcount += 1
check(len(a["markers"]) == yamlcount, "all YAML markers present")
for m in a["markers"]:
    k = (m["object"], m["measurement"])
    src = markers[k]
    for f, sf in [
        ("E", "y_1992"),
        ("N", "x_1992"),
        ("Z", "elevation_m"),
        ("source", "source"),
        ("datum", "elevation_datum"),
    ]:
        check(m[f] == src[sf], str(k) + f)
    dist2 = (xyz[:, 0] - m["E"]) ** 2 + (xyz[:, 1] - m["N"]) ** 2
    for kind, keep in [("accepted", ok), ("ground", ground)]:
        candidates = np.nonzero(keep)[0]
        sortindex = np.lexsort((candidates, dist2[candidates]))
        nearest = int(candidates[sortindex[0]])
        given = m[kind + "_nearest"]
        check(given["record_index"] == nearest, str(k) + kind + " nearest index")
        for dim in range(3):
            close(given["xyz"][dim], xyz[nearest, dim], str(k) + kind + " nearest XYZ")
        close(given["dXY"], math.sqrt(float(dist2[nearest])), str(k) + kind + " nearest dXY")
        check(given["class"] == int(cl[nearest]), "nearest classification")
        check(given["source_id"] == int(raw["source_id"][nearest]), "nearest source")
        for radius_string, summary in m[kind + "_radii"].items():
            rr = float(radius_string)
            ids = np.nonzero(keep & (dist2 <= rr * rr))[0]
            check(len(ids) == summary["n"], str(k) + kind + radius_string + " count")
            if len(ids):
                close(min(xyz[ids, 2]), summary["z_min"], "radius z_min")
                close(max(xyz[ids, 2]), summary["z_max"], "radius z_max")
            else:
                check(summary["z_min"] is None and summary["z_max"] is None, "empty radius null")
# CSV rows are decoded directly using struct, without relying on the bulk dtype.
groups = collections.defaultdict(list)
rows = 0
for row in csv.DictReader((d / "sections-1m.csv").open()):
    rows += 1
    k = (row["object"], row["measurement"])
    check(k in markers, "known marker")
    i = int(row["record_index"])
    check(0 <= i < count, "index bounds")
    start = off + i * recsize
    x, y, z = struct.unpack_from("<iii", blob, start)
    flags = blob[start + 15]
    psid = struct.unpack_from("<H", blob, start + 18)[0]
    true = [v * s + o for v, s, o in zip((x, y, z), scales, offsets, strict=False)]
    for f, v in zip(["E", "N", "Z"], true, strict=False):
        close(row[f], v, "CSV " + f)
    check(int(row["class"]) == (flags & 31), "CSV classification")
    check(int(row["source_id"]) == psid, "CSV PSID")
    check((flags & 31) not in (7, 18) and not (flags & 128), "CSV accepted")
    src = markers[k]
    de = true[0] - src["y_1992"]
    dn = true[1] - src["x_1992"]
    along, cross = (de, dn) if row["axis"] == "E" else (dn, de)
    check(row["axis"] in ["E", "N"], "axis")
    check(abs(along) <= 15 + 1e-9 and abs(cross) <= 0.5 + 1e-9, "CSV section bounds")
    groups[(*k, row["axis"])].append(i)
# Completeness using LAS integer centimetres avoids copying float-window code.
check(scales == (0.01, 0.01, 0.01) and offsets == (0, 0, 0), "integer-centimetre domain")
for k, src in markers.items():
    ce = round(src["y_1992"] * 100)
    cn = round(src["x_1992"] * 100)
    for axis in ["E", "N"]:
        da = raw["X"].astype(np.int64) - ce
        db = raw["Y"].astype(np.int64) - cn
        if axis == "N":
            da, db = db, da
        ids = np.flatnonzero(ok & (abs(da) <= 1500) & (abs(db) <= 50)).tolist()
        given = groups[(*k, axis)]
        check(len(given) == len(set(given)), "CSV no duplicate record within section")
        check(given == ids, str(k) + axis + " complete section")
net = json.loads((here / "network.json").read_text())
nodes = {n["station"]: n for n in net["nodes"]}
anchor = nodes["Pawlikowskiego:Mylna:0"]
for sc in a["scenarios"]:
    m = markers[("KSZ-0064", sc["anchor"])]
    de = m["y_1992"] - anchor["easting"]
    dn = m["x_1992"] - anchor["northing"]
    close(sc["shift"][0], de, "scenario dE")
    close(sc["shift"][1], dn, "scenario dN")
    for q in sc["predicted"]:
        n = nodes[q["station"]]
        close(q["E"], n["easting"] + de, "scenario E")
        close(q["N"], n["northing"] + dn, "scenario N")
        close(q["Z"], n["elevation"], "scenario Z unchanged")
report = {
    "status": "PASS",
    "assertions": checks,
    "point_count": count,
    "csv_rows": rows,
    "markers": yamlcount,
    "sections": len(groups),
    "scenarios": len(a["scenarios"]),
    "method": "Independent LAS1.2/type3 struct decoding; explicit raw dtype; full CSV readback; integer-centimetre completeness; exhaustive nearest search/radius statistics; YAML and network input comparison",
    "files": {
        str(fp.relative_to(root)): hashlib.sha256(fp.read_bytes()).hexdigest()
        for fp in [
            p,
            d / "analysis.json",
            d / "sections-1m.csv",
            here / "analyze.py",
            here / "network.json",
        ]
    },
    "limits": [
        "Does not identify cave entrances or prove the field meaning of a station.",
        "Does not compare unknown catalogue height datum with PL-KRON86-NH.",
        "Network topology/source compilation is checked by separate reconstruction evidence; this readback checks scenario translations.",
    ],
}
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(report, ensure_ascii=False, indent=2))
