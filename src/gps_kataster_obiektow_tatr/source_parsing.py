"""Parse external source values without applying a consumer's validation policy."""

from datetime import UTC, datetime


def clean_text(raw_value: object) -> str:
    """Convert None to empty text and strip only leading/trailing whitespace."""
    if raw_value is None:
        return ""
    return str(raw_value).strip()


def parse_decimal(raw_value: object) -> float | None:
    """Parse comma/dot decimals with space/NBSP grouping; preserve NaN and Infinity."""
    text = clean_text(raw_value)
    if text == "":
        return None
    text = text.replace("\u00a0", " ").replace(" ", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def date_part_or_today(timestamp: str) -> str:
    """Keep the timestamp's declared day, falling back to today in UTC if invalid."""
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(UTC).date().isoformat()
    return parsed.date().isoformat()
