from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture
def make_data_dir() -> Callable[[Path], Path]:
    """Explicitly initialize a complete, empty source dataset for a test."""

    def create(path: Path) -> Path:
        for name in ("objects", "caves", "relations"):
            (path / name).mkdir(parents=True, exist_ok=True)
        return path

    return create
