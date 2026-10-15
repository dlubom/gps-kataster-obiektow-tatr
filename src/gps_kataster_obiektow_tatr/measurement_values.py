"""Numeric measurement fields shared by validation and best selection."""

from math import isfinite
from typing import Any

MEASUREMENT_NUMERIC_FIELDS = (
    "lat",
    "lon",
    "x_1992",
    "y_1992",
    "elevation_m",
    "horizontal_accuracy_m",
    "vertical_accuracy_m",
)


def non_finite_measurement_fields(measurement: dict[str, Any]) -> tuple[str, ...]:
    """Find numbers without a finite float representation; schema owns other types."""

    return tuple(
        field
        for field in MEASUREMENT_NUMERIC_FIELDS
        if _is_non_finite_number(measurement.get(field))
    )


def _is_non_finite_number(value: object) -> bool:
    if not isinstance(value, int | float):
        return False
    try:
        return not isfinite(value)
    except OverflowError:
        return True
