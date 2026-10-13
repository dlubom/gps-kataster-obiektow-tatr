"""Typed identities must not route an imported measurement to an unrelated opening."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_staging_review import _cave_data, _object_data, _read_yaml, _write_yaml
from test_tpn_staging import _tpn_row, _write_pig_staging, _write_tpn_csv

from gps_kataster_obiektow_tatr.coordinates import pl1992_to_wgs84
from gps_kataster_obiektow_tatr.staging_review import apply_review_decisions, load_staging_reports
from gps_kataster_obiektow_tatr.tpn_staging import build_tpn_staging, write_staging_files
from gps_kataster_obiektow_tatr.validator import has_errors, validate_data_dir

STAMP = "2026-10-13T10:00:00Z"
GLOBALID = "{TYPED-MATCH}"


def _ref(system: str, ref_type: str, value: str) -> dict[str, str]:
    return {"system": system, "ref_type": ref_type, "external_id": value}


def _pair(root: Path, number: int, *, name: str, nr: str, x: float, y: float) -> Path:
    object_id, cave_id = f"KSW-{number:04d}", f"C-{number:04d}"
    obj = _object_data(cave_id=cave_id)
    obj.update(id=object_id, name_local=name)
    obj["external_refs"] = []
    obj["id_assignment"]["prefix_override_reason"] = "Preserve historical opening ID."
    point = pl1992_to_wgs84(x_1992=x, y_1992=y)
    obj["measurements"][0].update(lat=point.lat, lon=point.lon, x_1992=x, y_1992=y)
    cave = _cave_data(
        object_ids=[object_id], external_refs=[_ref("NR_INWENT", "inventory_number", nr)]
    )
    cave.update(id=cave_id, name=name)
    path = root / f"objects/KSW/{object_id}.yml"
    _write_yaml(path, obj)
    _write_yaml(root / f"caves/{cave_id}.yml", cave)
    return path


def _snapshot(root: Path) -> dict[Path, bytes]:
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _source(root: Path, *, nr: str = "T.RIGHT-02", name: str = "Corrected opening") -> Path:
    path = root / "tpn.csv"
    _write_tpn_csv(
        path,
        [
            _tpn_row(
                nr_inwent=nr, name=name, globalid=GLOBALID, x_1992="152267,23", y_1992="563744,25"
            )
        ],
    )
    return path


def _review(root: Path, report, data_dir: Path, decisions: list[dict]) -> None:
    path, _ = write_staging_files(report, output_dir=root / "staging")
    reports = load_staging_reports(pig_staging_path=None, tpn_staging_path=path)
    before = _snapshot(data_dir)
    report_before = deepcopy(reports.tpn)
    document = {"reviewed_at": STAMP, "reviewed_by": "dl", "decisions": decisions}
    dry = apply_review_decisions(document, staging_reports=reports, data_dir=data_dir, write=False)
    assert not dry.has_errors, dry.issues
    assert dry.written_paths == ()
    assert _snapshot(data_dir) == before
    result = apply_review_decisions(document, staging_reports=reports, data_dir=data_dir)
    assert not result.has_errors, result.issues
    assert result.written_paths
    assert reports.tpn == report_before
    assert not has_errors(validate_data_dir(data_dir))


@pytest.mark.parametrize("reverse_candidates", [False, True])
@pytest.mark.parametrize(
    "system, ref_type",
    [
        ("TPN", "other"),
        ("TPN", "url"),
        ("TPN", "source_row"),
        ("TPN", "inventory_number"),
        ("TPN", "catalog_id"),
        ("inne", "source_globalid"),
        ("TPN", "source_globalid"),
    ],
)
def test_only_typed_globalid_routes_measurement_and_preserves_other_opening(
    tmp_path: Path, system: str, ref_type: str, reverse_candidates: bool
) -> None:
    # Removing either part of the identity filter sends the measurement 1414 m away.
    data = tmp_path / "data"
    wrong_number, right_number = (2, 1) if reverse_candidates else (1, 2)
    wrong = _pair(
        data, wrong_number, name="Original opening", nr="T.OLD-01", x=153267.23, y=564744.25
    )
    right = _pair(
        data, right_number, name="Corrected opening", nr="T.RIGHT-02", x=152267.23, y=563744.25
    )
    obj = _read_yaml(wrong)
    obj["external_refs"] = [_ref(system, ref_type, GLOBALID)]
    _write_yaml(wrong, obj)
    assert not has_errors(validate_data_dir(data))
    before = _snapshot(data)
    report = build_tpn_staging(
        _source(tmp_path), generated_at=STAMP, data_dir=data, pig_staging_path=None
    )
    assert _snapshot(data) == before
    typed = (system, ref_type) == ("TPN", "source_globalid")
    target, untouched = (wrong, right) if typed else (right, wrong)
    target_id = target.stem
    row = report.rows[0]
    assert (row.status, row.object_id, row.match_strategy) == (
        "matched",
        target_id,
        "globalid" if typed else "nr_inwent",
    )
    assert row.distance_m == pytest.approx(2**0.5 * 1000 if typed else 0)
    assert report.matched_measurements[0]["target_object_id"] == target_id
    _review(
        tmp_path, report, data, [{"action": "add_measurement", "source": "TPN", "record_number": 1}]
    )
    saved = _read_yaml(target)
    assert [m["id"] for m in saved["measurements"]] == ["m-001", "m-002"]
    assert saved["measurements"][1]["source_ref"] == f"TPN:{GLOBALID}"
    assert saved["measurements"][1]["x_1992"] == 152267.23
    assert saved["measurements"][1]["y_1992"] == 563744.25
    if typed:
        assert saved["external_refs"] == obj["external_refs"]
    else:
        assert saved["external_refs"] == [
            {
                "system": "TPN",
                "ref_type": "source_globalid",
                "external_id": GLOBALID,
                "scope": "object",
                "notes": "TPN GLOBALID belongs to the object/source feature.",
            }
        ]
    assert untouched.read_bytes() == before[untouched.relative_to(data)]
    untouched_cave = data / f"caves/C-{untouched.stem.split('-')[1]}.yml"
    assert untouched_cave.read_bytes() == before[untouched_cave.relative_to(data)]
    for old in before:
        if old != target.relative_to(data) and old != Path(
            f"caves/C-{target_id.split('-')[1]}.yml"
        ):
            assert (data / old).read_bytes() == before[old]


@pytest.mark.parametrize(
    "ref_type, expected", [("other", "new"), ("source_row", "new"), ("source_globalid", "matched")]
)
def test_pig_staging_candidate_uses_typed_globalid(
    tmp_path: Path, ref_type: str, expected: str
) -> None:
    # The staging loader must use the same filter as final YAML.
    pig = tmp_path / "pig.json"
    _write_pig_staging(
        pig,
        object_id="KSW-0001",
        cave_id="C-0001",
        nr_inwent="T.OLD-01",
        name="Original opening",
        x_1992=153267.23,
        y_1992=564744.25,
    )
    content = json.loads(pig.read_text())
    content["proposed_objects"][0]["external_refs"] = [_ref("TPN", ref_type, GLOBALID)]
    pig.write_text(json.dumps(content))
    before = pig.read_bytes()
    data = tmp_path / "data"
    data.mkdir()
    report = build_tpn_staging(
        _source(tmp_path), generated_at=STAMP, data_dir=data, pig_staging_path=pig
    )
    assert report.rows[0].status == expected
    assert report.rows[0].match_strategy == ("globalid" if expected == "matched" else None)
    assert pig.read_bytes() == before
    assert _snapshot(data) == {}


@pytest.mark.parametrize("reverse_refs", [False, True])
@pytest.mark.parametrize("nr, expected", [("T.UNRELATED", "new"), ("T.RIGHT-02", "matched")])
def test_inventory_other_is_not_a_number_and_does_not_hide_typed_number(
    tmp_path: Path, nr: str, expected: str, reverse_refs: bool
) -> None:
    # Taking the first ref of the system both invents an identity and hides the real number.
    data = tmp_path / "data"
    old = _pair(data, 1, name="Original opening", nr="T.RIGHT-02", x=153267.23, y=564744.25)
    cave_path = data / "caves/C-0001.yml"
    cave = _read_yaml(cave_path)
    refs = [_ref("NR_INWENT", "other", "T.UNRELATED"), *cave["external_refs"]]
    cave["external_refs"] = list(reversed(refs)) if reverse_refs else refs
    _write_yaml(cave_path, cave)
    assert not has_errors(validate_data_dir(data))
    before = _snapshot(data)
    report = build_tpn_staging(
        _source(tmp_path, nr=nr), generated_at=STAMP, data_dir=data, pig_staging_path=None
    )
    assert report.rows[0].status == expected
    assert _snapshot(data) == before
    if expected == "new":
        assert report.rows[0].object_id == "KSW-0002"
        _review(
            tmp_path,
            report,
            data,
            [
                {"action": a, "source": "TPN", "record_number": 1}
                for a in ("create_cave", "create_object")
            ],
        )
        assert old.read_bytes() == before[old.relative_to(data)]
        assert cave_path.read_bytes() == before[cave_path.relative_to(data)]
        assert (
            _read_yaml(data / "objects/KSW/KSW-0002.yml")["measurements"][0]["source_ref"]
            == f"TPN:{GLOBALID}"
        )
    else:
        assert (report.rows[0].object_id, report.rows[0].match_strategy) == (
            "KSW-0001",
            "nr_inwent",
        )
        _review(
            tmp_path,
            report,
            data,
            [{"action": "add_measurement", "source": "TPN", "record_number": 1}],
        )
        assert _read_yaml(cave_path)["external_refs"] == cave["external_refs"]
        assert _read_yaml(old)["measurements"][-1]["source_ref"] == f"TPN:{GLOBALID}"


@pytest.mark.parametrize("ref_type", ["url", "other", "catalog_id"])
@pytest.mark.parametrize("has_pig_measurement", [False, True])
def test_pig_refs_do_not_replace_measurement_provenance_in_candidate_deduplication(
    tmp_path: Path, ref_type: str, has_pig_measurement: bool
) -> None:
    # A PIG/url or PIG/other equality is never proof that the two object IDs share provenance.
    data = tmp_path / "data"
    path = _pair(data, 1, name="Original opening", nr="T.RIGHT-02", x=152267.23, y=563744.25)
    obj = _read_yaml(path)
    if has_pig_measurement:
        obj["measurements"][0].update(source="PIG", source_ref="PIG:1692")
    _write_yaml(path, obj)
    cave_path = data / "caves/C-0001.yml"
    cave = _read_yaml(cave_path)
    cave["external_refs"].append(_ref("PIG", ref_type, "1692"))
    _write_yaml(cave_path, cave)
    assert not has_errors(validate_data_dir(data))
    pig = tmp_path / "pig.json"
    _write_pig_staging(
        pig,
        object_id="KSW-0001",
        cave_id="C-0001",
        nr_inwent="T.RIGHT-02",
        name="Historical PIG opening",
        x_1992=153267.23,
        y_1992=564744.25,
    )
    before = _snapshot(tmp_path)
    source = _source(tmp_path)
    if has_pig_measurement:
        report = build_tpn_staging(source, generated_at=STAMP, data_dir=data, pig_staging_path=pig)
        assert (report.rows[0].status, report.rows[0].object_id) == ("matched", "KSW-0001")
        assert report.matched_measurements[0]["match"]["source"] == "data_yaml"
        assert report.matched_measurements[0]["measurement"]["id"] == "m-002"
    else:
        with pytest.raises(ValueError, match="conflicting or unverified PIG provenance"):
            build_tpn_staging(source, generated_at=STAMP, data_dir=data, pig_staging_path=pig)
    assert _snapshot(data) == {
        p.relative_to("data"): v for p, v in before.items() if p.parts[0] == "data"
    }
    assert pig.read_bytes() == before[Path("pig.json")]
