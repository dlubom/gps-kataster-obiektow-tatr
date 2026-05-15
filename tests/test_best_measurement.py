import pytest

from gps_kataster_obiektow_tatr.best_measurement import (
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
