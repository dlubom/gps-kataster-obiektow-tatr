import pytest

from gps_kataster_obiektow_tatr.prefix_resolver import (
    OUTSIDE_COUNTRIES_CODE,
    OUTSIDE_VALLEYS_CODE,
    PrefixResolutionArea,
    PrefixResolutionStatus,
    PrefixResolver,
)


@pytest.fixture(scope="module")
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
