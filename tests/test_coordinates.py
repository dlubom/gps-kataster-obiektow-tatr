import pytest

from gps_kataster_obiektow_tatr.coordinates import (
    DEFAULT_CONSISTENCY_TOLERANCE_M,
    coordinate_consistency_error_m,
    coordinates_are_consistent,
    pl1992_to_wgs84,
    wgs84_to_1992,
)


@pytest.mark.parametrize(
    ("lat", "lon"),
    [
        (49.27391671, 20.07713884),
        (49.23459299, 19.87589498),
        (49.21138887, 20.09027783),
    ],
)
def test_wgs84_pl1992_round_trip_for_tatra_points(lat: float, lon: float) -> None:
    pl_1992 = wgs84_to_1992(lat=lat, lon=lon)
    wgs84 = pl1992_to_wgs84(x_1992=pl_1992.x_1992, y_1992=pl_1992.y_1992)

    assert wgs84.lat == pytest.approx(lat, abs=1e-9)
    assert wgs84.lon == pytest.approx(lon, abs=1e-9)


def test_wgs84_to_1992_uses_polish_axis_convention() -> None:
    pl_1992 = wgs84_to_1992(lat=49.27391671, lon=20.07713884)

    assert pl_1992.x_1992 == pytest.approx(156826.50, abs=0.01)
    assert pl_1992.y_1992 == pytest.approx(578327.52, abs=0.01)


def test_coordinate_consistency_detects_swapped_pl1992_axes() -> None:
    pl_1992 = wgs84_to_1992(lat=49.27391671, lon=20.07713884)

    assert coordinates_are_consistent(
        lat=49.27391671,
        lon=20.07713884,
        x_1992=pl_1992.x_1992,
        y_1992=pl_1992.y_1992,
    )
    assert not coordinates_are_consistent(
        lat=49.27391671,
        lon=20.07713884,
        x_1992=pl_1992.y_1992,
        y_1992=pl_1992.x_1992,
    )
    swapped_axis_error_m = coordinate_consistency_error_m(
        lat=49.27391671,
        lon=20.07713884,
        x_1992=pl_1992.y_1992,
        y_1992=pl_1992.x_1992,
    )

    assert swapped_axis_error_m > DEFAULT_CONSISTENCY_TOLERANCE_M
    assert swapped_axis_error_m > 100_000


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("field", ["lat", "lon", "x_1992", "y_1992"])
def test_coordinate_helpers_reject_non_finite_inputs(field, value):
    fields = dict(lat=49.23459299, lon=19.87589498, x_1992=152267.23, y_1992=563744.25)
    fields[field] = value
    with pytest.raises(ValueError, match=field):
        coordinate_consistency_error_m(**fields)
    with pytest.raises(ValueError, match=field):
        coordinates_are_consistent(**fields)
    if field in {"lat", "lon"}:
        with pytest.raises(ValueError, match=field):
            wgs84_to_1992(lat=fields["lat"], lon=fields["lon"])
    else:
        with pytest.raises(ValueError, match=field):
            pl1992_to_wgs84(x_1992=fields["x_1992"], y_1992=fields["y_1992"])


def test_coordinate_helpers_reject_non_finite_projection_result():
    with pytest.raises(ValueError, match="finite"):
        wgs84_to_1992(lat=100, lon=20)
