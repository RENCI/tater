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
# Base widget
# ---------------------------------------------------------------------------

class HierarchicalLabelWidget(TaterWidget):
    """Base class for hierarchical label widgets.

    Subclasses implement ``_render_sections`` to control how the tree is
    displayed at each navigation depth.

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
                f"{self.__class__.__name__}: field '{self.field_path}' not found in {model.__name__}"
            )
        inner = _unwrap_optional(field_info.annotation)
        if inner is not str:
            raise TypeError(
                f"{self.__class__.__name__}: field '{self.field_path}' must be str or "
                f"Optional[str], got {field_info.annotation!r}"
            )

    # ------------------------------------------------------------------
    # Subclass interface
    # ------------------------------------------------------------------

    @property
    def _show_breadcrumb(self) -> bool:
        return False

    def _render_sections(
        self, path: list[str], cid: str, selected_value: Optional[str]
    ) -> list:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Component + callbacks
    # ------------------------------------------------------------------

    def component(self) -> Any:
        cid = self.component_id
        initial_sections = self._render_sections([], cid, None)

        return dmc.Stack(
            [
                dmc.TextInput(
                    id=f"hier-search-{cid}",
                    placeholder="Search…",
                    size="xs",
                    style={} if self.searchable else {"display": "none"},
                    rightSection=dmc.ActionIcon(
                        "×",
                        id=f"hier-search-clear-{cid}",
                        size="xs",
                        variant="transparent",
                        c="dimmed",
                        style={"display": "none"},
                    ),
                    rightSectionPointerEvents="all",
                ),
                dmc.Text(
                    "",
                    id=f"hier-breadcrumb-{cid}",
                    size="xs",
                    fw=600,
                    style={} if self._show_breadcrumb else {"display": "none"},
                ),
                dmc.Stack(initial_sections, id=f"hier-sections-{cid}", gap="sm"),
                dcc.Store(id=f"hier-nav-{cid}", data=[]),
            ],
            gap="xs",
        )

    def register_callbacks(self, app: Any) -> None:
        from tater.ui import value_helpers

        field_path = self.field_path
        cid = self.component_id
        root = self.root

        nav_id = f"hier-nav-{cid}"
        sections_id = f"hier-sections-{cid}"
        search_id = f"hier-search-{cid}"
        search_clear_id = f"hier-search-clear-{cid}"
        breadcrumb_id = f"hier-breadcrumb-{cid}"

        def node_at(path: list[str]) -> Node:
            node = root
            for name in path:
                child = node.find(name)
                if child is None:
                    return root
                node = child
            return node

        # ---- 1a. Show/hide clear button based on search value ----
        @app.callback(
            Output(search_clear_id, "style"),
            Input(search_id, "value"),
            prevent_initial_call=False,
        )
        def toggle_clear(value):
            return {} if value else {"display": "none"}

        # ---- 1b. Clear search on button click ----
        @app.callback(
            Output(search_id, "value", allow_duplicate=True),
            Input(search_clear_id, "n_clicks"),
            prevent_initial_call=True,
        )
        def clear_search(_):
            return ""

        # ---- 2. Reset navigation when document changes ----
        @app.callback(
            Output(nav_id, "data"),
            Input("current-doc-id", "data"),
            prevent_initial_call=True,
        )
        def reset_nav(_doc_id):
            return []

        # ---- 3. Handle node button click → update path, write if leaf ----
        @app.callback(
            Output(nav_id, "data", allow_duplicate=True),
            Output(search_id, "value", allow_duplicate=True),
            Input({"type": "hier-node-btn", "field": cid, "idx": ALL, "name": ALL}, "n_clicks"),
            State(nav_id, "data"),
            State("current-doc-id", "data"),
            prevent_initial_call=True,
        )
        def handle_click(node_clicks, current_path, doc_id):
            if not ctx.triggered_id:
                return no_update, no_update
            triggered = ctx.triggered_id
            if not isinstance(triggered, dict) or triggered.get("type") != "hier-node-btn":
                return no_update, no_update
            # Guard against phantom fires when buttons are re-rendered (n_clicks resets to 0)
            if not ctx.triggered or not ctx.triggered[0].get("value"):
                return no_update, no_update

            idx = triggered["idx"]
            node_name = triggered["name"]
            path = list(current_path or [])

            parent = node_at(path[:idx])
            clicked = parent.find(node_name)
            is_search_result = False
            if clicked is None:
                # Fallback: search result buttons have idx=0 but may be deep leaves
                clicked = next((n for n in root.all_leaves() if n.name == node_name), None)
                if clicked is None:
                    return no_update, no_update
                is_search_result = True

            tater_app = app._tater_app

            if clicked.is_leaf:
                current_value = None
                annotation = None
                if doc_id and tater_app:
                    annotation = tater_app.annotations.get(doc_id)
                    if annotation is not None:
                        current_value = value_helpers.get_model_value(annotation, field_path)

                if is_search_result:
                    # Navigate to parent level so siblings are shown
                    full_path = _find_path(root, node_name)
                    new_path = full_path[:-1]
                else:
                    new_path = path[:idx]

                if current_value == node_name:
                    # Toggle off: clear annotation
                    if annotation is not None:
                        value_helpers.set_model_value(annotation, field_path, None)
                        tater_app._save_annotations_to_file()
                else:
                    if annotation is not None:
                        value_helpers.set_model_value(annotation, field_path, node_name)
                        tater_app._save_annotations_to_file()

                clear_search = "" if is_search_result else no_update
                return new_path, clear_search
            else:
                # Intermediate node: toggle collapses from this level
                if idx < len(path) and path[idx] == node_name:
                    return path[:idx], no_update
                return path[:idx] + [node_name], no_update

        # ---- 4. Rebuild sections from nav state / search / doc change ----
        render_sections = self._render_sections  # capture for closure

        @app.callback(
            Output(sections_id, "children"),
            Output(breadcrumb_id, "children"),
            Input(nav_id, "data"),
            Input(search_id, "value"),
            Input("current-doc-id", "data"),
            prevent_initial_call=False,
        )
        def update_display(current_path, search_query, doc_id):
            path = list(current_path or [])
            tater_app = app._tater_app

            selected_value = None
            if doc_id and tater_app:
                annotation = tater_app.annotations.get(doc_id)
                if annotation is not None:
                    selected_value = value_helpers.get_model_value(annotation, field_path)

            breadcrumb = " → ".join(path) if path else "None selected"

            # Search mode: flat list of matching leaves
            if search_query and search_query.strip():
                q = search_query.strip().lower()
                matches = [n for n in root.all_leaves() if q in n.name.lower()]
                search_buttons = _make_buttons(matches, cid, idx=0, selected_name=selected_value)
                return [_section("Search results", search_buttons)], breadcrumb

            return render_sections(path, cid, selected_value), breadcrumb


# ---------------------------------------------------------------------------
# Concrete widgets
# ---------------------------------------------------------------------------

class HierarchicalLabelFullWidget(HierarchicalLabelWidget):
    """Progressive disclosure widget showing all sibling nodes at each level.

    Clicking an intermediate node reveals its children in a new section below.
    Clicking a node at an earlier level resets the selection from that level
    downward.
    """

    @property
    def _show_breadcrumb(self) -> bool:
        return True

    def _render_sections(
        self, path: list[str], cid: str, selected_value: Optional[str]
    ) -> list:
        return _build_sections_full(self.root, path, cid, selected_value=selected_value)


class HierarchicalLabelCompactWidget(HierarchicalLabelWidget):
    """Compact hierarchical widget showing only the selected node per level.

    Already-navigated levels collapse to a single highlighted button. Only
    the active (deepest) level shows all available options. Clicking a
    collapsed button at any earlier level expands it again.
    """

    def _render_sections(
        self, path: list[str], cid: str, selected_value: Optional[str]
    ) -> list:
        items = _build_sections_compact(self.root, path, cid, selected_value=selected_value)
        return [dmc.Stack(items, gap=2)]


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
    buttons = []
    for node in nodes:
        if node.is_leaf:
            left_section = None
            right_section = None
        else:
            left_section = None
            right_section = dmc.Badge(
                dmc.Group(
                    [
                        dmc.Text(str(len(node.children)), size="xs", lh=1),
                        dmc.Text("▾", size="lg", lh=1),
                    ],
                    gap=0,
                ),
                size="sm", color="gray", variant="light",
                style={"pointerEvents": "none"},
            )
        buttons.append(
            dmc.Button(
                node.name,
                id={"type": "hier-node-btn", "field": field, "idx": idx, "name": node.name},
                size="xs",
                variant="light" if node.name == selected_name else "default",
                n_clicks=0,
                leftSection=left_section,
                rightSection=right_section,
            )
        )
    return buttons


def _build_sections_full(
    root: Node,
    path: list[str],
    cid: str,
    selected_value: Optional[str] = None,
) -> list:
    """Full mode: show all sibling nodes at every revealed level."""
    sections = []

    selected_at = path[0] if path else None
    buttons = _make_buttons(
        root.children, cid, idx=0, selected_name=selected_at or selected_value
    )
    sections.append(_section("Top level categories", buttons))

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


def _build_sections_compact(
    root: Node,
    path: list[str],
    cid: str,
    selected_value: Optional[str] = None,
) -> list:
    """Compact mode: collapse navigated levels to a single button each."""
    sections = []
    current_node = root

    def _add(buttons: list) -> None:
        if sections:
            sections.append(dmc.Text("▾", size="xl", c="dimmed", lh=0.5, pl="sm"))
        sections.append(dmc.Group(buttons, gap="xs", wrap="wrap"))

    for depth, name in enumerate(path):
        child = current_node.find(name)

        if child is not None and child.is_leaf:
            # Show all siblings at this leaf level with the leaf highlighted
            _add(_make_buttons(current_node.children, cid, idx=depth, selected_name=name))
            return sections

        # Intermediate: collapse to just the selected button
        _add(_make_buttons([child] if child else [], cid, idx=depth, selected_name=name))

        if child is None:
            return sections
        current_node = child

    # Active level: show all children of the current node
    depth = len(path)
    _add(_make_buttons(current_node.children, cid, idx=depth, selected_name=selected_value))

    return sections
