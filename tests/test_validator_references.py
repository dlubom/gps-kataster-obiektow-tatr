"""Public, schema-valid regressions for validator reference and attachment rules."""

from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest
from test_validator import _valid_object, _write_object, _write_yaml

import gps_kataster_obiektow_tatr.validator as validator
from gps_kataster_obiektow_tatr.coordinates import (
    PL1992Coordinate,
    pl1992_to_wgs84,
    wgs84_to_1992,
)
from gps_kataster_obiektow_tatr.data_loader import load_dataset
from gps_kataster_obiektow_tatr.validator import ValidationSeverity as Severity


def _object(object_id: str = "KSW-0001") -> dict:
    record = _valid_object()
    record.update(id=object_id, category="inne", cave_id=None)
    return record


def _attachment(path: str = "https://example.test/report") -> dict:
    return {
        "id": "a-017",
        "kind": "raport_gnss",
        "path": path,
        "created_at": "2026-10-14T10:00:00Z",
        "created_by": "fixture",
    }


def _snapshot(root: Path) -> dict:
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _validate(data_dir: Path, repo_root: Path) -> tuple:
    before = _snapshot(repo_root)
    assert validator.validate_record_schemas(load_dataset(data_dir).records()) == ()
    issues = validator.validate_data_dir(data_dir, repo_root=repo_root)
    assert _snapshot(repo_root) == before
    return issues


def _assert_issues(issues: tuple, expected: list[tuple[str, Severity, Path]]) -> None:
    assert Counter((issue.code, issue.severity, issue.path) for issue in issues) == Counter(
        expected
    )
    expected_error = any(severity == Severity.ERROR for _, severity, _ in expected)
    assert validator.has_errors(issues) is expected_error
    assert validator.exit_code_for_issues(issues) == int(expected_error)


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("second_id", ["{TPN-ALPHA}", "{TPN-BETA}"])
def test_duplicate_typed_globalid_reports_each_owner(
    tmp_path: Path, reverse: bool, second_id: str
) -> None:
    # Missing duplicate iteration, changed key/severity or reporting one owner must fail.
    data_dir = tmp_path / "data"
    records = [_object(), _object("KSW-0002")]
    for record, external_id in zip(records, ("{TPN-ALPHA}", second_id), strict=True):
        record["external_refs"] = [
            {"system": "TPN", "ref_type": "source_globalid", "external_id": external_id}
        ]
    for record in reversed(records) if reverse else records:
        _write_object(data_dir, record)
    issues = _validate(data_dir, tmp_path)
    paths = [data_dir / f"objects/KSW/{record['id']}.yml" for record in records]
    _assert_issues(
        issues,
        [("DUPLICATE_TPN_GLOBALID", Severity.ERROR, p) for p in paths]
        if second_id == "{TPN-ALPHA}"
        else [],
    )
    for issue in issues:
        assert "{TPN-ALPHA}" in issue.description
        assert all(str(path) in issue.description for path in paths)


@pytest.mark.parametrize(
    ("system", "ref_type"), [("inne", "source_globalid"), ("TPN", "other"), ("inne", "other")]
)
@pytest.mark.parametrize("untyped_owner", [0, 1])
def test_equal_value_with_different_system_or_type_is_not_globalid_duplicate(
    tmp_path: Path, system: str, ref_type: str, untyped_owner: int
) -> None:
    # AND -> OR in the typed-reference filter would incorrectly reject this catalog.
    data_dir = tmp_path / "data"
    for index, record in enumerate([_object(), _object("KSW-0002")]):
        record["external_refs"] = [
            {
                "system": system if index == untyped_owner else "TPN",
                "ref_type": ref_type if index == untyped_owner else "source_globalid",
                "external_id": "{SAME-VALUE}",
            }
        ]
        _write_object(data_dir, record)
    _assert_issues(_validate(data_dir, tmp_path), [])


@pytest.mark.parametrize("measurement_ref", ["m-001", "m-777", None, "absent"])
@pytest.mark.parametrize("other_owner", [False, True])
def test_attachment_measurement_reference_is_local_to_its_owner(
    tmp_path: Path, measurement_ref: str | None, other_owner: bool
) -> None:
    # A global lookup or omitted attachment loop would accept another object's m-777.
    data_dir = tmp_path / "data"
    record = _object()
    attachment = _attachment()
    if measurement_ref != "absent":
        attachment["measurement_id"] = measurement_ref
    record["attachments"] = [attachment]
    _write_object(data_dir, record)
    if other_owner:
        other = _object("KSW-0002")
        other["measurements"][0]["id"] = "m-777"
        other["id_assignment"]["assigned_from_measurement_id"] = "m-777"
        other["best_measurement"]["measurement_id"] = "m-777"
        _write_object(data_dir, other)
    issues = _validate(data_dir, tmp_path)
    invalid = measurement_ref == "m-777"
    _assert_issues(
        issues,
        [("ATTACHMENT_MEASUREMENT_MISSING", Severity.ERROR, data_dir / "objects/KSW/KSW-0001.yml")]
        if invalid
        else [],
    )
    if invalid:
        assert "KSW-0001" in issues[0].description
        assert "m-777" in issues[0].description


@pytest.mark.parametrize(
    ("from_id", "to_id", "missing_fields"),
    [
        ("KSW-0001", "KSW-0002", ()),
        ("KSW-7777", "KSW-0002", ("from_object_id",)),
        ("KSW-0001", "KSW-8888", ("to_object_id",)),
        ("KSW-7777", "KSW-8888", ("from_object_id", "to_object_id")),
    ],
)
def test_relation_validates_both_endpoint_objects(
    tmp_path: Path, from_id: str, to_id: str, missing_fields: tuple[str, ...]
) -> None:
    # Dropping either field or the relation loop loses an independently attributable error.
    data_dir = tmp_path / "data"
    for object_id in ("KSW-0001", "KSW-0002"):
        _write_object(data_dir, _object(object_id))
    relation = {
        "schema_version": 1,
        "id": "R-0017",
        "from_object_id": from_id,
        "to_object_id": to_id,
        "relation_type": "sasiad",
    }
    path = data_dir / "relations/R-0017.yml"
    _write_yaml(path, relation)
    issues = _validate(data_dir, tmp_path)
    _assert_issues(
        issues, [("RELATION_OBJECT_REFERENCE_MISSING", Severity.ERROR, path)] * len(missing_fields)
    )
    for field in missing_fields:
        matching = [issue for issue in issues if field in issue.description]
        assert len(matching) == 1
        assert "R-0017" in matching[0].description
        assert relation[field] in matching[0].description


@pytest.mark.parametrize(
    ("url", "valid"),
    [
        ("http://example.test/report", True),
        ("https://example.test/report", True),
        ("HTTPS://example.test/report", True),
        ("ftp://example.test/report", False),
        ("file://example.test/report", False),
        ("http:///report", False),
        ("https:///report", False),
        ("unknown:///report", False),
    ],
)
def test_attachment_url_requires_http_scheme_and_netloc(
    tmp_path: Path, url: str, valid: bool
) -> None:
    # OR or a missing scheme/netloc check must fail, as must wrong URL diagnostics.
    data_dir = tmp_path / "data"
    record = _object()
    record["attachments"] = [_attachment(url)]
    _write_object(data_dir, record)
    issues = _validate(data_dir, tmp_path)
    _assert_issues(
        issues,
        []
        if valid
        else [("ATTACHMENT_URL_INVALID", Severity.ERROR, data_dir / "objects/KSW/KSW-0001.yml")],
    )
    if not valid:
        assert "KSW-0001" in issues[0].description
        assert "a-017" in issues[0].description
        assert url in issues[0].description


@pytest.mark.parametrize("absolute", [False, True])
@pytest.mark.parametrize("exists", [False, True])
def test_local_attachment_path_is_resolved_from_supplied_repo_root(
    tmp_path: Path, absolute: bool, exists: bool
) -> None:
    data_dir = tmp_path / "data"
    local_path = tmp_path / "data/attachments/KSW/KSW-0001/report.txt"
    if exists:
        local_path.parent.mkdir(parents=True)
        local_path.write_text("field report", encoding="utf-8")
    stored_path = str(local_path if absolute else local_path.relative_to(tmp_path))
    record = _object()
    record["attachments"] = [_attachment(stored_path)]
    _write_object(data_dir, record)
    issues = _validate(data_dir, tmp_path)
    _assert_issues(
        issues,
        []
        if exists
        else [("ATTACHMENT_PATH_MISSING", Severity.ERROR, data_dir / "objects/KSW/KSW-0001.yml")],
    )
    if not exists:
        assert "KSW-0001" in issues[0].description
        assert "a-017" in issues[0].description
        assert stored_path in issues[0].description


def _two_measurements(dx: float, dy: float) -> dict:
    record = _object()
    first = record["measurements"][0]
    second = deepcopy(first)
    second["id"] = "m-017"
    point = pl1992_to_wgs84(x_1992=first["x_1992"] + dx, y_1992=first["y_1992"] + dy)
    second["lat"], second["lon"] = point.lat, point.lon
    cached = wgs84_to_1992(lat=point.lat, lon=point.lon)
    second["x_1992"], second["y_1992"] = cached.x_1992, cached.y_1992
    record["measurements"].append(second)
    return record


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    ("dx", "dy", "warning"),
    [(0, 0, False), (99.999, 0, False), (100.001, 0, True), (0, 101, True), (72, 96, True)],
)
def test_measurement_distance_public_validation_with_real_projection(
    tmp_path: Path, reverse: bool, dx: float, dy: float, warning: bool
) -> None:
    # Lost pairs, wrong axis/exponent/threshold, or severity ERROR must fail.
    data_dir = tmp_path / "data"
    record = _two_measurements(dx, dy)
    if reverse:
        record["measurements"].reverse()
    _write_object(data_dir, record)
    issues = _validate(data_dir, tmp_path)
    _assert_issues(
        issues,
        [("MEASUREMENT_DISTANCE_OUTLIER", Severity.WARNING, data_dir / "objects/KSW/KSW-0001.yml")]
        if warning
        else [],
    )
    if warning:
        assert "KSW-0001" in issues[0].description
        assert "m-001" in issues[0].description
        assert "m-017" in issues[0].description


@pytest.mark.parametrize(("dx", "dy", "warning"), [(60, 80, False), (60, 81, True)])
def test_measurement_distance_exact_threshold_excludes_equality(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, dx: float, dy: float, warning: bool
) -> None:
    # Isolate the projection dependency for exactly 100 m without round-trip drift.
    # Schema, consistency, prefix resolution, pair iteration and reporting remain real.
    data_dir = tmp_path / "data"
    record = _two_measurements(72, 96)
    points = {
        (m["lat"], m["lon"]): PL1992Coordinate(x_1992=x, y_1992=y)
        for m, x, y in zip(
            record["measurements"], (300000, 300000 + dx), (500000, 500000 + dy), strict=True
        )
    }

    def projection(*, lat: float, lon: float) -> PL1992Coordinate:
        return points[(lat, lon)]

    monkeypatch.setattr(validator, "wgs84_to_1992", projection)
    _write_object(data_dir, record)
    issues = _validate(data_dir, tmp_path)
    _assert_issues(
        issues,
        [("MEASUREMENT_DISTANCE_OUTLIER", Severity.WARNING, data_dir / "objects/KSW/KSW-0001.yml")]
        if warning
        else [],
    )


def test_duplicate_globalid_after_unique_group_is_still_reported(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    first, second = _object(), _object("KSW-0002")
    first["external_refs"] = [
        {"system": "TPN", "ref_type": "source_globalid", "external_id": "{UNIQUE}"},
        {"system": "TPN", "ref_type": "source_globalid", "external_id": "{DUP}"},
    ]
    second["external_refs"] = [
        {"system": "TPN", "ref_type": "source_globalid", "external_id": "{DUP}"},
    ]
    for record in (first, second):
        _write_object(data_dir, record)
    issues = _validate(data_dir, tmp_path)
    _assert_issues(
        issues,
        [
            ("DUPLICATE_TPN_GLOBALID", Severity.ERROR, data_dir / f"objects/KSW/{object_id}.yml")
            for object_id in ("KSW-0001", "KSW-0002")
        ],
    )
    assert all("{DUP}" in issue.description for issue in issues)


def test_url_attachment_does_not_stop_validation_of_later_local_path(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    record = _object()
    later = _attachment("data/attachments/missing.txt")
    later["id"] = "a-018"
    record["attachments"] = [_attachment(), later]
    _write_object(data_dir, record)
    issues = _validate(data_dir, tmp_path)
    _assert_issues(
        issues, [("ATTACHMENT_PATH_MISSING", Severity.ERROR, data_dir / "objects/KSW/KSW-0001.yml")]
    )
    assert "a-018" in issues[0].description
    assert "data/attachments/missing.txt" in issues[0].description


def test_distance_checks_all_pairs_after_a_close_pair(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    record = _two_measurements(72, 96)  # 120 m from m-001.
    middle = deepcopy(record["measurements"][0])
    middle["id"] = "m-008"  # Same point as m-001; m-001/m-008 is the first close pair.
    record["measurements"].insert(1, middle)
    _write_object(data_dir, record)
    issues = _validate(data_dir, tmp_path)
    _assert_issues(
        issues,
        [("MEASUREMENT_DISTANCE_OUTLIER", Severity.WARNING, data_dir / "objects/KSW/KSW-0001.yml")]
        * 2,
    )
    assert (
        sum("m-001" in issue.description and "m-017" in issue.description for issue in issues) == 1
    )
    assert (
        sum("m-008" in issue.description and "m-017" in issue.description for issue in issues) == 1
    )


def test_missing_best_measurement_reports_error_at_owner(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    record = _object()
    record["best_measurement"].update(
        mode="manual", reason="Operator selects measurement", measurement_id="m-777"
    )
    _write_object(data_dir, record)
    issues = _validate(data_dir, tmp_path)
    _assert_issues(
        issues,
        [("BEST_MEASUREMENT_MISSING", Severity.ERROR, data_dir / "objects/KSW/KSW-0001.yml")],
    )
    assert "KSW-0001" in issues[0].description
    assert "m-777" in issues[0].description


def test_missing_cave_reference_reports_error_at_owner(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    record = _object()
    record["cave_id"] = "C-0777"
    _write_object(data_dir, record)
    issues = _validate(data_dir, tmp_path)
    _assert_issues(
        issues, [("CAVE_REFERENCE_MISSING", Severity.ERROR, data_dir / "objects/KSW/KSW-0001.yml")]
    )
    assert "KSW-0001" in issues[0].description
    assert "C-0777" in issues[0].description


def test_missing_cave_object_reference_reports_error_at_cave(tmp_path: Path) -> None:
    from test_validator import _valid_cave

    data_dir = tmp_path / "data"
    _write_object(data_dir, _object())
    path = data_dir / "caves/C-0001.yml"
    _write_yaml(path, _valid_cave("KSW-7777"))
    issues = _validate(data_dir, tmp_path)
    _assert_issues(issues, [("CAVE_OBJECT_REFERENCE_MISSING", Severity.ERROR, path)])
    assert "C-0001" in issues[0].description
    assert "KSW-7777" in issues[0].description
