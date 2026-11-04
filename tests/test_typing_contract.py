"""Exercise the real checker: removing useful annotations must break these probes."""

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

REPO_ROOT = Path(__file__).resolve().parents[1]


def _check(tmp_path: Path, source: str) -> subprocess.CompletedProcess[str]:
    probe = tmp_path / "probe.py"
    probe.write_text(dedent(source).lstrip(), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--config-file",
            str(REPO_ROOT / "pyproject.toml"),
            "--cache-dir",
            str(tmp_path / "cache"),
            "--no-pretty",
            "--no-error-summary",
            str(probe),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_mypy_accepts_typed_best_and_model_consumers(tmp_path: Path) -> None:
    result = _check(
        tmp_path,
        """
        from typing import assert_type
        from gps_kataster_obiektow_tatr.best_measurement import (
            select_default_best_measurement_id,
        )
        from gps_kataster_obiektow_tatr.measurement_values import non_finite_measurement_fields
        from gps_kataster_obiektow_tatr.models import Measurement, RelationRecord

        assert_type(select_default_best_measurement_id([{
            "id": "m-001", "source": "TPN", "verification_status": "nieweryfikowany",
            "observed_date": "2026-11-04", "observed_at": None,
            "horizontal_accuracy_m": 2,
        }]), str | None)
        assert_type(non_finite_measurement_fields({"lat": 49}), tuple[str, ...])

        def model_consumer(measurement: Measurement) -> str:
            assert_type(measurement.lat, float)
            return measurement.id

        RelationRecord(schema_version=1, id="R-0001", from_object_id="KSW-0001",
                       to_object_id="KSW-0002", relation_type="sasiad")
        """,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_mypy_rejects_wrong_arguments_and_unknown_fields(tmp_path: Path) -> None:
    source = """
        from gps_kataster_obiektow_tatr.best_measurement import (
            _parse_observed_at, select_default_best_measurement_id,
        )
        from gps_kataster_obiektow_tatr.measurement_values import non_finite_measurement_fields
        from gps_kataster_obiektow_tatr.models import Measurement, RelationRecord

        select_default_best_measurement_id([{"id": 123}])  # typeddict-item
        select_default_best_measurement_id([
            {"id": "m-001", "observed_att": "today"},  # typeddict-unknown-key
        ])
        non_finite_measurement_fields(123)  # arg-type
        _parse_observed_at(123)  # arg-type

        def model_consumer(measurement: Measurement) -> None:
            print(measurement.latitude)  # attr-defined

        RelationRecord(schema_version="1", id="R-0001", from_object_id="KSW-0001",  # arg-type
                       to_object_id="KSW-0002", relation_type="sasiad")
    """
    result = _check(tmp_path, source)
    assert result.returncode == 1, result.stdout + result.stderr
    expected_lines = {
        number: line.rsplit("# ", 1)[1]
        for number, line in enumerate(dedent(source).lstrip().splitlines(), start=1)
        if "# " in line
    }
    diagnostics = [line for line in result.stdout.splitlines() if ": error:" in line]
    assert len(diagnostics) == len(expected_lines), result.stdout + result.stderr
    for number, code in expected_lines.items():
        assert any(
            f"probe.py:{number}: error:" in line and f"[{code}]" in line for line in diagnostics
        ), result.stdout + result.stderr
