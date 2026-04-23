"""Hierarchical label widget for tree-based label selection."""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
import json
from pathlib import Path
from typing import Any, List, Optional, Union

from dash import dcc, html
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from tater.widgets.base import ControlWidget, TaterWidget, _unwrap_optional, _resolve_field_info


# ---------------------------------------------------------------------------
# Tree data structure
# ---------------------------------------------------------------------------

@dataclass
class Node:
    """A node in the label hierarchy tree."""

    name: str
    children: list[Node] = dc_field(default_factory=list)

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def find(self, name: str) -> Optional[Node]:
        for child in self.children:
            if child.name == name:
                return child
        return None

    def all_leaves(self) -> list[Node]:
        if self.is_leaf:
            return [self]
        result = []
        for child in self.children:
            result.extend(child.all_leaves())
        return result

    def all_nodes(self) -> list[Node]:
        """BFS traversal of the subtree (self included)."""
        result, queue = [], [self]
        while queue:
            node = queue.pop(0)
            result.append(node)
            queue.extend(node.children)
        return result


def _build_tree(name: str, data: Any) -> Node:
    if data is None or data == [] or data == {}:
        return Node(name)
    if isinstance(data, list):
        children = []
        for item in data:
            if isinstance(item, dict):
                for k, v in item.items():
                    children.append(_build_tree(k, v))
            else:
                children.append(Node(str(item)))
        return Node(name, children)
    if isinstance(data, dict):
        return Node(name, [_build_tree(k, v) for k, v in data.items()])
    return Node(str(data))


def _node_at(root: Node, path: list[str]) -> Node:
    """Return the node reached by traversing *path* from *root*, or *root* on failure."""
    node = root
    for name in path:
        child = node.find(name)
        if child is None:
            return root
        node = child
    return node


def _find_path(root: Node, name: str) -> list[str]:
    """Return the path (list of node names) from root's children to the named node.

    Returns an empty list if not found.
    """
    def _dfs(node: Node, target: str, current: list[str]) -> Optional[list[str]]:
        for child in node.children:
            path = current + [child.name]
            if child.name == target:
                return path
            result = _dfs(child, target, path)
            if result is not None:
                return result
        return None

    result = _dfs(root, name, [])
    return result if result is not None else []


def build_tree(hierarchy: Union[dict, list]) -> Node:
    """Build a Node tree from a Python dict or list.

    Dict with multiple top-level keys creates a virtual ``__root__`` node::

        {
            "Animals": {"Mammals": ["Dog", "Cat"], "Birds": ["Parrot"]},
            "Plants": ["Rose", "Oak"],
        }

    Dict with a single top-level key uses that key as the root::

        {"Animals": {"Mammals": ["Dog", "Cat"]}}

    A flat list creates a one-level tree::

        ["cat", "dog", "fish"]
    """
    if isinstance(hierarchy, list):
        return _build_tree("__root__", hierarchy)
    if isinstance(hierarchy, dict):
        if len(hierarchy) == 1:
            name, data = next(iter(hierarchy.items()))
            return _build_tree(name, data)
        return Node("__root__", [_build_tree(k, v) for k, v in hierarchy.items()])
    raise TypeError(f"hierarchy must be dict or list, got {type(hierarchy)}")


def load_hierarchy_from_yaml(path: Union[str, Path]) -> Node:
    """Build a Node tree from a YAML file.

    Supported YAML formats::

        # Multi-key top-level (creates virtual root)
        Category A:
            Sub1:
            - Item 1
            - Item 2
            Sub2: []          # Sub2 itself is a selectable leaf
        Category B:
        - Item 3
        - Item 4
    """
    import yaml  # soft dependency
    with open(path) as f:
        data = yaml.safe_load(f)
    return build_tree(data)


# ---------------------------------------------------------------------------
# Shared data-building helper
# ---------------------------------------------------------------------------

def _build_dropdown_data(root: Node, allow_non_leaf: bool = False) -> list:
    """Build dmc.Select / dmc.MultiSelect data from a Node tree.

    Each item: ``{value: '["A","B","C"]', label: "C"}``.
    ``value`` is the full path serialized as a compact JSON array (no spaces), which
    uniquely identifies the node even when leaf names are duplicated across the tree.
    ``label`` is the plain node name; depth-based indentation is handled by the
    ``hlRenderOption`` JS function via the ``renderOption`` prop.
    Depth is relative to root's children (root itself is not included).
    """
    items = []

    def _walk(node: Node, path: list[str]) -> None:
        if node.name == "__root__":
            for child in node.children:
                _walk(child, [])
            return
        current_path = path + [node.name]
        value = json.dumps(current_path, separators=(",", ":"))
        if node.is_leaf:
            items.append({"value": value, "label": node.name, "leaf": True})
        else:
            # Non-leaf nodes always appear to provide hierarchy context.
            # Disabled when allow_non_leaf=False so they act as visual headers only.
            item = {"value": value, "label": node.name, "leaf": False}
            if not allow_non_leaf:
                item["disabled"] = True
            items.append(item)
            for child in node.children:
                _walk(child, current_path)

    for child in root.children:
        _walk(child, [])
    return items


# ---------------------------------------------------------------------------
# Base widget
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class HierarchicalLabelWidget(ControlWidget):
    """Base class for hierarchical label widgets.

    Holds the shared hierarchy/root/allow_non_leaf state used by both
    HierarchicalLabelSelectWidget (single) and HierarchicalLabelMultiWidget (multi).
    """

    hierarchy: Union[Node, dict, list, str, Path, None] = None
    allow_non_leaf: bool = False
    root: Node = dc_field(init=False, repr=False)
    # Pre-serialized value injected by repeater._render_item_widgets so the
    # component renders with the correct value without waiting for a callback.
    _preset_value: Any = dc_field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        if isinstance(self.hierarchy, (str, Path)):
            self.root = load_hierarchy_from_yaml(self.hierarchy)
        elif isinstance(self.hierarchy, Node):
            self.root = self.hierarchy
        else:
            self.root = build_tree(self.hierarchy or {})

    # ------------------------------------------------------------------
    # TaterWidget interface
    # ------------------------------------------------------------------

    @property
    def renders_own_label(self) -> bool:
        return True

    def to_python_type(self) -> type:
        return list

    def bind_schema(self, model: type) -> None:
        import typing
        field_info = _resolve_field_info(model, self.field_path)
        if field_info is None:
            raise ValueError(
                f"{self.__class__.__name__}: field '{self.field_path}' not found in {model.__name__}"
            )
        inner = _unwrap_optional(field_info.annotation)
        origin = typing.get_origin(inner)
        args = typing.get_args(inner)
        if not (origin is list and args and args[0] is str):
            raise TypeError(
                f"{self.__class__.__name__}: field '{self.field_path}' must be List[str] or "
                f"Optional[List[str]], got {field_info.annotation!r}"
            )

    def register_callbacks(self, app: Any) -> None:
        pass

    def _input_wrapper(self, children: Any) -> dmc.InputWrapper:
        """Label group with browser button, plus auto-advance tooltip when enabled."""
        pipe_field = self.field_path.replace(".", "|")
        label = self._label_with_browser_btn(pipe_field)
        if self.auto_advance:
            label = dmc.Group(
                [
                    label,
                    dmc.Tooltip(
                        DashIconify(
                            icon="tabler:circle-open-arrow-right",
                            width=13,
                            color="var(--mantine-color-dimmed)",
                        ),
                        label="Auto-advances to next document",
                        position="right",
                        withArrow=True,
                    ),
                ],
                gap=4,
            )
        return TaterWidget._input_wrapper(
            self,
            children,
            label,
            self.required,
            {"style": {"display": "inline-flex", "alignItems": "center", "gap": "4px"}},
        )

    # ------------------------------------------------------------------
    # Hierarchy browser helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _render_tree_html(root: "Node") -> Any:
        """Build a nested html.Ul/Li tree from a Node for the browser modal."""

        def _children_ul(node: "Node") -> html.Ul:
            return html.Ul(
                [_node(child) for child in node.children],
                style={
                    "listStyleType": "none",
                    "paddingLeft": "1em",
                    "margin": "2px 0 4px 0",
                    "borderLeft": "2px solid var(--mantine-color-default-border)",
                },
            )

        def _node(node: "Node") -> html.Li:
            if node.is_leaf:
                return html.Li(
                    node.name,
                    style={"padding": "1px 4px"},
                )
            return html.Li(
                [
                    html.Span(node.name, style={"fontWeight": 600}),
                    _children_ul(node),
                ],
                style={"padding": "2px 0"},
            )

        top_nodes = root.children if root.name == "__root__" else [root]
        return html.Div(
            html.Ul(
                [_node(n) for n in top_nodes],
                style={"listStyleType": "none", "padding": 0, "margin": 0},
            ),
            style={
                "maxHeight": "65vh",
                "overflowY": "auto",
                "fontSize": "var(--mantine-font-size-sm)",
                "lineHeight": 1.7,
            },
        )

    def _label_with_browser_btn(self, pipe_field: str) -> Any:
        """Return a label group with an inline hierarchy-browser action icon."""
        return dmc.Group(
            [
                self.label,
                dmc.ActionIcon(
                    DashIconify(icon="tabler:binary-tree-2", width=14),
                    id={"type": "hl-browser-btn", "field": pipe_field},
                    size="xs",
                    variant="subtle",
                    color="gray",
                ),
            ],
            gap=4,
            align="center",
        )

    def _browser_modal(self, pipe_field: str) -> dmc.Modal:
        """Return a hidden Modal containing the full hierarchy tree."""
        return dmc.Modal(
            id={"type": "hl-browser-modal", "field": pipe_field},
            title=self.label,
            children=self._render_tree_html(self.root),
            opened=False,
            size="lg",
            centered=True,
        )


# ---------------------------------------------------------------------------
# HierarchicalLabelSelectWidget  (single-select dropdown)
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class HierarchicalLabelSelectWidget(HierarchicalLabelWidget):
    """Single-select hierarchical widget using dmc.Select with depth-indented options.

    Stores ``Optional[List[str]]`` — the full path to the selected node
    (e.g. ``["Animals", "Mammals", "Dog"]``).  The dropdown uses
    ``renderOption`` (``hlRenderOption`` JS function) to indent each
    option based on its depth in the hierarchy and highlight the search match.
    Search is handled natively by Mantine via the ``hlFilter`` JS function,
    which also accepts the sentinel config for sibling/child expansion.

    ``search_show_siblings``: also show sibling nodes of each matched term.
    ``search_show_children``: also show direct children of each matched term.
    Ancestor nodes are always included to provide hierarchy context.

    Component IDs use ``hl-select-*`` types; a single MATCH callback in
    ``setup_hl_select_callbacks`` handles all instances.
    """

    search_show_siblings: bool = False
    search_show_children: bool = False

    def _serialize_value(self, v: Any) -> Any:
        """Serialize a stored path list to the string value expected by dmc.Select."""
        return json.dumps(v, separators=(",", ":")) if v else None

    @property
    def schema_id(self) -> dict:
        return {"type": "hl-select", "ld": self._repeater_ld, "path": self._repeater_path, "tf": self._item_relative_tf}

    def component(self) -> Any:
        pipe_field = self.field_path.replace(".", "|")
        data = _build_dropdown_data(self.root, self.allow_non_leaf)
        # Prepend sentinel encoding filter config for hlFilter (same pattern as Multi).
        sentinel_config = json.dumps({
            "showSiblings": self.search_show_siblings,
            "showChildren": self.search_show_children,
        })
        sentinel = {"value": f"__config__{sentinel_config}", "label": "", "disabled": True}
        return self._input_wrapper(
            dmc.Stack(
                [
                    dmc.Select(
                        id={"type": "hl-select", "field": pipe_field},
                        data=[sentinel] + data,
                        value=self._preset_value,
                        searchable=True,
                        clearable=True,
                        autoSelectOnBlur=True,
                        placeholder="Search…",
                        size="sm",
                        renderOption={"function": "hlRenderOption"},
                        filter={"function": "hlFilter"},
                        comboboxProps={"shadow": "md"},
                    ),
                    dcc.Store(id={"type": "hl-select-relay", "field": pipe_field}, data=None),
                    self._browser_modal(pipe_field),
                ],
                gap="xs",
            ),
        )

    def register_callbacks(self, app: Any) -> None:
        pass  # Handled by setup_hl_select_callbacks


# ---------------------------------------------------------------------------
# HierarchicalLabelMultiWidget  (multi-select dropdown)
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class HierarchicalLabelMultiWidget(HierarchicalLabelWidget):
    """Multi-select hierarchical widget using dmc.MultiSelect with depth-indented options.

    Stores ``Optional[List[List[str]]]`` — a list of full paths, one per selection.
    The dropdown uses ``renderOption`` (``hlRenderOption`` JS function) to indent
    each option based on its depth in the hierarchy. Selected pills show the node name only.
    Search is handled natively by Mantine (matches against the label, i.e. node name).

    ``search_show_siblings``: also show sibling nodes of each matched term.
    ``search_show_children``: also show direct children of each matched term.
    Ancestor nodes are always included to provide hierarchy context.

    Component IDs use ``hl-multi-*`` types; a single MATCH callback in
    ``setup_hl_multi_callbacks`` handles all instances.
    """

    search_show_siblings: bool = False
    search_show_children: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
        self.auto_advance = False  # auto-advance is not meaningful for multi-select

    def to_python_type(self) -> type:
        return list

    def bind_schema(self, model: type) -> None:
        import typing as _t
        field_info = _resolve_field_info(model, self.field_path)
        if field_info is None:
            raise ValueError(
                f"{self.__class__.__name__}: field '{self.field_path}' not found in {model.__name__}"
            )
        inner = _unwrap_optional(field_info.annotation)
        origin = _t.get_origin(inner)
        args = _t.get_args(inner)
        # Expect List[List[str]]
        if origin is list and args:
            item_origin = _t.get_origin(args[0])
            item_args = _t.get_args(args[0])
            if item_origin is list and item_args and item_args[0] is str:
                return
        raise TypeError(
            f"{self.__class__.__name__}: field '{self.field_path}' must be "
            f"List[List[str]] or Optional[List[List[str]]], got {field_info.annotation!r}"
        )

    def _serialize_value(self, v: Any) -> Any:
        """Serialize a list of stored paths to the list of JSON strings expected by dmc.MultiSelect."""
        return [json.dumps(p, separators=(",", ":")) for p in v] if v else []

    @property
    def schema_id(self) -> dict:
        return {"type": "hl-multi", "ld": self._repeater_ld, "path": self._repeater_path, "tf": self._item_relative_tf}

    def component(self) -> Any:
        pipe_field = self.field_path.replace(".", "|")
        data = _build_dropdown_data(self.root, self.allow_non_leaf)
        # Prepend a hidden sentinel item encoding filter config as JSON for the JS filter
        # function (hlFilter in utils.js). The sentinel value starts with "__config__"
        # followed by a JSON object. The filter function detects this prefix, parses the
        # config, and strips the sentinel from the returned options.
        sentinel_config = json.dumps({"showSiblings": self.search_show_siblings, "showChildren": self.search_show_children})
        sentinel = {"value": f"__config__{sentinel_config}", "label": "", "disabled": True}
        return self._input_wrapper(
            dmc.Stack(
                [
                    dmc.MultiSelect(
                        id={"type": "hl-multi", "field": pipe_field},
                        data=[sentinel] + data,
                        value=self._preset_value if self._preset_value is not None else [],
                        searchable=True,
                        clearSearchOnChange=False,
                        clearable=True,
                        placeholder="Search…",
                        size="sm",
                        renderOption={"function": "hlRenderOption"},
                        filter={"function": "hlFilter"},
                        comboboxProps={"shadow": "md"},
                    ),
                    dcc.Store(id={"type": "hl-multi-relay", "field": pipe_field}, data=None),
                    self._browser_modal(pipe_field),
                ],
                gap="xs",
            ),
        )

    def register_callbacks(self, app: Any) -> None:
        pass  # Handled by setup_hl_multi_callbacks
