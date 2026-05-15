import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from gps_kataster_obiektow_tatr.prefix_resolver import (
    OUTSIDE_COUNTRIES_CODE,
    OUTSIDE_COUNTRIES_MESSAGE,
    OUTSIDE_VALLEYS_CODE,
    OUTSIDE_VALLEYS_MESSAGE,
    PrefixResolution,
    PrefixResolutionArea,
    PrefixResolutionStatus,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSIGN_ID_PATH = REPO_ROOT / "scripts" / "assign_id.py"

spec = importlib.util.spec_from_file_location("assign_id", ASSIGN_ID_PATH)
assert spec is not None
assert spec.loader is not None
assign_id = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = assign_id
spec.loader.exec_module(assign_id)


class StubResolver:
    def __init__(self, resolution: PrefixResolution) -> None:
        self.resolution = resolution

    def resolve(self, *, lat: float, lon: float) -> PrefixResolution:
        return self.resolution


def test_empty_prefix_directory_gives_first_id(tmp_path: Path) -> None:
    assert assign_id.next_object_id("KSW", objects_dir=tmp_path) == "KSW-0001"


def test_existing_object_files_give_next_number(tmp_path: Path) -> None:
    prefix_dir = tmp_path / "KSW"
    prefix_dir.mkdir()
    (prefix_dir / "KSW-0001.yml").touch()
    (prefix_dir / "KSW-0002.yml").touch()
    (prefix_dir / "KSW-not-a-number.yml").touch()
    (prefix_dir / "OTHER-9999.yml").touch()

    assert assign_id.next_object_id("KSW", objects_dir=tmp_path) == "KSW-0003"


def test_large_existing_number_extends_beyond_four_digits(tmp_path: Path) -> None:
    prefix_dir = tmp_path / "KSW"
    prefix_dir.mkdir()
    (prefix_dir / "KSW-9999.yml").touch()

    assert assign_id.next_object_id("KSW", objects_dir=tmp_path) == "KSW-10000"


def test_proposal_formats_resolver_warning(tmp_path: Path) -> None:
    resolution = PrefixResolution(
        status=PrefixResolutionStatus.WARNING,
        area=PrefixResolutionArea.POLAND,
        prefix="PL",
        code=OUTSIDE_VALLEYS_CODE,
        message=OUTSIDE_VALLEYS_MESSAGE,
        x_1992=485_000.123,
        y_1992=637_000.456,
    )

    proposal = assign_id.propose_id(
        lat=52.2297,
        lon=21.0122,
        objects_dir=tmp_path,
        resolver=StubResolver(resolution),
    )

    assert assign_id.format_proposal(proposal).splitlines() == [
        "proposed_id: PL-0001",
        "prefix: PL",
        "next_number: 1",
        "status: warning",
        "area: poland",
        "x_1992: 485000.12",
        "y_1992: 637000.46",
        f"warning: {OUTSIDE_VALLEYS_CODE}: {OUTSIDE_VALLEYS_MESSAGE}",
    ]


def test_resolution_without_prefix_exits_without_proposal(tmp_path: Path) -> None:
    resolution = PrefixResolution(
        status=PrefixResolutionStatus.ERROR,
        area=PrefixResolutionArea.OUTSIDE_PL_SK,
        prefix=None,
        code=OUTSIDE_COUNTRIES_CODE,
        message=OUTSIDE_COUNTRIES_MESSAGE,
        x_1992=320_000.0,
        y_1992=460_000.0,
    )

    with pytest.raises(assign_id.IdAssignmentError):
        assign_id.propose_id(
            lat=50.0755,
            lon=14.4378,
            objects_dir=tmp_path,
            resolver=StubResolver(resolution),
        )


def test_cli_accepts_lat_lon_and_prints_proposed_id(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ASSIGN_ID_PATH),
            "--objects-dir",
            str(tmp_path),
            "49.23459299",
            "19.87589498",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "proposed_id: KSW-0001" in result.stdout
    assert "status: ok" in result.stdout
    assert "warning:" not in result.stdout
