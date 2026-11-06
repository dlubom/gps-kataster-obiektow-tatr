"""Literal canonical export fixtures and accepted Git snapshots.

No production loader, validator, SQL session or writer runs during setup.
Accept the completed valid fixture before corrupting the candidate; pass the
returned immutable commit SHA explicitly to the production API or CLI.
"""

import os
import shutil
import subprocess
import tempfile
from copy import deepcopy
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
KSW_LAT = 49.23459299
KSW_LON = 19.87589498
GENERATED_AT = "2026-05-16T12:00:00Z"


def initialize_source(data_dir):
    for name in ("objects", "caves", "relations", "publications"):
        directory = data_dir / name
        directory.mkdir(parents=True, exist_ok=True)
        (directory / ".gitkeep").touch()
    (data_dir / "catalog.json").write_text(
        '{"format":"postgresql-yaml","schema_version":2}', encoding="utf-8"
    )
    return data_dir


def write_sample_data(data_dir, *, notes=False, manual=False, bibliography=False):
    initialize_source(data_dir)
    obj = valid_object(notes=notes)
    cave = valid_cave(notes=notes)
    if manual:
        obj["best_measurement"].update(
            mode="manual", measurement_id="m-001", reason="Keep the older PIG point"
        )
    if bibliography:
        publication = {
            "id": "fixture-publication",
            "citation": "Fixture author (2026), Cave survey.",
        }
        write_yaml(data_dir / "publications/fixture-publication.yml", publication)
        citation = {
            "publication_id": "fixture-publication",
            "locator": "p. 7",
            "purpose": "existence",
        }
        obj.update(bibliography_status="known", citations=[deepcopy(citation)])
        cave.update(bibliography_status="known", citations=[deepcopy(citation)])
        obj["measurements"][0]["citations"] = [
            {"publication_id": "fixture-publication", "locator": "p. 7"}
        ]
    write_yaml(data_dir / "objects/KSW/KSW-0001.yml", obj)
    write_yaml(data_dir / "caves/C-0001.yml", cave)
    return data_dir


def accept_source(data_dir):
    """Copy bytes into a separate real Git repository; never repair the input."""
    root = Path(tempfile.mkdtemp(prefix=f".{data_dir.name}-accepted-", dir=data_dir.parent))
    shutil.copytree(data_dir, root / "data", symlinks=True)
    # Git cannot index empty directories; preserve only those actually copied.
    for directory in (root / "data").rglob("*"):
        if directory.is_dir() and not directory.is_symlink() and not any(directory.iterdir()):
            (directory / ".gitkeep").touch()
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}

    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(root), *args], text=True, env=env, stderr=subprocess.PIPE
        ).strip()

    git("init", "-q")
    git("add", "data")
    git(
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        "Accepted fixture",
    )
    return {"history_repo": root, "base_ref": git("rev-parse", "HEAD")}


def cli_args(baseline):
    return ["--history-repo", str(baseline["history_repo"]), "--base-ref", baseline["base_ref"]]


def source(root, *, empty=False):
    data = initialize_source(root / "data") if empty else write_sample_data(root / "data")
    return data, accept_source(data)


def excel_records(sheet):
    headers = [cell.value for cell in sheet[6]]
    return [
        dict(zip(headers, row, strict=True)) for row in sheet.iter_rows(min_row=7, values_only=True)
    ]


def valid_object(*, notes=False) -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "KSW-0001",
        "category": "jaskinia_otwor",
        "name_local": "Test Cave - main entrance",
        "cave_id": "C-0001",
        "membership_ordinal": 1,
        "bibliography_status": "unknown",
        "id_assignment": {
            "method": "auto",
            "assigned_from_measurement_id": "m-001",
            "assigned_prefix": "KSW",
            "prefix_override_reason": None,
        },
        "external_refs": [
            {
                "system": "TPN",
                "ref_type": "source_globalid",
                "external_id": "{38626571-CAA6-4317-8900-D61A995020E9}",
                "scope": "object",
                "notes": "TPN point reference.",
            }
        ],
        "measurements": [
            measurement("m-001", source="PIG", observed_date="2026-05-15", notes=notes),
            measurement("m-002", source="TPN", observed_date="2026-05-16", notes=notes),
        ],
        "best_measurement": {
            "mode": "auto",
            "reason": None,
            "updated_at": "2026-05-16T10:30:00Z",
            "updated_by": "dl",
        },
        "attachments": [],
        "notes": "Object terrain note." if notes else None,
        "created_at": "2026-05-15T10:00:00Z",
        "created_by": "dl",
        "updated_at": "2026-05-16T10:30:00Z",
        "updated_by": "dl",
    }


def valid_cave(*, notes=False) -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "C-0001",
        "name": "Test Cave",
        "system_name": None,
        "external_refs": (
            [
                {
                    "system": "NR_INWENT",
                    "ref_type": "inventory_number",
                    "external_id": "T.E-08.75",
                    "scope": "cave",
                    "notes": "Inventory number belongs to the cave/catalog entry.",
                }
            ]
            if notes
            else []
        )
        + [
            {
                "system": "PIG",
                "ref_type": "catalog_id",
                "external_id": "1094",
                "url": "https://jaskiniepolski.pgi.gov.pl/Details/Information/1094",
                "scope": "cave",
                "notes": "PIG catalog record identifier.",
            },
        ],
        "bibliography_status": "unknown",
        "notes": "Cave catalog note." if notes else None,
        "created_at": "2026-05-15T10:00:00Z",
        "created_by": "dl",
        "updated_at": "2026-05-16T10:30:00Z",
        "updated_by": "dl",
    }


def measurement(
    measurement_id: str,
    *,
    source: str,
    observed_date: str,
    notes=False,
) -> dict[str, object]:
    return {
        "id": measurement_id,
        "lat": KSW_LAT,
        "lon": KSW_LON,
        "elevation_m": 1240.0,
        "elevation_datum": "unknown",
        "elevation_source": "source_record",
        "horizontal_accuracy_m": 5.0,
        "vertical_accuracy_m": 8.0,
        "source": source,
        "source_ref": f"{source}:{measurement_id}",
        "observed_at": None,
        "observed_date": observed_date,
        "source_date": None,
        "method": "source_record",
        "device": None,
        "tags": ["fixture"],
        "verification_status": "nieweryfikowany",
        "verified_by": None,
        "verified_at": None,
        "notes": f"{source} measurement note." if notes else None,
        "created_at": "2026-05-15T10:00:00Z",
        "created_by": "dl",
    }


def write_yaml(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(deepcopy(data), sort_keys=False), encoding="utf-8")
