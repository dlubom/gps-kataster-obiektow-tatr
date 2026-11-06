"""Timestamp contract shared by production builders and CLI."""

from datetime import UTC, datetime

from gps_kataster_obiektow_tatr import report_formatting


class FixedClock(datetime):
    @classmethod
    def now(cls, tz=None):
        assert tz is UTC
        return cls(2030, 1, 2, 0, 0, 1, 123456, tzinfo=UTC)


def test_generated_timestamp_has_utc_seconds(monkeypatch):
    monkeypatch.setattr(report_formatting, "datetime", FixedClock)
    assert report_formatting.utc_timestamp() == "2030-01-02T00:00:01Z"
