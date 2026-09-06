"""Safe YAML with unique mapping keys and explicit, non-shared values."""

from collections.abc import Hashable
from pathlib import Path
from typing import Any

import yaml
from yaml.constructor import ConstructorError
from yaml.events import AliasEvent
from yaml.nodes import MappingNode, Node


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Keep SafeLoader scalar/date types; reject duplicates, aliases and merges."""

    def compose_node(self, parent: Node | None, index: Any) -> Node:
        if self.check_event(AliasEvent):
            event = self.peek_event()
            raise ConstructorError(
                None,
                None,
                "YAML aliases are not supported; write values explicitly",
                event.start_mark,
            )
        return super().compose_node(parent, index)

    def construct_scalar(self, node: Node) -> str:
        # SafeLoader accepts !!str {=: value, ...} and discards other keys.
        # A scalar must not hide a mapping from the checks below.
        if isinstance(node, MappingNode):
            raise ConstructorError(
                None, None, "scalar-tagged mappings are not supported", node.start_mark
            )
        return super().construct_scalar(node)

    def construct_mapping(self, node: Node, deep: bool = False) -> dict:
        if not isinstance(node, MappingNode):
            return super().construct_mapping(node, deep=deep)

        # Check before SafeLoader can flatten a merge into an implicit override.
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                raise ConstructorError(
                    None,
                    None,
                    "YAML merge keys are not supported; write values explicitly",
                    key_node.start_mark,
                )
        self.flatten_mapping(node)
        mapping = {}
        marks = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, Hashable):
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found unhashable key",
                    key_node.start_mark,
                )
            if key in mapping:
                raise ConstructorError(
                    f"first occurrence of key {key!r}",
                    marks[key],
                    f"duplicate key {key!r}",
                    key_node.start_mark,
                )
            marks[key] = key_node.start_mark
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def load_yaml(path: Path) -> Any:
    """Read one document, retaining file/line marks in PyYAML errors."""

    with path.open(encoding="utf-8") as yaml_file:
        return yaml.load(yaml_file, Loader=_UniqueKeySafeLoader)
