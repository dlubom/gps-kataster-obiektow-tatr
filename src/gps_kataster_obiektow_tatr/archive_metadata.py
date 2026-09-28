"""Stable timestamps and file metadata for generated release archives."""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


class ArchiveTimestampError(ValueError):
    """The requested release time cannot be represented in a ZIP archive."""


@dataclass(frozen=True, slots=True)
class ArchiveTimestamp:
    """One build instant used by metadata, ZIP members, and the DBF header."""

    text: str
    utc: datetime

    @property
    def zip_date_time(self) -> tuple[int, int, int, int, int, int]:
        """Return the UTC instant at ZIP's two-second resolution."""

        return (
            self.utc.year,
            self.utc.month,
            self.utc.day,
            self.utc.hour,
            self.utc.minute,
            self.utc.second // 2 * 2,
        )

    @property
    def dbf_date(self) -> bytes:
        """Return the dBase header date as year-since-1900, month, day."""

        return bytes((self.utc.year - 1900, self.utc.month, self.utc.day))


def resolve_archive_timestamp(generated_at: str | None) -> ArchiveTimestamp:
    """Resolve one aware instant and reject dates outside ZIP's 1980–2107 range."""

    if generated_at is None:
        instant = datetime.now(UTC).replace(microsecond=0)
        text = instant.isoformat().replace("+00:00", "Z")
    else:
        text = generated_at
        try:
            instant = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ArchiveTimestampError(f"Invalid generated_at timestamp: {text!r}.") from exc
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ArchiveTimestampError("generated_at must include a timezone offset.")
        instant = instant.astimezone(UTC)

    if not 1980 <= instant.year <= 2107:
        raise ArchiveTimestampError(
            "generated_at UTC date is outside the ZIP range 1980-01-01 through 2107-12-31."
        )
    return ArchiveTimestamp(text=text, utc=instant)


def write_archive_member(
    archive: zipfile.ZipFile, file_path: Path, timestamp: ArchiveTimestamp
) -> None:
    """Write file contents with fixed ZIP time and portable regular-file attributes."""

    info = zipfile.ZipInfo(file_path.name, timestamp.zip_date_time)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    with file_path.open("rb") as source, archive.open(info, mode="w") as destination:
        shutil.copyfileobj(source, destination)
