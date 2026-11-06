"""Characterize source/report boundaries independently of their serializers."""

from datetime import UTC, datetime
from math import isnan
from pathlib import Path

import pytest

from gps_kataster_obiektow_tatr import (
    pig_staging,
    report_formatting,
    source_parsing,
    source_profile,
    source_table,
    staging_review,
    tpn_staging,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("", None),
        (" \t\r\n\u00a0", None),
        (" 1 234,50 ", 1234.5),
        ("1\u00a0234.50", 1234.5),
        ("-12,5", -12.5),
        ("+1.2e3", 1200.0),
        ("0", 0.0),
        ("bad", None),
        ("1,2.3", None),
        ("1\t234", None),
        ("1\u202f234", None),
        (True, None),
        (False, None),
        (0, 0.0),
        (2.5, 2.5),
        ("Infinity", float("inf")),
        ("-Infinity", float("-inf")),
        ("1e999", float("inf")),
        (float("inf"), float("inf")),
        ("NaN", float("nan")),
        (float("nan"), float("nan")),
    ],
)
def test_decimal_preserves_blanks_separators_and_non_finite_values(raw, expected):
    actual = source_parsing.parse_decimal(raw)
    if expected is not None and isnan(expected):
        assert isnan(actual)
    else:
        assert actual == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, ""),
        ("", ""),
        (" \t\u00a0", ""),
        (" A\u00a0B ", "A\u00a0B"),
        ("\r\n A\r\nB \t", "A\r\nB"),
        (True, "True"),
        (False, "False"),
        (0, "0"),
        (2.5, "2.5"),
        (float("nan"), "nan"),
        (float("inf"), "inf"),
    ],
)
def test_source_text_only_strips_edges_and_converts_none(raw, expected):
    assert source_parsing.clean_text(raw) == expected


@pytest.mark.parametrize(
    ("raw", "text", "code"),
    [
        (None, "-", "-"),
        ("", "-", "-"),
        (" \u00a0", "-", "`-`"),
        (" A|B ", "A\\|B", "`A\\|B`"),
        ("a`b", "a`b", "`a`b`"),
        ("a\r\nb", "a\r<br>b", "`a\r<br>b`"),
        ("a\rb", "a\rb", "`a\rb`"),
        ("a\nb", "a<br>b", "`a<br>b`"),
        (0, "0", "-"),
        (False, "False", "-"),
    ],
)
def test_markdown_preserves_existing_escaping_and_falsy_code_policy(raw, text, code):
    assert report_formatting.markdown_text(raw) == text
    assert report_formatting.markdown_code_or_dash(raw) == code


@pytest.mark.parametrize(
    ("stamp", "expected"),
    [
        ("2026-01-01T00:30:00+02:00", "2026-01-01"),
        ("2026-01-01T23:30:00-03:00", "2026-01-01"),
        ("2026-02-03T12:00:00Z", "2026-02-03"),
        ("2026-02-03", "2026-02-03"),
        ("2026-02-03T12:00:00", "2026-02-03"),
    ],
)
def test_timestamp_date_keeps_declared_day_without_timezone_conversion(stamp, expected):
    assert source_parsing.date_part_or_today(stamp) == expected


class FixedClock(datetime):
    @classmethod
    def now(cls, tz=None):
        assert tz is UTC
        return cls(2030, 1, 2, 0, 0, 1, 123456, tzinfo=UTC)


def test_invalid_timestamp_falls_back_to_current_utc_day(monkeypatch):
    monkeypatch.setattr(source_parsing, "datetime", FixedClock)
    assert source_parsing.date_part_or_today("invalid") == "2030-01-02"


def test_generated_timestamp_has_utc_seconds(monkeypatch):
    monkeypatch.setattr(report_formatting, "datetime", FixedClock)
    assert report_formatting.utc_timestamp() == "2030-01-02T00:00:01Z"


@pytest.mark.parametrize(
    ("raw", "pig", "tpn"),
    [
        ("2020", "2020-12-31", None),
        ("2020-02-29", None, "2020-02-29"),
        (" 29.02.2020 ", None, "2020-02-29"),
        ("29-02-2020", None, "2020-02-29"),
        ("2020-02-29 12:34:56", None, "2020-02-29"),
        ("2019-02-29", None, None),
        ("2020-02-29T12:34:56Z", None, None),
        ("", None, None),
    ],
)
def test_source_year_and_calendar_dates_keep_separate_policies(raw, pig, tpn):
    assert pig_staging._parse_source_year_date(raw) == pig
    assert tpn_staging._parse_date(raw) == tpn


def test_tpn_source_date_prefers_edit_date_and_falls_back_to_creation_date():
    assert (
        tpn_staging._parse_source_date({"LAST_EDI_1": "2021-01-02", "CREATED_DA": "2020-01-01"})
        == "2021-01-02"
    )
    assert (
        tpn_staging._parse_source_date({"LAST_EDI_1": "bad", "CREATED_DA": "2020-01-01"})
        == "2020-01-01"
    )


def test_csv_raw_profile_and_trimmed_table_have_distinct_value_contracts(tmp_path):
    path = tmp_path / "source.csv"
    path.write_bytes(
        '\ufeff ID ,Name,Note\r\n 1 ," a\r\nb ",\u00a0\r\n2\r\n3,x,y,extra\r\n'.encode("utf-8")
    )
    raw_table = source_table.read_raw_csv_table(path)
    columns, raw_rows = raw_table.columns, raw_table.rows
    table = source_table.read_source_table(path)
    assert columns == table.columns == (" ID ", "Name", "Note")
    assert raw_rows == (
        {" ID ": " 1 ", "Name": " a\r\nb ", "Note": "\u00a0"},
        {" ID ": "2", "Name": "", "Note": ""},
        {" ID ": "3", "Name": "x", "Note": "y"},
    )
    assert table.rows == (
        {" ID ": "1", "Name": "a\r\nb", "Note": ""},
        {" ID ": "2", "Name": "", "Note": ""},
        {" ID ": "3", "Name": "x", "Note": "y"},
    )


def test_profile_counts_non_finite_values_without_adopting_staging_validation(tmp_path):
    path = tmp_path / "numbers.csv"
    path.write_text("x\nNaN\nInfinity\n-Infinity\n1e999\nbad\n \n", encoding="utf-8")
    spec = source_profile.SourceProfileSpec("sample", ("x",), (), ("x",))
    profile = source_profile.profile_csv_source(path, spec)
    numbers = profile.coordinate_ranges["x"]
    assert profile.record_count == 6
    assert profile.key_missing_counts == {"x": 1}
    assert (numbers.numeric_count, numbers.missing_count, numbers.non_numeric_count) == (4, 1, 1)
    assert isnan(numbers.minimum)
    assert isnan(numbers.maximum)


@pytest.mark.parametrize("source", ["PIG", "TPN", "review"])
def test_public_report_renderers_preserve_cell_escaping(source):
    text = " \u00a0A|`B`\r\nC "
    if source == "PIG":
        report = pig_staging.PigStagingReport(
            source_path=Path("source.csv"),
            generated_at="fixed",
            record_count=1,
            proposed_caves=(),
            proposed_objects=(),
            issues=(),
            rows=(pig_staging.PigStagingRow(1, "", "", text, "C-0001", None, "cave_only"),),
        )
        markdown = pig_staging.render_markdown_report(report)
    elif source == "TPN":
        report = tpn_staging.TpnStagingReport(
            source_path=Path("source.csv"),
            generated_at="fixed",
            record_count=1,
            proposed_caves=(),
            proposed_objects=(),
            matched_measurements=(),
            issues=(),
            rows=(tpn_staging.TpnStagingRow(1, "", "", text, "new", None, None, None, None),),
        )
        markdown = tpn_staging.render_markdown_report(report)
    else:
        result = staging_review.StagingReviewResult(
            reviewed_at="fixed",
            reviewed_by="reviewer",
            data_dir=Path("data"),
            applied_decisions=(
                staging_review.AppliedDecision(1, "reject", "skipped", None, 1, None, None, text),
            ),
            issues=(),
            written_paths=(),
        )
        markdown = staging_review.render_review_markdown(result)
    assert "A\\|`B`\r<br>C |" in markdown


@pytest.mark.parametrize("source", ["PIG", "TPN", "profile"])
def test_cli_explicit_timestamp_takes_precedence_over_clock(
    tmp_path, make_canonical_data_dir, monkeypatch, source
):
    import importlib.util
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    script = {
        "PIG": "importers/import_pig.py",
        "TPN": "importers/import_tpn.py",
        "profile": "profile_sources.py",
    }[source]
    spec = importlib.util.spec_from_file_location("u08_cli", root / "scripts" / script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def no_clock():
        pytest.fail("An explicit generated_at must not read the clock")

    monkeypatch.setattr(module, "utc_timestamp", no_clock)
    pig = tmp_path / "pig.csv"
    tpn = tmp_path / "tpn.csv"
    pig.write_text("ID,Nazwa\n", encoding="utf-8")
    tpn.write_text("GLOBALID,NAZWA\n", encoding="utf-8")
    output = tmp_path / "reports"
    stamp = "2025-03-04T23:00:00.123456-02:00"
    args = ["--generated-at", stamp, "--output-dir", str(output)]
    if source == "profile":
        args += ["--pig-csv", str(pig), "--tpn-csv", str(tpn)]
        filename = "source-profile.json"
    else:
        data = make_canonical_data_dir(tmp_path / "data")
        args += ["--data-dir", str(data)]
        args += (
            ["--pig-source", str(pig)]
            if source == "PIG"
            else ["--tpn-source", str(tpn), "--no-pig-staging"]
        )
        filename = f"{source.lower()}-staging.json"
    assert module.main(args) == 0
    assert json.loads((output / filename).read_text())["generated_at"] == stamp
