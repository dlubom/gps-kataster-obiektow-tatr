#!/usr/bin/env python3
"""Independent offline acceptance of a relocated release package (stdlib + PyQGIS)."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import shutil
import sqlite3
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from contextlib import closing
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_zip(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), "Duplicate archive members")
        for info in archive.infolist():
            parts = PurePosixPath(info.filename).parts
            require(
                parts
                and not info.filename.startswith("/")
                and ".." not in parts
                and "\\" not in info.filename,
                "Unsafe member path",
            )
            require(info.external_attr >> 16 & 0o170000 != 0o120000, "Symlink member")
        require(
            sum(i.file_size for i in archive.infolist()) <= 250 * 1024 * 1024, "Oversized archive"
        )
        return {n: archive.read(n) for n in names}


def indexed(features):
    result = {}
    for f in features:
        key = (f["properties"]["object_id"], f["properties"]["measurement_id"])
        require(key not in result, f"Duplicate measurement: {key}")
        result[key] = f
    return result


def verify_sources(package, sqlite_zip, jktz_source_dir, destination):
    """Validate with independent readers before letting QGIS resolve any provider."""
    members = read_zip(package)
    manifest = json.loads(members["manifest.json"])
    require(
        manifest["schema_version"] == 1 and manifest["project"] == "kataster.qgs",
        "Package schema/project",
    )
    require(set(members) == set(manifest["sha256"]) | {"manifest.json"}, "Checksum coverage")
    for name, digest in manifest["sha256"].items():
        require(sha(members[name]) == digest, f"Checksum: {name}")
    sqlite_members = read_zip(sqlite_zip)
    require(set(sqlite_members) == {"katalog.sqlite"}, "SQLite ZIP members")
    require(
        sha(sqlite_members["katalog.sqlite"]) == manifest["gps"]["sqlite_sha256"],
        "SQLite provenance",
    )
    destination.mkdir(parents=True)
    database = destination.parent / "source.sqlite"
    database.write_bytes(sqlite_members["katalog.sqlite"])
    with closing(sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        rows = {
            (r["object_id"], r["id"]): dict(r) for r in db.execute("SELECT * FROM measurements")
        }
        choices = {r["object_id"]: dict(r) for r in db.execute("SELECT * FROM best_measurements")}
        objects = {r["id"]: dict(r) for r in db.execute("SELECT * FROM objects")}
    require(set(choices) == set(objects), "Incomplete Best selection")
    require(
        set(manifest["counts"])
        == {"best", "other", "rejected", "differences", "full", "jktz_models", "jktz_legs"},
        "Count roles",
    )
    roles = {}
    for layer in manifest["layers"]:
        if layer["role"] != "jktz":
            require(layer["role"] not in roles, "Repeated GPS role")
            roles[layer["role"]] = json.loads(members[layer["path"]])["features"]
            require(
                len(roles[layer["role"]]) == layer["count"] == manifest["counts"][layer["role"]],
                "Layer count",
            )
    require(set(roles) == {"best", "other", "rejected", "differences", "full"}, "GPS roles")
    full = indexed(roles["full"])
    require(set(full) == set(rows), "Full measurement coverage")
    expected = {"best": set(), "other": set(), "rejected": set()}
    lines = {}
    for key, row in rows.items():
        f = full[key]
        p = f["properties"]
        require(
            f["geometry"] == {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
            f"Geometry: {key}",
        )
        require(all(p[k] == v for k, v in row.items()), f"Measurement attributes: {key}")
        require(p["measurement_notes"] == row["notes"], f"Notes: {key}")
        require(p["name_local"] == objects[key[0]]["name_local"], f"Name: {key}")
        choice = choices[key[0]]
        best_key = (key[0], choice["measurement_id"])
        require(best_key in rows, "Best points to missing row")
        best = rows[best_key]
        is_best = key == best_key
        role = (
            "best"
            if is_best
            else "rejected"
            if row["verification_status"] == "odrzucony"
            else "other"
        )
        expected[role].add(key)
        require(
            p["is_best"] == int(is_best)
            and p["best_mode"] == choice["mode"]
            and p["best_reason"] == choice["reason"],
            f"Best provenance: {key}",
        )
        distance = math.hypot(row["x_1992"] - best["x_1992"], row["y_1992"] - best["y_1992"])
        require(
            math.isclose(p["distance_to_best_m"], distance, abs_tol=1e-8), f"XY distance: {key}"
        )
        for raw, escaped in (
            ("display_name", "display_name_html"),
            ("source", "source_html"),
            ("measurement_notes", "measurement_notes_html"),
        ):
            require(p[escaped] == html.escape(p[raw] or ""), f"HTML escaping: {key}")
        if not is_best and distance > 0:
            lines[key] = (row, best, distance)
    for role, keys in expected.items():
        actual = indexed(roles[role])
        require(set(actual) == keys, f"Partition: {role}")
        require(all(actual[k] == full[k] for k in keys), f"Attributes: {role}")
    actual_lines = indexed(roles["differences"])
    require(set(actual_lines) == set(lines), "Difference coverage")
    for key, (row, best, distance) in lines.items():
        f = actual_lines[key]
        require(
            f["geometry"]
            == {
                "type": "LineString",
                "coordinates": [[row["lon"], row["lat"]], [best["lon"], best["lat"]]],
            },
            "Difference geometry",
        )
        require(
            math.isclose(f["properties"]["distance_m"], distance, abs_tol=1e-8)
            and f["properties"]["best_measurement_id"] == best["id"],
            "Difference attributes",
        )
    upstream = read_zip(jktz_source_dir / "JKTZ.zip")
    source = json.loads((jktz_source_dir / "source.json").read_text())
    require(
        manifest["jktz"] == source
        and source["sha256"] == sha((jktz_source_dir / "JKTZ.zip").read_bytes()),
        "JKTZ provenance",
    )
    expected_jktz = {
        "jktz/" + n.removeprefix("exports/caves/"): b
        for n, b in upstream.items()
        if n.startswith("exports/caves/")
        and Path(n).suffix in {".shp", ".shx", ".dbf", ".prj", ".cpg"}
    }
    expected_jktz.update(
        {
            "jktz/" + n: upstream[n]
            for n in ("LICENCE", "INFO.txt", "README.md", "LISTA_JASKIN.md")
            if n in upstream
        }
    )
    require(
        {n: b for n, b in members.items() if n.startswith("jktz/")} == expected_jktz,
        "JKTZ member bytes",
    )
    model_paths = {n for n in expected_jktz if n.endswith(".shp")}
    models = [s for s in manifest["layers"] if s["role"] == "jktz"]
    require(
        {s["path"] for s in models} == model_paths
        and len(models) == len(model_paths) == manifest["counts"]["jktz_models"],
        "JKTZ model coverage",
    )
    require(sum(s["count"] for s in models) == manifest["counts"]["jktz_legs"], "JKTZ leg count")
    xml = ET.fromstring(members["kataster.qgs"])
    require(
        not xml.findall(".//pythonCode") and not xml.findall(".//actionsetting/action"),
        "Executable project content",
    )
    native = {n.findtext("id"): n for n in xml.findall("./projectlayers/maplayer")}
    require(len(native) == len(manifest["layers"]) + 5, "Project layer count")
    for layer in manifest["layers"]:
        node = native[layer["id"]]
        source_uri = "./" + layer["path"]
        if layer["role"] != "jktz" and layer["count"] == 0:
            source_uri += "|geometrytype=" + (
                "LineString" if layer["role"] == "differences" else "Point"
            )
        require(
            node.findtext("provider") == "ogr" and node.findtext("datasource") == source_uri,
            "Relative local provider",
        )
    allowed = {
        "tpn_rgb_2020": ("https://tpn.obliview.com/Data/rgb_2020/{z}/{x}/{y}.jpg", 15, 20),
        "tpn_rgb_2018": ("https://tpn.obliview.com/Data/rgb_2018/{z}/{x}/{y}.jpg", 15, 20),
        "tpn_nmt_image": ("https://tpn.obliview.com/Data/NMT/{z}/{x}/{y}.jpg", 15, 20),
        "tpn_nmpt_image": ("https://tpn.obliview.com/Data/nmpt/{z}/{x}/{y}.jpg", 15, 20),
        "osm_basemap": ("https://tile.openstreetmap.org/{z}/{x}/{y}.png", 0, 19),
    }
    require({b["id"] for b in manifest["basemaps"]} == set(allowed), "Basemap coverage")
    for ident, (url, low, high) in allowed.items():
        node = native[ident]
        uri = parse_qs(node.findtext("datasource"))
        require(
            node.findtext("provider") == "wms"
            and uri
            == {
                "type": ["xyz"],
                "url": [url],
                "zmin": [str(low)],
                "zmax": [str(high)],
                "crs": ["EPSG:3857"],
            },
            "Online provider allowlist",
        )
    for name, content in members.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return manifest


def init_native():
    from qgis.core import QgsApplication

    app = QgsApplication([], False)
    prefix = os.environ.get("QGIS_PREFIX_PATH")
    if prefix:
        app.setPrefixPath(prefix, True)
        if (Path(prefix) / "Resources/qgis").is_dir():
            app.setPkgDataPath(str(Path(prefix) / "Resources/qgis"))
            app.setPluginPath(str(Path(prefix) / "PlugIns/qgis"))
    app.initQgis()
    return app


def verify_native(destination, manifest):
    from qgis.core import (
        Qgis,
        QgsExpression,
        QgsExpressionContext,
        QgsExpressionContextScope,
        QgsMapRendererSequentialJob,
        QgsMapSettings,
        QgsProject,
        QgsVariantUtils,
        QgsWkbTypes,
    )
    from qgis.PyQt.QtCore import QSize
    from qgis.PyQt.QtGui import QColor

    project = QgsProject.instance()
    require(project.read(str(destination / "kataster.qgs")), "Native project read")
    require(project.crs().authid() == "EPSG:2180", "Native project CRS")
    require(len(project.mapLayers()) == len(manifest["layers"]) + 5, "Native layer count")
    tree = project.layerTreeRoot()
    local_layers = []
    for spec in manifest["layers"]:
        layer = project.mapLayer(spec["id"])
        require(layer is not None and layer.isValid(), f"Native provider: {spec['id']}")
        require(
            layer.featureCount() == spec["count"] and layer.crs().authid() == spec["crs"],
            f"Native count/CRS: {spec['id']}",
        )
        require(
            tree.findLayer(layer.id()).isVisible() == (spec["role"] == "best"),
            "Native default visibility",
        )
        require(
            layer.renderer() is not None and layer.renderer().type() == "singleSymbol",
            "Native renderer",
        )
        if spec["role"] == "jktz":
            require(QgsWkbTypes.hasZ(layer.wkbType()), "Native JKTZ Z coordinates")
        elif spec["role"] != "differences":
            original = indexed(json.loads((destination / spec["path"]).read_text())["features"])
            for feature in layer.getFeatures():
                key = (feature["object_id"], feature["measurement_id"])
                expected = original[key]
                point = feature.geometry().asPoint()
                require(
                    [point.x(), point.y()] == expected["geometry"]["coordinates"],
                    "Native point coordinates",
                )
                for field in (
                    "source",
                    "verification_status",
                    "measurement_notes",
                    "horizontal_accuracy_m",
                    "best_mode",
                    "best_reason",
                ):
                    value = feature[field]
                    require(
                        value == expected["properties"][field]
                        or (
                            expected["properties"][field] is None and QgsVariantUtils.isNull(value)
                        ),
                        f"Native attribute: {field}",
                    )
                context = QgsExpressionContext()
                context.setFields(layer.fields())
                context.setFeature(feature)
                rendered = QgsExpression.replaceExpressionText(layer.mapTipTemplate(), context)
                require(
                    "[%" not in rendered
                    and expected["properties"]["display_name_html"] in rendered,
                    "Native map tip",
                )
        if spec["role"] == "best":
            require(layer.labelsEnabled() and layer.labeling() is not None, "Native labels")
            require(layer.labeling().settings().format().fontFound(), "Native label font")
            expression = QgsExpression(layer.labeling().settings().fieldName)
            require(not expression.hasParserError(), "Label expression")
            if layer.featureCount():
                context = QgsExpressionContext()
                scope = QgsExpressionContextScope()
                scope.setVariable("map_scale", 3000)
                context.appendScope(scope)
                context.setFields(layer.fields())
                context.setFeature(next(layer.getFeatures()))
                require(
                    expression.evaluate(context) is not None and not expression.hasEvalError(),
                    "Label evaluation",
                )
        local_layers.append(layer)
    for spec in manifest["basemaps"]:
        layer = project.mapLayer(spec["id"])
        require(
            layer is not None and layer.isValid() and layer.crs().authid() == "EPSG:3857",
            f"Native basemap provider: {spec['id']} "
            f"{(layer.isValid(), layer.crs().authid()) if layer else 'missing'}",
        )
        require(
            tree.findLayer(layer.id()).isVisible()
            == (spec["id"] in {"tpn_rgb_2020", "osm_basemap"}),
            "Native basemap visibility",
        )
        if spec["id"].startswith("tpn_"):
            require(
                layer.hasScaleBasedVisibility()
                and not layer.isInScaleRange(50000)
                and layer.isInScaleRange(10000),
                "TPN overview scale",
            )
    groups = [n for n in tree.findGroups(True) if n.name().startswith("TPN")]
    require(len(groups) == 1 and groups[0].isMutuallyExclusive(), "Native TPN choice")
    require(len(project.bookmarkManager().bookmarks()) >= 1, "Native bookmarks")
    settings = QgsMapSettings()
    settings.setDestinationCrs(project.crs())
    settings.setLayers(local_layers)
    settings.setExtent(project.viewSettings().defaultViewExtent())
    settings.setOutputSize(QSize(1000, 700))
    settings.setBackgroundColor(QColor("#353c40"))
    job = QgsMapRendererSequentialJob(settings)
    job.start()
    job.waitForFinished()
    require(not job.errors() and not job.renderedImage().isNull(), "Native local render")
    job.renderedImage().save(str(destination / "offline-render.png"))
    print(
        json.dumps(
            {
                "qgis": Qgis.QGIS_VERSION,
                "scenario": manifest.get("scenario", "actual-package"),
                "layers": len(project.mapLayers()),
                "counts": manifest["counts"],
                "offline_render": "PASS",
            },
            sort_keys=True,
        )
    )


def verify_empty_scenarios(destination, manifest):
    """Exercise both empty GPS and empty partitions in every pinned native runtime."""
    for scenario, roles in (
        ("empty-gps", {"best", "full", "other", "rejected", "differences"}),
        ("empty-alternatives", {"other", "rejected", "differences"}),
    ):
        probe = destination.parent / scenario
        shutil.copytree(destination, probe)
        modified = json.loads(json.dumps(manifest))
        modified["scenario"] = scenario
        xml = ET.parse(probe / "kataster.qgs")
        nodes = {n.findtext("id"): n for n in xml.findall("./projectlayers/maplayer")}
        for spec in modified["layers"]:
            if spec["role"] in roles:
                (probe / spec["path"]).write_text('{"type":"FeatureCollection","features":[]}')
                spec["count"] = modified["counts"][spec["role"]] = 0
                geometry = "LineString" if spec["role"] == "differences" else "Point"
                nodes[spec["id"]].find("datasource").text = (
                    "./" + spec["path"] + "|geometrytype=" + geometry
                )
        xml.write(probe / "kataster.qgs", encoding="utf-8", xml_declaration=True)
        verify_native(probe, modified)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--sqlite-zip", type=Path, required=True)
    parser.add_argument("--jktz-source-dir", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="qgis-relocated-") as temporary:
        destination = Path(temporary) / "package"
        manifest = verify_sources(args.package, args.sqlite_zip, args.jktz_source_dir, destination)
        app = init_native()
        verify_native(destination, manifest)
        verify_empty_scenarios(destination, manifest)
        # Keep the runtime alive until all Python/Qt wrappers have gone out of scope.
        del app


if __name__ == "__main__":
    main()
