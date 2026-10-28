"""Small, real survey archives for offline QGIS export tests."""

import hashlib
import io
import json
import zipfile
from pathlib import Path

import shapefile
from pyproj import CRS

JKTZ_REPOSITORY = "dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich"


def jktz_members() -> dict[str, bytes]:
    members = {
        "LICENCE": b"Creative Commons Attribution-ShareAlike 4.0 International\n",
        "INFO.txt": b"Synthetic survey fixture, not real cave data.\n",
        "README.md": b"Fixture authors; https://creativecommons.org/licenses/by-sa/4.0/\n",
        "LISTA_JASKIN.md": b"- Alpha\n- Beta\n",
    }
    for prefix, offset in (("Alpha", 0), ("Beta", 100)):
        shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
        with shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POLYLINEZ) as writer:
            writer.field("Layer", "C", size=80)
            writer.linez([[[420000 + offset, 5450000, 1200], [420010 + offset, 5450020, 1180]]])
            writer.record("CentreLine")
        stem = f"exports/caves/{prefix}"
        for suffix, stream in (("shp", shp), ("shx", shx), ("dbf", dbf)):
            members[f"{stem}.{suffix}"] = stream.getvalue()
        members[f"{stem}.prj"] = CRS.from_epsg(32634).to_wkt(version="WKT1_ESRI").encode()
        members[f"{stem}.cpg"] = b"UTF-8"
    return members


def write_jktz_source(
    path: Path, *, members: dict[str, bytes] | None = None, version: str = "v9.8.7"
) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    archive = path / "JKTZ.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for name, content in (members if members is not None else jktz_members()).items():
            zipped.writestr(name, content)
    metadata = {
        "schema_version": 1,
        "repository": JKTZ_REPOSITORY,
        "version": version,
        "release_url": f"https://github.com/{JKTZ_REPOSITORY}/releases/tag/{version}",
        "asset_url": (
            f"https://github.com/{JKTZ_REPOSITORY}/releases/download/{version}/JKTZ-{version}.zip"
        ),
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }
    (path / "source.json").write_text(json.dumps(metadata), encoding="utf-8")
    return path
