import re
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from test_best_measurements_export import GENERATED_AT, REPO_ROOT, _valid_object, _write_yaml

from gps_kataster_obiektow_tatr.best_measurements_export import export_best_measurements
from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992

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
    for directory in ("objects", "caves", "relations"):
        (data / directory).mkdir(parents=True, exist_ok=True)
    for i, (lat, lon) in enumerate(locations, 1):
        obj = deepcopy(_valid_object())
        obj["id"] = f"KSW-{i:04d}"
        obj.pop("cave_id")
        obj["external_refs"] = []
        obj["id_assignment"].update(
            method="manual", prefix_override_reason="Historical durable ID retained."
        )
        obj["name_local"] = "Żółta <jaskinia> & wspólna nazwa"
        xy = wgs84_to_1992(lat=lat, lon=lon)
        obj["measurements"][1].update(lat=lat, lon=lon, x_1992=xy.x_1992, y_1992=xy.y_1992)
        _write_yaml(data / "objects/KSW" / f"{obj['id']}.yml", obj)


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
    _write_points(data, LOCATIONS)
    result = export_best_measurements(
        data_dir=data, output_dir=tmp_path / "exports", generated_at=GENERATED_AT
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
    _write_points(data, ())
    result = export_best_measurements(data_dir=data, output_dir=tmp_path / "exports")
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
    _write_points(data, (location,) * 500)
    result = export_best_measurements(data_dir=data, output_dir=tmp_path / "exports")
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
    _write_points(data, (LOCATIONS[3],))
    output = tmp_path / "exports"
    export_best_measurements(data_dir=data, output_dir=output, generated_at=GENERATED_AT)
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    _write_points(data, (location,) * 501)
    with pytest.raises(ValueError, match=rf"{re.escape(filename)}.*501.*500"):
        export_best_measurements(data_dir=data, output_dir=output)
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    for script, extra in (
        ("export_best_measurements.py", []),
        ("build_release_artifacts.py", ["--sqlite-output", str(tmp_path / "catalog.sqlite")]),
    ):
        command = [
            sys.executable,
            str(REPO_ROOT / "scripts" / script),
            "--data-dir",
            str(data),
            "--output-dir",
            str(output),
            *extra,
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        assert completed.returncode == 1
        assert filename in completed.stderr
        assert "501" in completed.stderr and "500" in completed.stderr
        assert "Traceback" not in completed.stderr
        assert before == {p.name: p.read_bytes() for p in output.iterdir()}


def test_full_gpx_keeps_more_than_500_points_across_groups(tmp_path):
    data = tmp_path / "data"
    _write_points(data, (LOCATIONS[3],) * 500 + (LOCATIONS[5],))
    result = export_best_measurements(data_dir=data, output_dir=tmp_path / "exports")
    assert len(_waypoints(result.gpx_path)) == 501
    assert [len(_waypoints(result.output_dir / name)) for name in FILENAMES] == [500, 1, 0]


def test_cli_reports_full_and_all_additional_gpx(tmp_path):
    data = tmp_path / "data"
    _write_points(data, LOCATIONS)
    command = [
        sys.executable,
        str(REPO_ROOT / "scripts/export_best_measurements.py"),
        "--data-dir",
        str(data),
        "--output-dir",
        str(tmp_path / "exports"),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    for filename in ("best-measurements.gpx", *FILENAMES):
        assert filename in completed.stdout
