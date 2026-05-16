"""Default best-measurement selection for object YAML records."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime, time
from math import inf
from typing import Any


def select_default_best_measurement_id(measurements: Iterable[dict[str, Any]]) -> str | None:
    """Return the measurement id selected by the V1 default ``auto`` algorithm."""

    candidates = [
        measurement for measurement in measurements if isinstance(measurement.get("id"), str)
    ]
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


def selected_default_uses_rejected_fallback(measurements: Iterable[dict[str, Any]]) -> bool:
    """Return whether the default selection can only choose from rejected measurements."""

    candidates = [
        measurement for measurement in measurements if isinstance(measurement.get("id"), str)
    ]
    return bool(candidates) and all(
        measurement_priority(measurement) == 5 for measurement in candidates
    )


def measurement_priority(measurement: dict[str, Any]) -> int:
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


def _best_measurement_within_priority(measurements: Sequence[dict[str, Any]]) -> dict[str, Any]:
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


def _measurement_observed_sort_value(measurement: dict[str, Any]) -> datetime:
    observed_at = measurement.get("observed_at")
    if isinstance(observed_at, str):
        return _parse_observed_at(observed_at)
    observed_date = measurement.get("observed_date")
    if isinstance(observed_date, str):
        return _parse_observed_date(observed_date)
    return datetime.min.replace(tzinfo=UTC)


def _parse_observed_at(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_observed_date(value: str) -> datetime:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)
    return datetime.combine(parsed, time.min, tzinfo=UTC)


def _measurement_accuracy_sort_value(measurement: dict[str, Any]) -> float:
    accuracy = measurement.get("horizontal_accuracy_m")
    if isinstance(accuracy, int | float):
        return float(accuracy)
    return inf
