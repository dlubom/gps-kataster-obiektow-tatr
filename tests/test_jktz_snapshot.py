import hashlib
import importlib
import io
import json
import zipfile
from urllib.error import URLError

import pytest
from qgis_fixtures import JKTZ_REPOSITORY, jktz_members, write_jktz_source


def module():
    return importlib.import_module("gps_kataster_obiektow_tatr.jktz_snapshot")


def test_local_snapshot_preserves_original_model_and_attribution_bytes(tmp_path):
    source = write_jktz_source(tmp_path / "input")
    snapshot = module().load_jktz_snapshot(source)
    assert snapshot.metadata["version"] == "v9.8.7"
    assert [model.prefix for model in snapshot.models] == ["Alpha", "Beta"]
    assert [model.feature_count for model in snapshot.models] == [1, 1]
    assert snapshot.members == jktz_members()
    assert (
        snapshot.metadata["sha256"]
        == hashlib.sha256((source / "JKTZ.zip").read_bytes()).hexdigest()
    )


@pytest.mark.parametrize("broken", ["digest", "missing-prj", "missing-dbf", "wrong-crs", "unsafe"])
def test_snapshot_rejects_broken_or_unsafe_survey_inputs(tmp_path, broken):
    members = jktz_members()
    if broken.startswith("missing-"):
        members.pop("exports/caves/Alpha." + broken.removeprefix("missing-"))
    elif broken == "wrong-crs":
        members["exports/caves/Alpha.prj"] = b'GEOGCS["incomplete"]'
    elif broken == "unsafe":
        members["exports/caves/../../outside.shp"] = b"bad"
    source = write_jktz_source(tmp_path / "input", members=members)
    if broken == "digest":
        (source / "JKTZ.zip").write_bytes(b"changed after resolution")
    with pytest.raises(ValueError):
        module().load_jktz_snapshot(source)


def test_snapshot_rejects_duplicate_archive_members(tmp_path):
    source = write_jktz_source(tmp_path / "input")
    with pytest.warns(UserWarning), zipfile.ZipFile(source / "JKTZ.zip", "a") as archive:
        archive.writestr("exports/caves/Alpha.shp", b"ambiguous second member")
    metadata = json.loads((source / "source.json").read_text())
    metadata["sha256"] = hashlib.sha256((source / "JKTZ.zip").read_bytes()).hexdigest()
    (source / "source.json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="duplicate"):
        module().load_jktz_snapshot(source)


def test_snapshot_requires_attribution_and_at_least_one_model(tmp_path):
    for number, members in enumerate(({}, {"README.md": b"no license or models"})):
        source = write_jktz_source(tmp_path / str(number), members=members)
        with pytest.raises(ValueError):
            module().load_jktz_snapshot(source)


@pytest.mark.parametrize(
    "field,value", [("version", "../main"), ("repository", "other/repo"), ("schema_version", 9)]
)
def test_snapshot_rejects_metadata_for_an_unapproved_source(tmp_path, field, value):
    source = write_jktz_source(tmp_path / "input")
    metadata = json.loads((source / "source.json").read_text())
    metadata[field] = value
    (source / "source.json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError):
        module().load_jktz_snapshot(source)


def release_response(archive: bytes, *, draft=False, prerelease=False):
    version = "v9.8.7"
    url = f"https://github.com/{JKTZ_REPOSITORY}/releases/download/{version}/JKTZ-{version}.zip"
    return {
        "tag_name": version,
        "draft": draft,
        "prerelease": prerelease,
        "html_url": f"https://github.com/{JKTZ_REPOSITORY}/releases/tag/{version}",
        "assets": [
            {
                "name": f"JKTZ-{version}.zip",
                "browser_download_url": url,
                "digest": "sha256:" + hashlib.sha256(archive).hexdigest(),
                "size": len(archive),
            }
        ],
    }


def test_acquisition_publishes_one_verified_snapshot_and_does_not_forward_token(
    tmp_path, monkeypatch
):
    fixture = write_jktz_source(tmp_path / "fixture")
    data = (fixture / "JKTZ.zip").read_bytes()
    release = release_response(data)

    def open_url(request, **kwargs):
        if request.full_url.startswith("https://api.github.com/"):
            assert request.get_header("Authorization") == "Bearer read-token"
            return io.BytesIO(json.dumps(release).encode())
        assert request.full_url == release["assets"][0]["browser_download_url"]
        assert request.get_header("Authorization") is None
        return io.BytesIO(data)

    monkeypatch.setattr("urllib.request.urlopen", open_url)
    target = tmp_path / "resolved"
    result = module().fetch_latest_jktz(target, token="read-token")
    assert result == target
    snapshot = module().load_jktz_snapshot(target)
    assert (target / "JKTZ.zip").read_bytes() == data
    assert snapshot.metadata["asset_url"] == release["assets"][0]["browser_download_url"]
    assert snapshot.metadata["version"] == "v9.8.7"


def test_acquisition_does_not_publish_partial_or_overwrite_existing_input(tmp_path, monkeypatch):
    def broken_url(request, **kwargs):
        raise URLError("unavailable")

    monkeypatch.setattr("urllib.request.urlopen", broken_url)
    target = tmp_path / "input"
    with pytest.raises(ValueError, match="unavailable"):
        module().fetch_latest_jktz(target)
    assert not target.exists()
    target.mkdir()
    sentinel = target / "existing"
    sentinel.write_bytes(b"keep")
    with pytest.raises(ValueError, match="exists"):
        module().fetch_latest_jktz(target)
    assert sentinel.read_bytes() == b"keep"


def test_api_redirect_cannot_forward_authorization(tmp_path, monkeypatch):
    from urllib.request import HTTPRedirectHandler

    fixture = write_jktz_source(tmp_path / "fixture")
    data = (fixture / "JKTZ.zip").read_bytes()
    release = release_response(data)

    def open_url(request, **kwargs):
        if request.full_url.startswith("https://api.github.com/"):
            assert request.get_header("Authorization") == "Bearer dummy-token"
            redirected = HTTPRedirectHandler().redirect_request(
                request, None, 302, "Found", {}, "https://example.invalid/redirect"
            )
            assert redirected.get_header("Authorization") is None
            return io.BytesIO(json.dumps(release).encode())
        return io.BytesIO(data)

    monkeypatch.setattr("urllib.request.urlopen", open_url)
    module().fetch_latest_jktz(tmp_path / "resolved", token="dummy-token")


@pytest.mark.parametrize("case", ["draft", "prerelease", "wrong-url", "wrong-digest", "wrong-size"])
def test_acquisition_rejects_unstable_or_mismatched_release_before_publication(
    tmp_path, monkeypatch, case
):
    source = write_jktz_source(tmp_path / "fixture")
    data = (source / "JKTZ.zip").read_bytes()
    release = release_response(data, draft=case == "draft", prerelease=case == "prerelease")
    if case == "wrong-url":
        release["assets"][0]["browser_download_url"] = "https://example.invalid/unrelated.zip"
    elif case == "wrong-digest":
        release["assets"][0]["digest"] = "sha256:" + "0" * 64
    elif case == "wrong-size":
        release["assets"][0]["size"] += 1

    def open_url(request, **kwargs):
        return io.BytesIO(
            json.dumps(release).encode() if "api.github.com" in request.full_url else data
        )

    monkeypatch.setattr("urllib.request.urlopen", open_url)
    target = tmp_path / "resolved"
    with pytest.raises(ValueError):
        module().fetch_latest_jktz(target)
    assert not target.exists()
