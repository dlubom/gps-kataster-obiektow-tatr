"""Default best-measurement selection for object YAML records."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from datetime import date, datetime, timedelta
from math import inf
from typing import NotRequired, TypedDict

from gps_kataster_obiektow_tatr.measurement_values import non_finite_measurement_fields

_SECONDS_PER_DAY = 86_400
_MICROSECONDS_PER_SECOND = 1_000_000
_MIN_OBSERVED = (date.min.toordinal() * _SECONDS_PER_DAY, "")
_RFC3339_SUBMICROSECOND = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}"
    r"([0-9]+)(?:[Zz]|[+-][0-9]{2}:[0-9]{2})"
)


class BestMeasurementInput(TypedDict):
    """Fields read by Best, not a second catalog schema or a raw YAML validator.

    Optional fields preserve the selector's support for partial records. Full
    catalog validation belongs to models.py; runtime defensive checks stay here.
    """

    id: str
    source: NotRequired[str]
    verification_status: NotRequired[str]
    observed_at: NotRequired[str | None]
    observed_date: NotRequired[str | None]
    horizontal_accuracy_m: NotRequired[int | float | None]


def select_default_best_measurement_id(
    measurements: Iterable[BestMeasurementInput],
) -> str | None:
    """Return the measurement id selected by the V1 default ``auto`` algorithm."""

    candidates = []
    seen_ids: set[str] = set()
    for measurement in measurements:
        invalid_fields = non_finite_measurement_fields(measurement)
        if invalid_fields:
            raise ValueError(
                f"Measurement {measurement.get('id')} fields {', '.join(invalid_fields)} "
                "must be finite before best selection."
            )
        measurement_id = measurement.get("id")
        if isinstance(measurement_id, str):
            if measurement_id in seen_ids:
                raise ValueError(
                    f"Duplicate measurement.id {measurement_id} before best selection."
                )
            seen_ids.add(measurement_id)
            candidates.append(measurement)
    if not candidates:
        return None

    for priority in (0, 1, 2, 3, 4, 5):
        priority_measurements = [
            measurement
            for measurement in candidates
            if measurement_priority(measurement) == priority
        ]
        if priority_measurements:
            return _best_measurement_within_priority(priority_measurements)["id"]

    return None


def selected_default_uses_rejected_fallback(measurements: Iterable[BestMeasurementInput]) -> bool:
    """Return whether the default selection can only choose from rejected measurements."""

    candidates = [
        measurement for measurement in measurements if isinstance(measurement.get("id"), str)
    ]
    return bool(candidates) and all(
        measurement_priority(measurement) == 5 for measurement in candidates
    )


def measurement_priority(measurement: BestMeasurementInput) -> int:
    """Return source/status priority for the default best-measurement algorithm."""

    source = measurement.get("source")
    status = measurement.get("verification_status")
    is_rejected = status == "odrzucony"

    if source == "wlasne" and status == "zweryfikowany":
        return 0
    if source == "TPN" and not is_rejected:
        return 1
    if source == "wlasne" and not is_rejected:
        return 2
    if source == "PIG" and not is_rejected:
        return 3
    if not is_rejected:
        return 4
    return 5


def _best_measurement_within_priority(
    measurements: Sequence[BestMeasurementInput],
) -> BestMeasurementInput:
    latest_observed = max(
        _measurement_observed_sort_value(measurement) for measurement in measurements
    )
    latest_measurements = [
        measurement
        for measurement in measurements
        if _measurement_observed_sort_value(measurement) == latest_observed
    ]
    return min(
        latest_measurements,
        key=lambda measurement: (
            _measurement_accuracy_sort_value(measurement),
            measurement["id"],
        ),
    )


def _measurement_observed_sort_value(measurement: BestMeasurementInput) -> tuple[int, str]:
    observed_at = measurement.get("observed_at")
    if isinstance(observed_at, str):
        return _parse_observed_at(observed_at)
    observed_date = measurement.get("observed_date")
    if isinstance(observed_date, str):
        return _parse_observed_date(observed_date)
    return _MIN_OBSERVED


def _parse_observed_at(value: str) -> tuple[int, str]:
    try:
        parsed = datetime.fromisoformat(value[:-1] + "Z" if value.endswith("z") else value)
    except ValueError:
        return _MIN_OBSERVED

    # Compute UTC as an ordinal-based number so offsets at the calendar bounds
    # do not need to construct a datetime in year 0 or 10000.
    local_seconds = (
        parsed.toordinal() * _SECONDS_PER_DAY
        + parsed.hour * 3600
        + parsed.minute * 60
        + parsed.second
    )
    offset = parsed.utcoffset() or timedelta()
    offset_seconds = offset.days * _SECONDS_PER_DAY + offset.seconds
    carry, microseconds = divmod(parsed.microsecond - offset.microseconds, _MICROSECONDS_PER_SECOND)

    # Python's parser truncates fractional seconds to six digits. Recover the
    # remaining digits for RFC 3339 timestamps, whose offsets have minute precision.
    match = _RFC3339_SUBMICROSECOND.fullmatch(value)
    tail = match[1] if match else ""
    # Trailing zeroes are immaterial; canonical digit strings sort like fractions.
    return (local_seconds - offset_seconds + carry, f"{microseconds:06d}{tail}".rstrip("0"))


def _parse_observed_date(value: str) -> tuple[int, str]:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return _MIN_OBSERVED
    return (parsed.toordinal() * _SECONDS_PER_DAY, "")


def _measurement_accuracy_sort_value(measurement: BestMeasurementInput) -> float:
    accuracy = measurement.get("horizontal_accuracy_m")
    if isinstance(accuracy, int | float):
        return float(accuracy)
    return inf
