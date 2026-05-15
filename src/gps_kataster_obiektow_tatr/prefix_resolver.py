"""Resolve durable object ID prefixes from WGS84 coordinates."""

from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

import shapefile
import yaml

from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PREFIX_CONFIG_PATH = REPO_ROOT / "config" / "prefixes.yml"
DEFAULT_SHAPES_DIR = REPO_ROOT / "data" / "shapes"

VALLEY_SHAPE_NAME = "doliny.shp"
POLAND_SHAPE_NAME = "granica_polski.shp"
SLOVAKIA_SHAPE_NAME = "granica_slowacji.shp"

POLAND_FALLBACK_KEY = "polska"
SLOVAKIA_FALLBACK_KEY = "slowacja"

OUTSIDE_VALLEYS_CODE = "POINT_OUTSIDE_VALLEYS"
OUTSIDE_COUNTRIES_CODE = "POINT_OUTSIDE_PL_SK"
OUTSIDE_VALLEYS_MESSAGE = (
    "Point is inside Poland or Slovakia but outside configured Tatra valley polygons; "
    "manual review is required before assigning a durable ID."
)
OUTSIDE_COUNTRIES_MESSAGE = "Point is outside Poland and Slovakia fallback boundaries."

Point = tuple[float, float]
Ring = tuple[Point, ...]
Bounds = tuple[float, float, float, float]


class PrefixResolutionStatus(StrEnum):
    """Severity of a prefix resolution result."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


class PrefixResolutionArea(StrEnum):
    """Spatial class used to resolve a prefix."""

    VALLEY = "valley"
    POLAND = "poland"
    SLOVAKIA = "slovakia"
    OUTSIDE_PL_SK = "outside_pl_sk"


@dataclass(frozen=True, slots=True)
class PrefixResolution:
    """Result of resolving a point to an ID prefix."""

    status: PrefixResolutionStatus
    area: PrefixResolutionArea
    prefix: str | None
    code: str | None
    message: str | None
    x_1992: float
    y_1992: float
    valley_name: str | None = None


@dataclass(frozen=True, slots=True)
class _PolygonFeature:
    rings: tuple[Ring, ...]
    bounds: Bounds
    name: str | None = None
    prefix: str | None = None

    def contains(self, *, easting: float, northing: float) -> bool:
        return _bounds_contain(self.bounds, easting=easting, northing=northing) and _rings_contain(
            self.rings,
            easting=easting,
            northing=northing,
        )


class PrefixResolver:
    """Resolve WGS84 points against valley and PL/SK fallback shapefiles."""

    def __init__(
        self,
        *,
        config_path: Path = DEFAULT_PREFIX_CONFIG_PATH,
        shapes_dir: Path = DEFAULT_SHAPES_DIR,
    ) -> None:
        self.config_path = config_path
        self.shapes_dir = shapes_dir
        config = _load_prefix_config(config_path)
        self._valley_features = _load_valley_features(
            shapes_dir / VALLEY_SHAPE_NAME,
            config.valley_prefixes,
        )
        self._poland_features = _load_country_features(shapes_dir / POLAND_SHAPE_NAME)
        self._slovakia_features = _load_country_features(shapes_dir / SLOVAKIA_SHAPE_NAME)
        self._poland_prefix = config.fallback_prefixes[POLAND_FALLBACK_KEY]
        self._slovakia_prefix = config.fallback_prefixes[SLOVAKIA_FALLBACK_KEY]

    def resolve(self, *, lat: float, lon: float) -> PrefixResolution:
        """Resolve a WGS84 coordinate to a valley prefix or PL/SK fallback."""

        pl_1992 = wgs84_to_1992(lat=lat, lon=lon)
        # Shapefile geometry uses GIS X/Y: easting/northing. Project YAML stores Y/X.
        easting = pl_1992.y_1992
        northing = pl_1992.x_1992

        for feature in self._valley_features:
            if feature.contains(easting=easting, northing=northing):
                return PrefixResolution(
                    status=PrefixResolutionStatus.OK,
                    area=PrefixResolutionArea.VALLEY,
                    prefix=feature.prefix,
                    code=None,
                    message=None,
                    x_1992=pl_1992.x_1992,
                    y_1992=pl_1992.y_1992,
                    valley_name=feature.name,
                )

        if _any_feature_contains(self._poland_features, easting=easting, northing=northing):
            return PrefixResolution(
                status=PrefixResolutionStatus.WARNING,
                area=PrefixResolutionArea.POLAND,
                prefix=self._poland_prefix,
                code=OUTSIDE_VALLEYS_CODE,
                message=OUTSIDE_VALLEYS_MESSAGE,
                x_1992=pl_1992.x_1992,
                y_1992=pl_1992.y_1992,
            )

        if _any_feature_contains(self._slovakia_features, easting=easting, northing=northing):
            return PrefixResolution(
                status=PrefixResolutionStatus.WARNING,
                area=PrefixResolutionArea.SLOVAKIA,
                prefix=self._slovakia_prefix,
                code=OUTSIDE_VALLEYS_CODE,
                message=OUTSIDE_VALLEYS_MESSAGE,
                x_1992=pl_1992.x_1992,
                y_1992=pl_1992.y_1992,
            )

        return PrefixResolution(
            status=PrefixResolutionStatus.ERROR,
            area=PrefixResolutionArea.OUTSIDE_PL_SK,
            prefix=None,
            code=OUTSIDE_COUNTRIES_CODE,
            message=OUTSIDE_COUNTRIES_MESSAGE,
            x_1992=pl_1992.x_1992,
            y_1992=pl_1992.y_1992,
        )


@dataclass(frozen=True, slots=True)
class _PrefixConfig:
    valley_prefixes: dict[str, str]
    fallback_prefixes: dict[str, str]


@lru_cache(maxsize=1)
def default_prefix_resolver() -> PrefixResolver:
    """Return the repository default prefix resolver."""

    return PrefixResolver()


def resolve_prefix(*, lat: float, lon: float) -> PrefixResolution:
    """Resolve a WGS84 coordinate with the repository default resolver."""

    return default_prefix_resolver().resolve(lat=lat, lon=lon)


def _load_prefix_config(config_path: Path) -> _PrefixConfig:
    with config_path.open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    if not isinstance(config, dict):
        raise ValueError(f"Prefix config must be a mapping: {config_path}")

    valley_prefixes = _string_mapping(config.get("valley_prefixes"), "valley_prefixes")
    fallback_prefixes = _string_mapping(config.get("fallback_prefixes"), "fallback_prefixes")
    missing_fallbacks = {POLAND_FALLBACK_KEY, SLOVAKIA_FALLBACK_KEY} - set(fallback_prefixes)
    if missing_fallbacks:
        missing = ", ".join(sorted(missing_fallbacks))
        raise ValueError(f"Missing fallback prefix keys in {config_path}: {missing}")

    return _PrefixConfig(valley_prefixes=valley_prefixes, fallback_prefixes=fallback_prefixes)


def _string_mapping(value: object, label: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    if not all(isinstance(key, str) and isinstance(item, str) for key, item in value.items()):
        raise ValueError(f"{label} must map strings to strings")
    return dict(value)


def _load_valley_features(
    shape_path: Path, valley_prefixes: dict[str, str]
) -> tuple[_PolygonFeature, ...]:
    features: list[_PolygonFeature] = []
    with shapefile.Reader(str(shape_path), encoding="utf-8") as reader:
        for shape_record in reader.iterShapeRecords():
            name = str(shape_record.record["NAME"])
            try:
                prefix = valley_prefixes[name]
            except KeyError as exc:
                raise ValueError(f"Missing prefix for valley polygon {name!r}") from exc
            features.append(
                _PolygonFeature(
                    rings=_shape_rings(shape_record.shape),
                    bounds=_shape_bounds(shape_record.shape),
                    name=name,
                    prefix=prefix,
                )
            )
    return tuple(features)


def _load_country_features(shape_path: Path) -> tuple[_PolygonFeature, ...]:
    with shapefile.Reader(str(shape_path), encoding="utf-8") as reader:
        return tuple(
            _PolygonFeature(
                rings=_shape_rings(shape),
                bounds=_shape_bounds(shape),
            )
            for shape in reader.shapes()
        )


def _shape_rings(shape: Any) -> tuple[Ring, ...]:
    points = tuple((float(point[0]), float(point[1])) for point in shape.points)
    parts = [int(part) for part in shape.parts]
    ring_starts = [*parts, len(points)]
    rings: list[Ring] = []

    for start, end in zip(ring_starts, ring_starts[1:], strict=False):
        ring = points[start:end]
        if len(ring) >= 3:
            rings.append(ring)

    return tuple(rings)


def _shape_bounds(shape: Any) -> Bounds:
    xmin, ymin, xmax, ymax = shape.bbox
    return (float(xmin), float(ymin), float(xmax), float(ymax))


def _any_feature_contains(
    features: tuple[_PolygonFeature, ...],
    *,
    easting: float,
    northing: float,
) -> bool:
    return any(feature.contains(easting=easting, northing=northing) for feature in features)


def _bounds_contain(bounds: Bounds, *, easting: float, northing: float) -> bool:
    xmin, ymin, xmax, ymax = bounds
    return xmin <= easting <= xmax and ymin <= northing <= ymax


def _rings_contain(rings: tuple[Ring, ...], *, easting: float, northing: float) -> bool:
    # Shapefile polygons may contain multiple rings; even-odd semantics handle holes.
    return sum(_ring_contains(ring, easting=easting, northing=northing) for ring in rings) % 2 == 1


def _ring_contains(ring: Ring, *, easting: float, northing: float) -> bool:
    inside = False
    previous = ring[-1]

    for current in ring:
        if _point_is_on_segment(
            point=(easting, northing),
            segment_start=previous,
            segment_end=current,
        ):
            return True

        x1, y1 = previous
        x2, y2 = current
        crosses_horizontal_ray = (y1 > northing) != (y2 > northing)
        if crosses_horizontal_ray:
            intersection_x = ((x2 - x1) * (northing - y1) / (y2 - y1)) + x1
            if intersection_x > easting:
                inside = not inside

        previous = current

    return inside


def _point_is_on_segment(
    *,
    point: Point,
    segment_start: Point,
    segment_end: Point,
    tolerance: float = 1e-9,
) -> bool:
    px, py = point
    x1, y1 = segment_start
    x2, y2 = segment_end

    cross_product = (py - y1) * (x2 - x1) - (px - x1) * (y2 - y1)
    if abs(cross_product) > tolerance:
        return False

    return (
        min(x1, x2) - tolerance <= px <= max(x1, x2) + tolerance
        and min(y1, y2) - tolerance <= py <= max(y1, y2) + tolerance
    )
