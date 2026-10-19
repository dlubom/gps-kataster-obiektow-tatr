"""Contract values, not implementation-shaped golden hashes."""

import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest

from gps_kataster_obiektow_tatr import tpn_normalization as norm

REPO = Path(__file__).resolve().parents[1]


def feature():
    return json.loads((REPO / "tests/fixtures/tpn_api/page-0.json").read_bytes())["features"][0]


def test_canonical_numbers_text_and_rejection_of_nonfinite():
    assert norm.canonical({"z": Decimal("-0"), "a": [Decimal("1.2300"), 1e-7]}) == (
        b'{"a":[1.23,0.0000001],"z":0}'
    )
    assert norm.text("  z\u0307\r\na  b\r c  ") == "ż\na  b\n c"
    assert norm.text(" \n ") is None
    for bad in [float("nan"), float("inf"), Decimal("NaN")]:
        with pytest.raises(ValueError):
            norm.canonical(bad)


def test_technical_fields_do_not_change_revision_or_location_but_metadata_does():
    original = norm.normalize_feature(feature())
    technical = feature()
    technical["attributes"].update(OBJECTID=99, FIELD=None, LAST_EDITED_DATE=1)
    changed = norm.normalize_feature(technical)
    assert original["revision_hash"] == changed["revision_hash"]
    assert original["location_hash"] == changed["location_hash"]
    technical["attributes"]["UWAGI"] = "nowy kontekst"
    metadata = norm.normalize_feature(technical)
    assert metadata["revision_hash"] != changed["revision_hash"]
    assert metadata["location_hash"] == changed["location_hash"]


def test_exact_decimal_xy_and_null_zero_are_not_collapsed():
    original = feature()
    original["geometry"]["x"] = Decimal("19.1234567890123456789")
    changed = copy.deepcopy(original)
    changed["geometry"]["x"] += Decimal("0.0000000000000000001")
    assert (
        norm.normalize_feature(original)["location_hash"]
        != norm.normalize_feature(changed)["location_hash"]
    )
    original["attributes"]["WERYF"] = 0
    changed = copy.deepcopy(original)
    changed["attributes"]["WERYF"] = None
    assert (
        norm.normalize_feature(original)["revision_hash"]
        != norm.normalize_feature(changed)["revision_hash"]
    )


@pytest.mark.parametrize("fault", ["extra", "missing", "nan", "guid", "bool", "z"])
def test_normalizer_refuses_schema_drift_and_invalid_values(fault):
    value = feature()
    if fault == "extra":
        value["attributes"]["UNKNOWN"] = None
    elif fault == "missing":
        del value["attributes"]["UWAGI"]
    elif fault == "nan":
        value["geometry"]["x"] = Decimal("NaN")
    elif fault == "guid":
        value["attributes"]["GLOBALID"] = "bad"
    elif fault == "bool":
        value["attributes"]["WERYF"] = True
    else:
        value["geometry"]["z"] = 1000
    with pytest.raises(ValueError):
        norm.normalize_feature(value)


def test_csv_bootstrap_preserves_raw_elevation_and_projects_polish_axes():
    records = norm.read_csv(REPO / norm.CSV_PATH)
    item = records["d7c052e6-d584-4320-b886-367312d2219f"]
    assert item["metadata"]["DLUGOSC"] == Decimal("2.3")
    assert item["raw"]["Z"] == "1297,367139"
    assert item["elevation"] == Decimal("1297.367139")
    assert 49 < item["location"]["lat"] < 50
    assert 19 < item["location"]["lon"] < 21


def test_csv_rejects_duplicate_header_guid_and_unknown_columns(tmp_path):
    raw = (REPO / norm.CSV_PATH).read_text()
    path = tmp_path / "input.csv"
    for bad in [
        raw.replace("NAZWA,", "GLOBALID,", 1),
        raw.replace("NAZWA,", "UNKNOWN,", 1),
        raw + raw.splitlines()[1] + "\n",
    ]:
        path.write_text(bad)
        with pytest.raises(ValueError):
            norm.read_csv(path)


def test_unicode_empty_text_and_numeric_spelling_have_same_revision():
    a, b = feature(), feature()
    a["attributes"].update(NAZWA="  z\u0307\r\na  b  ", UWAGI="", DLUGOSC=0)
    b["attributes"].update(NAZWA="ż\na  b", UWAGI=None, DLUGOSC=Decimal("0.00"))
    assert norm.normalize_feature(a)["revision_hash"] == norm.normalize_feature(b)["revision_hash"]


@pytest.mark.parametrize(
    "column,value",
    [("WERYF", "0.5"), ("FIELD", "2147483648"), ("LAST_EDI_1", "yesterday"), ("Z", "NaN")],
)
def test_csv_rejects_wrong_integer_date_and_nonfinite_values(tmp_path, column, value):
    import csv
    import io

    rows = list(csv.DictReader(io.StringIO((REPO / norm.CSV_PATH).read_text())))
    rows[0][column] = value
    path = tmp_path / "bad.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerow(rows[0])
    with pytest.raises(ValueError):
        norm.read_csv(path)


def test_source_modification_time_preserves_epoch_zero_and_unknown_observation():
    value = feature()
    value["attributes"]["LAST_EDITED_DATE"] = 0
    record = norm.normalize_feature(value)
    assert record["source_time"]["source_modified_at"] == "1970-01-01T00:00:00Z"
    assert record["source_time"]["field_observed_at"] is None
    assert record["source_time"]["date_basis"] == "source_modified"
    value["attributes"]["LAST_EDITED_DATE"] = None
    record = norm.normalize_feature(value)
    assert record["source_time"]["source_modified_at"] is None
    assert record["source_time"]["date_basis"] == "unavailable"


def test_malformed_decimal_is_a_validation_error():
    with pytest.raises(ValueError, match="numeric"):
        norm.decimal("not-a-number")
