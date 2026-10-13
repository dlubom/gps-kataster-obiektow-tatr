"""Check numeric DBF representations before PyShp can truncate them."""

from __future__ import annotations


class DbfNumericOverflowError(ValueError):
    """Raised when a numeric value cannot fit its declared DBF field."""


def validate_dbf_number(
    value: float | int | None,
    *,
    object_id: str,
    field_name: str,
    width: int,
    decimal: int,
) -> None:
    """Require the complete F/N representation, including sign and rounded digits."""

    if value is None:
        return
    # Match PyShp's conversion before its destructive [:size] slice.
    text = format(int(value), "d") if decimal == 0 else format(float(value), f".{decimal}f")
    if len(text) > width:
        raise DbfNumericOverflowError(
            f"DBF numeric overflow: object {object_id}, field {field_name}, value {value!r}; "
            f"width={width}, decimal={decimal}, required={len(text)} characters."
        )
