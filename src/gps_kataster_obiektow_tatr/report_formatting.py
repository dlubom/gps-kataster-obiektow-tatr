"""Second-resolution UTC generation time for builders and CLI."""

from datetime import UTC, datetime


def utc_timestamp() -> str:
    """Return the current UTC timestamp with whole seconds and a Z suffix."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
