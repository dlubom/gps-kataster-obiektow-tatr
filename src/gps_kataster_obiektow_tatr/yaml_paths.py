"""Shared discovery and filename-based numbering of source YAML records."""

import re
from pathlib import Path


def iter_yaml_paths(root_dir: Path) -> tuple[Path, ...]:
    """Return all ``.yml`` and ``.yaml`` files below ``root_dir`` sorted by path."""

    if not root_dir.exists():
        return ()

    paths = [
        path for suffix in ("*.yml", "*.yaml") for path in root_dir.rglob(suffix) if path.is_file()
    ]
    return tuple(sorted(paths))


def existing_yaml_numbers(directory: Path, *, prefix: str) -> tuple[int, ...]:
    """Read reserved numbers from both YAML extensions in the loaded tree."""

    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    return tuple(
        sorted(
            int(match.group(1))
            for path in iter_yaml_paths(directory)
            if (match := pattern.fullmatch(path.stem))
        )
    )
