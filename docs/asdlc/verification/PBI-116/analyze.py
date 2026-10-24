#!/usr/bin/env python3
"""Point-only comparison for issue #36; no catalogue changes or inferred surface.

Adapted workflow from PR #29 (05759aa): preserve all input records, omit
noise/withheld from views, keep ground separate, and distinguish unknown
catalogue height datum from the source LAS height datum.
Run from repo root: python .../analyze.py INPUT.las OUTPUT_DIR
Dependencies are listed in requirements.txt. Output files are overwritten.
"""

import csv
import hashlib
import json
import sys
from pathlib import Path

import laspy
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml
from matplotlib.collections import LineCollection

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
COLORS = {"m-001": "#a50c94", "m-002": "#00899a", "m-003": "#ed7b0b"}
OBJECTS = {
    "KSZ-0064": "Mylna S",
    "KSZ-0090": "Obłazkowa",
    "KSZ-0047": "Raptawicka",
    "KSZ-0113": "Mylna N",
}


def main():
    infile, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    expected = json.loads((HERE / "acquisition.json").read_text())["output"]["sha256"]
    assert hashlib.sha256(infile.read_bytes()).hexdigest() == expected, "Unexpected LAS input"
    las = laspy.read(infile)
    xyz = np.column_stack([las.x, las.y, las.z])
    cl = np.asarray(las.classification)
    accepted = (~np.isin(cl, [7, 18])) & (~np.asarray(las.withheld, dtype=bool))
    ground = accepted & (cl == 2)
    rgb = np.column_stack([las.red, las.green, las.blue]) / 65535
    markers = []
    sources = {}
    for oid, name in OBJECTS.items():
        p = ROOT / "data/objects/KSZ" / (oid + ".yml")
        obj = yaml.safe_load(p.read_text())
        sources[oid] = {
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "best": obj["best_measurement"],
        }
        for m in obj["measurements"]:
            markers.append(
                {
                    "object": oid,
                    "name": name,
                    "measurement": m["id"],
                    "source": m["source"],
                    "E": m["y_1992"],
                    "N": m["x_1992"],
                    "Z": m["elevation_m"],
                    "datum": m["elevation_datum"],
                }
            )
    diagnostics = []
    for m in markers:
        row = dict(m)
        d = np.hypot(xyz[:, 0] - m["E"], xyz[:, 1] - m["N"])
        for kind, mask in [("accepted", accepted), ("ground", ground)]:
            ii = np.flatnonzero(mask)
            i = ii[np.argmin(d[ii])]
            row[kind + "_nearest"] = {
                "record_index": int(i),
                "xyz": xyz[i].tolist(),
                "dXY": float(d[i]),
                "class": int(cl[i]),
                "source_id": int(las.point_source_id[i]),
            }
            row[kind + "_radii"] = {}
            for radius in [0.5, 1, 2, 5]:
                use = mask & (d <= radius + 1e-9)
                row[kind + "_radii"][str(radius)] = {
                    "n": int(use.sum()),
                    "z_min": float(xyz[use, 2].min()) if use.any() else None,
                    "z_max": float(xyz[use, 2].max()) if use.any() else None,
                }
        diagnostics.append(row)
    net = json.loads((HERE / "network.json").read_text())
    nodes = {n["station"]: n for n in net["nodes"]}
    # Common plan: exact XY positions, with no artificial draping to a surface.
    fig, axs = plt.subplots(1, 2, figsize=(15, 11), layout="constrained")
    lo = [562600, 152740]
    for ax, kind in zip(axs, ["height", "rgb"], strict=False):
        use = np.flatnonzero(ground if kind == "height" else accepted)
        sc = ax.scatter(
            xyz[use, 0] - lo[0],
            xyz[use, 1] - lo[1],
            c=xyz[use, 2] if kind == "height" else rgb[use],
            cmap="terrain" if kind == "height" else None,
            s=0.25,
            linewidths=0,
            rasterized=True,
        )
        if kind == "height":
            fig.colorbar(sc, ax=ax, shrink=0.5, label="Z LiDAR [m], PL-KRON86-NH (skorowidz)")
        for m in markers:
            color = COLORS[m["measurement"]] if m["object"] != "KSZ-0113" else "#00899a"
            ax.scatter(
                m["E"] - lo[0],
                m["N"] - lo[1],
                color=color,
                s=22,
                edgecolor="black",
                linewidth=0.4,
                zorder=5,
            )
            ax.annotate(
                m["name"] + " " + m["measurement"],
                (m["E"] - lo[0], m["N"] - lo[1]),
                (4, 5),
                textcoords="offset points",
                fontsize=7,
                bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none"},
                zorder=6,
            )
        ax.set(
            xlim=(0, 260),
            ylim=(0, 220),
            xlabel="E − 562600 [m] → wschód",
            ylabel="N − 152740 [m] → północ",
            title="Klasa 2 — rzeczywiste odbicia"
            if kind == "height"
            else "RGB odbić — wszystkie dopuszczone klasy",
        )
        ax.set_aspect("equal")
    fig.suptitle("Jaskinie Pawlikowskiego • wszystkie pozycje katalogowe • ALS 2012")
    fig.savefig(out / "system-overview.png", dpi=170)
    plt.close(fig)
    anchor = nodes["Pawlikowskiego:Mylna:0"]
    special = ["Pawlikowskiego:Mylna:" + s for s in ["0", "39", "52", "53", "333"]]
    special += [
        "Pawlikowskiego:Oblazkowa:0.0",
        "Pawlikowskiego:Raptawicka:1.0",
        "Pawlikowskiego:Raptawicka:5.1",
    ]
    fig, axs = plt.subplots(1, 3, figsize=(18, 11), layout="constrained")
    scenarios = []
    for ax, m in zip(axs, [m for m in markers if m["object"] == "KSZ-0064"], strict=False):
        shift = np.array([m["E"] - anchor["easting"], m["N"] - anchor["northing"]])
        # m-003 differs from original compiled node by stored coordinate rounding.
        ix = np.flatnonzero(ground)
        ax.scatter(
            xyz[ix, 0] - lo[0],
            xyz[ix, 1] - lo[1],
            c=xyz[ix, 2],
            cmap="terrain",
            s=0.2,
            linewidths=0,
        )
        segments = [np.array([p["start"][:2], p["end"][:2]]) + shift - lo for p in net["legs"]]
        ax.add_collection(LineCollection(segments, colors="#253c70", linewidths=0.5, alpha=0.7))
        predicted = []
        for station in special:
            node = nodes[station]
            pos = np.array([node["easting"], node["northing"]]) + shift
            predicted.append(
                {"station": station, "E": float(pos[0]), "N": float(pos[1]), "Z": node["elevation"]}
            )
            ax.scatter(
                *(pos - lo), color="#e74b23", s=25, edgecolor="black", linewidth=0.3, zorder=5
            )
            ax.annotate(
                station.removeprefix("Pawlikowskiego:"),
                pos - lo,
                (3, 4),
                textcoords="offset points",
                fontsize=7,
                bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none"},
            )
        for t in markers:
            if t["source"] == "TPN":
                ax.scatter(
                    t["E"] - lo[0],
                    t["N"] - lo[1],
                    s=55,
                    facecolor="none",
                    edgecolor="#00a1ad",
                    linewidth=1.5,
                    zorder=6,
                )
        ax.set(
            xlim=(0, 240),
            ylim=(0, 220),
            xlabel="E − 562600 [m]",
            ylabel="N − 152740 [m]",
            title=f"Kotwica {m['source']} {m['measurement']}\nΔE={shift[0]:.2f}, ΔN={shift[1]:.2f} m",
        )
        ax.set_aspect("equal")
        scenarios.append(
            {"anchor": m["measurement"], "shift": shift.tolist(), "predicted": predicted}
        )
    fig.suptitle(
        "Cała historyczna sieć JKTZ: ta sama geometria, trzy kotwice XY\nLinie = ciągi pomiarowe, nie ściany; czerwone = stacje; turkusowe okręgi = TPN; Z sieci bez zmian"
    )
    fig.savefig(out / "network-scenarios.png", dpi=170)
    plt.close(fig)
    # Each candidate's two orthogonal cuts, several selection widths.
    support = []
    for oid, name in OBJECTS.items():
        ms = [m for m in markers if m["object"] == oid]
        fig, axs = plt.subplots(
            len(ms), 2, figsize=(13, 3.8 * len(ms)), squeeze=False, layout="constrained"
        )
        for row, m in enumerate(ms):
            delta = xyz[:, :2] - [m["E"], m["N"]]
            for col in range(2):
                ax = axs[row, col]
                for width, color in [(2, "#c8c8c8"), (1, "#007e8f"), (0.5, "#171717")]:
                    # Include exact centimetre boundary records despite float cancellation.
                    mask = (
                        accepted
                        & (np.abs(delta[:, 1 - col]) <= width / 2 + 1e-9)
                        & (np.abs(delta[:, col]) <= 15 + 1e-9)
                    )
                    ii = np.flatnonzero(mask)
                    ax.scatter(
                        delta[ii, col],
                        xyz[ii, 2],
                        s=4,
                        c=color,
                        label=f"pas {width} m",
                        linewidths=0,
                    )
                    if width == 1:
                        for i in ii:
                            support.append(
                                {
                                    "object": oid,
                                    "measurement": m["measurement"],
                                    "axis": "EN"[col],
                                    "record_index": int(i),
                                    "E": xyz[i, 0],
                                    "N": xyz[i, 1],
                                    "Z": xyz[i, 2],
                                    "class": int(cl[i]),
                                    "source_id": int(las.point_source_id[i]),
                                }
                            )
                ax.scatter(
                    [0],
                    [m["Z"]],
                    marker="x",
                    c=COLORS[m["measurement"]],
                    s=80,
                    linewidths=2,
                    label="Z katalogu: datum unknown",
                )
                ax.axvline(0, color="black", alpha=0.3)
                ax.set(
                    xlabel="Δ" + "EN"[col] + " [m]",
                    ylabel="Z [m]",
                    xlim=(-15, 15),
                    title=f"{name} {m['measurement']} / {m['source']} • oś {'EN'[col]}",
                )
                ax.grid(alpha=0.2)
                ax.legend(fontsize=7)
        fig.suptitle(
            "Przekroje przez dokładne XY • brak interpolacji • zapisane Z nie są sprowadzone do wspólnego datum"
        )
        fig.savefig(out / (oid + "-sections.png"), dpi=160)
        plt.close(fig)
    # Detail plan and side views: geometry is visible without assuming catalogue Z.
    windows = {
        "mylna-s": (562728, 152790, 76, 50),
        "raptawicka": (562735, 152841, 44, 44),
        "mylna-n": (562798, 152922, 44, 40),
        "oblazkowa": (562755, 152810, 70, 60),
    }
    for label, (e, n, w, h) in windows.items():
        use = accepted & (abs(xyz[:, 0] - e) <= w / 2) & (abs(xyz[:, 1] - n) <= h / 2)
        ii = np.flatnonzero(use)
        fig, axs = plt.subplots(2, 2, figsize=(14, 11), layout="constrained")
        for ax, filt, title in [
            (axs[0, 0], accepted, "Wszystkie klasy: kolor Z"),
            (axs[0, 1], ground, "Klasa 2: kolor Z"),
        ]:
            ix = np.flatnonzero(use & filt)
            sc = ax.scatter(
                xyz[ix, 0] - e,
                xyz[ix, 1] - n,
                c=xyz[ix, 2],
                s=2,
                cmap="terrain",
                linewidths=0,
                vmin=xyz[ii, 2].min(),
                vmax=xyz[ii, 2].max(),
            )
            fig.colorbar(sc, ax=ax, shrink=0.7)
            ax.set(
                xlim=(-w / 2, w / 2),
                ylim=(-h / 2, h / 2),
                xlabel="ΔE [m]",
                ylabel="ΔN [m]",
                title=title,
            )
            ax.set_aspect("equal")
            for m in markers:
                if abs(m["E"] - e) < w / 2 and abs(m["N"] - n) < h / 2:
                    ax.scatter(
                        m["E"] - e,
                        m["N"] - n,
                        c=COLORS[m["measurement"]],
                        edgecolor="k",
                        s=50,
                        zorder=4,
                    )
                    ax.annotate(
                        m["name"] + " " + m["measurement"],
                        (m["E"] - e, m["N"] - n),
                        (4, 5),
                        textcoords="offset points",
                        fontsize=8,
                        zorder=5,
                        bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none"},
                    )
        for ax, col, title in [
            (axs[1, 0], 0, "Od południa: wszystkie punkty okna"),
            (axs[1, 1], 1, "Od wschodu: wszystkie punkty okna"),
        ]:
            ax.scatter(xyz[ii, col] - [e, n][col], xyz[ii, 2], c=rgb[ii], s=2, linewidths=0)
            for m in markers:
                if abs(m["E"] - e) < w / 2 and abs(m["N"] - n) < h / 2:
                    ax.scatter(
                        m["EN"[col]] - [e, n][col],
                        m["Z"],
                        marker="x",
                        c=COLORS[m["measurement"]],
                        s=70,
                        linewidth=2,
                        zorder=5,
                    )
                    ax.annotate(
                        m["name"] + " " + m["measurement"],
                        (m["EN"[col]] - [e, n][col], m["Z"]),
                        (5, 5),
                        textcoords="offset points",
                        fontsize=8,
                    )
            ax.set(xlabel="Δ" + "EN"[col] + " [m]", ylabel="Z [m]", title=title)
            ax.set_aspect("equal")
        fig.suptitle(
            f"{label} • środek E={e}, N={n} • × = Z katalogu, datum unknown\nALS2012 / PL-KRON86-NH, bez interpolacji; rzuty boczne sumują całą głębokość okna"
        )
        fig.savefig(out / (label + "-views.png"), dpi=170)
        plt.close(fig)
    raw = json.loads((HERE / "network-raw-comparison.json").read_text())
    fig, axs = plt.subplots(1, 2, figsize=(15, 11), layout="constrained")
    for ax, m in zip(
        axs,
        [
            m
            for m in markers
            if m["object"] == "KSZ-0064" and m["measurement"] in ["m-002", "m-003"]
        ],
        strict=False,
    ):
        shift = np.array([m["E"] - anchor["easting"], m["N"] - anchor["northing"]])
        origin = np.array([m["E"], m["N"]])
        ix = np.flatnonzero(ground)
        ax.scatter(xyz[ix, 0] - lo[0], xyz[ix, 1] - lo[1], c="#bcbcbc", s=0.15, linewidths=0)
        for records, offset, color, label in [
            (net["legs"], shift, "#d66d00", "Kompilacja historyczna"),
            (raw["raw_local_legs"], origin, "#005da8", "RAW: hipotetycznie równoległe osie"),
        ]:
            segments = [np.array([p["start"][:2], p["end"][:2]]) + offset - lo for p in records]
            ax.add_collection(
                LineCollection(segments, colors=color, linewidths=0.6, alpha=0.7, label=label)
            )
        for f in raw["raw_exact_fixes"]:
            if f["station"] in ["Mylna:0", "Mylna:39", "Oblazkowa:0.0", "Raptawicka:1.0"]:
                pos = np.array([f["local_x"], f["local_y"]]) + origin - lo
                ax.scatter(*pos, color="#005da8", s=35, edgecolor="white", zorder=5)
                ax.annotate(
                    f["station"],
                    pos,
                    (4, 5),
                    textcoords="offset points",
                    fontsize=8,
                    bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none"},
                )
        for t in markers:
            if t["source"] == "TPN":
                ax.scatter(
                    t["E"] - lo[0],
                    t["N"] - lo[1],
                    s=65,
                    facecolor="none",
                    edgecolor="#00a1ad",
                    linewidth=1.5,
                    zorder=6,
                )
        ax.set(
            xlim=(0, 240),
            ylim=(0, 220),
            xlabel="E − 562600 [m]",
            ylabel="N − 152740 [m]",
            title=f"Kotwica {m['source']} {m['measurement']}",
        )
        ax.set_aspect("equal")
        ax.legend(fontsize=8, loc="lower right")
    fig.suptitle(
        "Test wrażliwości na geometrię źródłową • nie jest georeferencją RAW\nTyp północy / rotacja RAW nieustalone; turkusowe okręgi oznaczają TPN (Raptawicka opisana jako górny)"
    )
    fig.savefig(out / "network-geometry-sensitivity.png", dpi=170)
    plt.close(fig)
    with (out / "sections-1m.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(support[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(support)
    try:
        crs = str(las.header.parse_crs())
    except Exception as exc:
        crs = f"Unreadable header CRS: {type(exc).__name__}: {exc}; use matched source index"
    result = {
        "input": str(infile),
        "sha256": hashlib.sha256(infile.read_bytes()).hexdigest(),
        "count": len(xyz),
        "accepted": int(accepted.sum()),
        "ground": int(ground.sum()),
        "classes": {
            str(k): int(v) for k, v in zip(*np.unique(cl, return_counts=True), strict=False)
        },
        "source_ids": {
            str(k): int(v)
            for k, v in zip(*np.unique(las.point_source_id, return_counts=True), strict=False)
        },
        "header_crs": crs,
        "scales": list(las.header.scales),
        "catalogue": sources,
        "markers": diagnostics,
        "scenarios": scenarios,
        "settings": {
            "excluded_classes": [7, 18],
            "withheld": False,
            "section_lengths": 30,
            "section_widths": [0.5, 1, 2],
            "boundary_tolerance_m": 1e-9,
            "interpolation": False,
        },
    }
    (out / "analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {"points": len(xyz), "accepted": int(accepted.sum()), "sections_rows": len(support)}
        )
    )


if __name__ == "__main__":
    main()
