"""Shared staging report cells and second-resolution UTC generation time."""

from datetime import UTC, datetime

from gps_kataster_obiektow_tatr.source_parsing import clean_text


def markdown_text(value: object) -> str:
    """Strip a cell, use a dash if blank, escape pipes and render LF as a break."""
    text = clean_text(value)
    if not text:
        return "-"
    return text.replace("|", "\\|").replace("\n", "<br>")


def markdown_code_or_dash(value: object) -> str:
    """Wrap a truthy cell in backticks, preserving the existing escaping policy."""
    if not value:
        return "-"
    return f"`{markdown_text(value)}`"


def utc_timestamp() -> str:
    """Return the current UTC timestamp with whole seconds and a Z suffix."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
