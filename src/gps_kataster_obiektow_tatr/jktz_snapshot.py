"""Resolve a public JKTZ release once, then consume its survey exports offline."""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
import stat
import struct
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import shapefile
from pyproj import CRS

REPOSITORY = "dlubom/Jaskiniowy-Kataster-Tatr-Zachodnich"
GITHUB_ROOT = f"https://github.com/{REPOSITORY}"
LATEST_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
DEFAULT_JKTZ_SOURCE_DIR = Path("build/inputs/jktz")
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_SELECTED_BYTES = 200 * 1024 * 1024
VERSION_PATTERN = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+")
MODEL_PATTERN = re.compile(
    r"exports/caves/([A-Za-z0-9_][A-Za-z0-9_.-]{0,127})\.(shp|shx|dbf|prj|cpg)"
)
ATTRIBUTION_FILES = ("LICENCE", "INFO.txt", "README.md", "LISTA_JASKIN.md")


@dataclass(frozen=True, slots=True)
class JktzModel:
    """One original per-prefix survey export, not a GPS catalog join."""

    prefix: str
    feature_count: int


@dataclass(frozen=True, slots=True)
class JktzSnapshot:
    """Validated local inputs; provenance contains no machine-specific paths."""

    metadata: dict
    models: tuple[JktzModel, ...]
    members: dict[str, bytes]


def load_jktz_snapshot(source_dir: Path) -> JktzSnapshot:
    """Verify a resolved local archive, including complete native XYZ model files."""
    try:
        metadata_path = source_dir / "source.json"
        if metadata_path.stat().st_size > 1024 * 1024:
            raise ValueError("JKTZ metadata exceeds the size limit")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        _validate_metadata(metadata)
        archive_path = source_dir / "JKTZ.zip"
        if archive_path.stat().st_size > MAX_ARCHIVE_BYTES:
            raise ValueError("JKTZ archive exceeds the size limit")
        archive_bytes = archive_path.read_bytes()
        if hashlib.sha256(archive_bytes).hexdigest() != metadata["sha256"]:
            raise ValueError("JKTZ archive SHA-256 differs from the resolved release")
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("JKTZ archive contains duplicate members")
            selected = []
            for info in archive.infolist():
                relevant = info.filename in ATTRIBUTION_FILES or MODEL_PATTERN.fullmatch(
                    info.filename
                )
                if (
                    info.filename.startswith("exports/caves/")
                    and info.filename.endswith((".shp", ".shx", ".dbf", ".prj", ".cpg"))
                    and not MODEL_PATTERN.fullmatch(info.filename)
                ):
                    raise ValueError(f"Unsafe JKTZ model path: {info.filename}")
                if relevant:
                    if stat.S_ISLNK(info.external_attr >> 16):
                        raise ValueError("JKTZ model members must be regular files")
                    selected.append(info)
            if sum(info.file_size for info in selected) > MAX_SELECTED_BYTES:
                raise ValueError("JKTZ model files exceed the size limit")
            members = {info.filename: archive.read(info) for info in selected}
        for required in ATTRIBUTION_FILES[:3]:
            if not members.get(required):
                raise ValueError(f"Missing JKTZ attribution file: {required}")
        prefixes = sorted(
            {match[1] for name in members if (match := MODEL_PATTERN.fullmatch(name))}
        )
        if not prefixes:
            raise ValueError("JKTZ archive contains no per-model survey exports")
        models = tuple(_validate_model(prefix, members) for prefix in prefixes)
        return JktzSnapshot(metadata=metadata, models=models, members=members)
    except (OSError, zipfile.BadZipFile, KeyError, TypeError, struct.error) as exc:
        raise ValueError(f"Invalid JKTZ snapshot in {source_dir}: {exc}") from exc


def _validate_metadata(metadata: dict) -> None:
    if not isinstance(metadata, dict):
        raise ValueError("JKTZ source metadata must be an object")
    version = metadata.get("version")
    if not isinstance(version, str) or not VERSION_PATTERN.fullmatch(version):
        raise ValueError("JKTZ requires a stable vMAJOR.MINOR.PATCH release")
    if metadata.get("schema_version") != 1 or metadata.get("repository") != REPOSITORY:
        raise ValueError("Unrecognized JKTZ source metadata")
    expected_url = f"{GITHUB_ROOT}/releases/download/{version}/JKTZ-{version}.zip"
    if metadata.get("release_url") != f"{GITHUB_ROOT}/releases/tag/{version}":
        raise ValueError("Unexpected JKTZ release URL")
    if metadata.get("asset_url") != expected_url:
        raise ValueError("Unexpected JKTZ archive URL")
    digest = metadata.get("sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("Missing JKTZ archive SHA-256")


def _validate_model(prefix: str, members: dict[str, bytes]) -> JktzModel:
    stem = f"exports/caves/{prefix}"
    if any(f"{stem}.{suffix}" not in members for suffix in ("shp", "shx", "dbf", "prj")):
        raise ValueError(f"Incomplete JKTZ Shapefile set: {prefix}")
    try:
        crs = CRS.from_wkt(members[f"{stem}.prj"].decode("utf-8"))
        if not crs.equals(CRS.from_epsg(32634), ignore_axis_order=True):
            raise ValueError(f"JKTZ model {prefix} is not EPSG:32634")
        with shapefile.Reader(
            shp=io.BytesIO(members[f"{stem}.shp"]),
            shx=io.BytesIO(members[f"{stem}.shx"]),
            dbf=io.BytesIO(members[f"{stem}.dbf"]),
        ) as reader:
            if reader.shapeType != shapefile.POLYLINEZ or len(reader) == 0:
                raise ValueError(f"JKTZ model {prefix} must contain XYZ survey lines")
            shapes = list(reader.iterShapes())
            records = list(reader.iterRecords())
            if len(shapes) != len(reader) or len(records) != len(reader):
                raise ValueError(f"Incomplete JKTZ geometry/attributes: {prefix}")
            for shape in shapes:
                if shape.shapeType != shapefile.POLYLINEZ or len(shape.points) < 2:
                    raise ValueError(f"Invalid JKTZ line: {prefix}")
                values = [value for point in shape.points for value in point] + list(shape.z)
                if not all(math.isfinite(value) for value in values):
                    raise ValueError(f"Non-finite JKTZ coordinate: {prefix}")
            return JktzModel(prefix=prefix, feature_count=len(reader))
    except (shapefile.ShapefileException, UnicodeError, RuntimeError) as exc:
        raise ValueError(f"Invalid JKTZ model {prefix}: {exc}") from exc


def fetch_latest_jktz(output_dir: Path, *, token: str | None = None) -> Path:
    """Resolve and atomically publish one latest stable release for subsequent offline builds."""
    if output_dir.exists():
        raise ValueError(f"JKTZ input directory already exists: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "gps-kataster-qgis"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        request = urllib.request.Request(LATEST_URL, headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read(1024 * 1024 + 1)
        if len(payload) > 1024 * 1024:
            raise ValueError("JKTZ release response exceeds the size limit")
        release = json.loads(payload)
        version = release.get("tag_name")
        if release.get("draft") is not False or release.get("prerelease") is not False:
            raise ValueError("JKTZ release must be stable and published")
        if not isinstance(version, str) or not VERSION_PATTERN.fullmatch(version):
            raise ValueError("Invalid JKTZ release tag")
        assets = [a for a in release.get("assets", []) if a.get("name") == f"JKTZ-{version}.zip"]
        if len(assets) != 1:
            raise ValueError("JKTZ release must contain exactly one versioned archive")
        asset = assets[0]
        digest = asset.get("digest", "")
        if not isinstance(digest, str) or not digest.startswith("sha256:"):
            raise ValueError("JKTZ release asset lacks a SHA-256 digest")
        metadata = {
            "schema_version": 1,
            "repository": REPOSITORY,
            "version": version,
            "release_url": release.get("html_url"),
            "asset_url": asset.get("browser_download_url"),
            "sha256": digest.removeprefix("sha256:"),
        }
        _validate_metadata(metadata)
        size = asset.get("size")
        if not isinstance(size, int) or not 0 < size <= MAX_ARCHIVE_BYTES:
            raise ValueError("Invalid JKTZ release archive size")
        with TemporaryDirectory(prefix="jktz-", dir=output_dir.parent) as temporary:
            stage = Path(temporary) / "input"
            stage.mkdir()
            # Public asset request has no token; redirects never receive API credentials.
            request = urllib.request.Request(
                metadata["asset_url"], headers={"User-Agent": "gps-kataster-qgis"}
            )
            received = 0
            with (
                urllib.request.urlopen(request, timeout=60) as response,
                (stage / "JKTZ.zip").open("wb") as stream,
            ):
                while chunk := response.read(1024 * 1024):
                    received += len(chunk)
                    if received > size:
                        raise ValueError("JKTZ download exceeds the resolved asset size")
                    stream.write(chunk)
            if received != size:
                raise ValueError("Incomplete JKTZ release download")
            (stage / "source.json").write_text(
                json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            load_jktz_snapshot(stage)
            stage.rename(output_dir)
        return output_dir
    except (OSError, urllib.error.URLError, KeyError, TypeError) as exc:
        raise ValueError(f"Could not resolve JKTZ release: {exc}") from exc
