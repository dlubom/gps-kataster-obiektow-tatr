"""Helpers for YAML fixtures and their PostgreSQL projections."""

import subprocess
from functools import lru_cache
from pathlib import Path

from gps_kataster_obiektow_tatr.history import _git_baseline
from gps_kataster_obiektow_tatr.postgres import read_catalog_projection


def history_cli_args(data_dir):
    """Accept this explicit legacy/review fixture without changing its source bytes."""
    from export_test_support import accept_source, cli_args

    return cli_args(accept_source(data_dir))


def read_record(path):
    import yaml

    if path.exists() and path.suffix in (".yml", ".yaml"):
        return yaml.safe_load(path.read_text())
    root = path.parent
    while root.name != "data":
        root = root.parent
        if root == root.parent:
            raise ValueError("Expected a fixture data directory")
    return next(
        r.data for r in read_catalog_projection(root).records() if r.data["id"] == path.stem
    )


@lru_cache(maxsize=1)
def repository_records():
    return {
        r.data["id"]: r.data
        for r in read_catalog_projection(Path(__file__).resolve().parents[1] / "data").records()
    }


def module(name):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parents[1] / f"scripts/{name}.py"
    )
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def make_legacy_history_baseline(tmp_path):
    root = tmp_path / "repo"
    for name in ("objects/KSW", "caves", "relations"):
        (root / "data" / name).mkdir(parents=True)
    (root / "data/objects/KSW/KSW-0001.yml").write_bytes(
        (Path(__file__).resolve().parents[1] / "tests/fixtures/valid-object.yml").read_bytes()
    )
    (root / "data/caves/C-0001.yml").write_bytes(
        (Path(__file__).resolve().parents[1] / "tests/fixtures/valid-cave.yml").read_bytes()
    )
    (root / "data/relations/.gitkeep").touch()

    import yaml

    from gps_kataster_obiektow_tatr.coordinates import wgs84_to_1992

    object_path = root / "data/objects/KSW/KSW-0001.yml"
    obj = yaml.safe_load(object_path.read_text())
    m = obj["measurements"][0]
    xy = wgs84_to_1992(lat=m["lat"], lon=m["lon"])
    m.update(x_1992=xy.x_1992, y_1992=xy.y_1992)
    object_path.write_text(yaml.safe_dump(obj))
    cave_path = root / "data/caves/C-0001.yml"
    cave = yaml.safe_load(cave_path.read_text())
    cave["object_ids"] = [obj["id"]]
    cave_path.write_text(yaml.safe_dump(cave))

    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

    git("init", "-q")
    git("add", "data")
    git(
        "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "baseline"
    )
    sha = git("rev-parse", "HEAD")
    return root, sha, _git_baseline(sha, root, "data")


def write_canonical_history_source(data_dir):
    """Literal v2 counterpart of the historical fixture, without conversion code."""
    from export_test_support import initialize_source

    from gps_kataster_obiektow_tatr.data_loader import load_yaml_dataset

    initialize_source(data_dir)
    fixtures = Path(__file__).parent / "fixtures"
    for kind, relative in (("object", "objects/KSW/KSW-0001.yml"), ("cave", "caves/C-0001.yml")):
        path = data_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((fixtures / f"canonical-{kind}.yml").read_bytes())
    return load_yaml_dataset(data_dir)
