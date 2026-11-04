from pathlib import Path

import pytest
import yaml

from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992
from gps_kataster_obiektow_tatr.validator import has_errors, validate_data_dir

FIXTURE = Path(__file__).parent / "fixtures" / "schema" / "valid-object.yml"


@pytest.mark.parametrize(
    ("first_timestamp", "second_timestamp", "expected_best"),
    [
        ("2026-05-16T10:00:00Z", "2026-05-16t10:00:01z", "m-002"),
        ("0001-01-01T00:00:00+00:01", "0001-01-01T00:00:00Z", "m-002"),
        ("9999-12-31T23:59:59Z", "9999-12-31T23:59:59-00:01", "m-002"),
        ("2026-05-16T10:00:00.1234561Z", "2026-05-16T10:00:00.1234569Z", "m-002"),
        ("2026-05-16T10:00:00.12345610Z", "2026-05-16T11:00:00.1234561+01:00", "m-001"),
    ],
)
def test_valid_yaml_timestamps_are_ordered_without_rewriting_source(
    tmp_path, first_timestamp, second_timestamp, expected_best
):
    data_dir = tmp_path / "data"
    path = data_dir / "objects" / "KSW" / "KSW-0001.yml"
    path.parent.mkdir(parents=True)
    for name in ("caves", "relations"):
        (data_dir / name).mkdir()
    obj = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    obj.pop("cave_id")
    obj["attachments"] = []
    first = obj["measurements"][0]
    projected = wgs84_to_1992(lat=first["lat"], lon=first["lon"])
    first.update(x_1992=projected.x_1992, y_1992=projected.y_1992, observed_at=first_timestamp)
    obj["measurements"].append(dict(first, id="m-002", observed_at=second_timestamp))
    obj["best_measurement"]["measurement_id"] = expected_best
    source = yaml.safe_dump(obj, sort_keys=False).encode("utf-8")
    path.write_bytes(source)

    issues = validate_data_dir(data_dir)

    assert not has_errors(issues), issues
    assert not any(issue.code == "BEST_MEASUREMENT_AUTO_MISMATCH" for issue in issues), issues
    assert path.read_bytes() == source
