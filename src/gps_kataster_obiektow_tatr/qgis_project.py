"""Conservative native QGIS XML and reviewed online image-layer definitions."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import urlencode
from uuid import NAMESPACE_URL, uuid5

from pyproj import CRS

TPN_MAX_SCALE_DENOMINATOR = 25000
BASEMAPS = (
    {
        "id": "tpn_rgb_2020",
        "name": "TPN — ortofotomapa RGB 2020",
        "url": "https://tpn.obliview.com/Data/rgb_2020/{z}/{x}/{y}.jpg",
        "zmin": 15,
        "zmax": 20,
    },
    {
        "id": "tpn_rgb_2018",
        "name": "TPN — ortofotomapa RGB 2018",
        "url": "https://tpn.obliview.com/Data/rgb_2018/{z}/{x}/{y}.jpg",
        "zmin": 15,
        "zmax": 20,
    },
    {
        "id": "tpn_nmt_image",
        "name": "TPN — NMT (obraz modelu gruntu)",
        "url": "https://tpn.obliview.com/Data/NMT/{z}/{x}/{y}.jpg",
        "zmin": 15,
        "zmax": 20,
    },
    {
        "id": "tpn_nmpt_image",
        "name": "TPN — NMPT (obraz pokrycia terenu)",
        "url": "https://tpn.obliview.com/Data/nmpt/{z}/{x}/{y}.jpg",
        "zmin": 15,
        "zmax": 20,
    },
    {
        "id": "osm_basemap",
        "name": "OpenStreetMap — przegląd i tło",
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "zmin": 0,
        "zmax": 19,
    },
)

MAP_TIP = """<b>[% "display_name_html" %]</b><br>
[% "object_id" %] / [% "measurement_id" %]<br>
Źródło: [% "source_html" %]<br>
Status: [% "verification_status" %]<br>
Odległość od Best: [% format_number("distance_to_best_m", 2) %] m<br>
Dokładność pozioma: [%
if("horizontal_accuracy_m" IS NULL,'nieznana',to_string("horizontal_accuracy_m") || ' m')
%]<br>
[% "measurement_notes_html" %]"""


def project_xml(
    *,
    layers: list[dict],
    extent: tuple,
    bookmarks: list[tuple],
    version: str | None,
    jktz_version: str,
) -> bytes:
    """Serialize a 3.x-compatible project; native acceptance checks own compatibility proof."""
    root = ET.Element(
        "qgis", {"version": "3.44.15-Solothurn", "projectname": "GPS Kataster Obiektów Tatr"}
    )
    ET.SubElement(root, "homePath", {"path": ""})
    ET.SubElement(
        root, "title"
    ).text = f"GPS — {version or 'podgląd lokalny'} · JKTZ {jktz_version}"
    _crs(ET.SubElement(root, "projectCrs"), 2180)
    tree = ET.SubElement(
        root, "layer-tree-group", {"name": "", "checked": "Qt::Checked", "expanded": "1"}
    )
    points = _group(tree, "Punkty GPS — Best i historia")
    tables = _group(tree, "Pełna tabela", checked=False)
    surveys = _group(tree, f"JKTZ {jktz_version} — ciągi poligonowe", checked=False, expanded=False)
    maps = _group(tree, "Podkłady online")
    tpn = _group(maps, "TPN — wybierz jeden podkład")
    tpn.set("mutually-exclusive", "1")
    tpn.set("mutually-exclusive-child", "0")
    native_layers = ET.SubElement(root, "projectlayers")
    for layer in layers:
        group = (
            surveys if layer["role"] == "jktz" else tables if layer["role"] == "full" else points
        )
        _tree_layer(group, layer["id"], layer["name"], layer["role"] == "best")
        _vector_layer(native_layers, layer)
    for basemap in BASEMAPS:
        _tree_layer(
            maps if basemap["id"] == "osm_basemap" else tpn,
            basemap["id"],
            basemap["name"],
            basemap["id"] in {"tpn_rgb_2020", "osm_basemap"},
        )
        _raster_layer(native_layers, basemap)
    order = ET.SubElement(root, "layerorder")
    for layer in [*layers, *BASEMAPS]:
        ET.SubElement(order, "layer", {"id": layer["id"]})
    canvas = ET.SubElement(root, "mapcanvas", {"name": "theMapCanvas"})
    ET.SubElement(canvas, "units").text = "meters"
    _extent(ET.SubElement(canvas, "extent"), extent)
    _crs(ET.SubElement(canvas, "destinationsrs"), 2180)
    views = ET.SubElement(root, "ProjectViewSettings", {"UseProjectScales": "0", "rotation": "0"})
    default = ET.SubElement(
        views,
        "DefaultViewExtent",
        dict(zip(("xmin", "ymin", "xmax", "ymax"), map(str, extent), strict=True)),
    )
    _crs(default, 2180)
    native_bookmarks = ET.SubElement(root, "Bookmarks")
    for name, rectangle in bookmarks:
        xmin, ymin, xmax, ymax = rectangle
        polygon = (
            f"Polygon (({xmin} {ymin}, {xmax} {ymin}, {xmax} {ymax}, {xmin} {ymax}, {xmin} {ymin}))"
        )
        bookmark = ET.SubElement(
            native_bookmarks,
            "Bookmark",
            {
                "id": str(uuid5(NAMESPACE_URL, f"gps-kataster/bookmark/{name}")),
                "name": name,
                "group": "GPS — rejony",
                "extent": polygon,
                "rotation": "0",
            },
        )
        _crs(bookmark, 2180)
    properties = ET.SubElement(root, "properties")
    projections = ET.SubElement(properties, "SpatialRefSys")
    ET.SubElement(projections, "ProjectionsEnabled", {"type": "int"}).text = "1"
    paths = ET.SubElement(properties, "Paths")
    ET.SubElement(paths, "Absolute", {"type": "bool"}).text = "false"
    gui = ET.SubElement(properties, "Gui")
    for component, value in (("Red", 53), ("Green", 60), ("Blue", 64)):
        ET.SubElement(gui, f"CanvasColor{component}Part", {"type": "int"}).text = str(value)
    measure = ET.SubElement(properties, "Measurement")
    ET.SubElement(measure, "DistanceUnits", {"type": "QString"}).text = "meters"
    ET.SubElement(measure, "AreaUnits", {"type": "QString"}).text = "m2"
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _crs(parent: ET.Element, epsg: int) -> None:
    crs = CRS.from_epsg(epsg)
    node = ET.SubElement(parent, "spatialrefsys", {"nativeFormat": "Wkt"})
    for name, value in (
        ("wkt", crs.to_wkt()),
        ("srsid", "0"),
        ("srid", str(epsg)),
        ("authid", f"EPSG:{epsg}"),
        ("description", crs.name),
        ("geographicflag", "true" if crs.is_geographic else "false"),
    ):
        ET.SubElement(node, name).text = value


def _group(
    parent: ET.Element, name: str, *, checked: bool = True, expanded: bool = True
) -> ET.Element:
    return ET.SubElement(
        parent,
        "layer-tree-group",
        {
            "name": name,
            "checked": "Qt::Checked" if checked else "Qt::Unchecked",
            "expanded": str(int(expanded)),
        },
    )


def _tree_layer(parent: ET.Element, layer_id: str, name: str, checked: bool) -> None:
    ET.SubElement(
        parent,
        "layer-tree-layer",
        {
            "id": layer_id,
            "name": name,
            "checked": "Qt::Checked" if checked else "Qt::Unchecked",
            "expanded": "0",
        },
    )


def _extent(parent: ET.Element, extent: tuple) -> None:
    for name, value in zip(("xmin", "ymin", "xmax", "ymax"), extent, strict=True):
        ET.SubElement(parent, name).text = repr(value)


def _vector_layer(parent: ET.Element, spec: dict) -> None:
    line = spec["role"] in {"jktz", "differences"}
    node = ET.SubElement(
        parent,
        "maplayer",
        {
            "type": "vector",
            "geometry": "Line" if line else "Point",
            "readOnly": "1",
            "labelsEnabled": str(int(spec["role"] == "best")),
            "hasScaleBasedVisibilityFlag": "0",
        },
    )
    ET.SubElement(node, "id").text = spec["id"]
    ET.SubElement(node, "layername").text = spec["name"]
    datasource = "./" + spec["path"]
    if spec["role"] != "jktz" and spec["count"] == 0:
        # Empty GeoJSON has no native geometry metadata. Preserve its intended
        # type so QGIS retains the symbol and accepts a legal empty partition.
        datasource += "|geometrytype=" + ("LineString" if line else "Point")
    ET.SubElement(node, "datasource").text = datasource
    ET.SubElement(node, "provider", {"encoding": "UTF-8"}).text = "ogr"
    _crs(ET.SubElement(node, "srs"), 32634 if spec["role"] == "jktz" else 4326)
    ET.SubElement(node, "previewExpression").text = (
        "'" + spec["model"] + "'"
        if spec["role"] == "jktz"
        else '"display_name" || \' / \' || "measurement_id"'
    )
    if not line:
        ET.SubElement(node, "mapTip").text = MAP_TIP
        aliases = ET.SubElement(node, "aliases")
        for field, label in (
            ("object_id", "ID obiektu"),
            ("measurement_id", "ID pomiaru"),
            ("source", "Źródło"),
            ("verification_status", "Status weryfikacji"),
            ("distance_to_best_m", "Odległość od Best [m]"),
            ("horizontal_accuracy_m", "Dokładność pozioma [m]"),
            ("measurement_notes", "Uwagi pomiaru"),
            ("best_reason", "Uzasadnienie Best"),
        ):
            ET.SubElement(aliases, "alias", {"field": field, "name": label})
    elif spec["role"] == "differences":
        ET.SubElement(node, "mapTip").text = (
            '[% "object_id" %] / [% "measurement_id" %]<br>'
            'Różnica XY: [% format_number("distance_m",2) %] m'
        )
    renderer = ET.SubElement(node, "renderer-v2", {"type": "singleSymbol", "symbollevels": "0"})
    symbol = ET.SubElement(
        ET.SubElement(renderer, "symbols"),
        "symbol",
        {"name": "0", "type": "line" if line else "marker", "alpha": "1"},
    )
    symbol_layer = ET.SubElement(
        symbol,
        "layer",
        {
            "class": "SimpleLine" if line else "SimpleMarker",
            "enabled": "1",
            "pass": "0",
            "locked": "0",
        },
    )
    if line:
        options = {
            "line_color": "194,153,255,255" if spec["role"] == "jktz" else "255,226,125,220",
            "line_width": "0.35" if spec["role"] == "jktz" else "0.28",
            "line_width_unit": "MM",
            "line_style": "solid" if spec["role"] == "jktz" else "dash",
        }
    else:
        role = spec["role"]
        options = {
            "name": "star" if role == "best" else "cross2" if role == "rejected" else "circle",
            "color": "255,210,58,255"
            if role == "best"
            else "255,102,190,255"
            if role == "rejected"
            else "0,0,0,0",
            "outline_color": "38,37,29,255"
            if role == "best"
            else "255,102,190,255"
            if role == "rejected"
            else "78,203,255,255",
            "outline_width": "0.3" if role == "best" else "0.5",
            "size": "3.6" if role == "best" else "3",
            "size_unit": "MM",
            "outline_width_unit": "MM",
        }
    values = ET.SubElement(symbol_layer, "Option", {"type": "Map"})
    for name, value in sorted(options.items()):
        ET.SubElement(values, "Option", {"name": name, "value": value, "type": "QString"})
    if spec["role"] == "best":
        settings = ET.SubElement(ET.SubElement(node, "labeling", {"type": "simple"}), "settings")
        style = ET.SubElement(
            settings,
            "text-style",
            {
                "fieldName": (
                    'CASE WHEN @map_scale <= 6500 THEN "display_name" || \'\\n\' || "object_id" END'
                ),
                "isExpression": "1",
                "fontFamily": "Sans Serif",
                "fontSize": "9",
                "fontWeight": "50",
                "fontSizeUnit": "Point",
                "textColor": "255,255,255,255",
                "textOpacity": "1",
                "allowHtml": "0",
            },
        )
        families = ET.SubElement(style, "families")
        for family in ("Arial", "DejaVu Sans", "Noto Sans", "Liberation Sans"):
            ET.SubElement(families, "family", {"name": family})
        ET.SubElement(
            style,
            "text-buffer",
            {
                "bufferDraw": "1",
                "bufferSize": "0.8",
                "bufferSizeUnits": "MM",
                "bufferColor": "37,42,43,255",
                "bufferOpacity": "1",
            },
        )
        ET.SubElement(settings, "placement", {"placement": "0", "dist": "1", "distUnits": "MM"})
        ET.SubElement(settings, "rendering", {"drawLabels": "1", "scaleVisibility": "0"})


def _raster_layer(parent: ET.Element, spec: dict) -> None:
    tpn = spec["id"].startswith("tpn_")
    node = ET.SubElement(
        parent,
        "maplayer",
        {
            "type": "raster",
            "hasScaleBasedVisibilityFlag": str(int(tpn)),
            "minScale": str(TPN_MAX_SCALE_DENOMINATOR if tpn else 1e8),
            "maxScale": "0",
        },
    )
    ET.SubElement(node, "id").text = spec["id"]
    ET.SubElement(node, "layername").text = spec["name"]
    ET.SubElement(node, "datasource").text = urlencode(
        {
            "type": "xyz",
            "url": spec["url"],
            "zmin": spec["zmin"],
            "zmax": spec["zmax"],
            "crs": "EPSG:3857",
        }
    )
    ET.SubElement(node, "provider").text = "wms"
    _crs(ET.SubElement(node, "srs"), 3857)
    renderer = ET.SubElement(
        ET.SubElement(node, "pipe"),
        "rasterrenderer",
        {"type": "singlebandcolordata", "band": "1", "alphaBand": "-1", "opacity": "1"},
    )
    ET.SubElement(renderer, "rasterTransparency")
