"""Publication and history failures reproduced in the PostgreSQL migration review."""

import sqlite3
from datetime import datetime

import pytest
from export_test_support import accept_source, source, write_yaml
from export_test_support import excel_records as _excel_records
from openpyxl import load_workbook

from gps_kataster_obiektow_tatr.best_measurements_export import export_best_measurements
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts


@pytest.mark.parametrize("missing", ["omitted", "null"])
def test_full_exports_do_not_fill_historical_gaps_from_best(tmp_path, missing):
    data, baseline = source(tmp_path)
    import yaml

    path = data / "objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(path.read_text())
    historical, selected = obj["measurements"]
    values = {
        "elevation_m": 1234.0,
        "source_ref": "TPN:selected-only",
        "horizontal_accuracy_m": 1.5,
        "vertical_accuracy_m": 3.0,
        "observed_at": "2026-11-02T10:00:00Z",
        "elevation_datum": "PL-EVRF2007-NH",
        "elevation_source": "gnss",
        "source_date": "2026-10-31",
        "device": "Selected receiver",
        "verified_by": "reviewer",
        "verified_at": "2026-11-02T11:00:00Z",
        "notes": "Selected measurement only",
    }
    selected.update(values)
    for field in values:
        if missing == "omitted":
            historical.pop(field, None)
        else:
            historical[field] = None
    write_yaml(path, obj)
    baseline = accept_source(data)

    result = build_release_artifacts(data_dir=data, output_dir=tmp_path / "exports", **baseline)
    with sqlite3.connect(result.geopackage_path) as db:
        assert db.execute(
            "SELECT measurement_id,elevation_m,source_ref,horizontal_accuracy_m,"
            "vertical_accuracy_m,observed_at,elevation_datum,elevation_source,source_date,"
            "device,verified_by,verified_at,measurement_notes "
            "FROM measurements ORDER BY measurement_id"
        ).fetchall() == [
            ("m-001", *([None] * 12)),
            ("m-002", *values.values()),
        ]
    book = load_workbook(result.excel_path)
    try:
        rows = _excel_records(book["Full"])
        headers = (
            "Wysokość [m]",
            "Odniesienie do źródła",
            "Dokładność pozioma [m]",
            "Dokładność pionowa [m]",
            "Czas pomiaru (ISO 8601)",
            "Układ wysokości",
            "Źródło wysokości",
            "Data źródła",
            "Urządzenie",
            "Zweryfikował",
            "Czas weryfikacji (ISO 8601)",
            "Uwagi pomiaru",
        )
        assert [rows[0][header] for header in headers] == [None] * 12
        assert [rows[1][header] for header in headers] == [
            1234,
            "TPN:selected-only",
            1.5,
            3,
            "2026-11-02T10:00:00Z",
            "PL-EVRF2007-NH",
            "gnss",
            datetime(2026, 10, 31),
            "Selected receiver",
            "reviewer",
            "2026-11-02T11:00:00Z",
            "Selected measurement only",
        ]
    finally:
        book.close()


def test_standalone_export_cannot_replace_a_complete_release(tmp_path):
    data, baseline = source(tmp_path)
    output = tmp_path / "exports"
    build_release_artifacts(data_dir=data, output_dir=output, **baseline)
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    with pytest.raises(ValueError, match="full release"):
        export_best_measurements(data_dir=data, output_dir=output, **baseline)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before
    separate = tmp_path / "best-only"
    export_best_measurements(data_dir=data, output_dir=separate, **baseline)
    assert len(list(separate.iterdir())) == 8
