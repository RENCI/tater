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

    Shows top-level categories as buttons. Clicking an intermediate node
    highlights it and reveals its children in a new row below. Clicking a
    leaf selects it as the annotation value. Clicking any button in an
    earlier row resets the selection from that level downward.

    An optional search bar filters across all leaf labels.

    Example usage::

        HierarchicalLabelWidget(
            schema_field="diagnosis",
            label="Diagnosis",
            hierarchy=build_tree_from_yaml("data/ontology.yaml"),
        )

    The schema field must be ``str`` or ``Optional[str]``.
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
        initial_sections = _build_sections(self.root, [], cid)

        return dmc.Stack(
            [
                dmc.TextInput(
                    id=f"hier-search-{cid}",
                    placeholder="Search…",
                    size="xs",
                    style={} if self.searchable else {"display": "none"},
                ),
                dmc.Stack(initial_sections, id=f"hier-sections-{cid}", gap="sm"),
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
        sections_id = f"hier-sections-{cid}"
        search_id = f"hier-search-{cid}"

        def node_at(path: list[str]) -> Node:
            node = root
            for name in path:
                child = node.find(name)
                if child is None:
                    return root
                node = child
            return node

        # ---- 1. Reset navigation when document changes ----
        @app.callback(
            Output(nav_id, "data"),
            Input("current-doc-id", "data"),
            prevent_initial_call=True,
        )
        def reset_nav(_doc_id):
            return []

        # ---- 2. Handle node button click → update path, write if leaf ----
        @app.callback(
            Output(nav_id, "data", allow_duplicate=True),
            Input({"type": "hier-node-btn", "field": cid, "idx": ALL, "name": ALL}, "n_clicks"),
            State(nav_id, "data"),
            State("current-doc-id", "data"),
            prevent_initial_call=True,
        )
        def handle_click(node_clicks, current_path, doc_id):
            if not ctx.triggered_id:
                return no_update
            triggered = ctx.triggered_id
            if not isinstance(triggered, dict) or triggered.get("type") != "hier-node-btn":
                return no_update

            idx = triggered["idx"]
            node_name = triggered["name"]
            path = list(current_path or [])

            # Resolve the clicked node
            parent = node_at(path[:idx])
            clicked = parent.find(node_name)
            if clicked is None:
                return no_update

            tater_app = app._tater_app

            if clicked.is_leaf:
                # Leaf selection is tracked via annotation value
                current_value = None
                annotation = None
                if doc_id and tater_app:
                    annotation = tater_app.annotations.get(doc_id)
                    if annotation is not None:
                        current_value = value_helpers.get_model_value(annotation, field_path)

                if current_value == node_name:
                    # Toggle off: clear annotation
                    if annotation is not None:
                        value_helpers.set_model_value(annotation, field_path, None)
                        tater_app._save_annotations_to_file()
                    return path[:idx]
                else:
                    if annotation is not None:
                        value_helpers.set_model_value(annotation, field_path, node_name)
                        tater_app._save_annotations_to_file()
                    return path[:idx] + [node_name]
            else:
                # Intermediate node: toggle collapses from this level
                if idx < len(path) and path[idx] == node_name:
                    return path[:idx]
                return path[:idx] + [node_name]

        # ---- 3. Rebuild sections from nav state / search / doc change ----
        @app.callback(
            Output(sections_id, "children"),
            Input(nav_id, "data"),
            Input(search_id, "value"),
            Input("current-doc-id", "data"),
            prevent_initial_call=False,
        )
        def update_display(current_path, search_query, doc_id):
            path = list(current_path or [])
            tater_app = app._tater_app

            # Read current annotation value
            selected_value = None
            if doc_id and tater_app:
                annotation = tater_app.annotations.get(doc_id)
                if annotation is not None:
                    selected_value = value_helpers.get_model_value(annotation, field_path)

            # Search mode
            if search_query and search_query.strip():
                q = search_query.strip().lower()
                matches = [n for n in root.all_leaves() if q in n.name.lower()]
                search_buttons = _make_buttons(matches, cid, idx=0, selected_name=selected_value)
                return [_section("Search results", search_buttons)]

            # Normal mode: stack a section per level
            return _build_sections(root, path, cid, selected_value=selected_value)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _section(label: str, buttons: list) -> Any:
    return dmc.Stack(
        [
            dmc.Text(label, size="xs", c="dimmed", fw=500),
            dmc.Group(buttons, gap="xs", wrap="wrap"),
        ],
        gap="xs",
    )


def _make_buttons(
    nodes: list[Node],
    field: str,
    idx: int,
    selected_name: Optional[str] = None,
) -> list:
    return [
        dmc.Button(
            node.name,
            id={"type": "hier-node-btn", "field": field, "idx": idx, "name": node.name},
            size="xs",
            variant="filled" if node.name == selected_name else (
                "default" if not node.is_leaf else "light"
            ),
            n_clicks=0,
        )
        for node in nodes
    ]


def _build_sections(
    root: Node,
    path: list[str],
    cid: str,
    selected_value: Optional[str] = None,
) -> list:
    """Build the stacked level sections for the current navigation path."""
    sections = []

    # Level 0: root's children, label "Top level categories"
    selected_at = path[0] if path else None
    level_label = "Top level categories"
    buttons = _make_buttons(root.children, cid, idx=0, selected_name=selected_at or selected_value)
    sections.append(_section(level_label, buttons))

    # Each subsequent level revealed by selection
    current_node = root
    for depth, name in enumerate(path):
        child = current_node.find(name)
        if child is None or child.is_leaf:
            break
        current_node = child
        selected_at = path[depth + 1] if depth + 1 < len(path) else None
        buttons = _make_buttons(
            current_node.children,
            cid,
            idx=depth + 1,
            selected_name=selected_at or selected_value,
        )
        sections.append(_section(current_node.name, buttons))

    return sections
