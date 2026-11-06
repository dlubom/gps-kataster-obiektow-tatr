"""Prepare legacy schemas once per operation, including Git history reads."""

from gps_kataster_obiektow_tatr import history_schema


def count_preparations(monkeypatch):
    calls = []
    original = history_schema._load_schema_validators

    def prepare(schema_dir):
        calls.append(schema_dir)
        return original(schema_dir)

    monkeypatch.setattr(history_schema, "_load_schema_validators", prepare)
    return calls


def test_git_baseline_prepares_schemas_once(tmp_path, monkeypatch):
    from sql_test_support import make_legacy_history_baseline

    from gps_kataster_obiektow_tatr.history import _git_baseline

    root, sha, original = make_legacy_history_baseline(tmp_path)
    calls = count_preparations(monkeypatch)
    actual = _git_baseline(sha, root, "data")
    assert [r.data for r in actual.objects] == [r.data for r in original.objects]
    assert len(calls) == 1
