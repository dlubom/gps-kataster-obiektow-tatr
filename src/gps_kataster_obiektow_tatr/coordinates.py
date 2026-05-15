"""Coordinate conversion helpers for WGS84 and PL-1992."""

from dataclasses import dataclass
from math import hypot

from pyproj import Transformer

WGS84_CRS = "EPSG:4326"
PL_1992_CRS = "EPSG:2180"
DEFAULT_CONSISTENCY_TOLERANCE_M = 0.5

_WGS84_TO_PL_1992 = Transformer.from_crs(WGS84_CRS, PL_1992_CRS, always_xy=True)
_PL_1992_TO_WGS84 = Transformer.from_crs(PL_1992_CRS, WGS84_CRS, always_xy=True)


@dataclass(frozen=True, slots=True)
class WGS84Coordinate:
    """Geographic coordinate in decimal degrees."""

    lat: float
    lon: float


@dataclass(frozen=True, slots=True)
class PL1992Coordinate:
    """PL-1992 coordinate using the project's YAML axis convention."""

    x_1992: float
    y_1992: float


def wgs84_to_1992(lat: float, lon: float) -> PL1992Coordinate:
    """Convert WGS84 latitude/longitude to project PL-1992 fields."""

    # PyProj returns GIS easting/northing; YAML stores Polish X/Y as northing/easting.
    easting, northing = _WGS84_TO_PL_1992.transform(lon, lat)
    return PL1992Coordinate(x_1992=northing, y_1992=easting)


def pl1992_to_wgs84(x_1992: float, y_1992: float) -> WGS84Coordinate:
    """Convert project PL-1992 fields to WGS84 latitude/longitude."""

    # Inverse transform expects GIS easting/northing, so project Y/X become inputs.
    lon, lat = _PL_1992_TO_WGS84.transform(y_1992, x_1992)
    return WGS84Coordinate(lat=lat, lon=lon)


def coordinate_consistency_error_m(
    *,
    lat: float,
    lon: float,
    x_1992: float,
    y_1992: float,
) -> float:
    """Return planar PL-1992 error between WGS84 and cached PL-1992 fields."""

    expected = wgs84_to_1992(lat=lat, lon=lon)
    return hypot(expected.x_1992 - x_1992, expected.y_1992 - y_1992)


def coordinates_are_consistent(
    *,
    lat: float,
    lon: float,
    x_1992: float,
    y_1992: float,
    tolerance_m: float = DEFAULT_CONSISTENCY_TOLERANCE_M,
) -> bool:
    """Check whether WGS84 and project PL-1992 fields agree within a tolerance."""

    return (
        coordinate_consistency_error_m(
            lat=lat,
            lon=lon,
            x_1992=x_1992,
            y_1992=y_1992,
        )
        <= tolerance_m
    )
