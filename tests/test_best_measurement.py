from datetime import UTC, date, datetime, time
from math import inf

import pytest

from gps_kataster_obiektow_tatr.best_measurement import (
    _measurement_accuracy_sort_value,
    _measurement_observed_sort_value,
    _parse_observed_at,
    _parse_observed_date,
    select_default_best_measurement_id,
    selected_default_uses_rejected_fallback,
)


@pytest.mark.parametrize(
    ("available_candidates", "expected_id"),
    [
        (
            [
                "own_verified",
                "tpn",
                "own_unverified",
                "pig",
                "other",
                "rejected",
            ],
            "m-001",
        ),
        (["tpn", "own_unverified", "pig", "other", "rejected"], "m-002"),
        (["own_unverified", "pig", "other", "rejected"], "m-003"),
        (["pig", "other", "rejected"], "m-004"),
        (["other", "rejected"], "m-005"),
        (["rejected"], "m-006"),
    ],
)
def test_selects_default_best_measurement_by_priority(
    available_candidates: list[str],
    expected_id: str,
) -> None:
    measurements = [_priority_candidate(candidate) for candidate in available_candidates]

    selected_id = select_default_best_measurement_id(measurements)

    assert selected_id == expected_id


def test_other_sources_share_priority_and_use_latest_date() -> None:
    measurements = [
        _measurement("m-001", source="geoportal", observed_date="2026-05-14"),
        _measurement("m-002", source="publikacja", observed_date="2026-05-16"),
        _measurement("m-003", source="inne", observed_date="2026-05-15"),
    ]

    selected_id = select_default_best_measurement_id(measurements)

    assert selected_id == "m-002"


def test_selects_latest_observation_within_same_priority() -> None:
    measurements = [
        _measurement("m-001", source="TPN", observed_date="2026-05-16"),
        _measurement(
            "m-002",
            source="TPN",
            observed_at="2026-05-16T11:30:00Z",
            observed_date="2026-05-16",
        ),
        _measurement("m-003", source="TPN", observed_date="2026-05-15"),
    ]

    selected_id = select_default_best_measurement_id(measurements)

    assert selected_id == "m-002"


def test_selects_lower_accuracy_when_dates_tie() -> None:
    measurements = [
        _measurement("m-001", source="TPN", accuracy=7.5),
        _measurement("m-002", source="TPN", accuracy=1.2),
    ]

    selected_id = select_default_best_measurement_id(measurements)

    assert selected_id == "m-002"


def test_selects_stable_measurement_id_when_date_and_accuracy_tie() -> None:
    measurements = [
        _measurement("m-003", source="TPN", accuracy=1.2),
        _measurement("m-001", source="TPN", accuracy=1.2),
        _measurement("m-002", source="TPN", accuracy=1.2),
    ]

    selected_id = select_default_best_measurement_id(measurements)

    assert selected_id == "m-001"


def test_detects_rejected_fallback_only_when_no_non_rejected_measurement_exists() -> None:
    rejected_measurements = [
        _measurement("m-001", source="TPN", status="odrzucony"),
        _measurement("m-002", source="PIG", status="odrzucony"),
    ]
    mixed_measurements = [
        *rejected_measurements,
        _measurement("m-003", source="PIG", status="nieweryfikowany"),
    ]

    assert selected_default_uses_rejected_fallback(rejected_measurements)
    assert not selected_default_uses_rejected_fallback(mixed_measurements)


def test_ignores_records_without_string_measurement_id() -> None:
    measurements = [
        {"id": 123, "source": "TPN", "verification_status": "nieweryfikowany"},
        {"source": "wlasne", "verification_status": "zweryfikowany"},
    ]

    assert select_default_best_measurement_id(measurements) is None
    assert not selected_default_uses_rejected_fallback(measurements)


def test_observed_at_is_normalized_to_utc_for_latest_selection() -> None:
    measurements = [
        _measurement("m-aware", source="TPN", observed_at="2026-05-16T13:30:00+02:00"),
        _measurement("m-naive", source="TPN", observed_at="2026-05-16T12:00:00"),
        _measurement("m-date", source="TPN", observed_date="2026-05-16"),
    ]

    selected_id = select_default_best_measurement_id(measurements)

    assert selected_id == "m-naive"


def test_invalid_observed_values_sort_before_valid_dates() -> None:
    measurements = [
        _measurement("m-invalid-at", source="TPN", observed_at="not-a-date"),
        _measurement("m-invalid-date", source="TPN", observed_date="not-a-date"),
        _measurement("m-valid", source="TPN", observed_date="2026-01-01"),
    ]

    selected_id = select_default_best_measurement_id(measurements)

    assert selected_id == "m-valid"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-05-16T12:00:00", datetime(2026, 5, 16, 12, 0, tzinfo=UTC)),
        ("2026-05-16T13:30:00+02:00", datetime(2026, 5, 16, 11, 30, tzinfo=UTC)),
        ("not-a-date", datetime.min.replace(tzinfo=UTC)),
    ],
)
def test_parse_observed_at(value: str, expected: datetime) -> None:
    assert _parse_observed_at(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-05-16", datetime.combine(date(2026, 5, 16), time.min, tzinfo=UTC)),
        ("not-a-date", datetime.min.replace(tzinfo=UTC)),
    ],
)
def test_parse_observed_date(value: str, expected: datetime) -> None:
    assert _parse_observed_date(value) == expected


def test_measurement_observed_sort_value_uses_observed_date_and_missing_fallback() -> None:
    assert _measurement_observed_sort_value({"observed_date": "2026-05-16"}) == datetime(
        2026,
        5,
        16,
        tzinfo=UTC,
    )
    assert _measurement_observed_sort_value({}) == datetime.min.replace(tzinfo=UTC)


@pytest.mark.parametrize(
    ("accuracy", "expected"),
    [(0, 0.0), (1.25, 1.25), (None, inf), ("1.25", inf)],
)
def test_measurement_accuracy_sort_value(accuracy: object, expected: float) -> None:
    assert _measurement_accuracy_sort_value({"horizontal_accuracy_m": accuracy}) == expected


def _priority_candidate(candidate: str) -> dict[str, object]:
    candidates = {
        "own_verified": _measurement(
            "m-001",
            source="wlasne",
            status="zweryfikowany",
            observed_date="2026-05-01",
        ),
        "tpn": _measurement("m-002", source="TPN", observed_date="2026-05-02"),
        "own_unverified": _measurement(
            "m-003",
            source="wlasne",
            status="nieweryfikowany",
            observed_date="2026-05-03",
        ),
        "pig": _measurement("m-004", source="PIG", observed_date="2026-05-04"),
        "other": _measurement("m-005", source="geoportal", observed_date="2026-05-05"),
        "rejected": _measurement(
            "m-006",
            source="TPN",
            status="odrzucony",
            observed_date="2026-05-06",
        ),
    }
    return candidates[candidate]


def _measurement(
    measurement_id: str,
    *,
    source: str,
    status: str = "nieweryfikowany",
    observed_date: str = "2026-05-15",
    observed_at: str | None = None,
    accuracy: float | None = 5.0,
) -> dict[str, object]:
    measurement: dict[str, object] = {
        "id": measurement_id,
        "source": source,
        "observed_date": observed_date,
        "horizontal_accuracy_m": accuracy,
        "verification_status": status,
    }
    if observed_at is not None:
        measurement["observed_at"] = observed_at
    return measurement
