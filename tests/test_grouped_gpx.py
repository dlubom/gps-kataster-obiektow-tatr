import re
import subprocess
import sys
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from export_test_support import GENERATED_AT, REPO_ROOT, accept_source, cli_args, initialize_source
from export_test_support import valid_object as _valid_object
from export_test_support import write_yaml as _write_yaml
from spatial_test_support import spatial_reference

from gps_kataster_obiektow_tatr.best_measurements_export import export_best_measurements

NS = "{http://www.topografix.com/GPX/1/1}"
FILENAMES = (
    "chocholowska-lejowa-koscieliska.gpx",
    "mietusia-sucha-woda.gpx",
    "pozostale-pl-sk.gpx",
)
# Independently selected interior points, in the approved group order. Durable IDs
# deliberately all start with KSW; older measurements all lie in Kościeliska.
LOCATIONS = (
    (49.24981322930804, 19.82256851112177),  # CHW
    (49.24292968802665, 19.806130945081946),  # CHZ
    (49.244165754644584, 19.839172566713174),  # LEJ
    (49.23459299308732, 19.875894982052095),  # KSW
    (49.239315636683756, 19.863189293753656),  # KSZ
    (49.24462826849196, 19.91258404819056),  # MTW
    (49.237925581626655, 19.90220458612156),  # MTZ
    (49.2666593976219, 19.879525694441938),  # STN
    (49.24999733238851, 19.92762228747166),  # MLW
    (49.24183330022517, 19.92359727062113),  # MLZ
    (49.266425199840825, 19.920063987182818),  # BRA
    (49.25232552039737, 19.939079942384442),  # STR
    (49.271543392325505, 19.94330632613412),  # DZI
    (49.26496874735799, 19.957180619196247),  # BIA
    (49.25111123895918, 19.99651954217368),  # BYW
    (49.2529932816009, 19.972692010128018),  # BYZ
    (49.26544348039321, 20.002141759198842),  # OLC
    (49.21891641697399, 20.01533247779099),  # SUW
    (49.273938062927, 20.077136282212635),  # PL outside valleys
    (49.22918839, 19.91418777),  # SK outside valleys
)


def _write_points(data: Path, locations: tuple[tuple[float, float], ...]) -> None:
    initialize_source(data)
    for i, (lat, lon) in enumerate(locations, 1):
        obj = deepcopy(_valid_object(notes=True))
        obj["id"] = f"KSW-{i:04d}"
        obj.pop("cave_id")
        obj.pop("membership_ordinal")
        obj["external_refs"] = []
        obj["id_assignment"].update(
            method="manual", prefix_override_reason="Historical durable ID retained."
        )
        obj["name_local"] = "Żółta <jaskinia> & wspólna nazwa"
        obj["measurements"][1].update(lat=lat, lon=lon)
        _write_yaml(data / "objects/KSW" / f"{obj['id']}.yml", obj)
    return accept_source(data)


def _waypoints(path: Path) -> dict[str, bytes]:
    points = {}
    for point in ET.parse(path).findall(NS + "wpt"):
        identity = re.search(r"object (KSW-\d+)", point.findtext(NS + "desc") or "")
        assert identity is not None
        object_id = identity.group(1)
        assert object_id not in points
        point.tail = None
        points[object_id] = ET.tostring(point)
    return points


def test_groups_use_selected_location_and_keep_all_waypoint_fields(tmp_path):
    data = tmp_path / "data"
    baseline = _write_points(data, LOCATIONS)
    result = export_best_measurements(
        **baseline, data_dir=data, output_dir=tmp_path / "exports", generated_at=GENERATED_AT
    )
    full = _waypoints(result.gpx_path)
    assert len(full) == 20
    expected_ids = (
        {f"KSW-{i:04d}" for i in range(1, 6)},
        {f"KSW-{i:04d}" for i in range(6, 19)},
        {"KSW-0019", "KSW-0020"},
    )
    actual = {}
    for filename, ids in zip(FILENAMES, expected_ids, strict=True):
        path = result.output_dir / filename
        assert path.exists(), f"Missing additional GPX: {filename}"
        group = _waypoints(path)
        assert set(group) == ids
        assert not set(actual) & set(group)
        assert all(point == full[key] for key, point in group.items())
        assert ET.parse(path).findtext(NS + "metadata/" + NS + "time") == GENERATED_AT
        actual.update(group)
    assert actual == full
    assert result.grouped_gpx_paths == tuple(result.output_dir / name for name in FILENAMES)


def test_empty_catalog_still_writes_full_and_three_empty_gpx(tmp_path):
    data = tmp_path / "data"
    baseline = _write_points(data, ())
    result = export_best_measurements(**baseline, data_dir=data, output_dir=tmp_path / "exports")
    for name in ("best-measurements.gpx", *FILENAMES):
        path = result.output_dir / name
        assert path.exists(), f"Missing GPX for empty catalog: {name}"
        assert ET.parse(path).getroot().tag == NS + "gpx"
        assert _waypoints(path) == {}


@pytest.mark.parametrize(
    ("location", "filename"),
    [(LOCATIONS[3], FILENAMES[0]), (LOCATIONS[5], FILENAMES[1]), (LOCATIONS[19], FILENAMES[2])],
)
def test_exactly_500_points_fit_without_truncation(tmp_path, location, filename):
    data = tmp_path / "data"
    baseline = _write_points(data, (location,) * 500)
    result = export_best_measurements(**baseline, data_dir=data, output_dir=tmp_path / "exports")
    group = result.output_dir / filename
    assert group.exists(), "Missing additional GPX for a group at the limit"
    assert len(_waypoints(group)) == len(_waypoints(result.gpx_path)) == 500


@pytest.mark.parametrize(
    ("location", "filename"),
    [(LOCATIONS[3], FILENAMES[0]), (LOCATIONS[5], FILENAMES[1]), (LOCATIONS[19], FILENAMES[2])],
)
def test_501_points_fail_before_overwriting_exports_and_cli_reports_the_group(
    tmp_path, location, filename
):
    data = tmp_path / "data"
    previous_data = tmp_path / "previous-data"
    previous_baseline = _write_points(previous_data, (LOCATIONS[3],))
    output = tmp_path / "exports"
    export_best_measurements(
        **previous_baseline, data_dir=previous_data, output_dir=output, generated_at=GENERATED_AT
    )
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    baseline = _write_points(data, (location,) * 501)
    with pytest.raises(ValueError, match=rf"{re.escape(filename)}.*501.*500"):
        export_best_measurements(**baseline, data_dir=data, output_dir=output)
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    for script, extra in (
        ("export_best_measurements.py", []),
        ("build_release_artifacts.py", []),
    ):
        command = [
            sys.executable,
            str(REPO_ROOT / "scripts" / script),
            "--data-dir",
            str(data),
            "--output-dir",
            str(output),
            *extra,
            *cli_args(baseline),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        assert completed.returncode == 1
        assert filename in completed.stderr
        assert "501" in completed.stderr and "500" in completed.stderr
        assert "Traceback" not in completed.stderr
        assert before == {p.name: p.read_bytes() for p in output.iterdir()}


def test_full_gpx_keeps_more_than_500_points_across_groups(tmp_path):
    data = tmp_path / "data"
    baseline = _write_points(data, (LOCATIONS[3],) * 500 + (LOCATIONS[5],))
    result = export_best_measurements(**baseline, data_dir=data, output_dir=tmp_path / "exports")
    assert len(_waypoints(result.gpx_path)) == 501
    assert [len(_waypoints(result.output_dir / name)) for name in FILENAMES] == [500, 1, 0]


def test_cli_reports_full_and_all_additional_gpx(tmp_path):
    data = tmp_path / "data"
    baseline = _write_points(data, LOCATIONS)
    command = [
        sys.executable,
        str(REPO_ROOT / "scripts/export_best_measurements.py"),
        "--data-dir",
        str(data),
        "--output-dir",
        str(tmp_path / "exports"),
    ]
    command += cli_args(baseline)
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    for filename in ("best-measurements.gpx", *FILENAMES):
        assert filename in completed.stdout


# Source EPSG:2180 coordinates, with independent expected regions/groups. The
# first valley has a hole; the second overlaps it but follows it in ordinal.
SPATIAL_CASES = (
    (560001, 150001, "MTW", 1),  # interior
    (560000, 150005, "MTW", 1),  # outer edge
    (560000, 150000, "MTW", 1),  # outer vertex
    (560004, 150004, "PL", 2),  # hole interior
    (560002, 150005, "MTW", 1),  # hole edge: ST_Covers includes the boundary
    (560009, 150009, "MTW", 1),  # overlap: first ordinal wins
    (560015, 150015, "KSW", 0),  # second valley only
    (560025, 150025, "PL", 2),  # outside valleys, both countries: PL first
    (560050, 150005, "SK", 2),  # SK only
    (560100, 150005, None, None),  # no region
)


def _spatial_source(root, make_canonical_data_dir, cases):
    # Author canonical YAML directly. No validator, converter or writer runs
    # before the production API under test. Each manual Best is the older PIG
    # point; auto Best and the durable KSW ID point to the other valley.
    data = make_canonical_data_dir(root / "data")
    for directory in ("caves", "relations", "publications"):
        (data / directory / ".gitkeep").touch()
    for i, (x, y, _, _) in enumerate(cases, 1):
        obj = _valid_object(notes=True)
        obj["id"] = f"KSW-{i:04d}"
        obj.pop("cave_id")
        obj.pop("membership_ordinal")
        obj["external_refs"] = []
        obj["id_assignment"].update(method="manual", prefix_override_reason="Retain durable ID")
        obj["best_measurement"].update(
            mode="manual", measurement_id="m-001", reason="Retain the older point"
        )
        for measurement, (easting, northing) in zip(
            obj["measurements"], ((x, y), (560015, 150015)), strict=True
        ):
            for key in ("lat", "lon", "x_1992", "y_1992"):
                measurement.pop(key, None)
            measurement.update(input_srid=2180, input_x=easting, input_y=northing)
        _write_yaml(data / "objects/KSW" / f"{obj['id']}.yml", obj)
    for args in (
        ["init"],
        ["add", "data"],
        [
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-qm",
            "Accepted spatial fixture",
        ],
    ):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    return data, {"base_ref": "HEAD", "history_repo": root}


@pytest.mark.parametrize("reverse", [False, True], ids=["first-ordinal", "reversed-ordinal"])
def test_sql_regions_cover_edges_holes_overlap_countries_and_missing_region(
    tmp_path, make_canonical_data_dir, reverse
):
    from gps_kataster_obiektow_tatr.export_data import prepare_export_data
    from gps_kataster_obiektow_tatr.postgres import open_catalog
    from gps_kataster_obiektow_tatr.prefix_resolver import PrefixResolver

    reference = spatial_reference(tmp_path / "reference", reverse=reverse)
    data, _ = _spatial_source(tmp_path / "source", make_canonical_data_dir, SPATIAL_CASES)
    with open_catalog(data, validate=False, reference_root=reference) as catalog:
        prepared = prepare_export_data(catalog.dataset())
    expected = {f"KSW-{i:04d}": prefix for i, (_, _, prefix, _) in enumerate(SPATIAL_CASES, 1)}
    if reverse:
        expected["KSW-0006"] = "KSW"
    assert dict(prepared.gpx_regions) == expected
    assert all(
        row.measurement_id == "m-001" and row.computed_best_measurement_id == "m-002"
        for row in prepared.best
    )
    with pytest.raises(TypeError):
        prepared.gpx_regions["KSW-0001"] = "KSW"
    # Contrast exact 2180 geometry, without a 4326 round-trip. The old even/odd
    # resolver excludes a hole boundary, while SQL ST_Covers includes it.
    resolver = PrefixResolver(
        config_path=reference / "config/prefixes.yml", shapes_dir=reference / "data/shapes"
    )
    first = next(f for f in resolver._valley_features if f.prefix == "MTW")
    assert first.contains(easting=560001, northing=150001)
    assert first.contains(easting=560000, northing=150005)
    assert not first.contains(easting=560004, northing=150004)
    assert not first.contains(easting=560002, northing=150005)


@pytest.mark.parametrize("full_release", [False, True], ids=["standalone", "release"])
def test_both_exports_use_sql_manual_regions_without_python_geography_or_extra_catalogue(
    tmp_path, make_canonical_data_dir, monkeypatch, full_release
):
    from gps_kataster_obiektow_tatr import postgres, prefix_resolver
    from gps_kataster_obiektow_tatr.best_measurements_export import export_best_measurements
    from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts

    reference = spatial_reference(tmp_path / "reference")
    data, baseline = _spatial_source(
        tmp_path / "source", make_canonical_data_dir, SPATIAL_CASES[:-1]
    )
    original = postgres.open_catalog
    opened = []

    @contextmanager
    def configured(*args, **kwargs):
        with original(*args, **kwargs, reference_root=reference) as catalog:
            opened.append(catalog.connection)
            yield catalog

    def unexpected(*args, **kwargs):
        pytest.fail("Export must use SQL regions, without Python geography")

    monkeypatch.setattr(postgres, "open_catalog", configured)
    monkeypatch.setattr(prefix_resolver.PrefixResolver, "resolve", unexpected)
    monkeypatch.setattr(prefix_resolver, "default_prefix_resolver", unexpected)
    build = build_release_artifacts if full_release else export_best_measurements
    result = build(
        data_dir=data, output_dir=tmp_path / "exports", generated_at=GENERATED_AT, **baseline
    )
    result = result.export_result if full_release else result
    assert len(opened) == 1
    full = _waypoints(result.gpx_path)
    expected = (
        ("KSW-0007",),
        ("KSW-0001", "KSW-0002", "KSW-0003", "KSW-0005", "KSW-0006"),
        ("KSW-0004", "KSW-0008", "KSW-0009"),
    )
    actual = []
    for name, ids in zip(FILENAMES, expected, strict=True):
        group = _waypoints(result.output_dir / name)
        assert tuple(group) == ids
        assert all(point == full[oid] for oid, point in group.items())
        actual.extend(group)
    assert len(actual) == len(set(actual)) == len(full) == 9
    assert set(actual) == set(full)
    import csv

    with result.csv_path.open() as stream:
        rows = list(csv.DictReader(stream))
    assert all(
        row["measurement_id"] == "m-001" and row["computed_best_measurement_id"] == "m-002"
        for row in rows
    )
    assert not any("region" in key for key in rows[0])


@pytest.mark.parametrize("full_release", [False, True], ids=["standalone", "release"])
@pytest.mark.parametrize("region", [None, "unknown", "missing"])
def test_unmapped_sql_region_blocks_publication_without_id_fallback(
    tmp_path, make_canonical_data_dir, monkeypatch, full_release, region
):
    from gps_kataster_obiektow_tatr import postgres
    from gps_kataster_obiektow_tatr.best_measurements_export import (
        GpxGroupingError,
        export_best_measurements,
    )
    from gps_kataster_obiektow_tatr.release_artifacts import build_release_artifacts

    # Geography validation succeeds first. A missing/damaged read-model region
    # must still fail closed at the grouping boundary for either public API.
    data, baseline = _spatial_source(
        tmp_path / "source", make_canonical_data_dir, SPATIAL_CASES[:1]
    )
    original = postgres.Catalog.dataset

    def unmapped(catalog):
        dataset = original(catalog)
        regions = {(oid, mid): prefix for oid, mid, prefix in dataset.measurement_regions}
        key = ("KSW-0001", "m-001")
        if region == "missing":
            del regions[key]
        else:
            regions[key] = region
        return replace(
            dataset, measurement_regions=tuple((*key, value) for key, value in regions.items())
        )

    monkeypatch.setattr(postgres.Catalog, "dataset", unmapped)
    output = tmp_path / "exports"
    output.mkdir()
    (output / "previous").write_bytes(b"accepted artifacts")
    build = build_release_artifacts if full_release else export_best_measurements
    with pytest.raises(GpxGroupingError, match="GPX group missing for object KSW-0001"):
        build(data_dir=data, output_dir=output, **baseline)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == {"previous": b"accepted artifacts"}


def test_copied_read_model_keeps_sql_regions_and_detached_records(
    tmp_path, make_canonical_data_dir
):
    from gps_kataster_obiektow_tatr.best_measurements_export import write_best_measurements
    from gps_kataster_obiektow_tatr.export_data import prepare_export_data
    from gps_kataster_obiektow_tatr.postgres import open_catalog

    reference = spatial_reference(tmp_path / "reference")
    data, _ = _spatial_source(tmp_path / "source", make_canonical_data_dir, SPATIAL_CASES[:1])
    with open_catalog(data, reference_root=reference) as catalog:
        dataset = catalog.dataset()
    candidate = deepcopy(dataset)
    dataset.objects[0].data["notes"] = "Separate later edit"
    prepared = prepare_export_data(candidate)
    assert prepared.best[0].object_notes == "Object terrain note."
    assert prepared.gpx_regions["KSW-0001"] == "MTW"
    result = write_best_measurements(prepared, output_dir=tmp_path / "exports")
    assert tuple(_waypoints(result.output_dir / FILENAMES[1])) == ("KSW-0001",)
    assert not _waypoints(result.output_dir / FILENAMES[0])
