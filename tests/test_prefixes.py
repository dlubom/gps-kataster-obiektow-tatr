import re
from pathlib import Path

import shapefile
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PREFIX_CONFIG_PATH = REPO_ROOT / "config" / "prefixes.yml"
DOLINY_SHAPE_PATH = REPO_ROOT / "data" / "shapes" / "doliny.shp"
PREFIX_RE = re.compile(r"^[A-Z]{2,3}$")


def load_prefix_config() -> dict[str, object]:
    with PREFIX_CONFIG_PATH.open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)
    assert isinstance(config, dict)
    return config


def load_valley_names_from_shape() -> set[str]:
    with shapefile.Reader(str(DOLINY_SHAPE_PATH), encoding="utf-8") as reader:
        return {str(record["NAME"]) for record in reader.records()}


def test_all_doliny_polygons_have_prefixes() -> None:
    config = load_prefix_config()
    valley_prefixes = config["valley_prefixes"]
    assert isinstance(valley_prefixes, dict)

    shape_names = load_valley_names_from_shape()

    assert set(valley_prefixes) == shape_names


def test_prefixes_are_uppercase_ascii_codes() -> None:
    config = load_prefix_config()
    valley_prefixes = config["valley_prefixes"]
    fallback_prefixes = config["fallback_prefixes"]
    assert isinstance(valley_prefixes, dict)
    assert isinstance(fallback_prefixes, dict)

    prefixes = [*valley_prefixes.values(), *fallback_prefixes.values()]

    assert prefixes
    assert all(isinstance(prefix, str) for prefix in prefixes)
    assert all(prefix.isascii() for prefix in prefixes)
    assert all(PREFIX_RE.fullmatch(prefix) for prefix in prefixes)
