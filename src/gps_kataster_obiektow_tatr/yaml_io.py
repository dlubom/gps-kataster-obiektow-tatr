"""Safe YAML input with unique mapping keys, including expanded merges."""

from __future__ import annotations

from collections.abc import Hashable
from pathlib import Path
from typing import Any

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode


class _UniqueKeySafeLoader(yaml.SafeLoader):
    def flatten_mapping(self, node: MappingNode) -> None:
        # Check before flattening too: PyYAML removes merge directives, and a
        # mapping used only by a merge may never be constructed independently.
        self._check_unique_keys(node)
        super().flatten_mapping(node)
        self._check_unique_keys(node)

    def _check_unique_keys(self, node: MappingNode) -> None:
        seen = {}
        for key_node, _ in node.value:
            # SafeConstructor handles these special scalar tags during flattening.
            if key_node.tag in {"tag:yaml.org,2002:merge", "tag:yaml.org,2002:value"}:
                key = self.construct_scalar(key_node)
            else:
                key = self.construct_object(key_node)
            if not isinstance(key, Hashable):
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found unhashable key",
                    key_node.start_mark,
                )
            if key in seen:
                raise ConstructorError(
                    "first occurrence of key",
                    seen[key],
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            seen[key] = key_node.start_mark


def load_unique_yaml(path: Path) -> Any:
    """Load one safe document; report collisions with both source positions.

    Keep constructors private to this loader; ordinary PyYAML users are unchanged.
    Domain callers translate YAML errors into their public exception types.
    """

    with path.open(encoding="utf-8") as stream:
        return yaml.load(stream, Loader=_UniqueKeySafeLoader)
