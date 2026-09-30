"""Reproduce full-catalog archive determinism without changing source data."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import shapefile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

import verify_project  # noqa: E402

from gps_kataster_obiektow_tatr import (  # noqa: E402
    archive_metadata,
    best_measurements_export,
    release_artifacts,
)
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts  # noqa: E402

GENERATED_AT = "2026-09-30T12:00:00Z"


def file_hashes(directory: Path) -> dict[str, str]:
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def main() -> None:
    evidence = Path(tempfile.mkdtemp(prefix="PBI-054-repro-", dir=ROOT / "build/verification"))
    original_hashes = file_hashes(ROOT / "data")
    results = []
    with tempfile.TemporaryDirectory(prefix="gps-kataster-PBI-054-") as temporary:
        data = Path(temporary) / "data"
        shutil.copytree(ROOT / "data", data)
        for name, date, mode in (
            ("first", datetime(2024, 3, 4, 10, 11, 12, tzinfo=UTC), 0o600),
            ("second", datetime(2025, 7, 9, 13, 14, 15, tzinfo=UTC), 0o644),
        ):
            run = evidence / name
            epoch = date.timestamp()
            for source in data.rglob("*"):
                if source.is_file():
                    os.utime(source, (epoch, epoch))
                    os.chmod(source, mode)
            write_member = archive_metadata.write_archive_member
            archive_inputs = []

            def vary_member_metadata(
                archive,
                file_path,
                timestamp,
                *,
                epoch=epoch,
                mode=mode,
                archive_inputs=archive_inputs,
                write_member=write_member,
            ):
                os.utime(file_path, (epoch, epoch))
                os.chmod(file_path, mode)
                archive_inputs.append(
                    {"file": file_path.name, "mtime": file_path.stat().st_mtime, "mode": oct(mode)}
                )
                write_member(archive, file_path, timestamp)

            with (
                patch.object(shapefile.time, "localtime", lambda *_, date=date: date.timetuple()),
                patch.object(
                    best_measurements_export, "write_archive_member", vary_member_metadata
                ),
                patch.object(release_artifacts, "write_archive_member", vary_member_metadata),
            ):
                build_release_artifacts(
                    data_dir=data,
                    sqlite_path=run / "katalog.sqlite",
                    output_dir=run / "exports",
                    generated_at=GENERATED_AT,
                )
            readback = verify_project.readback_artifacts(data, run, GENERATED_AT)
            if len(archive_inputs) != 6:
                raise RuntimeError("Did not vary metadata of all six archive inputs")
            if file_hashes(data) != original_hashes:
                raise RuntimeError("Copied source contents changed during build")
            results.append(
                {
                    "clock": date.isoformat(),
                    "mode": oct(mode),
                    "archive_inputs": archive_inputs,
                    **readback,
                }
            )
    if results[0]["artifact_sha256"] != results[1]["artifact_sha256"]:
        raise RuntimeError("The two builds differ")
    if file_hashes(ROOT / "data") != original_hashes:
        raise RuntimeError("Repository source data changed")
    report = {"generated_at": GENERATED_AT, "identical": True, "builds": results}
    (evidence / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Evidence: {evidence.relative_to(ROOT)}/report.json")


if __name__ == "__main__":
    main()
