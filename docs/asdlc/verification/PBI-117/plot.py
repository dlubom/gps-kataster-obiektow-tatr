#!/usr/bin/env python3
"""Make evidence plots from preserved pixels, ALS records, and network results."""

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection

HERE = Path(__file__).resolve().parent
anchor = json.loads((HERE / "anchor.json").read_text())
before = json.loads((HERE / "network-before.json").read_text())
after = json.loads((HERE / "results/network-after.json").read_text())
named = {n["station"]: n for n in after["nodes"] if n["station"]}
rows = list(csv.DictReader((HERE / "lidar-window.csv").open()))
xyz = np.array([[float(r[k]) for k in ["E", "N", "Z"]] for r in rows])
im = mpimg.imread(HERE / "ortho-hires-5cm.png")
fig, axes = plt.subplots(1, 3, figsize=(15, 6), layout="constrained")
for ax in axes[:2]:
    ax.imshow(im, extent=[562707, 562765, 152810, 152870], origin="upper", interpolation="nearest")
axes[0].set(
    xlim=(562720, 562752), ylim=(152828, 152850), title="Rozpoznana studnia i dawne pozycje"
)
for e, n, label, c in [
    (562742.35, 152841.98, "JKTZ", "magenta"),
    (562744.57, 152840.37, "PIG", "orange"),
    (562730.81, 152838.92, "TPN: górny", "cyan"),
]:
    axes[0].plot(e, n, "+", color=c, ms=12, mew=2)
    axes[0].annotate(
        label,
        (e, n),
        xytext=(4, 7),
        textcoords="offset points",
        fontsize=8,
        color=c,
        bbox={"facecolor": "black", "alpha": 0.65, "edgecolor": "none"},
    )
axes[1].set(
    xlim=(562725, 562733), ylim=(152835.5, 152844), title="Wschodni brzeg — estymata stacji 1.0"
)
use = (
    (xyz[:, 0] >= 562725)
    & (xyz[:, 0] <= 562733)
    & (xyz[:, 1] >= 152835.5)
    & (xyz[:, 1] <= 152844)
    & (xyz[:, 2] < 1150)
)
sc = axes[2].scatter(
    xyz[use, 0], xyz[use, 1], c=xyz[use, 2], cmap="turbo", s=18, vmin=1135, vmax=1150
)
floor = json.loads((HERE / "floor-cluster.json").read_text())
f = np.array([r["xyz"] for r in floor["records"]])
axes[2].scatter(
    f[:, 0],
    f[:, 1],
    s=46,
    facecolors="none",
    edgecolors="black",
    label="15 odbić niskiej powierzchni",
)
fig.colorbar(sc, ax=axes[2], shrink=0.6, label="Z ALS [m], PL-KRON86-NH")
axes[2].set(
    xlim=(562725, 562733), ylim=(152835.5, 152844), title="ALS: wszystkie klasy, wycinek Z < 1150 m"
)
bottom = named["Pawlikowskiego:Raptawicka:1.1"]
for ax in axes:
    ax.plot(anchor["easting"], anchor["northing"], "x", color="#f00000", ms=12, mew=2)
    ax.set_aspect("equal")
    ax.set_xlabel("E [m], EPSG:2180")
    ax.set_ylabel("N [m]")
    ax.ticklabel_format(style="plain", useOffset=False)
    ax.tick_params(axis="x", rotation=35)
    ax.grid(alpha=0.25)
for ax in axes[1:]:
    ax.plot(
        [anchor["easting"], bottom["easting"]],
        [anchor["northing"], bottom["northing"]],
        "--",
        color="white",
        lw=2,
    )
    ax.plot(bottom["easting"], bottom["northing"], "s", color="#ef0066", ms=6)
    ax.annotate(
        "1.1 z sieci",
        (bottom["easting"], bottom["northing"]),
        xytext=(3, 7),
        textcoords="offset points",
        fontsize=8,
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none"},
    )
fig.suptitle(
    "Raptawicka • kotwica E562729,5 / N152838,5 • czerwony krzyż: estymata brzegu\n"
    "GUGiK WMS 5 cm (2021 wnioskowane z indeksu) + ALS 2012; "
    "nie rozpoznano znaku pomiarowego",
    fontsize=11,
)
fig.savefig(HERE / "anchor-evidence.png", dpi=160)
plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 8), layout="constrained")
for data, color, label in [
    (before, "#aaaaaa", "Wyrównana sieć, dawna kotwica"),
    (after, "#217850", "Nowa kotwica ALS"),
]:
    segments = [[leg["start"][:2], leg["end"][:2]] for leg in data["legs"]]
    ax.add_collection(LineCollection(segments, colors=color, linewidths=0.6, label=label))
for st, label in [
    ("Mylna:0", "Mylna główna"),
    ("Mylna:39", "Mylna północna"),
    ("Oblazkowa:0.0", "Obłazkowa"),
    ("Raptawicka:1.0", "Raptawicka główna"),
    ("Raptawicka:5.1", "Raptawicka górna"),
]:
    n = named["Pawlikowskiego:" + st]
    ax.plot(n["easting"], n["northing"], "o", ms=4, color="#217850")
    ax.annotate(
        label,
        (n["easting"], n["northing"]),
        xytext=(5, 5 if st != "Raptawicka:1.0" else -12),
        textcoords="offset points",
        fontsize=8,
    )
ax.autoscale()
ax.set_aspect("equal")
ax.grid(alpha=0.2)
ax.legend()
ax.ticklabel_format(style="plain", useOffset=False)
ax.tick_params(axis="x", rotation=35)
ax.set(
    xlabel="E [m], EPSG:2180",
    ylabel="N [m]",
    title=f"{len(after['nodes'])} węzły: ΔE −12,849703 m, ΔN −3,480376 m, ΔZ −0,51 m\n"
    "Bez obrotu i zmiany skali; różnice wysokości zachowane",
)
fig.savefig(HERE / "network-translation.png", dpi=150)
