"""Hierarchical label widget for tree-based label selection."""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Optional, Union

from dash import dcc, Input, Output, State, ALL, MATCH, no_update, ctx
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from tater.widgets.base import TaterWidget, _unwrap_optional, _resolve_field_info


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

@dataclass(eq=False)
class HierarchicalLabelWidget(TaterWidget):
    """Base class for hierarchical label widgets.

    Subclasses implement ``_render_sections`` to control how the tree is
    displayed at each navigation depth.

    The schema field must be ``str`` or ``Optional[str]``.
    """

    hierarchy: Union[Node, dict, list, str, Path, None] = None
    searchable: bool = True
    root: Node = dc_field(init=False, repr=False)

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
        return False

    _description_in_component = True

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

    def _render_sections_in_list(
        self, path: list[str], ld: str, li: int, selected_value: Optional[str]
    ) -> list:
        raise NotImplementedError

    def _render_sections_in_nested_list(
        self, path: list[str], ld: str, li: int, inner_li: int, selected_value: Optional[str]
    ) -> list:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Component + callbacks
    # ------------------------------------------------------------------

    def component(self) -> Any:
        cid = self.component_id
        initial_sections = self._render_sections([], cid, None)
        description = [dmc.Text(self.description, size="xs", c="dimmed")] if self.description else []

        return dmc.Stack(
            description + [
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

    def component_in_list(self, ld: str, li: int) -> Any:
        """Render this widget for use inside a ListableWidget item at list-index ``li``.

        Uses MATCH-compatible dict IDs keyed by ``ld`` (list discriminator) and ``li``
        (list index) so that a single set of registered callbacks handles all indices.
        """
        initial_sections = self._render_sections_in_list([], ld, li, None)
        description = [dmc.Text(self.description, size="xs", c="dimmed")] if self.description else []
        return dmc.Stack(
            description + [
                dmc.TextInput(
                    id={"type": "hier-search-list", "ld": ld, "li": li},
                    placeholder="Search…",
                    size="xs",
                    style={} if self.searchable else {"display": "none"},
                    rightSection=dmc.ActionIcon(
                        "×",
                        id={"type": "hier-search-clear-list", "ld": ld, "li": li},
                        size="xs",
                        variant="transparent",
                        c="dimmed",
                        style={"display": "none"},
                    ),
                    rightSectionPointerEvents="all",
                ),
                dmc.Text(
                    "",
                    id={"type": "hier-breadcrumb-list", "ld": ld, "li": li},
                    size="xs",
                    fw=600,
                    style={} if self._show_breadcrumb else {"display": "none"},
                ),
                dmc.Stack(
                    initial_sections,
                    id={"type": "hier-sections-list", "ld": ld, "li": li},
                    gap="sm",
                ),
                dcc.Store(id={"type": "hier-nav-list", "ld": ld, "li": li}, data=[]),
            ],
            gap="xs",
        )

    def component_in_nested_list(self, ld: str, outer_li: int, inner_li: int) -> Any:
        """Render this widget when nested two levels deep (repeater inside repeater)."""
        initial_sections = self._render_sections_in_nested_list([], ld, outer_li, inner_li, None)
        description = [dmc.Text(self.description, size="xs", c="dimmed")] if self.description else []
        return dmc.Stack(
            description + [
                dmc.TextInput(
                    id={"type": "hier-search-nested", "ld": ld, "li": outer_li, "inner_li": inner_li},
                    placeholder="Search…",
                    size="xs",
                    style={} if self.searchable else {"display": "none"},
                    rightSection=dmc.ActionIcon(
                        "×",
                        id={"type": "hier-search-clear-nested", "ld": ld, "li": outer_li, "inner_li": inner_li},
                        size="xs",
                        variant="transparent",
                        c="dimmed",
                        style={"display": "none"},
                    ),
                    rightSectionPointerEvents="all",
                ),
                dmc.Text(
                    "",
                    id={"type": "hier-breadcrumb-nested", "ld": ld, "li": outer_li, "inner_li": inner_li},
                    size="xs",
                    fw=600,
                    style={} if self._show_breadcrumb else {"display": "none"},
                ),
                dmc.Stack(
                    initial_sections,
                    id={"type": "hier-sections-nested", "ld": ld, "li": outer_li, "inner_li": inner_li},
                    gap="sm",
                ),
                dcc.Store(
                    id={"type": "hier-nav-nested", "ld": ld, "li": outer_li, "inner_li": inner_li},
                    data=[],
                ),
            ],
            gap="xs",
        )

    def register_nested_list_callbacks(
        self,
        app: Any,
        ld: str,
        outer_list_field: str,
        item_field: str,
        inner_item_field: str,
    ) -> None:
        """Register MATCH-based callbacks for widgets nested two levels deep.

        ``ld`` is the discriminator; ``li`` (outer index) and ``inner_li``
        (inner index) both use MATCH so each (outer, inner) pair is independent.
        """
        from tater.ui import value_helpers

        root = self.root
        render_sections_in_nested_list = self._render_sections_in_nested_list

        def node_at(path: list[str]) -> Node:
            node = root
            for name in path:
                child = node.find(name)
                if child is None:
                    return root
                node = child
            return node

        def field_path_for(li: int, inner_li: int) -> str:
            return f"{outer_list_field}.{li}.{item_field}.{inner_li}.{inner_item_field}"

        # ---- 1a. Show/hide clear button ----
        @app.callback(
            Output({"type": "hier-search-clear-nested", "ld": ld, "li": MATCH, "inner_li": MATCH}, "style"),
            Input({"type": "hier-search-nested", "ld": ld, "li": MATCH, "inner_li": MATCH}, "value"),
            prevent_initial_call=False,
        )
        def toggle_clear_nested(value):
            return {} if value else {"display": "none"}

        # ---- 1b. Clear search on button click ----
        @app.callback(
            Output({"type": "hier-search-nested", "ld": ld, "li": MATCH, "inner_li": MATCH}, "value", allow_duplicate=True),
            Input({"type": "hier-search-clear-nested", "ld": ld, "li": MATCH, "inner_li": MATCH}, "n_clicks"),
            prevent_initial_call=True,
        )
        def clear_search_nested(_):
            return ""

        # ---- 2. Reset all nav stores when document changes ----
        @app.callback(
            Output({"type": "hier-nav-nested", "ld": ld, "li": ALL, "inner_li": ALL}, "data"),
            Input("current-doc-id", "data"),
            prevent_initial_call=True,
        )
        def reset_nav_nested(_doc_id):
            return [[] for _ in ctx.outputs_list]

        # ---- 3. Handle node button click ----
        @app.callback(
            Output({"type": "hier-nav-nested", "ld": ld, "li": MATCH, "inner_li": MATCH}, "data", allow_duplicate=True),
            Output({"type": "hier-search-nested", "ld": ld, "li": MATCH, "inner_li": MATCH}, "value", allow_duplicate=True),
            Input({"type": "hier-node-btn-nested", "ld": ld, "li": MATCH, "inner_li": MATCH, "depth": ALL, "name": ALL}, "n_clicks"),
            State({"type": "hier-nav-nested", "ld": ld, "li": MATCH, "inner_li": MATCH}, "data"),
            State("current-doc-id", "data"),
            prevent_initial_call=True,
        )
        def handle_click_nested(node_clicks, current_path, doc_id):
            if not ctx.triggered_id:
                return no_update, no_update
            triggered = ctx.triggered_id
            if not isinstance(triggered, dict) or triggered.get("type") != "hier-node-btn-nested":
                return no_update, no_update
            if not ctx.triggered or not ctx.triggered[0].get("value"):
                return no_update, no_update

            li = triggered["li"]
            inner_li = triggered["inner_li"]
            depth = triggered["depth"]
            node_name = triggered["name"]
            path = list(current_path or [])
            fp = field_path_for(li, inner_li)

            parent = node_at(path[:depth])
            clicked = parent.find(node_name)
            is_search_result = False
            if clicked is None:
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
                        current_value = value_helpers.get_model_value(annotation, fp)

                if is_search_result:
                    full_path = _find_path(root, node_name)
                    new_path = full_path[:-1]
                else:
                    new_path = path[:depth]

                if current_value == node_name:
                    if annotation is not None:
                        value_helpers.set_model_value(annotation, fp, None)
                        tater_app._save_annotations_to_file()
                else:
                    if annotation is not None:
                        value_helpers.set_model_value(annotation, fp, node_name)
                        tater_app._save_annotations_to_file()

                return new_path, ("" if is_search_result else no_update)
            else:
                if depth < len(path) and path[depth] == node_name:
                    return path[:depth], no_update
                return path[:depth] + [node_name], no_update

        # ---- 4. Rebuild sections ----
        @app.callback(
            Output({"type": "hier-sections-nested", "ld": ld, "li": MATCH, "inner_li": MATCH}, "children"),
            Output({"type": "hier-breadcrumb-nested", "ld": ld, "li": MATCH, "inner_li": MATCH}, "children"),
            Input({"type": "hier-nav-nested", "ld": ld, "li": MATCH, "inner_li": MATCH}, "data"),
            Input({"type": "hier-search-nested", "ld": ld, "li": MATCH, "inner_li": MATCH}, "value"),
            Input("current-doc-id", "data"),
            prevent_initial_call=False,
        )
        def update_display_nested(current_path, search_query, doc_id):
            li = ctx.outputs_list[0]["id"]["li"]
            inner_li = ctx.outputs_list[0]["id"]["inner_li"]
            fp = field_path_for(li, inner_li)
            path = list(current_path or [])
            tater_app = app._tater_app

            selected_value = None
            if doc_id and tater_app:
                annotation = tater_app.annotations.get(doc_id)
                if annotation is not None:
                    selected_value = value_helpers.get_model_value(annotation, fp)

            breadcrumb = " → ".join(path) if path else "None selected"

            if search_query and search_query.strip():
                q = search_query.strip().lower()
                matches = [n for n in root.all_leaves() if q in n.name.lower()]
                return [_section("Search results", _make_buttons_nested(matches, ld, li, inner_li, 0, selected_value))], breadcrumb

            return render_sections_in_nested_list(path, ld, li, inner_li, selected_value), breadcrumb

    def register_list_callbacks(self, app: Any, ld: str, list_field: str, item_field: str) -> None:
        """Register MATCH-based callbacks for list-embedded instances of this widget.

        A single call handles all list indices via Dash MATCH on ``li``.
        ``ld`` is the list discriminator (e.g. "findings-diagnosis"); ``list_field``
        and ``item_field`` are used to construct the annotation field path at runtime.
        """
        from tater.ui import value_helpers

        root = self.root
        render_sections_in_list = self._render_sections_in_list  # bound method

        def node_at(path: list[str]) -> Node:
            node = root
            for name in path:
                child = node.find(name)
                if child is None:
                    return root
                node = child
            return node

        def field_path_for(li: int) -> str:
            return f"{list_field}.{li}.{item_field}"

        # ---- 1a. Show/hide clear button ----
        @app.callback(
            Output({"type": "hier-search-clear-list", "ld": ld, "li": MATCH}, "style"),
            Input({"type": "hier-search-list", "ld": ld, "li": MATCH}, "value"),
            prevent_initial_call=False,
        )
        def toggle_clear(value):
            return {} if value else {"display": "none"}

        # ---- 1b. Clear search on button click ----
        @app.callback(
            Output({"type": "hier-search-list", "ld": ld, "li": MATCH}, "value", allow_duplicate=True),
            Input({"type": "hier-search-clear-list", "ld": ld, "li": MATCH}, "n_clicks"),
            prevent_initial_call=True,
        )
        def clear_search(_):
            return ""

        # ---- 2. Reset all nav stores when document changes ----
        @app.callback(
            Output({"type": "hier-nav-list", "ld": ld, "li": ALL}, "data"),
            Input("current-doc-id", "data"),
            prevent_initial_call=True,
        )
        def reset_nav(_doc_id):
            return [[] for _ in ctx.outputs_list]

        # ---- 3. Handle node button click ----
        @app.callback(
            Output({"type": "hier-nav-list", "ld": ld, "li": MATCH}, "data", allow_duplicate=True),
            Output({"type": "hier-search-list", "ld": ld, "li": MATCH}, "value", allow_duplicate=True),
            Input({"type": "hier-node-btn-list", "ld": ld, "li": MATCH, "depth": ALL, "name": ALL}, "n_clicks"),
            State({"type": "hier-nav-list", "ld": ld, "li": MATCH}, "data"),
            State("current-doc-id", "data"),
            prevent_initial_call=True,
        )
        def handle_click(node_clicks, current_path, doc_id):
            if not ctx.triggered_id:
                return no_update, no_update
            triggered = ctx.triggered_id
            if not isinstance(triggered, dict) or triggered.get("type") != "hier-node-btn-list":
                return no_update, no_update
            if not ctx.triggered or not ctx.triggered[0].get("value"):
                return no_update, no_update

            li = triggered["li"]
            depth = triggered["depth"]
            node_name = triggered["name"]
            path = list(current_path or [])
            fp = field_path_for(li)

            parent = node_at(path[:depth])
            clicked = parent.find(node_name)
            is_search_result = False
            if clicked is None:
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
                        current_value = value_helpers.get_model_value(annotation, fp)

                if is_search_result:
                    full_path = _find_path(root, node_name)
                    new_path = full_path[:-1]
                else:
                    new_path = path[:depth]

                if current_value == node_name:
                    if annotation is not None:
                        value_helpers.set_model_value(annotation, fp, None)
                        tater_app._save_annotations_to_file()
                else:
                    if annotation is not None:
                        value_helpers.set_model_value(annotation, fp, node_name)
                        tater_app._save_annotations_to_file()

                return new_path, ("" if is_search_result else no_update)
            else:
                if depth < len(path) and path[depth] == node_name:
                    return path[:depth], no_update
                return path[:depth] + [node_name], no_update

        # ---- 4. Rebuild sections ----
        @app.callback(
            Output({"type": "hier-sections-list", "ld": ld, "li": MATCH}, "children"),
            Output({"type": "hier-breadcrumb-list", "ld": ld, "li": MATCH}, "children"),
            Input({"type": "hier-nav-list", "ld": ld, "li": MATCH}, "data"),
            Input({"type": "hier-search-list", "ld": ld, "li": MATCH}, "value"),
            Input("current-doc-id", "data"),
            prevent_initial_call=False,
        )
        def update_display(current_path, search_query, doc_id):
            li = ctx.outputs_list[0]["id"]["li"]
            fp = field_path_for(li)
            path = list(current_path or [])
            tater_app = app._tater_app

            selected_value = None
            if doc_id and tater_app:
                annotation = tater_app.annotations.get(doc_id)
                if annotation is not None:
                    selected_value = value_helpers.get_model_value(annotation, fp)

            breadcrumb = " → ".join(path) if path else "None selected"

            if search_query and search_query.strip():
                q = search_query.strip().lower()
                matches = [n for n in root.all_leaves() if q in n.name.lower()]
                return [_section("Search results", _make_buttons_list(matches, ld, li, 0, selected_value))], breadcrumb

            return render_sections_in_list(path, ld, li, selected_value), breadcrumb


# ---------------------------------------------------------------------------
# Concrete widgets
# ---------------------------------------------------------------------------

@dataclass(eq=False)
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

    def _render_sections_in_list(
        self, path: list[str], ld: str, li: int, selected_value: Optional[str]
    ) -> list:
        return _build_sections_full_list(self.root, path, ld, li, selected_value=selected_value)

    def _render_sections_in_nested_list(
        self, path: list[str], ld: str, li: int, inner_li: int, selected_value: Optional[str]
    ) -> list:
        return _build_sections_full_nested(self.root, path, ld, li, inner_li, selected_value=selected_value)


@dataclass(eq=False)
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

    def _render_sections_in_list(
        self, path: list[str], ld: str, li: int, selected_value: Optional[str]
    ) -> list:
        items = _build_sections_compact_list(self.root, path, ld, li, selected_value=selected_value)
        return [dmc.Stack(items, gap=2)]

    def _render_sections_in_nested_list(
        self, path: list[str], ld: str, li: int, inner_li: int, selected_value: Optional[str]
    ) -> list:
        items = _build_sections_compact_nested(self.root, path, ld, li, inner_li, selected_value=selected_value)
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
    def btn_id(node, depth):
        return {"type": "hier-node-btn", "field": field, "idx": depth, "name": node.name}
    return _make_buttons_impl(nodes, idx, selected_name, btn_id)


def _make_buttons_list(
    nodes: list[Node],
    ld: str,
    li: int,
    depth: int,
    selected_name: Optional[str] = None,
) -> list:
    def btn_id(node, d):
        return {"type": "hier-node-btn-list", "ld": ld, "li": li, "depth": d, "name": node.name}
    return _make_buttons_impl(nodes, depth, selected_name, btn_id)


def _make_buttons_nested(
    nodes: list[Node],
    ld: str,
    li: int,
    inner_li: int,
    depth: int,
    selected_name: Optional[str] = None,
) -> list:
    def btn_id(node, d):
        return {"type": "hier-node-btn-nested", "ld": ld, "li": li, "inner_li": inner_li, "depth": d, "name": node.name}
    return _make_buttons_impl(nodes, depth, selected_name, btn_id)


def _make_buttons_impl(
    nodes: list[Node],
    depth: int,
    selected_name: Optional[str],
    btn_id_fn,
) -> list:
    buttons = []
    for node in nodes:
        right_section = (
            dmc.Badge(
                dmc.Group(
                    [
                        dmc.Text(str(len(node.children)), size="xs", lh=1),
                        DashIconify(icon="tabler:chevron-down", width=12),
                    ],
                    gap=0,
                ),
                size="sm", color="gray", variant="light",
                style={"pointerEvents": "none"},
            )
            if not node.is_leaf else None
        )
        buttons.append(
            dmc.Button(
                node.name,
                id=btn_id_fn(node, depth),
                size="xs",
                variant="light" if node.name == selected_name else "default",
                n_clicks=0,
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
    def make_btns(nodes, depth, sel):
        return _make_buttons(nodes, cid, depth, sel)
    return _build_sections_full_impl(root, path, selected_value, make_btns)


def _build_sections_full_list(
    root: Node,
    path: list[str],
    ld: str,
    li: int,
    selected_value: Optional[str] = None,
) -> list:
    def make_btns(nodes, depth, sel):
        return _make_buttons_list(nodes, ld, li, depth, sel)
    return _build_sections_full_impl(root, path, selected_value, make_btns)


def _build_sections_full_nested(
    root: Node,
    path: list[str],
    ld: str,
    li: int,
    inner_li: int,
    selected_value: Optional[str] = None,
) -> list:
    def make_btns(nodes, depth, sel):
        return _make_buttons_nested(nodes, ld, li, inner_li, depth, sel)
    return _build_sections_full_impl(root, path, selected_value, make_btns)


def _build_sections_full_impl(
    root: Node,
    path: list[str],
    selected_value: Optional[str],
    make_btns_fn,
) -> list:
    sections = []
    selected_at = path[0] if path else None
    sections.append(_section("Top level categories", make_btns_fn(root.children, 0, selected_at or selected_value)))

    current_node = root
    for depth, name in enumerate(path):
        child = current_node.find(name)
        if child is None or child.is_leaf:
            break
        current_node = child
        selected_at = path[depth + 1] if depth + 1 < len(path) else None
        sections.append(_section(current_node.name, make_btns_fn(current_node.children, depth + 1, selected_at or selected_value)))

    return sections


def _build_sections_compact(
    root: Node,
    path: list[str],
    cid: str,
    selected_value: Optional[str] = None,
) -> list:
    """Compact mode: collapse navigated levels to a single button each."""
    def make_btns(nodes, depth, sel):
        return _make_buttons(nodes, cid, depth, sel)
    return _build_sections_compact_impl(root, path, selected_value, make_btns)


def _build_sections_compact_list(
    root: Node,
    path: list[str],
    ld: str,
    li: int,
    selected_value: Optional[str] = None,
) -> list:
    def make_btns(nodes, depth, sel):
        return _make_buttons_list(nodes, ld, li, depth, sel)
    return _build_sections_compact_impl(root, path, selected_value, make_btns)


def _build_sections_compact_nested(
    root: Node,
    path: list[str],
    ld: str,
    li: int,
    inner_li: int,
    selected_value: Optional[str] = None,
) -> list:
    def make_btns(nodes, depth, sel):
        return _make_buttons_nested(nodes, ld, li, inner_li, depth, sel)
    return _build_sections_compact_impl(root, path, selected_value, make_btns)


def _build_sections_compact_impl(
    root: Node,
    path: list[str],
    selected_value: Optional[str],
    make_btns_fn,
) -> list:
    """Compact mode: collapse navigated levels to a single button each."""
    sections = []
    current_node = root

    if selected_value and not path:
        computed_path = _find_path(root, selected_value)
        if computed_path:
            path = computed_path

    def _add(buttons: list) -> None:
        if sections:
            sections.append(dmc.Box(DashIconify(icon="tabler:chevron-down", width=16, color="gray"), pl="xs", style={"lineHeight": 0, "display": "block"}))
        sections.append(dmc.Group(buttons, gap="xs", wrap="wrap"))

    for depth, name in enumerate(path):
        child = current_node.find(name)
        if child is not None and child.is_leaf:
            _add(make_btns_fn([child], depth, name))
            return sections
        _add(make_btns_fn([child] if child else [], depth, name))
        if child is None:
            return sections
        current_node = child

    depth = len(path)
    if selected_value:
        selected_child = current_node.find(selected_value)
        if selected_child and selected_child.is_leaf:
            _add(make_btns_fn([selected_child], depth, selected_value))
            return sections

    _add(make_btns_fn(current_node.children, depth, selected_value))
    return sections
