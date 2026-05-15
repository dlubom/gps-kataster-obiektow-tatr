"""Load source-of-truth YAML data records from the repository."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = REPO_ROOT / "data"

OBJECTS_DIR_NAME = "objects"
CAVES_DIR_NAME = "caves"
RELATIONS_DIR_NAME = "relations"


class DataKind(StrEnum):
    """Kinds of domain YAML records loaded from ``data/``."""

    OBJECT = "object"
    CAVE = "cave"
    RELATION = "relation"


@dataclass(frozen=True, slots=True)
class LoadedYamlRecord:
    """A YAML record plus its file path for validation reports."""

    kind: DataKind
    path: Path
    data: dict[str, Any]
    raw_data: dict[str, Any]


@dataclass(frozen=True, slots=True)
class LoadedDataset:
    """All source-of-truth domain records loaded from a data directory."""

    objects: tuple[LoadedYamlRecord, ...]
    caves: tuple[LoadedYamlRecord, ...]
    relations: tuple[LoadedYamlRecord, ...]

    def records(self) -> tuple[LoadedYamlRecord, ...]:
        """Return all loaded records in stable validation order."""

        return (*self.objects, *self.caves, *self.relations)


class YamlDataLoadError(ValueError):
    """Raised when a YAML source file cannot be loaded as a domain record."""

    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        super().__init__(f"{path}: {message}")


def load_dataset(data_dir: Path = DEFAULT_DATA_DIR) -> LoadedDataset:
    """Load objects, caves and relations from a repository ``data/`` directory."""

    return LoadedDataset(
        objects=load_records(
            data_dir / OBJECTS_DIR_NAME,
            kind=DataKind.OBJECT,
            normalize=_normalize_object,
        ),
        caves=load_records(
            data_dir / CAVES_DIR_NAME,
            kind=DataKind.CAVE,
            normalize=_normalize_cave,
        ),
        relations=load_records(
            data_dir / RELATIONS_DIR_NAME,
            kind=DataKind.RELATION,
            normalize=_normalize_relation,
        ),
    )


def load_records(
    root_dir: Path,
    *,
    kind: DataKind,
    normalize: _Normalizer,
) -> tuple[LoadedYamlRecord, ...]:
    """Load all YAML records below ``root_dir`` in deterministic path order."""

    return tuple(
        _load_record(path, kind=kind, normalize=normalize) for path in iter_yaml_paths(root_dir)
    )


def iter_yaml_paths(root_dir: Path) -> tuple[Path, ...]:
    """Return all ``.yml`` and ``.yaml`` files below ``root_dir`` sorted by path."""

    if not root_dir.exists():
        return ()

    paths = [
        path for suffix in ("*.yml", "*.yaml") for path in root_dir.rglob(suffix) if path.is_file()
    ]
    return tuple(sorted(paths))


type _Normalizer = Callable[[dict[str, Any]], dict[str, Any]]


def _load_record(
    path: Path,
    *,
    kind: DataKind,
    normalize: _Normalizer,
) -> LoadedYamlRecord:
    raw_data = _load_yaml_mapping(path)
    return LoadedYamlRecord(
        kind=kind,
        path=path,
        raw_data=raw_data,
        data=normalize(raw_data),
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as yaml_file:
            data = yaml.safe_load(yaml_file)
    except yaml.YAMLError as exc:
        raise YamlDataLoadError(path, f"invalid YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise YamlDataLoadError(path, "YAML document must be a mapping")

    return data


def _normalize_object(raw_data: dict[str, Any]) -> dict[str, Any]:
    data = deepcopy(raw_data)
    _setdefault_list(data, "external_refs")
    _setdefault_list(data, "measurements")
    _setdefault_list(data, "attachments")

    measurements = data.get("measurements")
    if isinstance(measurements, list):
        for measurement in measurements:
            if isinstance(measurement, dict):
                _setdefault_list(measurement, "tags")

    return data


def _normalize_cave(raw_data: dict[str, Any]) -> dict[str, Any]:
    data = deepcopy(raw_data)
    _setdefault_list(data, "external_refs")
    _setdefault_list(data, "object_ids")
    return data


def _normalize_relation(raw_data: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(raw_data)


def _setdefault_list(data: dict[str, Any], key: str) -> None:
    if key not in data:
        data[key] = []
