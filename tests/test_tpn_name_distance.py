"""Public TPN staging regressions for matching without a shared source identity."""

import json
from copy import deepcopy

import pytest
from test_staging_review import _cave_data, _object_data, _write_yaml
from test_tpn_staging import StubResolver, _tpn_header, _tpn_row, _write_tpn_csv

from gps_kataster_obiektow_tatr.coordinates import pl1992_to_wgs84
from gps_kataster_obiektow_tatr.tpn_staging import build_tpn_staging

NAME = "Jaskinia Śnieżna-II"
SOURCE_NAME = "  JASKINIA SNIEZNA / II  "
X, Y = 152000, 563000


def _candidate(number, *, name=NAME, offsets=((3, 4),), nr="", refs=()):
    """Real YAML/proposal input; coordinates are specified independently in metres."""
    cave_id, object_id = f"C-{number:04d}", f"KSW-{number:04d}"
    obj = _object_data(cave_id=cave_id)
    obj.update(id=object_id, name_local=name, external_refs=list(refs))
    template = obj["measurements"][0]
    measurements = []
    for index, (dx, dy) in enumerate(offsets, start=1):
        m = deepcopy(template)
        coordinate = pl1992_to_wgs84(x_1992=X + dx, y_1992=Y + dy)
        m.update(
            id=f"m-{index:03d}",
            x_1992=X + dx,
            y_1992=Y + dy,
            lat=coordinate.lat,
            lon=coordinate.lon,
        )
        measurements.append(m)
    obj["measurements"] = measurements
    cave = _cave_data(object_ids=[object_id])
    cave.update(id=cave_id, name="Different catalog name")
    if nr:
        cave["external_refs"] = [_ref("NR_INWENT", "inventory_number", nr)]
    return obj, cave, nr


def _ref(system, ref_type, value="{ROW}"):
    return dict(system=system, ref_type=ref_type, external_id=value)


def _build(tmp_path, candidates, *, origin="final", rows=None, radius=25):
    data_dir, pig = tmp_path / "data", tmp_path / "pig.json"
    if origin == "final":
        for obj, cave, _ in candidates:
            _write_yaml(data_dir / f"objects/KSW/{obj['id']}.yml", obj)
            _write_yaml(data_dir / f"caves/{cave['id']}.yml", cave)
    else:
        pig.write_text(
            json.dumps(
                dict(
                    proposed_objects=[obj for obj, _, _ in candidates],
                    rows=[
                        dict(
                            object_id=obj["id"],
                            cave_id=cave["id"],
                            nr_inwent=nr,
                            name=obj["name_local"],
                            pig_id="",
                        )
                        for obj, cave, nr in candidates
                    ],
                )
            )
        )
    source = tmp_path / "tpn.csv"
    _write_tpn_csv(
        source,
        rows
        or [
            _tpn_row(nr_inwent="", name=SOURCE_NAME, globalid="{ROW}", x_1992=str(X), y_1992=str(Y))
        ],
    )
    inputs = [p for p in tmp_path.rglob("*") if p.is_file()]
    before = {p: p.read_bytes() for p in inputs}
    report = build_tpn_staging(
        source,
        generated_at="2026-10-14T08:00:00Z",
        data_dir=data_dir,
        pig_staging_path=pig if origin == "pig" else None,
        prefix_resolver=StubResolver(),
        duplicate_radius_m=radius,
    )
    assert {p: p.read_bytes() for p in inputs} == before
    assert {p for p in tmp_path.rglob("*") if p.is_file()} == set(inputs)
    return report


def _assert_match(report, *, object_id, strategy, distance, source="data_yaml", mid="m-002"):
    assert len(report.rows) == len(report.matched_measurements) == 1
    assert report.proposed_objects == report.proposed_caves == ()
    row = report.rows[0]
    assert row.status == "matched"
    assert row.object_id == object_id
    assert row.cave_id == "C-" + object_id.split("-")[1]
    assert row.match_strategy == strategy
    assert row.distance_m == pytest.approx(distance)
    assert row.payload is None
    update = report.matched_measurements[0]
    assert update["target_object_id"] == row.object_id
    assert update["target_cave_id"] == row.cave_id
    assert update["match"] == dict(source=source, strategy=strategy, distance_m=row.distance_m)
    assert update["measurement"]["id"] == mid
    assert update["measurement"]["source"] == "TPN"
    assert update["measurement"]["source_ref"] == "TPN:{ROW}"
    assert (update["measurement"]["x_1992"], update["measurement"]["y_1992"]) == (X, Y)


@pytest.mark.parametrize("origin", ["final", "pig"])
@pytest.mark.parametrize("target_number", [1, 3])
@pytest.mark.parametrize("reverse_history", [False, True])
def test_name_distance_uses_named_best_in_either_history_order(
    tmp_path, origin, target_number, reverse_history
):
    # Removing the name/radius conjunction, or ignoring explicit best, chooses a decoy.
    target = _candidate(target_number, offsets=((100, 0), (3, 4), (0, 200)))
    target[0]["best_measurement"].update(mode="manual", measurement_id="m-002", reason="GNSS")
    if reverse_history:
        target[0]["measurements"].reverse()
    others = [n for n in (1, 2, 3) if n != target_number]
    candidates = [
        _candidate(others[0], name="Different opening", offsets=((0, 0),)),
        target,
        _candidate(others[1], offsets=((0, 26),)),
    ]
    if target_number == 3:
        candidates.reverse()
    report = _build(tmp_path, candidates, origin=origin)
    _assert_match(
        report,
        object_id=f"KSW-{target_number:04d}",
        strategy="name_distance",
        distance=5,
        source="data_yaml" if origin == "final" else "pig_staging",
        mid="m-004",
    )
    assert report.issues == ()


@pytest.mark.parametrize("origin", ["final", "pig"])
@pytest.mark.parametrize("reverse", [False, True])
def test_close_historical_measurement_cannot_override_best_outside_radius(
    tmp_path, origin, reverse
):
    candidate = _candidate(1, offsets=((0, 0), (30, 40)))
    candidate[0]["best_measurement"].update(mode="manual", measurement_id="m-002", reason="GNSS")
    if reverse:
        candidate[0]["measurements"].reverse()
    report = _build(tmp_path, [candidate], origin=origin)
    assert report.rows[0].status == "new"
    assert report.rows[0].object_id == "KSW-0002"
    assert report.matched_measurements == ()
    assert len(report.proposed_objects) == len(report.proposed_caves) == 1


@pytest.mark.parametrize("origin", ["final", "pig"])
@pytest.mark.parametrize(
    ("offset", "radius", "status"),
    [
        ((15, 20), 25, "matched"),
        ((15, 19.999), 25, "matched"),
        ((15, 20.001), 25, "new"),
        ((3, 4), 4.999, "new"),
        ((3, 4), 5, "matched"),
        ((0, 0), 0, "matched"),
    ],
)
def test_name_distance_includes_exact_radius_and_obeys_custom_radius(
    tmp_path, origin, offset, radius, status
):
    report = _build(tmp_path, [_candidate(1, offsets=(offset,))], origin=origin, radius=radius)
    assert report.rows[0].status == status
    if status == "matched":
        assert report.rows[0].object_id == "KSW-0001"
        assert report.rows[0].match_strategy == "name_distance"
        assert len(report.matched_measurements) == 1
        assert report.proposed_objects == report.proposed_caves == ()
    else:
        assert report.matched_measurements == ()
        assert len(report.proposed_objects) == len(report.proposed_caves) == 1
        assert report.rows[0].object_id == "KSW-0002"
        assert report.rows[0].match_strategy is None


@pytest.mark.parametrize("origin", ["final", "pig"])
@pytest.mark.parametrize("kind", ["different_name", "empty_normalized_name", "no_candidates"])
def test_nearby_or_empty_names_alone_do_not_match(tmp_path, origin, kind):
    candidates = (
        []
        if kind == "no_candidates"
        else [_candidate(1, name="!!!" if kind == "empty_normalized_name" else "Another cave")]
    )
    rows = [
        _tpn_row(
            nr_inwent="",
            name="???" if kind == "empty_normalized_name" else NAME,
            globalid="{ROW}",
            x_1992=str(X),
            y_1992=str(Y),
        )
    ]
    report = _build(tmp_path, candidates, origin=origin, rows=rows)
    assert report.rows[0].status == "new"
    assert report.rows[0].match_strategy is report.rows[0].payload is None
    assert report.matched_measurements == ()
    assert len(report.proposed_objects) == len(report.proposed_caves) == 1
    assert report.proposed_objects[0]["measurements"][0]["source_ref"] == "TPN:{ROW}"


@pytest.mark.parametrize("origin", ["final", "pig"])
@pytest.mark.parametrize("reverse", [False, True])
def test_two_name_distance_candidates_remain_unresolved_even_when_one_is_nearer(
    tmp_path, origin, reverse
):
    candidates = [_candidate(1), _candidate(2, offsets=((6, 8),))]
    if reverse:
        candidates.reverse()
    report = _build(tmp_path, candidates, origin=origin)
    assert report.rows[0].status == "unresolved"
    assert report.rows[0].object_id is report.rows[0].cave_id is None
    assert report.rows[0].match_strategy is report.rows[0].distance_m is None
    assert report.matched_measurements == report.proposed_objects == report.proposed_caves == ()
    assert [issue.code for issue in report.issues] == ["TPN_NAME_DISTANCE_AMBIGUOUS"]
    payload = report.rows[0].payload
    assert payload["measurement"]["source_ref"] == "TPN:{ROW}"
    assert "id" not in payload["measurement"]
    assert (payload["measurement"]["x_1992"], payload["measurement"]["y_1992"]) == (X, Y)
    assert payload["category"] == "jaskinia_otwor"
    assert payload["cave_external_refs"] == []
    assert payload["object_external_refs"][0]["external_id"] == "{ROW}"


@pytest.mark.parametrize("origin", ["final", "pig"])
@pytest.mark.parametrize("stronger", ["globalid", "nr_inwent"])
def test_stronger_reference_precedes_closer_name_distance(tmp_path, origin, stronger):
    refs = [_ref("TPN", "source_globalid")] if stronger == "globalid" else []
    target = _candidate(
        1,
        name="Different old name",
        offsets=((300, 400),),
        nr="T.1" if stronger == "nr_inwent" else "",
        refs=refs,
    )
    rows = [_tpn_row(nr_inwent="T.1", name=NAME, globalid="{ROW}", x_1992=str(X), y_1992=str(Y))]
    report = _build(tmp_path, [target, _candidate(2)], origin=origin, rows=rows)
    _assert_match(
        report,
        object_id="KSW-0001",
        strategy=stronger,
        distance=500,
        source="data_yaml" if origin == "final" else "pig_staging",
    )
    assert [issue.code for issue in report.issues] == ["TPN_MATCH_DISTANCE_REVIEW"]


@pytest.mark.parametrize(
    ("system", "ref_type", "level", "value"),
    [
        ("TPN", "other", "object", "{ROW}"),
        ("inne", "source_globalid", "object", "{ROW}"),
        ("NR_INWENT", "other", "cave", "T.1"),
        ("inne", "inventory_number", "cave", "T.1"),
    ],
)
def test_same_value_in_wrong_reference_pair_does_not_mask_name_distance(
    tmp_path, system, ref_type, level, value
):
    decoy = _candidate(1, name="Unrelated", offsets=((300, 400),))
    decoy[0 if level == "object" else 1]["external_refs"] = [_ref(system, ref_type, value)]
    rows = [_tpn_row(nr_inwent="T.1", name=NAME, globalid="{ROW}", x_1992=str(X), y_1992=str(Y))]
    report = _build(tmp_path, [decoy, _candidate(2)], rows=rows)
    _assert_match(report, object_id="KSW-0002", strategy="name_distance", distance=5)
    assert report.issues == ()


@pytest.mark.parametrize("origin", ["final", "pig"])
@pytest.mark.parametrize(
    ("names", "offsets", "strategy", "issue"),
    [
        ((NAME, "Other"), ((3, 4), (6, 8)), "nr_inwent_name_distance", None),
        ((NAME, "Other"), ((15, 20), (30, 40)), "nr_inwent_name_distance", None),
        (("Other", NAME), ((3, 4), (30, 40)), "nr_inwent_distance", None),
        (("Other", "Other"), ((3, 4), (6, 8)), None, "TPN_NR_INWENT_AMBIGUOUS"),
        ((NAME, "Other"), ((30, 40), (60, 80)), None, "TPN_NR_INWENT_AMBIGUOUS"),
    ],
)
def test_inventory_ambiguity_requires_one_close_name_or_one_close_candidate(
    tmp_path, origin, names, offsets, strategy, issue
):
    candidates = [
        _candidate(n, name=name, offsets=(offset,), nr="T.1")
        for n, name, offset in zip((1, 2), names, offsets, strict=True)
    ]
    # The unrelated perfect fallback must not override an unresolved inventory identity.
    candidates.append(_candidate(3, offsets=((0, 0),)))
    rows = [_tpn_row(nr_inwent="T.1", name=NAME, globalid="{ROW}", x_1992=str(X), y_1992=str(Y))]
    report = _build(tmp_path, candidates, origin=origin, rows=rows)
    if strategy:
        _assert_match(
            report,
            object_id="KSW-0001",
            strategy=strategy,
            distance=25 if offsets[0] == (15, 20) else 5,
            source="data_yaml" if origin == "final" else "pig_staging",
        )
        assert report.issues == ()
    else:
        assert report.rows[0].status == "unresolved"
        assert report.rows[0].object_id is None
        assert report.rows[0].payload["measurement"]["source_ref"] == "TPN:{ROW}"
        assert report.matched_measurements == report.proposed_objects == report.proposed_caves == ()
        assert [i.code for i in report.issues] == [issue]


@pytest.mark.parametrize("status", ["new", "unresolved"])
@pytest.mark.parametrize(
    ("name", "genesis", "category"),
    [
        ("Nowy obiekt", "", "jaskinia_otwor"),
        ("Nowy obiekt", "SZTOLNIA", "sztolnia"),
        ("Sztolnia Dolna", "ponor", "sztolnia"),
        ("Nowy obiekt", "WYwierzysko", "wywierzysko"),
        ("Obcasna Vyvieracka", "", "wywierzysko"),
        ("Mala Wyvieracka", "", "wywierzysko"),
        ("Ponor pod Skałą", "", "ponor"),
        ("Nowy obiekt", "PONOR", "ponor"),
    ],
)
def test_new_and_unresolved_payload_preserves_category_from_name_or_genesis(
    tmp_path, status, name, genesis, category
):
    candidates = (
        [_candidate(1, name=name), _candidate(2, name=name)] if status == "unresolved" else []
    )
    row = _tpn_row(nr_inwent="", name=name, globalid="{ROW}", x_1992=str(X), y_1992=str(Y))
    row[_tpn_header().index("GENEZA")] = genesis
    report = _build(tmp_path, candidates, rows=[row])
    assert report.rows[0].status == status
    assert report.matched_measurements == ()
    if status == "new":
        assert len(report.proposed_objects) == 1
        assert report.proposed_objects[0]["category"] == category
        assert report.proposed_objects[0]["name_local"] == name
    else:
        assert report.proposed_objects == report.proposed_caves == ()
        assert report.rows[0].payload["category"] == category


@pytest.mark.parametrize("origin", ["final", "pig"])
@pytest.mark.parametrize("outside", [False, True])
def test_repeated_source_inventory_needs_name_and_radius_for_each_row(tmp_path, origin, outside):
    candidates = [
        _candidate(1, nr="T.1", offsets=((15, 20.001 if outside else 20),)),
        _candidate(2, nr="T.1", name="Another cave", offsets=((0, 0),)),
    ]
    rows = [
        _tpn_row(nr_inwent="T.1", name=name, globalid=gid, x_1992=str(X), y_1992=str(Y))
        for name, gid in ((NAME, "{ROW}"), ("Another cave", "{ROW-2}"))
    ]
    report = _build(tmp_path, candidates, origin=origin, rows=rows)
    first, second = report.rows
    assert second.status == "matched"
    assert second.object_id == "KSW-0002"
    assert second.match_strategy == "nr_inwent_name_distance"
    assert second.distance_m == 0
    assert first.status == ("unresolved" if outside else "matched")
    assert first.object_id == (None if outside else "KSW-0001")
    if outside:
        assert len(report.matched_measurements) == 1
        assert first.payload["measurement"]["source_ref"] == "TPN:{ROW}"
        assert [i.code for i in report.issues] == ["TPN_NR_INWENT_AMBIGUOUS"]
    else:
        assert first.match_strategy == "nr_inwent_name_distance"
        assert first.distance_m == 25
        assert len(report.matched_measurements) == 2
        assert report.issues == ()
    assert report.proposed_objects == report.proposed_caves == ()


@pytest.mark.parametrize(
    ("local", "catalog", "status"),
    [
        (None, NAME, "matched"),
        ("", NAME, "matched"),
        ("Different opening", NAME, "new"),
        (NAME, "Different cave", "matched"),
    ],
)
def test_local_name_precedes_catalog_name_with_catalog_fallback(tmp_path, local, catalog, status):
    candidate = _candidate(1, name=local)
    candidate[1]["name"] = catalog
    report = _build(tmp_path, [candidate])
    assert report.rows[0].status == status
    if status == "matched":
        _assert_match(report, object_id="KSW-0001", strategy="name_distance", distance=5)
    else:
        assert report.matched_measurements == ()
        assert report.rows[0].object_id == "KSW-0002"


@pytest.mark.parametrize("origin", ["final", "pig"])
@pytest.mark.parametrize("axis", ["x_1992", "y_1992"])
def test_name_match_without_both_cached_coordinates_cannot_supply_distance(tmp_path, origin, axis):
    candidate = _candidate(1)
    del candidate[0]["measurements"][0][axis]
    report = _build(tmp_path, [candidate], origin=origin)
    assert report.rows[0].status == "new"
    assert report.matched_measurements == ()
    assert report.rows[0].object_id == "KSW-0002"
    assert len(report.proposed_objects) == len(report.proposed_caves) == 1
