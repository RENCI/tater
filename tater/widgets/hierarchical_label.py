"""Hierarchical label widget for tree-based label selection."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

from dash import dcc, Input, Output, State, ALL, no_update, ctx
import dash_mantine_components as dmc

from tater.widgets.base import TaterWidget, _unwrap_optional, _resolve_field_info


# ---------------------------------------------------------------------------
# Tree data structure
# ---------------------------------------------------------------------------

@dataclass
class Node:
    """A node in the label hierarchy tree."""

    name: str
    children: list[Node] = field(default_factory=list)

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def find(self, name: str) -> Optional[Node]:
        """Return a direct child by name, or None."""
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
    """Recursively build a Node from a name + nested dict/list value."""
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


def build_tree_from_yaml(path: Union[str, Path]) -> Node:
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
# Widget
# ---------------------------------------------------------------------------

class HierarchicalLabelWidget(TaterWidget):
    """Progressive disclosure widget for tree-based label selection.

    Users navigate level-by-level through a hierarchy of labels. Clicking an
    intermediate node drills down; clicking a leaf selects it.  An optional
    search bar filters across all leaf labels.

    Example usage::

        HierarchicalLabelWidget(
            schema_field="diagnosis",
            label="Diagnosis",
            hierarchy=build_tree_from_yaml("data/ontology.yaml"),
        )

    The corresponding schema field must be ``str`` or ``Optional[str]``.
    """

    def __init__(
        self,
        schema_field: str,
        label: str = "",
        hierarchy: Union[Node, dict, list, None] = None,
        description: Optional[str] = None,
        searchable: bool = True,
    ):
        super().__init__(schema_field=schema_field, label=label, description=description)
        if isinstance(hierarchy, Node):
            self.root = hierarchy
        else:
            self.root = build_tree(hierarchy or {})
        self.searchable = searchable

    # ------------------------------------------------------------------
    # TaterWidget interface
    # ------------------------------------------------------------------

    @property
    def renders_own_label(self) -> bool:
        return False

    def to_python_type(self) -> type:
        return str

    def bind_schema(self, model: type) -> None:
        field_info = _resolve_field_info(model, self.field_path)
        if field_info is None:
            raise ValueError(
                f"HierarchicalLabelWidget: field '{self.field_path}' not found in {model.__name__}"
            )
        inner = _unwrap_optional(field_info.annotation)
        if inner is not str:
            raise TypeError(
                f"HierarchicalLabelWidget: field '{self.field_path}' must be str or "
                f"Optional[str], got {field_info.annotation!r}"
            )

    def component(self) -> Any:
        cid = self.component_id
        initial_buttons = _make_buttons(self.root.children, cid)

        return dmc.Stack(
            [
                # Navigation row: back button + breadcrumb path
                dmc.Group(
                    [
                        dmc.ActionIcon(
                            "←",
                            id=f"hier-back-{cid}",
                            variant="subtle",
                            size="sm",
                            n_clicks=0,
                        ),
                        dmc.Text("", id=f"hier-crumb-{cid}", size="sm", c="dimmed"),
                    ],
                    gap="xs",
                ),
                # Currently selected value
                dmc.Text("", id=f"hier-selected-{cid}", size="sm", fw=500),
                # Search input (always in DOM; hidden when searchable=False)
                dmc.TextInput(
                    id=f"hier-search-{cid}",
                    placeholder="Search…",
                    size="xs",
                    style={} if self.searchable else {"display": "none"},
                ),
                # Node buttons (dynamically updated)
                dmc.Group(initial_buttons, id=f"hier-buttons-{cid}", gap="xs", wrap="wrap"),
                # Navigation state store
                dcc.Store(id=f"hier-nav-{cid}", data=[]),
            ],
            gap="xs",
        )

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def register_callbacks(self, app: Any) -> None:
        from tater.ui import value_helpers

        field_path = self.field_path
        cid = self.component_id
        root = self.root

        nav_id = f"hier-nav-{cid}"
        back_id = f"hier-back-{cid}"
        buttons_id = f"hier-buttons-{cid}"
        crumb_id = f"hier-crumb-{cid}"
        selected_id = f"hier-selected-{cid}"
        search_id = f"hier-search-{cid}"

        def node_at(path: list[str]) -> Node:
            node = root
            for name in path:
                child = node.find(name)
                if child is None:
                    return root
                node = child
            return node

        def crumb_label(path: list[str]) -> str:
            parts = ([] if root.name == "__root__" else [root.name]) + list(path)
            return " › ".join(parts) if parts else ""

        # ---- 1. Reset navigation when document changes ----
        @app.callback(
            Output(nav_id, "data"),
            Input("current-doc-id", "data"),
            prevent_initial_call=True,
        )
        def reset_nav(_doc_id):
            return []

        # ---- 2. Handle node click or back button → navigate / select ----
        @app.callback(
            Output(nav_id, "data", allow_duplicate=True),
            Input({"type": "hier-node-btn", "field": cid, "name": ALL}, "n_clicks"),
            Input(back_id, "n_clicks"),
            State(nav_id, "data"),
            State("current-doc-id", "data"),
            prevent_initial_call=True,
        )
        def handle_click(node_clicks, _back, current_path, doc_id):
            if not ctx.triggered_id:
                return no_update

            path = list(current_path or [])

            # Back button
            if ctx.triggered_id == back_id:
                return path[:-1]

            triggered = ctx.triggered_id
            if not isinstance(triggered, dict) or triggered.get("type") != "hier-node-btn":
                return no_update

            node_name = triggered["name"]
            current_node = node_at(path)
            clicked = current_node.find(node_name)

            # Fall back to full-tree search (handles search result clicks)
            if clicked is None:
                clicked = next(
                    (n for n in root.all_nodes() if n.name == node_name), None
                )
            if clicked is None:
                return no_update

            if clicked.is_leaf:
                # Save the selection
                tater_app = app._tater_app
                if doc_id and tater_app:
                    annotation = tater_app.annotations.get(doc_id)
                    if annotation is not None:
                        value_helpers.set_model_value(annotation, field_path, clicked.name)
                        tater_app._save_annotations_to_file()
                return path  # stay at current level after selecting
            else:
                return path + [node_name]

        # ---- 3. Update buttons, breadcrumb, and selected label ----
        @app.callback(
            Output(buttons_id, "children"),
            Output(crumb_id, "children"),
            Output(selected_id, "children"),
            Input(nav_id, "data"),
            Input(search_id, "value"),
            Input("current-doc-id", "data"),
            prevent_initial_call=False,
        )
        def update_display(current_path, search_query, doc_id):
            path = list(current_path or [])
            tater_app = app._tater_app

            # Read current annotation value for this doc
            selected_text = ""
            if doc_id and tater_app:
                annotation = tater_app.annotations.get(doc_id)
                if annotation is not None:
                    val = value_helpers.get_model_value(annotation, field_path)
                    if val:
                        selected_text = f"✓ {val}"

            # Search mode: show matching leaves as flat buttons
            if search_query and search_query.strip():
                q = search_query.strip().lower()
                matches = [n for n in root.all_leaves() if q in n.name.lower()]
                return _make_buttons(matches, cid), crumb_label(path), selected_text

            # Normal navigation: show current level's children
            current_node = node_at(path)
            return _make_buttons(current_node.children, cid), crumb_label(path), selected_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_buttons(nodes: list[Node], field: str) -> list:
    """Build Dash Button components for a list of nodes."""
    return [
        dmc.Button(
            node.name,
            id={"type": "hier-node-btn", "field": field, "name": node.name},
            size="xs",
            variant="light" if node.is_leaf else "outline",
            rightSection="›" if not node.is_leaf else None,
            n_clicks=0,
        )
        for node in nodes
    ]
