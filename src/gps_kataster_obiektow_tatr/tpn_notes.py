"""Preserve source location context at the TPN measurement that it qualifies."""

from __future__ import annotations

from collections.abc import Mapping

CONTEXT_FIELDS = ("WER_LOK", "UWAGI")


def append_tpn_context(notes: str | None, row: Mapping[str, str]) -> str | None:
    """Append labelled source values once, preserving all existing note text."""

    result = notes
    for field in CONTEXT_FIELDS:
        value = row.get(field, "").strip()
        if not value:
            continue
        entry = f"TPN {field}: {value}"
        if f"\n{entry}\n" not in f"\n{result or ''}\n":
            result = f"{result}\n{entry}" if result else entry
    return result
