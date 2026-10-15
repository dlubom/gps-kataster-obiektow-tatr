from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture(
    params=[
        pytest.param(("measurements: []\nmeasurements: []\n", "measurements", 2), id="same-value"),
        pytest.param(
            (
                "measurements: [{id: m-001}, {id: m-002}]\nmeasurements: [{id: m-002}]\n",
                "measurements",
                2,
            ),
            id="history-replaced",
        ),
        pytest.param(("measurements: [{id: m-001, lat: 49, lat: 50}]\n", "lat", 1), id="nested"),
        pytest.param(("best_measurement: {mode: auto, mode: manual}\n", "mode", 1), id="best"),
        pytest.param(('id: KSW-0001\n"id": KSW-0002\n', "id", 2), id="quoted-key"),
        pytest.param(("decisions: []\ndecisions: []\n", "decisions", 2), id="decisions-list"),
        pytest.param(
            ("decisions: [{action: link_cave, action: reject}]\n", "action", 1), id="action"
        ),
        pytest.param(
            ("defaults: &d {notes: first, notes: second}\ncopy: *d\n", "notes", 1),
            id="alias-with-duplicate",
        ),
        pytest.param(
            ("key: &k measurements\n*k: []\nmeasurements: []\n", "measurements", 3),
            id="aliased-key",
        ),
        pytest.param(
            ("<<: {measurements: []}\nmeasurements: []\n", "measurements", 2),
            id="merge-override-after",
        ),
        pytest.param(
            ("measurements: []\n<<: {measurements: []}\n", "measurements", 1),
            id="merge-override-before",
        ),
        pytest.param(("<<: [{notes: first}, {notes: second}]\n", "notes", 1), id="merge-sequence"),
        pytest.param(("<<: {<<: {notes: first}, notes: second}\n", "notes", 1), id="nested-merge"),
        pytest.param(
            ("defaults: &d {notes: same}\nitem: {<<: *d, notes: same}\n", "notes", 2),
            id="anchored-merge-override",
        ),
        pytest.param(
            ("defaults: &d {notes: same}\nitem: {<<: [*d, *d]}\n", "notes", 1),
            id="repeated-merge-alias",
        ),
        pytest.param(("<<: {id: KSW-0001}\n<<: {notes: separate}\n", "<<", 2), id="repeated-merge"),
        pytest.param(
            ("<<: {<<: {id: KSW-0001}, <<: {notes: separate}}\n", "<<", 1),
            id="nested-repeated-merge",
        ),
        pytest.param(("1: first\ntrue: second\n", "True", 2), id="resolved-key-collision"),
    ]
)
def yaml_key_collision(request) -> tuple[str, str, int]:
    """Text, duplicated key and conflicting key line for both public loaders."""

    return request.param


@pytest.fixture
def make_data_dir() -> Callable[[Path], Path]:
    """Explicitly initialize a complete, empty source dataset for a test."""

    def create(path: Path) -> Path:
        for name in ("objects", "caves", "relations"):
            (path / name).mkdir(parents=True, exist_ok=True)
        return path

    return create
