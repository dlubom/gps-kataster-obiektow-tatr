#!/usr/bin/env python3
"""Independent read-only review of eight Pawlikowski catalogue objects.

Usage:
  .venv/bin/python docs/asdlc/verification/PBI-117/check_catalogue.py \
    --gps /path/to/gps --jktz /path/to/jktz --source-revision FULL_SHA
Writes JSON only to stdout. Does not import the production recalculation code.
"""

import argparse
import json
import re
import subprocess
from decimal import Decimal
from pathlib import Path

import yaml
from pyproj import Transformer

BASE = "2a40b8e224ce248296e1d82742728bd9b8b6d8d1"
PRE_EDIT = "fb7efd47792fab368e3a0d9b85bfdba3bdac819f"
SYST = "Poligony/D_Koscieliska/Kom_Wierch/Rapt_Turnia/Syst_Pawlikowskiego"
MAP = {
    "KSZ-0047": ("Pawlikowskiego:Raptawicka:1.0", "C-0403", "m-004"),
    "KSZ-0064": ("Pawlikowskiego:Mylna:0", "C-0573", "m-004"),
    "KSZ-0090": ("Pawlikowskiego:Oblazkowa:0.0", "C-0759", "m-004"),
    "KSZ-0113": ("Pawlikowskiego:Mylna:39", "C-0573", "m-002"),
    "KSZ-0114": ("Pawlikowskiego:Raptawicka:5.1", "C-0403", "m-001"),
    "KSZ-0115": ("Pawlikowskiego:Mylna:52", "C-0573", "m-001"),
    "KSZ-0116": ("Pawlikowskiego:Mylna:53", "C-0573", "m-001"),
    "KSZ-0117": ("Pawlikowskiego:Mylna:333", "C-0573", "m-001"),
}


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True)


def load(p):
    return yaml.safe_load(p.read_text())


def assert_close(actual, expected, tolerance, label):
    assert abs(actual - expected) <= tolerance, (label, actual, expected, tolerance)


def numeric_rows(text):
    out = []
    for line in text.splitlines():
        line = line.split(";")[0].strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            nums = tuple(Decimal(p) for p in parts[2:5])
        except Exception:
            continue
        out.append((parts[0], parts[1], *nums))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gps", required=True, type=Path)
    ap.add_argument("--jktz", required=True, type=Path)
    ap.add_argument("--source-revision", required=True)
    args = ap.parse_args()
    gps, jktz = args.gps, args.jktz
    assert re.fullmatch(r"[0-9a-f]{40}", args.source_revision)
    src = git(jktz, "rev-parse", args.source_revision + "^{commit}").strip()
    assert src == args.source_revision
    objects = {p.stem: load(p) for p in (gps / "data/objects").rglob("*.yml")}
    caves = {p.stem: load(p) for p in (gps / "data/caves").rglob("*.yml")}
    assert len(objects) == 1028, len(objects)
    assert len(caves) == 1019, len(caves)
    measurements = sum(len(o["measurements"]) for o in objects.values())
    assert measurements == 1934, measurements
    old_count = 0
    for oid in list(MAP)[:4]:
        old = yaml.safe_load(git(gps, "show", BASE + ":data/objects/KSZ/" + oid + ".yml"))
        current = {m["id"]: m for m in objects[oid]["measurements"]}
        for m in old["measurements"]:
            assert current[m["id"]] == m, (oid, m["id"], "historical measurement changed")
            old_count += 1
    assert old_count == 10, old_count
    for oid in list(MAP)[4:]:
        history = git(gps, "log", PRE_EDIT, "--format=%H", "--", "data/objects/KSZ/" + oid + ".yml")
        assert not history.strip(), (oid, "exists before implementation")
        assert len(objects[oid]["measurements"]) == 1
        assert not any(r.get("system") == "TPN" for r in objects[oid].get("external_refs", []))
    ev = gps / "docs/asdlc/verification/PBI-117"
    before = json.loads((ev / "network-before.json").read_text())
    after = json.loads((ev / "results/network-after.json").read_text())
    anchor = json.loads((ev / "anchor.json").read_text())
    rows = json.loads((ev / "results/entrances.json").read_text())
    assert before["revision"] == src, before["revision"]
    assert after["source_revision"] == src
    assert len(before["nodes"]) == 704, len(before["nodes"])
    named = {n["station"]: n for n in before["nodes"] if n["station"]}
    assert len(named) == 601, len(named)
    assert len(before["nodes"]) - len(named) == 103
    assert len(before["legs"]) == 748, len(before["legs"])
    assert len(after["nodes"]) == len(before["nodes"])
    assert len(after["legs"]) == len(before["legs"])
    a = named["Pawlikowskiego:Raptawicka:1.0"]
    delta = (
        anchor["easting"] - a["easting"],
        anchor["northing"] - a["northing"],
        float(Decimal(str(anchor["elevation_m"])) - Decimal(str(a["elevation"]))),
    )
    transformer = Transformer.from_crs(2180, 4326, always_xy=True)
    max_delta = 0.0
    for b, n in zip(before["nodes"], after["nodes"], strict=True):
        assert b["station"] == n["station"]
        expected = (
            b["easting"] + delta[0],
            b["northing"] + delta[1],
            float(
                Decimal(str(anchor["elevation_m"]))
                + Decimal(str(b["elevation"]))
                - Decimal(str(a["elevation"]))
            ),
        )
        for k, v in zip(("easting", "northing", "elevation"), expected, strict=True):
            err = abs(n[k] - v)
            max_delta = max(max_delta, err)
            assert err < 1e-8, (b["station"], k, err)
        lon, lat = transformer.transform(expected[0], expected[1])
        assert_close(n["lon"], lon, 1e-11, "longitude")
        assert_close(n["lat"], lat, 1e-11, "latitude")
    for b, n in zip(before["legs"], after["legs"], strict=True):
        for endpoint in ("start", "end"):
            for v, w, d in zip(b[endpoint], n[endpoint], delta, strict=True):
                assert_close(w - v, d, 1e-8, "leg translation")
    derived = {r["object_id"]: r for r in rows}
    assert set(derived) == set(MAP), set(derived)
    for oid, (station, cid, mid) in MAP.items():
        o = objects[oid]
        row = derived[oid]
        assert o["cave_id"] == cid
        assert oid in caves[cid]["object_ids"]
        assert o["best_measurement"]["mode"] == "manual"
        assert o["best_measurement"]["measurement_id"] == mid
        m = next(m for m in o["measurements"] if m["id"] == mid)
        assert row["station"] == station
        assert_close(m["x_1992"], row["northing"], 0.00500001, oid + " northing")
        assert_close(m["y_1992"], row["easting"], 0.00500001, oid + " easting")
        assert_close(m["elevation_m"], row["elevation"], 0.00500001, oid + " elevation")
        assert_close(m["lat"], row["lat"], 5.0001e-11, oid + " latitude")
        assert_close(m["lon"], row["lon"], 5.0001e-11, oid + " longitude")
        assert m["horizontal_accuracy_m"] is None
        assert m["vertical_accuracy_m"] is None
        assert m["verification_status"] == "nieweryfikowany"
        assert m["elevation_datum"] == "Kronstadt86"
        if oid == "KSZ-0047":
            assert m["method"] == "ustalenie"
        else:
            assert m["method"] == "siec_pomiarowa"
            assert src in m["source_ref"], (oid, "missing source revision")
            assert station.removeprefix("Pawlikowskiego:") in m["source_ref"], (
                oid,
                "missing station",
            )
    # Preserve the original source records independently of file packaging and comments.
    raw = git(jktz, "show", src + ":" + SYST + "/_RAW/01/SJP_P/POW ORM.SRV")
    raw_rows = numeric_rows(raw)
    assert len(raw_rows) == 66, len(raw_rows)
    tracked = git(jktz, "ls-tree", "-r", "--name-only", src, "--", SYST).splitlines()
    candidates = []
    for path in tracked:
        if "/_RAW/" in path or not path.lower().endswith(".srv"):
            continue
        content = git(jktz, "show", src + ":" + path)
        records = numeric_rows(content)
        # Surface file is identifiable by its p1.* station names, independent of filename.
        surface = [row for row in records if row[0].startswith("p1.") and row[1].startswith("p1.")]
        if surface:
            assert surface == raw_rows, (path, "surface records differ")
            candidates.append(path)
    assert len(candidates) == 1, candidates
    print(
        json.dumps(
            {
                "objects": len(objects),
                "caves": len(caves),
                "measurements": measurements,
                "historical_measurements_preserved": old_count,
                "manual_best": len(MAP),
                "new_objects": list(MAP)[4:],
                "source_revision": src,
                "nodes": len(before["nodes"]),
                "named_nodes": len(named),
                "drawing_legs": len(before["legs"]),
                "max_translation_error_m": max_delta,
                "source_surface_records": len(raw_rows),
                "surface_file": candidates[0],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
