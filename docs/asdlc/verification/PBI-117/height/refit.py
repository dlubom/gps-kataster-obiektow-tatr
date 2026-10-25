"""Reproduce the local rim plane from six preserved ALS returns; stdlib only."""

import csv
import json
import math
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
reference = json.loads((HERE / "threshold-height.json").read_text())
anchor = json.loads((HERE.parent / "anchor.json").read_text())
with (HERE / "rim-six-points.csv").open() as stream:
    rows = list(csv.DictReader(stream))
assert len(rows) == 6
assert [int(row["record_index"]) for row in rows] == reference["core_OLS"]["indices"]
x = [float(row["E"]) - anchor["easting"] for row in rows]
y = [float(row["N"]) - anchor["northing"] for row in rows]
z = [float(row["Z"]) for row in rows]
mx, my, mz = mean(x), mean(y), mean(z)
sxx = sum((v - mx) ** 2 for v in x)
syy = sum((v - my) ** 2 for v in y)
sxy = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True))
sxz = sum((a - mx) * (b - mz) for a, b in zip(x, z, strict=True))
syz = sum((a - my) * (b - mz) for a, b in zip(y, z, strict=True))
denominator = sxx * syy - sxy**2
a = (sxz * syy - syz * sxy) / denominator
b = (syz * sxx - sxz * sxy) / denominator
h = mz - a * mx - b * my
rmse = math.sqrt(mean((v - h - a * xx - b * yy) ** 2 for xx, yy, v in zip(x, y, z, strict=True)))
assert abs(h - reference["core_OLS"]["estimate_m"]) < 1e-8
assert round(h, 1) == anchor["elevation_m"]
print(
    json.dumps(
        {
            "estimated_rim_height_m": h,
            "adopted_height_m": round(h, 1),
            "dZ_dE": a,
            "dZ_dN": b,
            "fit_rmse_m_not_absolute_accuracy": rmse,
            "network_elevations_used": False,
        },
        indent=2,
    )
)
