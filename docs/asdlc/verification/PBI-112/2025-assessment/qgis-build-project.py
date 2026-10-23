#!/usr/bin/env python3
"""Rebuild the read-only QGIS 2025 evidence project and north-up point maps.

Run with the QGIS Python runtime; see qgis-notes.md. No catalogue writes,
interpolation, vertical transformation, ground projection or point filtering.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import yaml
from qgis.PyQt.QtCore import QCoreApplication, QMetaType
from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import (
    Qgis, QgsApplication, QgsBookmark, QgsCategorizedSymbolRenderer,
    QgsContrastEnhancement, QgsCoordinateReferenceSystem, QgsFeature, QgsField,
    QgsGeometry, QgsLayoutExporter, QgsLayoutItemLabel, QgsLayoutItemMap,
    QgsLayoutItemScaleBar, QgsLayoutPoint, QgsLayoutSize, QgsMapLayerStyle,
    QgsMarkerSymbol, QgsPalLayerSettings, QgsPointCloudCategory,
    QgsPointCloudClassifiedRenderer, QgsPointCloudLayer, QgsPointCloudRgbRenderer,
    QgsPointXY, QgsPrintLayout, QgsProject, QgsRectangle,
    QgsReferencedRectangle, QgsRendererCategory, QgsTextBufferSettings,
    QgsTextFormat, QgsVectorFileWriter, QgsVectorLayer, QgsVectorLayerSimpleLabeling,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
BUILD = ROOT / "build/research/lidar-2026-10-23"
CRS = None  # Construct after QGIS initializes its CRS database.
SOURCE_COLOURS = {"TPN": "#00bcd4", "PIG": "#ff00e6"}
ID_COLOURS = {79: "#c52c37", 80: "#1b9e77", 81: "#7570b3", 82: "#d99b16"}
CASES = {
    "sniezna": ("MLZ", "MLZ-0068", "C-0648", "T.E-13.01", "Jaskinia Śnieżna", "sniezna-2025-100m.las"),
    "pod-wanta": ("MTW", "MTW-0054", "C-0711", "T.E-12.03", "Jaskinia pod Wantą", "pod-wanta-2025-both-positions.las"),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb_renderer():
    renderer = QgsPointCloudRgbRenderer()
    renderer.setRedAttribute("Red")
    renderer.setGreenAttribute("Green")
    renderer.setBlueAttribute("Blue")
    for colour in ("Red", "Green", "Blue"):
        contrast = QgsContrastEnhancement(Qgis.DataType.UInt16)
        contrast.setMinimumValue(0)
        contrast.setMaximumValue(65535)
        contrast.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum)
        getattr(renderer, f"set{colour}ContrastEnhancement")(contrast)
    renderer.setPointSize(3.0)
    renderer.setPointSizeUnit(Qgis.RenderUnit.Pixels)
    renderer.setMaximumScreenError(0.1)
    renderer.setMaximumScreenErrorUnit(Qgis.RenderUnit.Pixels)
    renderer.setDrawOrder2d(Qgis.PointCloudDrawOrder.BottomToTop)
    return renderer


def source_renderer():
    renderer = QgsPointCloudClassifiedRenderer("PointSourceId", [
        QgsPointCloudCategory(i, QColor(colour), f"PointSourceId {i}")
        for i, colour in ID_COLOURS.items()
    ])
    renderer.setPointSize(3.0)
    renderer.setPointSizeUnit(Qgis.RenderUnit.Pixels)
    renderer.setMaximumScreenError(0.1)
    renderer.setMaximumScreenErrorUnit(Qgis.RenderUnit.Pixels)
    renderer.setDrawOrder2d(Qgis.PointCloudDrawOrder.BottomToTop)
    return renderer


def make_markers(project):
    memory = QgsVectorLayer("Point?crs=EPSG:2180", "Pozycje YAML — XY bez wysokości", "memory")
    provider = memory.dataProvider()
    fields = [
        QgsField("object_id", QMetaType.Type.QString),
        QgsField("source", QMetaType.Type.QString),
        QgsField("measurement", QMetaType.Type.QString),
        QgsField("label", QMetaType.Type.QString),
        QgsField("easting_m", QMetaType.Type.Double),
        QgsField("northing_m", QMetaType.Type.Double),
        QgsField("record_z_m", QMetaType.Type.Double),
        QgsField("record_datum", QMetaType.Type.QString),
        QgsField("source_ref", QMetaType.Type.QString),
    ]
    provider.addAttributes(fields)
    memory.updateFields()
    records = {}
    yaml_hashes = {}
    for key, (prefix, object_id, cave_id, inventory, name, filename) in CASES.items():
        path = ROOT / f"data/objects/{prefix}/{object_id}.yml"
        data = yaml.safe_load(path.read_text())
        assert data["id"] == object_id and data["cave_id"] == cave_id
        yaml_hashes[str(path.relative_to(ROOT))] = sha256(path)
        records[key] = {}
        for row in data["measurements"]:
            if row["source"] not in SOURCE_COLOURS:
                continue
            assert row["source"] not in records[key], "Ambiguous source: choose measurement explicitly"
            x, y = row["y_1992"], row["x_1992"]
            records[key][row["source"]] = {**row, "easting": x, "northing": y}
            feature = QgsFeature(memory.fields())
            feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
            feature.setAttributes([
                object_id, row["source"], row["id"],
                f'{object_id} · {row["source"]}\n{row["id"]} · XY',
                x, y, row.get("elevation_m"), row.get("elevation_datum", "unknown"),
                row.get("source_ref", ""),
            ])
            provider.addFeatures([feature])
    memory.updateExtents()
    marker_path = BUILD / "qgis-2025-markers.gpkg"
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = "yaml_xy"
    result = QgsVectorFileWriter.writeAsVectorFormatV3(memory, str(marker_path), project.transformContext(), options)
    assert result[0] == QgsVectorFileWriter.NoError, result
    markers = QgsVectorLayer(str(marker_path) + "|layername=yaml_xy", memory.name(), "ogr")
    assert markers.isValid() and markers.featureCount() == 4
    categories = []
    for source, colour in SOURCE_COLOURS.items():
        symbol = QgsMarkerSymbol.createSimple({
            "name": "cross2", "color": "#ffffff", "outline_color": "#ffffff",
            "outline_width": "0.9", "size": "3.6", "size_unit": "MM",
        })
        foreground = QgsMarkerSymbol.createSimple({
            "name": "cross2", "color": colour, "outline_color": colour,
            "outline_width": "0.45", "size": "3", "size_unit": "MM",
        })
        symbol.appendSymbolLayer(foreground.symbolLayer(0).clone())
        categories.append(QgsRendererCategory(source, symbol, source + " · zapisane XY"))
    markers.setRenderer(QgsCategorizedSymbolRenderer("source", categories))
    settings = QgsPalLayerSettings()
    settings.fieldName = "label"
    settings.dist = 2.0
    text_format = QgsTextFormat()
    text_format.setFont(QFont("Arial", 9))
    text_format.setSize(9)
    text_format.setColor(QColor("#111111"))
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(0.9)
    buffer.setColor(QColor("#ffffff"))
    text_format.setBuffer(buffer)
    settings.setFormat(text_format)
    markers.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    markers.setLabelsEnabled(True)
    project.addMapLayer(markers)
    return markers, records, yaml_hashes


def label(layout, text, x, y, w, h, size=10):
    item = QgsLayoutItemLabel(layout)
    item.setText(text)
    item.setFont(QFont("Arial", size))
    layout.addLayoutItem(item)
    item.attemptMove(QgsLayoutPoint(x, y))
    item.attemptResize(QgsLayoutSize(w, h))
    return item


def render_layout(project, name, title, subtitle, extent, layers, scale_length):
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(name)
    layout.pageCollection().pages()[0].setPageSize(QgsLayoutSize(210, 258))
    label(layout, title, 12, 7, 190, 10, 14)
    label(layout, subtitle, 12, 18, 190, 10, 9)
    item = QgsLayoutItemMap(layout)
    layout.addLayoutItem(item)
    item.attemptMove(QgsLayoutPoint(12, 35))
    item.attemptResize(QgsLayoutSize(186, 186))
    item.setCrs(CRS)
    item.setLayers(layers)
    item.setKeepLayerSet(True)
    item.setMapRotation(0)
    item.zoomToExtent(extent)
    item.setFrameEnabled(True)
    item.setBackgroundEnabled(True)
    item.setBackgroundColor(QColor("#1d242b"))
    label(layout, "↑ N", 182, 27, 20, 8, 11)
    bar = QgsLayoutItemScaleBar(layout)
    bar.setStyle("Single Box")
    bar.setLinkedMap(item)
    bar.setUnits(Qgis.DistanceUnit.Meters)
    bar.setUnitsPerSegment(scale_length / 2)
    bar.setNumberOfSegments(2)
    bar.setNumberOfSegmentsLeft(0)
    bar.setUnitLabel("m")
    bar.setFont(QFont("Arial", 8))
    bar.setHeight(2)
    layout.addLayoutItem(bar)
    bar.attemptMove(QgsLayoutPoint(12, 225))
    label(layout, "Północ siatkowa ↑ · EPSG:2180 · X = easting, Y = northing", 70, 226, 130, 9, 8)
    label(layout, "Krzyżyki = zapisane XY. Z YAML nie użyto; datum wszystkich pomiarów: unknown.\n"
                  "Punkty ALS 2025, RGB; bez interpolacji. Brak odbić nie dowodzi istnienia otworu.",
          12, 238, 188, 12, 8)
    project.layoutManager().addLayout(layout)
    settings = QgsLayoutExporter.ImageExportSettings()
    settings.dpi = 180
    destination = HERE / f"qgis-{name}.png"
    result = QgsLayoutExporter(layout).exportToImage(str(destination), settings)
    assert result == QgsLayoutExporter.Success, result
    bookmark = QgsBookmark()
    bookmark.setName(title)
    bookmark.setGroup("PBI-112 · 2025 · XY")
    bookmark.setExtent(QgsReferencedRectangle(item.extent(), CRS))
    project.bookmarkManager().addBookmark(bookmark)
    return {"name": name, "extent": [item.extent().xMinimum(), item.extent().yMinimum(), item.extent().xMaximum(), item.extent().yMaximum()],
            "rotation_degrees": 0, "scale_bar_m": scale_length, "png": destination.name,
            "sha256": sha256(destination)}


def square(x, y, width):
    return QgsRectangle(x - width/2, y - width/2, x + width/2, y + width/2)


def main():
    global CRS
    app = QgsApplication([], False)
    app_path = Path(os.environ.get("QGIS_APP", "/Applications/QGIS-final-4_0_1.app"))
    app.setPrefixPath(str(app_path), True)
    app.initQgis()
    CRS = QgsCoordinateReferenceSystem("EPSG:2180")
    project = QgsProject.instance()
    project.setCrs(CRS)
    project.setTitle("PBI-112: chmury 2025 i zapisane pozycje XY")
    inspection = json.loads((HERE.parent / "inspection.json").read_text())
    clouds = {}
    provenance = {}
    for key, (_, object_id, cave_id, inventory, name, filename) in CASES.items():
        path = BUILD / filename
        digest = sha256(path)
        assert digest == inspection[filename]["sha256"], filename + " checksum mismatch"
        # Explicit indexing avoids a stale -indexing lock left by asynchronous
        # PDAL-provider indexing when a short standalone process ends early.
        # COPC is a spatially indexed copy; the original LAS is retained.
        copc = BUILD / f"qgis-{key}.copc.laz"
        subprocess.run([str(app_path / "Contents/MacOS/untwine"), "-i", str(path),
                        "-o", str(copc), "--stats", "--metadata"], check=True)
        layer = QgsPointCloudLayer(str(copc), f"{name} · ALS 2025 · COPC copy", "copc")
        assert layer.isValid(), layer.error().summary()
        deadline = time.monotonic() + 180
        while not layer.dataProvider().hasValidIndex():
            QCoreApplication.processEvents()
            if time.monotonic() > deadline:
                raise RuntimeError("QGIS point cloud index timed out: " + filename)
            time.sleep(0.1)
        assert layer.pointCount() == inspection[filename]["count"]
        layer.setRenderer(rgb_renderer())
        rgb = QgsMapLayerStyle()
        rgb.readFromLayer(layer)
        layer.styleManager().addStyle("RGB · punkty", rgb)
        layer.setRenderer(source_renderer())
        source = QgsMapLayerStyle()
        source.readFromLayer(layer)
        layer.styleManager().addStyle("PointSourceId · grupy nie azymuty", source)
        layer.setRenderer(rgb_renderer())
        project.addMapLayer(layer)
        clouds[key] = layer
        provenance[filename] = {"sha256": digest, "copc_file": str(copc.relative_to(ROOT)),
                                "copc_sha256": sha256(copc), "point_count": layer.pointCount(), "crs": layer.crs().authid(),
                                "point_source_ids": list(inspection[filename]["source_id_counts"])}
        print("Indexed", filename, layer.pointCount(), flush=True)
    markers, records, yaml_hashes = make_markers(project)
    views = []
    sn = records["sniezna"]["TPN"]
    pw = records["pod-wanta"]
    configs = [
        ("sniezna-overview", "Jaskinia Śnieżna · MLZ-0068", "T.E-13.01 · 2025 · widok z góry · obie pozycje", "sniezna", square(sn["easting"], sn["northing"], 110), 20),
        ("sniezna-detail", "Śnieżna · TPN i PIG · XY", "MLZ-0068 · T.E-13.01 · 2025 · szczegół 30 × 30 m", "sniezna", square(sn["easting"] + 1.5, sn["northing"] - 2, 30), 5),
        ("pod-wanta-overview", "Jaskinia pod Wantą · MTW-0054", "T.E-12.03 · 2025 · TPN i PIG: odległość XY około 106 m", "pod-wanta", square((pw["TPN"]["easting"] + pw["PIG"]["easting"])/2, (pw["TPN"]["northing"] + pw["PIG"]["northing"])/2, 220), 40),
        ("pod-wanta-tpn-detail", "Pod Wantą · otoczenie pozycji TPN", "MTW-0054 · m-002 · 2025 · szczegół 30 × 30 m", "pod-wanta", square(pw["TPN"]["easting"], pw["TPN"]["northing"], 30), 5),
        ("pod-wanta-pig-detail", "Pod Wantą · otoczenie pozycji PIG", "MTW-0054 · m-001 · 2025 · szczegół 30 × 30 m", "pod-wanta", square(pw["PIG"]["easting"], pw["PIG"]["northing"], 30), 5),
    ]
    for name, title, subtitle, key, extent, scale in configs:
        views.append(render_layout(project, name, title, subtitle, extent, [markers, clouds[key]], scale))
        print("Rendered", name, flush=True)
    project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(configs[1][4], CRS))
    output = BUILD / "qgis-2025-assessment.qgz"
    assert project.write(str(output))
    metadata = {"qgis": Qgis.QGIS_VERSION, "python": sys.version, "project": str(output.relative_to(ROOT)),
                "map_crs": "EPSG:2180", "vertical_geometry": "none; markers are 2D XY only",
                "las_z_datum": "PL-EVRF2007-NH from index, absent in LAS header", "catalogue_hashes": yaml_hashes,
                "pointclouds": provenance, "views": views, "marker_count": markers.featureCount(),
                "rendering": {"point_size_px": 3.0, "maximum_screen_error_px": 0.1,
                              "rgb_range": [0, 65535], "draw_order": "BottomToTop", "interpolation": False}}
    (HERE / "qgis-manifest.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print("Saved", output, flush=True)
    # QGIS/Qt provider finalization in this app build emits teardown warnings;
    # all writes and exports are synchronously complete before returning.


if __name__ == "__main__":
    main()
