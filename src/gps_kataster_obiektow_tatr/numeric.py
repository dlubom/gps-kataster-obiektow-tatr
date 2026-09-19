"""Finite numeric values at catalog, import and geometry boundaries."""

from math import isfinite
from typing import Any


def is_finite_number(value: object) -> bool:
    """Accept real domain scalars representable as finite floats, excluding bool."""
    if not isinstance(value, int | float) or isinstance(value, bool):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False


def require_finite_numbers(**values: float) -> None:
    for name, value in values.items():
        if not is_finite_number(value):
            raise ValueError(f"{name}: expected a finite number, got {value!r}.")


def nonfinite_paths(value: Any, path: str = "") -> tuple[str, ...]:
    """Find unsafe numeric values in nested records, retaining field paths."""
    if isinstance(value, dict):
        return tuple(
            found
            for key, child in value.items()
            for found in nonfinite_paths(child, f"{path}.{key}" if path else str(key))
        )
    if isinstance(value, list):
        return tuple(
            found
            for index, child in enumerate(value)
            for found in nonfinite_paths(child, f"{path}[{index}]")
        )
    if (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and not is_finite_number(value)
    ):
        return (path,)
    return ()


def parse_decimal(raw_value: Any) -> float | None:
    """Parse finite source numbers; only a blank field means missing."""
    text = "" if raw_value is None else str(raw_value).strip()
    if not text:
        return None
    text = text.replace("\u00a0", " ").replace(" ", "").replace(",", ".")
    value = float(text)
    require_finite_numbers(value=value)
    return value
