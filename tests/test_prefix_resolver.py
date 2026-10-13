from collections.abc import Iterator
from pathlib import Path

import pytest
import shapefile
import yaml
from pyproj import Transformer

from gps_kataster_obiektow_tatr.prefix_resolver import (
    OUTSIDE_COUNTRIES_CODE,
    OUTSIDE_VALLEYS_CODE,
    PrefixResolution,
    PrefixResolutionArea,
    PrefixResolutionStatus,
    PrefixResolver,
    _bounds_contain,
    _point_is_on_segment,
    _PolygonFeature,
    _ring_contains,
    _rings_contain,
    default_prefix_resolver,
    resolve_prefix,
)


@pytest.fixture
def resolver() -> PrefixResolver:
    return PrefixResolver()


def test_resolves_point_inside_valley(resolver: PrefixResolver) -> None:
    result = resolver.resolve(lat=49.23459299, lon=19.87589498)

    assert result.status == PrefixResolutionStatus.OK
    assert result.area == PrefixResolutionArea.VALLEY
    assert result.prefix == "KSW"
    assert result.valley_name == "Dolina Kościeliska - Wschód"
    assert result.code is None


def test_resolves_poland_fallback_with_warning(resolver: PrefixResolver) -> None:
    result = resolver.resolve(lat=52.2297, lon=21.0122)

    assert result.status == PrefixResolutionStatus.WARNING
    assert result.area == PrefixResolutionArea.POLAND
    assert result.prefix == "PL"
    assert result.code == OUTSIDE_VALLEYS_CODE


def test_resolves_slovakia_fallback_with_warning(resolver: PrefixResolver) -> None:
    result = resolver.resolve(lat=49.141, lon=20.222)

    assert result.status == PrefixResolutionStatus.WARNING
    assert result.area == PrefixResolutionArea.SLOVAKIA
    assert result.prefix == "SK"
    assert result.code == OUTSIDE_VALLEYS_CODE


def test_returns_error_outside_poland_and_slovakia(resolver: PrefixResolver) -> None:
    result = resolver.resolve(lat=50.0755, lon=14.4378)

    assert result.status == PrefixResolutionStatus.ERROR
    assert result.area == PrefixResolutionArea.OUTSIDE_PL_SK
    assert result.prefix is None
    assert result.code == OUTSIDE_COUNTRIES_CODE


@pytest.fixture(autouse=True)
def isolated_default_resolver_cache() -> Iterator[None]:
    # Mutmut activates a mutant after collection: instantiate only during the test.
    default_prefix_resolver.cache_clear()
    try:
        yield
    finally:
        default_prefix_resolver.cache_clear()


def assert_resolution(
    result: PrefixResolution,
    *,
    area: str,
    prefix: str | None,
    x: float,
    y: float,
    valley: str | None = None,
) -> None:
    assert result.area == area
    assert result.prefix == prefix
    assert result.valley_name == valley
    assert result.x_1992 == pytest.approx(x, abs=1e-6)
    assert result.y_1992 == pytest.approx(y, abs=1e-6)
    if area == "valley":
        assert result.status == "ok"
        assert result.code is None
        assert result.message is None
    elif area in {"poland", "slovakia"}:
        assert result.status == "warning"
        assert result.code == "POINT_OUTSIDE_VALLEYS"
        assert result.message == (
            "Point is inside Poland or Slovakia but outside configured Tatra valley polygons; "
            "manual review is required before assigning a durable ID."
        )
    else:
        assert result.status == "error"
        assert result.code == "POINT_OUTSIDE_PL_SK"
        assert result.message == "Point is outside Poland and Slovakia fallback boundaries."


@pytest.mark.parametrize("entrypoint", ["instance", "wrapper"])
@pytest.mark.parametrize(
    ("lat", "lon", "area", "prefix", "x", "y", "valley"),
    [
        (
            49.23459299,
            19.87589498,
            "valley",
            "KSW",
            152267.22965516336,
            563744.2498546313,
            "Dolina Kościeliska - Wschód",
        ),
        (52.2297, 21.0122, "poland", "PL", 486757.20948080625, 637382.2044361834, None),
        (49.141, 20.222, "slovakia", "SK", 142215.35763398, 589099.8786000443, None),
        (50.0755, 14.4378, "outside_pl_sk", None, 255332.30945355352, 173711.4943975043, None),
    ],
)
def test_fresh_resolver_preserves_area_prefix_coordinates_and_diagnostics(
    entrypoint: str,
    lat: float,
    lon: float,
    area: str,
    prefix: str | None,
    x: float,
    y: float,
    valley: str | None,
) -> None:
    resolve = PrefixResolver().resolve if entrypoint == "instance" else resolve_prefix
    assert_resolution(resolve(lat=lat, lon=lon), area=area, prefix=prefix, x=x, y=y, valley=valley)


def test_default_resolver_reuses_instance_within_explicit_cache_lifetime() -> None:
    first = default_prefix_resolver()
    assert default_prefix_resolver() is first
    default_prefix_resolver.cache_clear()
    second = default_prefix_resolver()
    assert second is not first
    assert_resolution(
        second.resolve(lat=49.141, lon=20.222),
        area="slovakia",
        prefix="SK",
        x=142215.35763398,
        y=589099.8786000443,
    )


@pytest.fixture
def small_prefix_sources(tmp_path: Path) -> tuple[Path, Path]:
    shapes = tmp_path / "shapes"
    shapes.mkdir()
    # All fixture coordinates are GIS easting/northing, distinct from YAML X/Y.
    origin_e, origin_n = 578_000, 156_000
    triangle = [(0, 0), (800, 0), (0, 600), (0, 0)]
    shell = [(1000, 0), (1800, 0), (1800, 800), (1000, 800), (1000, 0)]
    hole = [(1200, 200), (1600, 200), (1600, 600), (1200, 600), (1200, 200)]
    island = [(1300, 300), (1500, 300), (1500, 500), (1300, 500), (1300, 300)]
    sources = {
        "doliny": [("Ukośna", [triangle]), ("Z otworem", [shell, hole, island])],
        "granica_polski": [
            ("PL", [[(-500, -500), (2200, -500), (2200, 1500), (-500, 1500), (-500, -500)]])
        ],
        "granica_slowacji": [
            ("SK", [[(-500, -2000), (2200, -2000), (2200, -1000), (-500, -1000), (-500, -2000)]])
        ],
    }
    for name, features in sources.items():
        with shapefile.Writer(
            str(shapes / name), shapeType=shapefile.POLYGON, encoding="utf-8"
        ) as writer:
            writer.field("NAME", "C", size=40)
            for label, rings in features:
                writer.poly([[(origin_e + e, origin_n + n) for e, n in ring] for ring in rings])
                writer.record(label)
    config = tmp_path / "prefixes.yml"
    config.write_text(
        yaml.safe_dump(
            {
                "valley_prefixes": {"Ukośna": "TRI", "Z otworem": "DON"},
                "fallback_prefixes": {"polska": "PX", "slowacja": "SX"},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return config, shapes


@pytest.mark.parametrize(
    ("e", "n", "area", "prefix", "valley"),
    [
        (100, 100, "valley", "TRI", "Ukośna"),
        (700, 500, "poland", "PX", None),  # Inside bbox, outside diagonal triangle.
        (1100, 400, "valley", "DON", "Z otworem"),
        (1250, 400, "poland", "PX", None),  # Hole excludes the valley.
        (1400, 400, "valley", "DON", "Z otworem"),  # Third nested ring restores it.
        (1900, 1000, "poland", "PX", None),
        (100, -1500, "slovakia", "SX", None),
        (3000, 2000, "outside_pl_sk", None, None),
    ],
)
def test_fresh_resolver_loads_custom_shapes_and_prefix_config(
    small_prefix_sources: tuple[Path, Path],
    e: float,
    n: float,
    area: str,
    prefix: str | None,
    valley: str | None,
) -> None:
    config, shapes = small_prefix_sources
    # Independent inverse projection supplies WGS84; expected output remains literal X/Y.
    lon, lat = Transformer.from_crs("EPSG:2180", "EPSG:4326", always_xy=True).transform(
        578_000 + e, 156_000 + n
    )
    result = PrefixResolver(config_path=config, shapes_dir=shapes).resolve(lat=lat, lon=lon)
    assert_resolution(result, area=area, prefix=prefix, x=156_000 + n, y=578_000 + e, valley=valley)


@pytest.mark.parametrize(
    ("config", "error"),
    [
        (None, "Prefix config must be a mapping"),
        ([], "Prefix config must be a mapping"),
        ("text", "Prefix config must be a mapping"),
        ({"valley_prefixes": [], "fallback_prefixes": {}}, "valley_prefixes must be a mapping"),
        (
            {"valley_prefixes": {1: "TRI"}, "fallback_prefixes": {}},
            "valley_prefixes must map strings to strings",
        ),
        (
            {"valley_prefixes": {"Ukośna": 1}, "fallback_prefixes": {}},
            "valley_prefixes must map strings to strings",
        ),
        ({"valley_prefixes": {}, "fallback_prefixes": []}, "fallback_prefixes must be a mapping"),
        (
            {"valley_prefixes": {}, "fallback_prefixes": {1: "PL"}},
            "fallback_prefixes must map strings to strings",
        ),
        (
            {"valley_prefixes": {}, "fallback_prefixes": {"polska": 1}},
            "fallback_prefixes must map strings to strings",
        ),
        (
            {"valley_prefixes": {}, "fallback_prefixes": {"polska": "PL"}},
            "Missing fallback prefix keys.*slowacja",
        ),
        (
            {"valley_prefixes": {}, "fallback_prefixes": {"slowacja": "SK"}},
            "Missing fallback prefix keys.*polska",
        ),
        (
            {"valley_prefixes": {}, "fallback_prefixes": {}},
            "Missing fallback prefix keys.*polska, slowacja",
        ),
        (
            {"valley_prefixes": {}, "fallback_prefixes": {"polska": "PL", "slowacja": "SK"}},
            "Missing prefix for valley polygon 'Ukośna'",
        ),
    ],
)
def test_fresh_resolver_rejects_invalid_config_before_resolving(
    small_prefix_sources: tuple[Path, Path],
    config: object,
    error: str,
) -> None:
    path, shapes = small_prefix_sources
    path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        PrefixResolver(config_path=path, shapes_dir=shapes)


@pytest.mark.parametrize(
    ("e", "n", "inside"),
    [
        (2, 3, True),
        (8, 3, True),
        (2, 11, True),
        (8, 11, True),
        (5, 7, True),
        (1.999, 7, False),
        (8.001, 7, False),
        (5, 2.999, False),
        (5, 11.001, False),
        (1, 2, False),
        (9, 12, False),
    ],
)
def test_bounds_require_both_axes_and_include_all_edges(e: float, n: float, inside: bool) -> None:
    assert _bounds_contain((2, 3, 8, 11), easting=e, northing=n) is inside


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    ("start", "end", "point", "inside"),
    [
        ((0, 0), (4, 3), (2, 1.5), True),
        ((0, 0), (4, 3), (0, 0), True),
        ((0, 0), (4, 3), (4, 3), True),
        ((0, 0), (4, 3), (2, 1), False),
        ((0, 0), (4, 3), (-4, -3), False),
        ((0, 0), (4, 3), (8, 6), False),
        ((2, 3), (6, 3), (4, 3), True),
        ((2, 3), (6, 3), (0, 3), False),
        ((2, 3), (6, 3), (8, 3), False),
        ((2, 3), (2, 7), (2, 5), True),
        ((2, 3), (2, 7), (2, 1), False),
        ((2, 3), (2, 7), (2, 9), False),
        ((2, 7), (6, 3), (4, 5), True),
        ((2, 7), (6, 3), (4, 4), False),
    ],
)
def test_segment_checks_diagonal_collinearity_and_both_ranges(
    start: tuple[float, float],
    end: tuple[float, float],
    point: tuple[float, float],
    inside: bool,
    reverse: bool,
) -> None:
    if reverse:
        start, end = end, start
    assert _point_is_on_segment(point=point, segment_start=start, segment_end=end) is inside


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    ("start", "end", "point", "inside"),
    [
        ((0, 0), (4, 0), (2, 0.03125), True),  # Cross product exactly tolerance.
        ((0, 0), (4, 0), (2, -0.03125), True),
        ((0, 0), (4, 0), (2, 0.0625), False),
        ((0, 0), (4, 0), (-0.125, 0), True),
        ((0, 0), (4, 0), (4.125, 0), True),
        ((0, 0), (4, 0), (-0.25, 0), False),
        ((0, 0), (4, 0), (4.25, 0), False),
        ((0, 0), (0, 4), (0, -0.125), True),
        ((0, 0), (0, 4), (0, 4.125), True),
        ((0, 0), (0, 4), (0, -0.25), False),
        ((0, 0), (0, 4), (0, 4.25), False),
    ],
)
def test_segment_tolerance_applies_to_cross_product_and_each_endpoint(
    start: tuple[float, float],
    end: tuple[float, float],
    point: tuple[float, float],
    inside: bool,
    reverse: bool,
) -> None:
    if reverse:
        start, end = end, start
    assert (
        _point_is_on_segment(point=point, segment_start=start, segment_end=end, tolerance=0.125)
        is inside
    )


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    ("point", "inside"),
    [
        ((1, 1), True),
        ((4, 3), True),
        ((0, 0), True),
        ((8, 0), True),
        ((0, 6), True),
        ((4, 0), True),
        ((0, 3), True),
        ((7, 5), False),
        ((-1, 3), False),
        ((9, 0), False),
        ((4, -1), False),
        ((0, 7), False),
    ],
)
def test_ring_ray_crossings_and_vertices_include_diagonal_boundary(
    point: tuple[float, float],
    inside: bool,
    reverse: bool,
) -> None:
    ring = ((0, 0), (8, 0), (0, 6), (0, 0))
    if reverse:
        ring = tuple(reversed(ring))
    assert _ring_contains(ring, easting=point[0], northing=point[1]) is inside


@pytest.mark.parametrize(
    ("point", "inside"),
    [
        ((0, 5), True),
        ((1, 5), True),
        ((3, 5), False),
        ((3.5, 5), False),
        ((4, 5), True),
        ((5, 5), True),
        ((8, 5), True),
        ((11, 5), False),
    ],
)
def test_rings_even_odd_rule_excludes_hole_and_restores_nested_island(
    point: tuple[float, float],
    inside: bool,
) -> None:
    rings = (
        ((0, 0), (10, 0), (10, 10), (0, 10), (0, 0)),
        ((3, 3), (7, 3), (7, 7), (3, 7), (3, 3)),
        ((4, 4), (6, 4), (6, 6), (4, 6), (4, 4)),
    )
    assert _rings_contain(rings, easting=point[0], northing=point[1]) is inside


def test_polygon_requires_bbox_even_with_segment_tolerance_near_edge() -> None:
    feature = _PolygonFeature(
        rings=(((0, 0), (1, 0), (1, 1), (0, 1), (0, 0)),), bounds=(0, 0, 1, 1)
    )
    assert feature.contains(easting=1, northing=0.5)
    assert not feature.contains(easting=1 + 1e-10, northing=0.5)
    assert not feature.contains(easting=0.5, northing=1 + 1e-10)


def test_ring_ray_intersection_keeps_strict_comparison_at_float_precision_boundary() -> None:
    # The rounded ray intersection equals easting, but the cross product exceeds
    # segment tolerance. Keep the existing strict ray rule at PL-1992 magnitudes.
    ring = (
        (500476.15826222935, 150630.21905431888),
        (500899.32703788416, 151282.23346192468),
        (499476.15826222935, 151282.23346192468),
        (500476.15826222935, 150630.21905431888),
    )
    assert not _ring_contains(ring, easting=500483.28934180277, northing=150641.20655361266)
