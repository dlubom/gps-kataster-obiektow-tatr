#!/usr/bin/env python3
"""Propose the next durable object ID for WGS84 coordinates."""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gps_kataster_obiektow_tatr.prefix_resolver import (  # noqa: E402
    PrefixResolution,
    PrefixResolutionStatus,
    default_prefix_resolver,
)

DEFAULT_OBJECTS_DIR = REPO_ROOT / "data" / "objects"


class PrefixResolverLike(Protocol):
    """Minimal resolver interface used by ID assignment."""

    def resolve(self, *, lat: float, lon: float) -> PrefixResolution:
        """Resolve WGS84 coordinates to a prefix resolution."""


@dataclass(frozen=True, slots=True)
class IdProposal:
    """Proposed durable object ID with the spatial resolution that produced it."""

    object_id: str
    prefix: str
    next_number: int
    resolution: PrefixResolution


class IdAssignmentError(ValueError):
    """Raised when coordinates cannot receive an automatic ID proposal."""

    def __init__(self, resolution: PrefixResolution) -> None:
        self.resolution = resolution
        message = resolution.message or "Coordinates cannot be assigned an ID."
        if resolution.code:
            message = f"{resolution.code}: {message}"
        super().__init__(message)


def next_object_id(prefix: str, *, objects_dir: Path = DEFAULT_OBJECTS_DIR) -> str:
    """Return the next ID under ``data/objects/{PREFIX}/``."""

    next_number = next_object_number(prefix, objects_dir=objects_dir)
    return format_object_id(prefix, next_number)


def next_object_number(prefix: str, *, objects_dir: Path = DEFAULT_OBJECTS_DIR) -> int:
    """Return one greater than the highest existing object number for a prefix."""

    prefix_dir = objects_dir / prefix
    if not prefix_dir.exists():
        return 1

    existing_numbers = tuple(iter_existing_object_numbers(prefix, prefix_dir=prefix_dir))
    if not existing_numbers:
        return 1

    return max(existing_numbers) + 1


def iter_existing_object_numbers(prefix: str, *, prefix_dir: Path) -> tuple[int, ...]:
    """Read existing ``{PREFIX}-{NNNN}.yml`` file names as object numbers."""

    object_file_re = re.compile(rf"^{re.escape(prefix)}-(\d+)\.yml$")
    numbers: list[int] = []

    for path in prefix_dir.iterdir():
        if not path.is_file():
            continue
        match = object_file_re.fullmatch(path.name)
        if match:
            numbers.append(int(match.group(1)))

    return tuple(sorted(numbers))


def format_object_id(prefix: str, number: int) -> str:
    """Format an object ID with at least four zero-padded digits."""

    return f"{prefix}-{number:04d}"


def propose_id(
    *,
    lat: float,
    lon: float,
    objects_dir: Path = DEFAULT_OBJECTS_DIR,
    resolver: PrefixResolverLike | None = None,
) -> IdProposal:
    """Resolve coordinates and propose the next durable object ID."""

    active_resolver = resolver or default_prefix_resolver()
    resolution = active_resolver.resolve(lat=lat, lon=lon)
    if resolution.prefix is None:
        raise IdAssignmentError(resolution)

    next_number = next_object_number(resolution.prefix, objects_dir=objects_dir)
    return IdProposal(
        object_id=format_object_id(resolution.prefix, next_number),
        prefix=resolution.prefix,
        next_number=next_number,
        resolution=resolution,
    )


def format_proposal(proposal: IdProposal) -> str:
    """Format a proposal for CLI output."""

    resolution = proposal.resolution
    lines = [
        f"proposed_id: {proposal.object_id}",
        f"prefix: {proposal.prefix}",
        f"next_number: {proposal.next_number}",
        f"status: {resolution.status.value}",
        f"area: {resolution.area.value}",
    ]

    if resolution.valley_name:
        lines.append(f"valley: {resolution.valley_name}")

    lines.extend(
        [
            f"x_1992: {resolution.x_1992:.2f}",
            f"y_1992: {resolution.y_1992:.2f}",
        ]
    )

    if resolution.status == PrefixResolutionStatus.WARNING:
        lines.append(f"warning: {_format_resolution_message(resolution)}")

    return "\n".join(lines)


def format_error(error: IdAssignmentError) -> str:
    """Format an ID assignment error for CLI output."""

    resolution = error.resolution
    return "\n".join(
        [
            f"status: {resolution.status.value}",
            f"area: {resolution.area.value}",
            f"x_1992: {resolution.x_1992:.2f}",
            f"y_1992: {resolution.y_1992:.2f}",
            f"error: {_format_resolution_message(resolution)}",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Propose the next object ID for WGS84 coordinates.",
    )
    parser.add_argument("lat", type=float, help="Latitude in WGS84 decimal degrees.")
    parser.add_argument("lon", type=float, help="Longitude in WGS84 decimal degrees.")
    parser.add_argument(
        "--objects-dir",
        type=Path,
        default=DEFAULT_OBJECTS_DIR,
        help="Objects root directory. Defaults to data/objects.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface."""

    args = build_parser().parse_args(argv)

    try:
        proposal = propose_id(lat=args.lat, lon=args.lon, objects_dir=args.objects_dir)
    except IdAssignmentError as exc:
        print(format_error(exc), file=sys.stderr)
        return 1

    print(format_proposal(proposal))
    return 0


def _format_resolution_message(resolution: PrefixResolution) -> str:
    message = resolution.message or "No details."
    if resolution.code:
        return f"{resolution.code}: {message}"
    return message


if __name__ == "__main__":
    raise SystemExit(main())
