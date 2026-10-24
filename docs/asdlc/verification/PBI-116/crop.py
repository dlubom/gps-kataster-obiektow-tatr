import collections
import copy
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode

import laspy
import numpy as np


def header_crs(h):
    out = []
    for v in h.vlrs:
        if hasattr(v, "parse_crs"):
            try:
                out.append({"type": type(v).__name__, "crs": str(v.parse_crs())})
            except Exception as e:
                out.append({"type": type(v).__name__, "error": str(e)})
    return out


D = Path("build/research/mylna-2026-10-24")
expected = json.loads((Path(__file__).parent / "acquisition.json").read_text())
for source in expected["inputs"]:
    assert hashlib.sha256((D / source["file"]).read_bytes()).hexdigest() == source["sha256"], (
        "Unexpected source LAZ"
    )
bounds = [562545.0, 562871.0, 152694.0, 152982.0]
inputs = ["mylna-2012-north-source.laz", "mylna-2012-south-source.laz"]
manifest = {
    "date": "2026-10-24",
    "source_year": 2012,
    "bbox_E_N": bounds,
    "axis_note": "LAS X=E=y_1992; LAS Y=N=x_1992",
    "selection": "all classes and flags, no interpolation, no filtering, no thinning, no reprojection",
    "vertical_crs": "PL-KRON86-NH from linked WFS metadata, not assigned to unknown catalogue elevations",
    "inputs": [],
    "software": {"laspy": laspy.__version__, "numpy": np.__version__},
}
ns = {"g": "http://www.gugik.gov.pl", "m": "http://www.opengis.net/gml/3.2"}
r = ET.parse(D / "lidar-kron-index.xml").getroot()
metas = []
for el in r.iter():
    if el.find("g:godlo", ns) is not None:
        m = {
            c.tag.split("}")[-1]: "".join(c.itertext()).strip()
            for c in el
            if c.tag.startswith("{" + ns["g"] + "}") and "Geometry" not in c.tag
        }
        metas.append(m)
merged = []
source_index = []
raw_index = []
ref_header = None
for ti, name in enumerate(inputs):
    p = D / name
    sel = []
    idx = []
    base = 0
    with laspy.open(p) as reader:
        h = copy.deepcopy(reader.header)
        if ref_header is None:
            ref_header = copy.deepcopy(h)
        for chunk in reader.chunk_iterator(1_000_000):
            mask = (
                (np.asarray(chunk.x) >= bounds[0])
                & (np.asarray(chunk.x) <= bounds[1])
                & (np.asarray(chunk.y) >= bounds[2])
                & (np.asarray(chunk.y) <= bounds[3])
            )
            ix = np.flatnonzero(mask)
            if len(ix):
                s = chunk[mask].copy()
                sel.append(s)
                idx.append(ix + base)
            base += len(chunk)
    crop = laspy.LasData(h)
    crop.points = laspy.ScaleAwarePointRecord(
        np.concatenate([s.array for s in sel]), h.point_format, h.scales, h.offsets
    )
    out = D / name.replace("-source.laz", "-crop.las")
    crop.write(out)
    merged_copy = laspy.LasData(copy.deepcopy(h))
    merged_copy.points = laspy.ScaleAwarePointRecord(
        crop.points.array.copy(), h.point_format, h.scales, h.offsets
    )
    merged_copy.change_scaling(scales=ref_header.scales, offsets=ref_header.offsets)
    assert (
        np.array_equal(np.asarray(crop.x), np.asarray(merged_copy.x))
        and np.array_equal(np.asarray(crop.y), np.asarray(merged_copy.y))
        and np.array_equal(np.asarray(crop.z), np.asarray(merged_copy.z))
    )
    merged.append(merged_copy.points.array)
    source_index.extend([ti] * len(crop.points))
    raw_index.extend(np.concatenate(idx).tolist())
    mm = next(m for m in metas if ("281506" if ti == 0 else "281508") in m["url_do_pobrania"])
    manifest["inputs"].append(
        {
            "file": name,
            "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "metadata": mm,
            "point_count": base,
            "version": str(h.version),
            "point_format": h.point_format.id,
            "scales": h.scales.tolist(),
            "offsets": h.offsets.tolist(),
            "crs_vlrs": header_crs(h),
            "crop_file": out.name,
            "crop_point_count": len(crop.points),
            "crop_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        }
    )
    print(name, "source", base, "crop", len(crop.points), flush=True)
result = laspy.LasData(ref_header)
result.points = laspy.ScaleAwarePointRecord(
    np.concatenate(merged), ref_header.point_format, ref_header.scales, ref_header.offsets
)
out = D / "pawlikowskiego-2012.las"
result.write(out)
np.savez_compressed(
    D / "pawlikowskiego-2012-source-records.npz",
    source_tile=np.array(source_index, dtype=np.uint8),
    source_record=np.array(raw_index, dtype=np.uint64),
)
reread = laspy.read(out)
assert np.array_equal(reread.points.array, result.points.array)
manifest["output"] = {
    "file": out.name,
    "bytes": out.stat().st_size,
    "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
    "point_count": len(result.points),
    "classes": dict(sorted(collections.Counter(map(int, result.classification)).items())),
    "point_source_ids": dict(sorted(collections.Counter(map(int, result.point_source_id)).items())),
    "min": [float(min(a)) for a in [result.x, result.y, result.z]],
    "max": [float(max(a)) for a in [result.x, result.y, result.z]],
    "readback_all_records_equal": True,
    "mapping_file": "pawlikowskiego-2012-source-records.npz",
}
manifest["xml"] = [
    {
        "file": p.name,
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        "numberMatched": ET.parse(p).getroot().attrib.get("numberMatched"),
    }
    for p in sorted(D.glob("*.xml"))
]

bb = "49.2387,19.8605,49.2412,19.8640"
queries = [
    ("lidar-2025-index.xml", "EVRF2007", [2025], bb),
    ("lidar-all-years-index.xml", "EVRF2007", range(2018, 2027), bb),
    ("lidar-broad-index.xml", "EVRF2007", [2023, 2025], "49.230,19.850,49.250,19.930"),
    ("lidar-kron-index.xml", "KRON86", range(2010, 2020), bb),
]
manifest["queries"] = []
for name, crs, years, b in queries:
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typenames": ",".join(f"gugik:SkorowidzDanychPomiarowychLIDAR{y}" for y in years),
        "srsname": "EPSG:4326",
        "bbox": b + ",urn:ogc:def:crs:EPSG::4326",
    }
    manifest["queries"].append(
        {
            "file": name,
            "url": "https://mapy.geoportal.gov.pl/wss/service/PZGIK/DanePomiaroweLidar"
            + crs
            + "/WFS/Skorowidze?"
            + urlencode(params),
            "response_timestamp": ET.parse(D / name).getroot().attrib.get("timeStamp"),
        }
    )
manifest["coverage_interpretation"] = (
    "No indexed EVRF2018-2026 footprint in the local query; broader EVRF query returns48 footprints. KRON query returns two2012 footprints covering the local query. This is service/index evidence, not proof no other LiDAR acquisition exists."
)
manifest["source_extent_note"] = (
    "Crop covers the full705-station JKTZ network and its translated variants, including PIG anchor approximately48m west, plus approximately60m margin."
)
(D / "acquisition.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(manifest["output"], indent=2))
