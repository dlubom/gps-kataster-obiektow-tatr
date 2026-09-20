"""Non-finite values must never become catalog measurements or artifacts."""

import csv
import json

import pytest
import yaml
from test_identifier_scopes import ARTIFACTS, _sample, _snapshot, _write
from test_pig_staging import _write_xlsx
from test_review_validation import _decisions
from test_staging_review import _pig_staging

from gps_kataster_obiektow_tatr import pig_staging, tpn_staging
from gps_kataster_obiektow_tatr.best_measurements_export import (
    BestMeasurementsExportValidationError,
    export_best_measurements,
)
from gps_kataster_obiektow_tatr.build_db import BuildDatabaseValidationError
from gps_kataster_obiektow_tatr.coordinates import (
    coordinate_consistency_error_m,
    pl1992_to_wgs84,
    wgs84_to_1992,
)
from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts
from gps_kataster_obiektow_tatr.source_profile import PIG_PROFILE_SPEC, profile_csv_source
from gps_kataster_obiektow_tatr.staging_review import StagingReports, apply_review_decisions
from gps_kataster_obiektow_tatr.validator import ValidationSeverity, validate_data_dir

FIELDS = (
    "lat",
    "lon",
    "x_1992",
    "y_1992",
    "elevation_m",
    "horizontal_accuracy_m",
    "vertical_accuracy_m",
)
BAD = [float("nan"), float("inf"), float("-inf")]
STAMP = "2026-09-19T12:00:00Z"


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("bad", BAD)
def test_nonfinite_yaml_blocks_validation_and_release_without_writes(tmp_path, field, bad):
    data_dir = tmp_path / "data"
    paths = _sample(data_dir)
    obj_path = paths["object"]
    obj = yaml.safe_load(obj_path.read_text())
    obj["measurements"][0][field] = bad
    _write(obj_path, obj)
    output = tmp_path / "output"
    output.mkdir()
    for name in ARTIFACTS:
        (output / name).write_bytes(b"previous artifact")
    before = _snapshot(tmp_path)
    issues = validate_data_dir(data_dir)
    errors = [i for i in issues if i.code == "NON_FINITE_NUMBER"]
    assert errors and all(i.severity == ValidationSeverity.ERROR for i in errors)
    assert any(i.path == obj_path and field in i.description for i in errors)
    with pytest.raises(BuildDatabaseValidationError):
        build_release_artifacts(
            data_dir=data_dir,
            sqlite_path=output / "katalog.sqlite",
            output_dir=output,
            generated_at=STAMP,
        )
    with pytest.raises(BestMeasurementsExportValidationError):
        export_best_measurements(data_dir=data_dir, output_dir=output, generated_at=STAMP)
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("write", [True, False])
def test_review_rejects_nonfinite_proposals_without_writes(tmp_path, field, write):
    pig = _pig_staging()
    pig["proposed_objects"][0]["measurements"][0][field] = float("nan")
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        _decisions("create_cave", "create_object"),
        staging_reports=StagingReports(pig=pig),
        data_dir=tmp_path,
        write=write,
    )
    assert result.has_errors
    assert any("NON_FINITE_NUMBER" in i.description for i in result.issues)
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("bad", BAD)
@pytest.mark.parametrize("field", ["lat", "lon", "x_1992", "y_1992"])
def test_coordinate_helpers_reject_nonfinite_inputs(field, bad):
    point = dict(lat=49.23459299, lon=19.87589498, x_1992=152267.23, y_1992=563744.25)
    point[field] = bad
    with pytest.raises(ValueError):
        coordinate_consistency_error_m(**point)
    with pytest.raises(ValueError):
        if field in ("lat", "lon"):
            wgs84_to_1992(lat=point["lat"], lon=point["lon"])
        else:
            pl1992_to_wgs84(x_1992=point["x_1992"], y_1992=point["y_1992"])


def _source_row(source):
    if source == "PIG":
        return {
            "ID": "1",
            "Nazwa": "Test",
            "B": "49.23459299",
            "L": "19.87589498",
            "X 1992": "152267.23",
            "Y 1992": "563744.25",
            "H (wg PIG)": "1200",
            "Stan na rok": "2010",
        }
    return {
        "GLOBALID": "gid-1",
        "NAZWA": "Test",
        "X1992": "152267.23",
        "Y1992": "563744.25",
        "Z": "1200",
    }


def _source(path, row):
    if path.suffix == ".xlsx":
        _write_xlsx(path, [list(row), list(row.values())])
    else:
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)


@pytest.mark.parametrize(
    "source,field",
    [("PIG", f) for f in ("B", "L", "X 1992", "Y 1992", "H (wg PIG)")]
    + [("TPN", f) for f in ("X1992", "Y1992", "Z")],
)
@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity", "1e999"])
@pytest.mark.parametrize("suffix", [".csv", ".xlsx"])
def test_import_rejects_nonfinite_row_with_diagnostic(tmp_path, source, field, bad, suffix):
    row = _source_row(source)
    row[field] = bad
    path = tmp_path / ("source" + suffix)
    _source(path, row)
    if source == "PIG":
        report = pig_staging.build_pig_staging(path, generated_at=STAMP, data_dir=tmp_path / "data")
        writer = pig_staging.write_staging_files
    else:
        report = tpn_staging.build_tpn_staging(
            path, generated_at=STAMP, data_dir=tmp_path / "data", pig_staging_path=None
        )
        assert report.matched_measurements == ()
        writer = tpn_staging.write_staging_files
    assert report.proposed_objects == ()
    expected_code = (
        f"{source}_ELEVATION_INVALID"
        if field in ("Z", "H (wg PIG)")
        else f"{source}_POINT_COORDINATES_INVALID"
    )
    assert report.issues[0].code == expected_code
    assert report.issues[0].severity == "warning"
    assert any(i.record_number == 1 and field in i.description for i in report.issues)
    json_path, _ = writer(report, output_dir=tmp_path / "reports")
    json.loads(json_path.read_text(), parse_constant=lambda s: pytest.fail(s))
    assert not (tmp_path / "data").exists()


def test_profile_counts_nonfinite_as_invalid_not_missing(tmp_path):
    path = tmp_path / "source.csv"
    path.write_text('B\nNaN\nInfinity\n-Infinity\n1e999\n49.2\n""\n""\n')
    profile = profile_csv_source(path, PIG_PROFILE_SPEC).coordinate_ranges["B"]
    assert (profile.numeric_count, profile.non_numeric_count, profile.missing_count) == (1, 4, 2)
    assert profile.minimum == profile.maximum == 49.2


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, None),
        ("", None),
        ("  ", None),
        ("1\u00a0234,5", 1234.5),
        ("-0", 0),
        ("0", 0),
        ("-12.5", -12.5),
        (123, 123),
    ],
)
def test_decimal_missing_and_finite_values(value, expected):
    from gps_kataster_obiektow_tatr.numeric import parse_decimal

    assert parse_decimal(value) == expected


@pytest.mark.parametrize("value", [True, False, None, "NaN", 10**400, *BAD])
def test_numeric_predicate_rejects_unsafe_values(value):
    from gps_kataster_obiektow_tatr.numeric import is_finite_number

    assert not is_finite_number(value)


@pytest.mark.parametrize("value", [0, -1, 2, 1.2, -2.5])
def test_numeric_predicate_accepts_finite_scalars(value):
    from gps_kataster_obiektow_tatr.numeric import is_finite_number

    assert is_finite_number(value)


def test_finite_field_paths_cover_nested_records():
    from gps_kataster_obiektow_tatr.numeric import nonfinite_paths

    assert nonfinite_paths(
        {"nested": [{"x": float("nan")}, {"y": float("inf")}], "valid": [0, None, True, "NaN"]}
    ) == ("nested[0].x", "nested[1].y")


@pytest.mark.parametrize("source,field", [("PIG", "H (wg PIG)"), ("TPN", "Z")])
@pytest.mark.parametrize("value", ["", "0", "-12.5", "1234,5"])
def test_optional_elevation_preserves_missing_and_finite_values(tmp_path, source, field, value):
    row = _source_row(source)
    row[field] = value
    path = tmp_path / "source.csv"
    _source(path, row)
    if source == "PIG":
        report = pig_staging.build_pig_staging(path, generated_at=STAMP, data_dir=tmp_path / "data")
    else:
        report = tpn_staging.build_tpn_staging(
            path, generated_at=STAMP, data_dir=tmp_path / "data", pig_staging_path=None
        )
    assert not report.issues
    assert report.proposed_objects[0]["measurements"][0]["elevation_m"] == (
        float(value.replace(",", ".")) if value else None
    )


@pytest.mark.parametrize("field", ["elevation_m", "horizontal_accuracy_m", "vertical_accuracy_m"])
@pytest.mark.parametrize("value", [None, 0, 1.5])
def test_nullable_yaml_fields_remain_valid(tmp_path, field, value):
    path = _sample(tmp_path)["object"]
    obj = yaml.safe_load(path.read_text())
    obj["measurements"][0][field] = value
    _write(path, obj)
    assert not any(i.severity == ValidationSeverity.ERROR for i in validate_data_dir(tmp_path))


@pytest.mark.parametrize("field", ["lat", "lon", "x_1992", "y_1992"])
def test_huge_finite_coordinates_report_errors_without_crash(tmp_path, field):
    path = _sample(tmp_path)["object"]
    obj = yaml.safe_load(path.read_text())
    obj["measurements"][0][field] = 1e308
    _write(path, obj)
    assert any(i.severity == ValidationSeverity.ERROR for i in validate_data_dir(tmp_path))


@pytest.mark.parametrize("source", ["PIG", "TPN"])
def test_staging_json_guard_preserves_existing_report(tmp_path, source):
    path = tmp_path / "source.csv"
    _source(path, _source_row(source))
    if source == "PIG":
        report = pig_staging.build_pig_staging(path, generated_at=STAMP, data_dir=tmp_path / "data")
        writer = pig_staging.write_staging_files
    else:
        report = tpn_staging.build_tpn_staging(
            path, generated_at=STAMP, data_dir=tmp_path / "data", pig_staging_path=None
        )
        writer = tpn_staging.write_staging_files
    output = tmp_path / "reports"
    writer(report, output_dir=output)
    before = _snapshot(output)
    report.proposed_objects[0]["measurements"][0]["elevation_m"] = float("nan")
    with pytest.raises(ValueError):
        writer(report, output_dir=output)
    assert _snapshot(output) == before


@pytest.mark.parametrize("source", ["yaml", "pig_staging"])
def test_tpn_rejects_nonfinite_candidate_data_before_proposing(tmp_path, source):
    path = tmp_path / "source.csv"
    _source(path, _source_row("TPN"))
    data_dir = tmp_path / "data"
    pig_path = None
    if source == "yaml":
        obj_path = _sample(data_dir)["object"]
        obj = yaml.safe_load(obj_path.read_text())
        obj["measurements"][0]["elevation_m"] = float("inf")
        _write(obj_path, obj)
    else:
        pig = _pig_staging()
        pig["proposed_objects"][0]["measurements"][0]["x_1992"] = float("nan")
        pig_path = tmp_path / "pig-staging.json"
        pig_path.write_text(json.dumps(pig))
    before = _snapshot(tmp_path)
    with pytest.raises(ValueError, match="non-finite"):
        tpn_staging.build_tpn_staging(
            path, generated_at=STAMP, data_dir=data_dir, pig_staging_path=pig_path
        )
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("bad", BAD)
def test_matching_radius_must_be_finite(tmp_path, bad):
    path = tmp_path / "source.csv"
    _source(path, _source_row("TPN"))
    with pytest.raises(ValueError, match="duplicate_radius_m"):
        tpn_staging.build_tpn_staging(
            path,
            generated_at=STAMP,
            data_dir=tmp_path / "data",
            pig_staging_path=None,
            duplicate_radius_m=bad,
        )


def test_bad_tpn_row_does_not_drop_following_valid_rows(tmp_path):
    bad = _source_row("TPN")
    bad["Z"] = "NaN"
    bad["NR_INWENT"] = "T.A-01"
    good = _source_row("TPN")
    good["GLOBALID"] = "gid-2"
    path = tmp_path / "source.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(bad))
        writer.writeheader()
        writer.writerows([bad, good])
    report = tpn_staging.build_tpn_staging(
        path, generated_at=STAMP, data_dir=tmp_path / "data", pig_staging_path=None
    )
    assert [(r.record_number, r.status) for r in report.rows] == [(1, "rejected"), (2, "new")]
    rejected = report.rows[0]
    assert (rejected.globalid, rejected.nr_inwent, rejected.name) == ("gid-1", "T.A-01", "Test")
    issue = report.issues[0]
    assert (issue.globalid, issue.nr_inwent) == ("gid-1", "T.A-01")
    assert len(report.proposed_objects) == 1
    assert report.proposed_objects[0]["measurements"][0]["source_ref"] == "TPN:gid-2"


@pytest.mark.parametrize("direction", ["forward", "inverse"])
@pytest.mark.parametrize("index", [0, 1])
def test_nonfinite_projection_output_is_rejected(monkeypatch, direction, index):
    from gps_kataster_obiektow_tatr import coordinates

    class BrokenTransform:
        def transform(self, *args):
            values = [1.0, 2.0]
            values[index] = float("inf")
            return values

    if direction == "forward":
        monkeypatch.setattr(coordinates, "_WGS84_TO_PL_1992", BrokenTransform())

        def call():
            return coordinates.wgs84_to_1992(49.2, 19.8)
    else:
        monkeypatch.setattr(coordinates, "_PL_1992_TO_WGS84", BrokenTransform())

        def call():
            return coordinates.pl1992_to_wgs84(152267.23, 563744.25)

    with pytest.raises(ValueError, match="finite"):
        call()


def test_consistency_includes_tolerance_boundary_and_rejects_infinite_tolerance():
    from gps_kataster_obiektow_tatr.coordinates import coordinates_are_consistent

    point = wgs84_to_1992(49.2, 19.8)
    args = dict(lat=49.2, lon=19.8, x_1992=point.x_1992 + 0.5, y_1992=point.y_1992)
    assert coordinates_are_consistent(**args, tolerance_m=0.5)
    with pytest.raises(ValueError, match="finite"):
        coordinates_are_consistent(**args, tolerance_m=float("inf"))


@pytest.mark.parametrize("source,field", [("PIG", "B"), ("TPN", "X1992")])
def test_projection_failure_reports_source_row(tmp_path, monkeypatch, source, field):
    row = _source_row(source)
    row[field] = "1e308"
    if source == "TPN":

        def broken_projection(**kwargs):
            raise ValueError("non-finite projection output")

        monkeypatch.setattr(tpn_staging, "pl1992_to_wgs84", broken_projection)
    path = tmp_path / "source.csv"
    _source(path, row)
    if source == "PIG":
        report = pig_staging.build_pig_staging(path, generated_at=STAMP, data_dir=tmp_path / "data")
    else:
        report = tpn_staging.build_tpn_staging(
            path, generated_at=STAMP, data_dir=tmp_path / "data", pig_staging_path=None
        )
    assert report.proposed_objects == ()
    assert report.issues[0].record_number == 1
    assert report.issues[0].code == f"{source}_POINT_COORDINATES_INVALID"
    assert report.issues[0].severity == "warning"
    assert "coordinate conversion" in report.issues[0].description


def test_profile_json_guard_preserves_existing_reports(tmp_path):
    from dataclasses import replace

    from gps_kataster_obiektow_tatr.source_profile import SourceProfileReport, write_report_files

    path = tmp_path / "source.csv"
    _source(path, _source_row("PIG"))
    profile = profile_csv_source(path, PIG_PROFILE_SPEC)
    report = SourceProfileReport(profiles=(profile,))
    output = tmp_path / "reports" / "nested"
    paths = write_report_files(report, output_dir=output, generated_at=STAMP)
    assert tuple(p.name for p in paths) == ("source-profile.json", "source-profile.md")
    before = _snapshot(output)
    profile.coordinate_ranges["B"] = replace(profile.coordinate_ranges["B"], minimum=float("nan"))
    with pytest.raises(ValueError):
        write_report_files(report, output_dir=output, generated_at=STAMP)
    assert _snapshot(output) == before


def test_review_json_guard_preserves_existing_reports(tmp_path):
    from dataclasses import replace

    from gps_kataster_obiektow_tatr.staging_review import write_review_report_files

    result = apply_review_decisions(
        _decisions("create_cave", "create_object"),
        staging_reports=StagingReports(pig=_pig_staging()),
        data_dir=tmp_path,
        write=False,
    )
    assert not result.has_errors
    output = tmp_path / "reports" / "nested"
    write_review_report_files(result, output_dir=output)
    before = _snapshot(output)
    bad_decision = replace(result.applied_decisions[0], record_number=float("nan"))
    result = replace(result, applied_decisions=(bad_decision,))
    with pytest.raises(ValueError):
        write_review_report_files(result, output_dir=output)
    assert _snapshot(output) == before


def test_validator_reports_projection_failure_with_file_and_measurement(tmp_path):
    path = _sample(tmp_path)["object"]
    obj = yaml.safe_load(path.read_text())
    obj["measurements"][0]["lat"] = 100.0
    _write(path, obj)
    issues = validate_data_dir(tmp_path)
    errors = [i for i in issues if i.code == "COORDINATE_INVALID"]
    assert len(errors) == 1
    assert errors[0].severity == ValidationSeverity.ERROR
    assert errors[0].path == path
    assert "KSW-0001" in errors[0].description and "m-001" in errors[0].description


@pytest.mark.parametrize("field", ["x_1992", "y_1992"])
def test_invalid_inverse_inputs_never_reach_projection(monkeypatch, field):
    from gps_kataster_obiektow_tatr import coordinates

    class MustNotRun:
        def transform(self, *args):
            pytest.fail("non-finite input reached projection")

    monkeypatch.setattr(coordinates, "_PL_1992_TO_WGS84", MustNotRun())
    values = dict(x_1992=1.0, y_1992=2.0)
    values[field] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        coordinates.pl1992_to_wgs84(**values)


@pytest.mark.parametrize("location", ["decision", "staging_row"])
@pytest.mark.parametrize("bad", BAD)
def test_review_rejects_nonfinite_record_numbers_without_writes(tmp_path, location, bad):
    decisions = _decisions("create_cave", "create_object")
    pig = _pig_staging()
    if location == "decision":
        decisions["decisions"][0]["record_number"] = bad
    else:
        pig["rows"][0]["record_number"] = bad
    before = _snapshot(tmp_path)
    result = apply_review_decisions(
        decisions, staging_reports=StagingReports(pig=pig), data_dir=tmp_path
    )
    assert result.has_errors
    assert result.written_paths == ()
    assert any("record_number" in i.description or "row" in i.description for i in result.issues)
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("field", ["lat", "lon"])
def test_invalid_forward_inputs_never_reach_projection(monkeypatch, field):
    from gps_kataster_obiektow_tatr import coordinates

    class MustNotRun:
        def transform(self, *args):
            pytest.fail("non-finite input reached projection")

    monkeypatch.setattr(coordinates, "_WGS84_TO_PL_1992", MustNotRun())
    values = dict(lat=49.2, lon=19.8)
    values[field] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        coordinates.wgs84_to_1992(**values)
