#!/usr/bin/env python3
"""Independently compare all LAS 1.2 points with the QGIS COPC copies.

Uses pdal_wrench only to decompress COPC; binary decoding and multiset
comparison are implemented here with Python's standard library.
"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
BUILD = ROOT / "build/research/lidar-2026-10-23"
APP = Path(os.environ.get("QGIS_APP", "/Applications/QGIS-final-4_0_1.app"))


def read_las(path):
    raw = path.read_bytes()
    assert raw[:4] == b"LASF"
    offset = struct.unpack_from("<I", raw, 96)[0]
    fmt = raw[104]
    size = struct.unpack_from("<H", raw, 105)[0]
    count = struct.unpack_from("<I", raw, 107)[0]
    if not count:
        count = struct.unpack_from("<Q", raw, 247)[0]
    assert fmt in (3, 7), fmt
    assert offset + count * size == len(raw), "Unexpected trailing data or truncation"
    scales = struct.unpack_from("<3d", raw, 131)
    offsets = struct.unpack_from("<3d", raw, 155)
    points = []
    classes = Counter()
    sources = Counter()
    overlaps = Counter()
    xyz_min = [float("inf")] * 3
    xyz_max = [float("-inf")] * 3
    for index in range(count):
        rec = raw[offset + index*size:offset + (index+1)*size]
        xyz = struct.unpack_from("<3i", rec)
        for axis, integer in enumerate(xyz):
            coordinate = integer * scales[axis] + offsets[axis]
            xyz_min[axis] = min(xyz_min[axis], coordinate)
            xyz_max[axis] = max(xyz_max[axis], coordinate)
        if fmt == 3:
            source = struct.unpack_from("<H", rec, 18)[0]
            classification = rec[15] & 31
            classes[classification] += 1
            overlaps[int(classification == 12)] += 1
            canonical = rec[:16] + rec[17:34]
            angle = struct.unpack_from("<b", rec, 16)[0]
        else:
            source = struct.unpack_from("<H", rec, 20)[0]
            classification = rec[16]
            flags = rec[15]
            overlap = (flags >> 3) & 1
            classes[classification] += 1
            overlaps[overlap] += 1
            legacy_class = 12 if classification == 0 and overlap else classification
            assert legacy_class < 32
            returns = rec[14] & 15
            total_returns = rec[14] >> 4
            assert returns < 8 and total_returns < 8
            return_byte = returns | total_returns << 3 | (flags & 0xC0)
            class_byte = legacy_class | (flags & 7) << 5
            canonical = rec[:14] + bytes([return_byte, class_byte, rec[17]]) + rec[20:36]
            angle = struct.unpack_from("<h", rec, 18)[0] * 0.006
            assert flags & 0x30 == 0, "Unexpected nonzero scanner channel"
        sources[source] += 1
        assert len(canonical) == 33
        points.append((canonical, angle))
    points.sort()
    digest = hashlib.sha256()
    for canonical, angle in points:
        digest.update(canonical)
    return points, {
        "filename": path.name, "sha256": hashlib.sha256(raw).hexdigest(),
        "version": f"{raw[24]}.{raw[25]}", "format": fmt,
        "count": count, "scale": scales, "offset": offsets,
        "xyz_min": xyz_min, "xyz_max": xyz_max,
        "classification_counts": dict(sorted(classes.items())),
        "source_id_counts": dict(sorted(sources.items())),
        "overlap_counts_normalized": dict(sorted(overlaps.items())),
        "normalized_multiset_sha256_without_scan_angle": digest.hexdigest(),
    }


def main():
    results = {}
    for name, source in [
        ("sniezna", "sniezna-2025-100m.las"),
        ("pod-wanta", "pod-wanta-2025-both-positions.las"),
    ]:
        unpacked = BUILD / f"qgis-{name}-readback.las"
        subprocess.run([
            str(APP / "Contents/MacOS/pdal_wrench"), "translate",
            f"--input={BUILD / f'qgis-{name}.copc.laz'}", f"--output={unpacked}",
        ], check=True)
        original, original_meta = read_las(BUILD / source)
        copied, copied_meta = read_las(unpacked)
        assert len(original) == len(copied)
        assert original_meta["scale"] == copied_meta["scale"]
        assert original_meta["offset"] == copied_meta["offset"]
        mismatches = sum(a[0] != b[0] for a, b in zip(original, copied))
        assert mismatches == 0, mismatches
        max_angle_delta = max(abs(a[1] - b[1]) for a, b in zip(original, copied))
        assert max_angle_delta <= 0.003000001
        results[name] = {
            "original": original_meta, "copc_decompressed": copied_meta,
            "normalized_multiset_mismatches": mismatches,
            "max_scan_angle_difference_degrees": max_angle_delta,
            "exact_fields": ["XYZ integer coordinates, scale and offset", "Intensity", "ReturnNumber",
                             "NumberOfReturns", "ScanDirectionFlag", "EdgeOfFlightLine",
                             "Classification after overlap normalization", "Synthetic", "KeyPoint", "Withheld",
                             "UserData", "PointSourceId", "GpsTime", "Red", "Green", "Blue"],
            "normalization": "LAS 1.2 class 12 == LAS 1.4 class 0 with Overlap=1; new ScanChannel=0",
            "scan_angle_note": "LAS 1.4 stores angle at 0.006 degree steps; source stores integer degrees",
        }
        print(name, "exact normalized multiset; scan-angle max delta", max_angle_delta)
    (HERE / "qgis-readback.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
