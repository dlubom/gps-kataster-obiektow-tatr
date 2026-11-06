import shutil
import subprocess
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from sql_test_support import make_legacy_history_baseline

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def baseline(tmp_path):
    return make_legacy_history_baseline(tmp_path)


@pytest.mark.parametrize(
    "damage", ["object", "measurement", "lat", "elevation_m", "elevation_datum"]
)
def test_git_history_rejects_source_loss(baseline, damage):
    from gps_kataster_obiektow_tatr.history import check_history

    root, sha, original = baseline
    candidate = deepcopy(original)
    if damage == "object":
        candidate = replace(candidate, objects=())
    elif damage == "measurement":
        candidate.objects[0].data["measurements"] = []
    else:
        candidate.objects[0].data["measurements"][0][damage] = {
            "lat": 49.9,
            "elevation_m": 999,
            "elevation_datum": "ellipsoidal",
        }[damage]
    issues = check_history(sha, candidate, repo_root=root)
    assert issues and all(issue.severity == "error" for issue in issues)


def test_git_history_allows_append_and_note_status_edits(baseline):
    from gps_kataster_obiektow_tatr.history import check_history

    root, sha, candidate = baseline
    m = candidate.objects[0].data["measurements"][0]
    m.update(notes="Reviewed", verification_status="zweryfikowany")
    new = deepcopy(m)
    new.update(id="m-002", lat=49.9)
    candidate.objects[0].data["measurements"].append(new)
    assert check_history(sha, candidate, repo_root=root) == ()


def test_missing_baseline_fails_closed(baseline):
    from gps_kataster_obiektow_tatr.history import check_history

    root, _, candidate = baseline
    assert (
        check_history("missing-ref", candidate, repo_root=root)[0].code
        == "HISTORY_BASELINE_UNAVAILABLE"
    )


def test_local_history_uses_native_geometry(baseline):
    from gps_kataster_obiektow_tatr.history import compare_history

    _, _, original = baseline
    original.objects[0].data["measurements"][0].update(
        input_srid=2180, input_x=562000.0, input_y=152000.0
    )
    candidate = deepcopy(original)
    candidate.objects[0].data["measurements"][0]["input_x"] += 1
    assert compare_history(original, candidate)[0].code == "HISTORY_MEASUREMENT_CHANGED"


def test_yaml_git_baseline_protects_native_source_not_derived_read_model(baseline):
    from gps_kataster_obiektow_tatr.catalog_records import write_dataset
    from gps_kataster_obiektow_tatr.history import check_history
    from gps_kataster_obiektow_tatr.postgres import read_catalog_projection

    root, _, dataset = baseline
    m = dataset.objects[0].data["measurements"][0]
    m.update(input_srid=2180, input_x=562729.5, input_y=152838.5)
    write_dataset(dataset, root / "data")
    subprocess.run(["git", "-C", str(root), "add", "data"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "SQL baseline",
        ],
        check=True,
    )
    sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    candidate = read_catalog_projection(root / "data")
    candidate.objects[0].data["measurements"][0]["lat"] = 0  # derived display value is not source
    assert check_history(sha, candidate, repo_root=root) == ()
    candidate.objects[0].data["measurements"][0]["input_y"] += 0.01
    assert check_history(sha, candidate, repo_root=root)[0].code == "HISTORY_MEASUREMENT_CHANGED"


def test_history_rejects_reordering_but_allows_same_id_on_another_object(baseline):
    from gps_kataster_obiektow_tatr.history import compare_history

    _, _, original = baseline
    m = deepcopy(original.objects[0].data["measurements"][0])
    m["id"] = "m-002"
    original.objects[0].data["measurements"].append(m)
    candidate = deepcopy(original)
    extra = deepcopy(candidate.objects[0])
    extra.data["id"] = "KSW-9999"
    candidate = replace(candidate, objects=(*candidate.objects, extra))
    assert compare_history(original, candidate) == ()
    candidate.objects[0].data["measurements"].reverse()
    assert compare_history(original, candidate)[0].code == "HISTORY_ORDER_CHANGED"


@pytest.mark.parametrize("storage", ["canonical", "legacy"])
def test_accepted_empty_yaml_baseline_is_not_a_missing_baseline(tmp_path, storage):
    from gps_kataster_obiektow_tatr.catalog_records import write_dataset
    from gps_kataster_obiektow_tatr.data_loader import LoadedDataset
    from gps_kataster_obiektow_tatr.history import check_history

    root = tmp_path / "repo"
    root.mkdir()
    dataset = LoadedDataset((), (), ())
    if storage == "canonical":
        write_dataset(dataset, root / "data")
    else:
        for name in ("objects", "caves", "relations"):
            directory = root / "data" / name
            directory.mkdir(parents=True)
            (directory / ".gitkeep").touch()
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "add", "data"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "Accepted empty catalogue",
        ],
        check=True,
    )
    assert check_history("HEAD", dataset, repo_root=root) == ()


def test_validation_cli_reuses_one_catalogue_for_validation_and_history(baseline, monkeypatch):
    import importlib.util
    from contextlib import contextmanager

    from gps_kataster_obiektow_tatr import postgres
    from gps_kataster_obiektow_tatr.catalog_records import write_dataset

    root, sha, dataset = baseline
    write_dataset(dataset, root / "data")
    calls = []
    original = postgres.open_catalog

    @contextmanager
    def counted(*args, **kwargs):
        with original(*args, **kwargs) as catalog:
            calls.append(catalog.connection.info.dbname)
            yield catalog

    monkeypatch.setattr(postgres, "open_catalog", counted)
    spec = importlib.util.spec_from_file_location("validate_cli", ROOT / "scripts/validate.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    assert (
        cli.main(["--data-dir", str(root / "data"), "--history-repo", str(root), "--base-ref", sha])
        == 0
    )
    assert len(calls) == 1


def test_cli_never_uses_head_when_origin_main_baseline_is_unavailable(
    baseline, monkeypatch, capsys
):
    import importlib.util

    from gps_kataster_obiektow_tatr.catalog_records import write_dataset

    root, _, dataset = baseline
    write_dataset(dataset, root / "data")
    spec = importlib.util.spec_from_file_location(
        "validate_cli_no_base", ROOT / "scripts/validate.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    assert cli.main(["--data-dir", str(root / "data"), "--history-repo", str(root)]) == 1
    assert "HISTORY_BASELINE_UNAVAILABLE" in capsys.readouterr().out


@pytest.mark.parametrize(
    "damage",
    [
        "unsupported-marker",
        "yaml-no-measurements",
        "mixed-with-marker",
        "mixed-no-marker",
        "legacy-no-measurements",
        "legacy-missing-coordinate",
        "legacy-duplicate-measurement",
    ],
)
def test_incomplete_or_mixed_git_baseline_fails_closed(baseline, damage):
    import yaml

    from gps_kataster_obiektow_tatr.catalog_records import write_dataset
    from gps_kataster_obiektow_tatr.data_loader import LoadedDataset
    from gps_kataster_obiektow_tatr.history import check_history

    root, _, dataset = baseline
    if not damage.startswith("legacy-"):
        write_dataset(dataset, root / "data")
        path = root / "data/objects/KSW/KSW-0001.yml"
        if damage == "yaml-no-measurements":
            obj = yaml.safe_load(path.read_text())
            obj["measurements"] = []
            path.write_text(yaml.safe_dump(obj))
        if damage.startswith("mixed-"):
            path.with_suffix(".sql").write_text("SELECT 1;")
        if damage == "mixed-no-marker":
            (root / "data/catalog.json").unlink()
        if damage == "unsupported-marker":
            (root / "data/catalog.json").write_text('{"format":"postgresql-inserts"}')
    else:
        path = root / "data/objects/KSW/KSW-0001.yml"
        obj = yaml.safe_load(path.read_text())
        if damage == "legacy-no-measurements":
            obj["measurements"] = []
        elif damage == "legacy-missing-coordinate":
            del obj["measurements"][0]["lat"]
        else:
            obj["measurements"].append(deepcopy(obj["measurements"][0]))
        path.write_text(yaml.safe_dump(obj))
    subprocess.run(["git", "-C", str(root), "add", "-A", "data"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "damaged baseline",
        ],
        check=True,
    )
    issues = check_history("HEAD", LoadedDataset((), (), ()), repo_root=root)
    assert [issue.code for issue in issues] == ["HISTORY_BASELINE_UNAVAILABLE"]


@pytest.mark.parametrize("srid,x,y", [(4326, 19.8145, 49.2423), (2180, 562729.5, 152838.5)])
def test_accepted_geometry_edit_remains_readable_as_next_git_baseline(baseline, srid, x, y):
    from gps_kataster_obiektow_tatr.catalog_records import write_dataset
    from gps_kataster_obiektow_tatr.history import check_history
    from gps_kataster_obiektow_tatr.postgres import open_catalog
    from gps_kataster_obiektow_tatr.validator import validate_catalog

    root, _, dataset = baseline
    dataset.objects[0].data["measurements"][0].update(input_srid=srid, input_x=x, input_y=y)
    write_dataset(dataset, root / "data")

    def commit(message):
        subprocess.run(["git", "-C", str(root), "add", "data"], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                message,
            ],
            check=True,
        )
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()

    accepted = commit("Canonical YAML baseline")
    path = root / "data/objects/KSW/KSW-0001.yml"
    key = "input_x" if "input_x:" in path.read_text() else "lon"
    path.write_text(path.read_text().replace(f"{key}: {x}", f"{key}: +{x}"))
    with open_catalog(root / "data") as catalog:
        candidate = catalog.dataset()
        assert not [issue for issue in validate_catalog(catalog) if issue.severity == "error"]
        m = candidate.objects[0].data["measurements"][0]
        assert (m["input_srid"], m["input_x"], m["input_y"]) == (srid, x, y)
        assert check_history(accepted, candidate, repo_root=root) == ()
    next_baseline = commit("Accepted human geometry spelling")
    assert check_history(next_baseline, candidate, repo_root=root) == ()
    candidate.objects[0].data["measurements"][0]["input_y"] += 0.01
    assert (
        check_history(next_baseline, candidate, repo_root=root)[0].code
        == "HISTORY_MEASUREMENT_CHANGED"
    )


@pytest.mark.parametrize(
    "geometry", [{"input_srid": 3857}, {"input_x": None}, {"input_y": ".nan"}, {"input_srid": True}]
)
def test_loader_and_git_baseline_reject_unsupported_geometry(baseline, geometry):
    import yaml

    from gps_kataster_obiektow_tatr.catalog_records import write_dataset
    from gps_kataster_obiektow_tatr.history import check_history
    from gps_kataster_obiektow_tatr.postgres import CatalogLoadError, open_catalog

    root, _, dataset = baseline
    write_dataset(dataset, root / "data")
    path = root / "data/objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(path.read_text())
    obj["measurements"][0].update(input_srid=4326, input_x=19.8145, input_y=49.2423)
    obj["measurements"][0].update(geometry)
    path.write_text(yaml.safe_dump(obj))
    with pytest.raises(CatalogLoadError), open_catalog(root / "data"):
        pass
    # Even an externally committed unsupported snapshot fails closed without executing SQL.
    subprocess.run(["git", "-C", str(root), "add", "data"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "Unsupported geometry",
        ],
        check=True,
    )
    assert check_history("HEAD", dataset, repo_root=root)[0].code == "HISTORY_BASELINE_UNAVAILABLE"


@pytest.mark.parametrize("canonical", [False, True], ids=["legacy", "canonical"])
@pytest.mark.parametrize("directory", ["objects", "caves", "relations", "publications"])
@pytest.mark.parametrize("damage", ["missing", "file"])
def test_git_baseline_preserves_the_accepted_directory_layout(
    tmp_path, make_data_dir, make_canonical_data_dir, canonical, directory, damage
):
    from gps_kataster_obiektow_tatr.data_loader import LoadedDataset
    from gps_kataster_obiektow_tatr.history import check_history

    root = tmp_path / "repo"
    initialize = make_canonical_data_dir if canonical else make_data_dir
    data = initialize(root / "data")
    for name in ("objects", "caves", "relations", "publications"):
        if (data / name).is_dir():
            # A real tracked tree whose only asset is not YAML must also count as a directory.
            (data / name / "README.txt").write_bytes(b"accepted empty entity directory")
    path = data / directory
    if path.exists():
        shutil.rmtree(path)
    if damage == "file":
        path.write_bytes(b"file in place of an entity directory")

    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

    git("init", "-q")
    git("add", "data")
    git(
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        "Accepted layout",
    )
    accepted = git("rev-parse", "HEAD")
    issues = check_history(accepted, LoadedDataset((), (), ()), repo_root=root)
    if not canonical and directory == "publications" and damage == "missing":
        assert issues == ()
    else:
        assert [i.code for i in issues] == ["HISTORY_BASELINE_UNAVAILABLE"]
        assert str(Path(directory)) in issues[0].description
    assert git("status", "--porcelain") == ""
    assert git("rev-parse", "HEAD") == accepted


@pytest.mark.parametrize("canonical", [False, True], ids=["legacy", "canonical"])
def test_git_baseline_accepts_empty_directories_tracked_by_non_yaml_assets(
    tmp_path, make_data_dir, make_canonical_data_dir, canonical
):
    from gps_kataster_obiektow_tatr.data_loader import LoadedDataset
    from gps_kataster_obiektow_tatr.history import check_history

    root = tmp_path / "repo"
    data = (make_canonical_data_dir if canonical else make_data_dir)(root / "data")
    for name in ("objects", "caves", "relations", "publications"):
        if (data / name).is_dir():
            (data / name / "README.txt").write_bytes(b"accepted empty directory")
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "add", "data"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "Accepted empty layout",
        ],
        check=True,
    )
    assert check_history("HEAD", LoadedDataset((), (), ()), repo_root=root) == ()


@pytest.mark.parametrize("interface", ["api", "cli"])
def test_git_blob_in_place_of_data_is_a_controlled_baseline_error(tmp_path, interface):
    from export_test_support import source

    from gps_kataster_obiektow_tatr.build_db import build_database

    data, _ = source(tmp_path)
    accepted = tmp_path / "accepted-blob"
    accepted.mkdir()
    (accepted / "data").write_bytes(b"not a catalogue tree")
    subprocess.run(["git", "-C", str(accepted), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(accepted), "add", "data"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(accepted),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "Accepted blob",
        ],
        check=True,
    )
    sha = subprocess.check_output(
        ["git", "-C", str(accepted), "rev-parse", "HEAD"], text=True
    ).strip()
    assert subprocess.check_output(["git", "-C", str(accepted), "ls-tree", sha, "data"]).startswith(
        b"100644 blob"
    )
    output = tmp_path / "output/katalog.dump"
    output.parent.mkdir()
    output.write_bytes(b"previous verified dump")
    if interface == "api":
        with pytest.raises(ValueError, match="HISTORY_BASELINE_UNAVAILABLE"):
            build_database(data_dir=data, output_path=output, history_repo=accepted, base_ref=sha)
    else:
        import sys

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/build_db.py"),
                "--data-dir",
                str(data),
                "--output",
                str(output),
                "--history-repo",
                str(accepted),
                "--base-ref",
                sha,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1
        assert "HISTORY_BASELINE_UNAVAILABLE" in result.stdout + result.stderr
        assert "Traceback" not in result.stdout + result.stderr
    assert output.read_bytes() == b"previous verified dump"
