"""
Tree-sitter-backed symbol metadata.

Line numbers follow tree-sitter's coordinate system (0-based row indices), consistent
with ``start_line_no`` / ``end_line_no`` on chunks.

``symbols`` lists the *simple names* of definitions whose line span **overlaps** the
chunk's span (inclusive on both ends). Two ranges [a, b] and [c, d] overlap iff
not (b < c or d < a).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, List, Optional

import tree_sitter as ts

# (node_type, field_name_for_name) — field_name None means use heuristics
_PYTHON_DEFS: tuple[tuple[str, Optional[str]], ...] = (
    ("function_definition", "name"),
    ("class_definition", "name"),
)

_JAVA_DEFS: tuple[tuple[str, Optional[str]], ...] = (
    ("method_declaration", "name"),
    ("constructor_declaration", "name"),
    ("class_declaration", "name"),
    ("interface_declaration", "name"),
    ("enum_declaration", "name"),
)

_CSHARP_DEFS: tuple[tuple[str, Optional[str]], ...] = (
    ("method_declaration", "name"),
    ("constructor_declaration", "name"),
    ("class_declaration", "name"),
    ("struct_declaration", "name"),
    ("interface_declaration", "name"),
    ("enum_declaration", "name"),
    ("record_declaration", "name"),
    ("delegate_declaration", "name"),
)

_TYPESCRIPT_DEFS: tuple[tuple[str, Optional[str]], ...] = (
    ("function_declaration", "name"),
    ("function_signature", "name"),
    ("class_declaration", "name"),
    ("interface_declaration", "name"),
    ("type_alias_declaration", "name"),
    ("enum_declaration", "name"),
    ("method_definition", "name"),
    ("method_signature", "name"),
)

_GO_DEFS: tuple[tuple[str, Optional[str]], ...] = (
    ("function_declaration", "name"),
    ("method_declaration", "name"),
    ("type_declaration", None),
    ("const_declaration", None),
    ("var_declaration", None),
)

_RUST_DEFS: tuple[tuple[str, Optional[str]], ...] = (
    ("function_item", "name"),
    ("struct_item", "name"),
    ("enum_item", "name"),
    ("trait_item", "name"),
    ("type_item", "name"),
    ("mod_item", "name"),
    ("impl_item", "type"),
    ("macro_definition", "name"),
)

_JAVASCRIPT_DEFS: tuple[tuple[str, Optional[str]], ...] = (
    ("function_declaration", "name"),
    ("class_declaration", "name"),
    ("lexical_declaration", None),
    ("export_statement", None),
)

_DEF_CONFIG: dict[str, tuple[tuple[str, Optional[str]], ...]] = {
    "python": _PYTHON_DEFS,
    "java": _JAVA_DEFS,
    "csharp": _CSHARP_DEFS,
    "typescript": _TYPESCRIPT_DEFS,
    "go": _GO_DEFS,
    "rust": _RUST_DEFS,
    "javascript": _JAVASCRIPT_DEFS,
}


def definition_node_types(language: str) -> FrozenSet[str]:
    """Node types treated as named definitions for chunking strategies."""
    cfg = _DEF_CONFIG.get(language)
    if not cfg:
        return frozenset()
    return frozenset(t for t, _ in cfg)


@dataclass(frozen=True)
class DefinitionSpan:
    name: str
    start_line: int
    end_line: int
    node_type: str


def _first_identifier_text(node: ts.Node) -> Optional[str]:
    # Grammars vary: Go uses type_identifier; JS uses shorthand_property_identifier, etc.
    if node.type in (
        "identifier",
        "type_identifier",
        "field_identifier",
        "property_identifier",
    ) and node.text:
        return node.text.decode("utf-8")
    for child in node.children:
        found = _first_identifier_text(child)
        if found:
            return found
    return None


def _extract_def_name(node: ts.Node, field_name: Optional[str]) -> Optional[str]:
    if field_name:
        name_node = node.child_by_field_name(field_name)
        if name_node is not None and name_node.text:
            return name_node.text.decode("utf-8")
    # Fallback: some grammars use identifier child
    return _first_identifier_text(node)


def _walk_definitions(
    node: ts.Node,
    pairs: tuple[tuple[str, Optional[str]], ...],
    out: List[DefinitionSpan],
) -> None:
    for ntype, fname in pairs:
        if node.type == ntype:
            name = _extract_def_name(node, fname)
            if name:
                out.append(
                    DefinitionSpan(
                        name=name,
                        start_line=node.start_point.row,
                        end_line=node.end_point.row,
                        node_type=ntype,
                    )
                )
            break
    for child in node.children:
        _walk_definitions(child, pairs, out)


def collect_definitions(root: ts.Node, language: str) -> List[DefinitionSpan]:
    """Depth-first list of named definitions in the tree (preorder by visit)."""
    pairs = _DEF_CONFIG.get(language)
    if not pairs:
        return []
    out: List[DefinitionSpan] = []
    _walk_definitions(root, pairs, out)
    return out


def symbols_overlapping_chunk(
    definitions: List[DefinitionSpan],
    chunk_start_line: int,
    chunk_end_line: int,
) -> List[str]:
    """
    Names of definitions whose line range overlaps the chunk (inclusive), stable-sorted unique.
    """
    seen: set[str] = set()
    ordered: List[str] = []
    for d in definitions:
        if chunk_end_line < d.start_line or d.end_line < chunk_start_line:
            continue
        if d.name not in seen:
            seen.add(d.name)
            ordered.append(d.name)
    return ordered


def is_definition_node(node: ts.Node, language: str) -> bool:
    return node.type in definition_node_types(language)
