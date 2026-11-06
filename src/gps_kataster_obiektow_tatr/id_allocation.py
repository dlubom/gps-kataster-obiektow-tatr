"""Batch-local sequential IDs, with a separate adapter for occupied file names."""

from __future__ import annotations

import re
from collections.abc import Iterable
from itertools import chain
from pathlib import Path


class IdSequence:
    """Reserve IDs in one namespace and allocate after its highest number."""

    def __init__(
        self,
        prefix: str,
        *,
        width: int = 4,
        existing_ids: Iterable[str] = (),
        reserved_ids: Iterable[str] = (),
    ) -> None:
        self.prefix = prefix
        self.width = width
        self._number = 0
        self.reserve(chain(existing_ids, reserved_ids))

    def reserve(self, identifiers: Iterable[str]) -> None:
        """Include occupied IDs; duplicates and IDs outside this namespace are ignored."""

        pattern = re.compile(rf"{re.escape(self.prefix)}-(\d+)")
        for identifier in identifiers:
            if match := pattern.fullmatch(identifier):
                self._number = max(self._number, int(match.group(1)))

    def next_number(self) -> int:
        """Reserve and return the next number without filling gaps."""

        self._number += 1
        return self._number

    def next_id(self) -> str:
        """Reserve and format the next ID; width grows without renumbering."""

        return format_id(self.prefix, self.next_number(), width=self.width)


def format_id(prefix: str, number: int, *, width: int = 4) -> str:
    """Format a number with the namespace's minimum digit width."""

    return f"{prefix}-{number:0{width}d}"


def file_ids(directory: Path) -> tuple[str, ...]:
    """Read occupied YAML/legacy SQL file stems, without loading a catalogue or database."""

    if not directory.exists():
        return ()
    return tuple(
        path.stem
        for path in directory.iterdir()
        if path.suffix in {".yml", ".yaml", ".sql"} and path.is_file()
    )
