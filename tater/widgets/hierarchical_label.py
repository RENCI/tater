"""Hierarchical label widget for tree-based label selection."""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, List, Optional, Union

from dash import dcc, html
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
# Base widget
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class HierarchicalLabelWidget(TaterWidget):
    """Base class for hierarchical label widgets.

    All component IDs use pipe-encoded field paths so a single MATCH callback
    in ``callbacks.setup_hl_callbacks`` handles every instance at every nesting
    depth without per-widget registration.

    The schema field must be ``str`` or ``Optional[str]``.
    """

    hierarchy: Union[Node, dict, list, str, Path, None] = None
    searchable: bool = True
    allow_non_leaf: bool = False
    root: Node = dc_field(init=False, repr=False)
    # Set by repeater rendering to pre-populate hier-nav from annotation so the
    # race between update_repeater (resets store to []) and reset_nav is avoided.
    _initial_nav_path: list = dc_field(init=False, default_factory=list, repr=False)

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

    # ------------------------------------------------------------------
    # Subclass interface
    # ------------------------------------------------------------------

    @property
    def _show_breadcrumb(self) -> bool:
        return False

    def _render_sections(
        self, path: list[str], pipe_field: str, selected_value: Optional[str]
    ) -> list:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Component
    # ------------------------------------------------------------------

    def component(self) -> Any:
        pipe_field = self.field_path.replace(".", "|")
        # _initial_nav_path is the full path (including selected node) set by
        # repeater rendering from the stored List[str] annotation value.
        init_path = list(self._initial_nav_path)
        selected_value = init_path[-1] if init_path else None
        render_path = init_path[:-1] if init_path else []
        initial_sections = self._render_sections(render_path, pipe_field, selected_value)

        return self._input_wrapper(dmc.Stack(
                [
                    dmc.TextInput(
                        id={"type": "hier-search", "field": pipe_field},
                        placeholder="Search all nodes…" if self.allow_non_leaf else "Search leaf nodes…",
                        size="xs",
                        style={} if self.searchable else {"display": "none"},
                        rightSection=dmc.ActionIcon(
                            "×",
                            id={"type": "hier-search-clear", "field": pipe_field},
                            size="xs",
                            variant="transparent",
                            c="dimmed",
                            style={"display": "none"},
                        ),
                        rightSectionPointerEvents="all",
                    ),
                    dmc.Text(
                        "",
                        id={"type": "hier-breadcrumb", "field": pipe_field},
                        size="xs",
                        fw=600,
                        style={} if self._show_breadcrumb else {"display": "none"},
                    ),
                    dmc.Stack(initial_sections, id={"type": "hier-sections", "field": pipe_field}, gap="sm"),
                    dcc.Store(id={"type": "hier-nav", "field": pipe_field}, data=self._initial_nav_path),
                    dcc.Store(id={"type": "hier-ann-relay", "field": pipe_field}, data=None),
                ],
                gap="xs",
            ), self.label)

    # register_callbacks is a no-op: setup_hl_callbacks in callbacks.py
    # registers a single MATCH callback handling all HL instances.
    def register_callbacks(self, app: Any) -> None:
        pass


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
        self, path: list[str], pipe_field: str, selected_value: Optional[str]
    ) -> list:
        return _build_sections_full(self.root, path, pipe_field, selected_value=selected_value)


@dataclass(eq=False)
class HierarchicalLabelCompactWidget(HierarchicalLabelWidget):
    """Compact hierarchical widget showing only the selected node per level.

    Already-navigated levels collapse to a single highlighted button. Only
    the active (deepest) level shows all available options. Clicking a
    collapsed button at any earlier level expands it again.
    """

    def _render_sections(
        self, path: list[str], pipe_field: str, selected_value: Optional[str]
    ) -> list:
        items = _build_sections_compact(self.root, path, pipe_field, selected_value=selected_value)
        return [dmc.Stack(items, gap=2)]


_SELECTED_STYLE = {"boxShadow": "0 0 0 1px var(--mantine-color-dimmed)"}

_PILL_STYLE = {
    "borderRadius": "var(--mantine-radius-xl)",
    "padding": "2px 10px",
    "fontSize": "var(--mantine-font-size-xs)",
    "display": "inline-flex",
    "alignItems": "center",
    "gap": "4px",
    "whiteSpace": "nowrap",
}


def _make_tags_option_buttons(nodes, pipe_field, depth, selected_value=None):
    """Option pill buttons for HierarchicalLabelTagsWidget, styled like TagsInput pills."""
    buttons = []
    for node in nodes:
        children = [node.name]
        if not node.is_leaf:
            children.append(DashIconify(icon="tabler:chevron-down", width=10))
        is_selected = selected_value is not None and node.name == selected_value
        bg = "var(--mantine-primary-color-light-hover)" if is_selected else "var(--mantine-color-default-hover)"
        style = {**_PILL_STYLE, "cursor": "pointer", "backgroundColor": bg}
        if is_selected:
            style.update(_SELECTED_STYLE)
        buttons.append(
            html.Div(
                children,
                id={"type": "hl-tags-node-btn", "field": pipe_field, "depth": depth, "name": node.name},
                n_clicks=0,
                style=style,
            )
        )
    return buttons


def _make_tags_pill(name: str, pipe_field: str, idx: int, is_selected: bool = False):
    """A clickable breadcrumb pill for the tags input. Clicking navigates back."""
    style = {
        **_PILL_STYLE,
        "backgroundColor": "var(--mantine-primary-color-light-hover)",
        "color": "var(--mantine-primary-color-default-color)",
        "cursor": "pointer",
    }
    if is_selected:
        style.update(_SELECTED_STYLE)
    return html.Div(
        name,
        id={"type": "hl-tags-pill", "field": pipe_field, "idx": idx},
        n_clicks=0,
        style=style,
    )


@dataclass(eq=False)
class HierarchicalLabelTagsWidget(HierarchicalLabelWidget):
    """Tags-style hierarchical widget.

    The navigation path and selected leaf are shown as dismissible pill tags
    inside a TagsInput.  Typing filters the option tags shown below.
    Single-value selection; behaviour is otherwise identical to
    HierarchicalLabelCompactWidget.
    """

    def component(self) -> Any:
        pipe_field = self.field_path.replace(".", "|")
        return self._input_wrapper(dmc.Stack(
                [
                    html.Div(
                        [
                            html.Div(
                                [],
                                id={"type": "hl-tags-pills", "field": pipe_field},
                                style={"display": "contents"},
                            ),
                            dcc.Input(
                                id={"type": "hl-tags-search", "field": pipe_field},
                                type="text",
                                value="",
                                placeholder=("Search all nodes…" if self.allow_non_leaf else "Search leaf nodes…") if self.searchable else "",
                                debounce=False,
                                style={
                                    "border": "none",
                                    "outline": "none",
                                    "flex": "1 1 60px",
                                    "minWidth": "60px",
                                    "background": "transparent",
                                    "color": "inherit",
                                    "fontSize": "var(--mantine-font-size-xs)",
                                    "alignSelf": "center",
                                    "padding": "0",
                                    "height": "22px",
                                } if self.searchable else {"display": "none"},
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexWrap": "wrap",
                            "alignItems": "center",
                            "gap": "4px",
                            "padding": "4px 2px",
                            "border": "1px solid var(--mantine-color-default-border)",
                            "borderRadius": "var(--mantine-radius-sm)",
                            "backgroundColor": "var(--mantine-color-default)",
                            "cursor": "text",
                        },
                    ),
                    dmc.Group([], id={"type": "hl-tags-options", "field": pipe_field}, gap="xs", wrap="wrap"),
                    dcc.Store(id={"type": "hl-tags-nav", "field": pipe_field}, data=self._initial_nav_path),
                    dcc.Store(id={"type": "hl-tags-ann-relay", "field": pipe_field}, data=None),
                ],
                gap="xs",
            ), self.label)

    def _render_sections(self, path, pipe_field, selected_value):
        return []  # Tags widget renders via callbacks, not _render_sections


# ---------------------------------------------------------------------------
# HierarchicalLabelMultiWidget
# ---------------------------------------------------------------------------

_PATH_SEP = "|"


def _build_multiselect_data(root: Node, allow_non_leaf: bool = False) -> list:
    """Build dmc.MultiSelect data from a Node tree.

    Each item: ``{value: "A|B|C", label: "C"}``.
    ``value`` is the full path joined by ``_PATH_SEP`` (unique even for duplicate leaf names).
    ``label`` is the plain node name; depth-based indentation is handled by the
    ``hlMultiRenderOption`` JS function via the ``renderOption`` prop.
    Depth is relative to root's children (root itself is not included).
    """
    items = []

    def _walk(node: Node, path: list[str]) -> None:
        if node.name == "__root__":
            for child in node.children:
                _walk(child, [])
            return
        current_path = path + [node.name]
        value = _PATH_SEP.join(current_path)
        if node.is_leaf:
            items.append({"value": value, "label": node.name})
        else:
            # Non-leaf nodes always appear to provide hierarchy context.
            # Disabled when allow_non_leaf=False so they act as visual headers only.
            item = {"value": value, "label": node.name}
            if not allow_non_leaf:
                item["disabled"] = True
            items.append(item)
            for child in node.children:
                _walk(child, current_path)

    for child in root.children:
        _walk(child, [])
    return items


@dataclass(eq=False)
class HierarchicalLabelMultiWidget(HierarchicalLabelWidget):
    """Multi-select hierarchical widget using dmc.MultiSelect with depth-indented options.

    Stores ``Optional[List[List[str]]]`` — a list of full paths, one per selection.
    The dropdown uses ``renderOption`` (``hlMultiRenderOption`` JS function) to indent
    each option based on its depth in the hierarchy. Selected pills show the node name only.
    Search is handled natively by Mantine (matches against the label, i.e. node name).

    Component IDs use ``hl-multi-*`` types; a single MATCH callback in
    ``setup_hl_multi_callbacks`` handles all instances.
    """

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

    @property
    def _show_breadcrumb(self) -> bool:
        return False

    def _render_sections(self, path, pipe_field, selected_value):
        return []  # Not used — MultiSelect renders its own dropdown

    def component(self) -> Any:
        pipe_field = self.field_path.replace(".", "|")
        data = _build_multiselect_data(self.root, self.allow_non_leaf)
        return self._input_wrapper(
            dmc.Stack(
                [
                    dmc.MultiSelect(
                        id={"type": "hl-multi", "field": pipe_field},
                        data=data,
                        value=[],
                        searchable=self.searchable,
                        clearable=True,
                        placeholder="Search…",
                        size="sm",
                        renderOption={"function": "hlMultiRenderOption"},
                        filter={"function": "hlMultiFilter"},
                    ),
                    dcc.Store(id={"type": "hl-multi-relay", "field": pipe_field}, data=None),
                ],
                gap="xs",
            ),
            self.label,
        )

    def register_callbacks(self, app: Any) -> None:
        pass  # Handled by setup_hl_multi_callbacks


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
    pipe_field: str,
    depth: int,
    nav_name: Optional[str] = None,
    selected_value: Optional[str] = None,
) -> list:
    def btn_id(node, d):
        return {"type": "hier-node-btn", "field": pipe_field, "depth": d, "name": node.name}
    return _make_buttons_impl(nodes, depth, nav_name, btn_id, selected_value)


def _make_buttons_impl(
    nodes: list[Node],
    depth: int,
    nav_name: Optional[str],
    btn_id_fn,
    selected_value: Optional[str] = None,
) -> list:
    buttons = []
    for node in nodes:
        is_nav = node.name == nav_name
        is_selected = node.name == selected_value
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
                variant="light" if (is_nav or is_selected) else "default",
                n_clicks=0,
                rightSection=right_section,
                style=_SELECTED_STYLE if is_selected else {},
            )
        )
    return buttons


def _build_sections_full(
    root: Node,
    path: list[str],
    pipe_field: str,
    selected_value: Optional[str] = None,
) -> list:
    """Full mode: show all sibling nodes at every revealed level."""
    def btns(nodes, depth, nav_name, sv=None):
        return _make_buttons(nodes, pipe_field, depth, nav_name, sv)

    sections = []
    selected_at = path[0] if path else None
    sections.append(_section("Top level categories", btns(root.children, 0, selected_at, selected_value)))

    current_node = root
    for depth, name in enumerate(path):
        child = current_node.find(name)
        if child is None or child.is_leaf:
            break
        current_node = child
        selected_at = path[depth + 1] if depth + 1 < len(path) else None
        sections.append(_section(current_node.name, btns(current_node.children, depth + 1, selected_at, selected_value)))

    return sections


def _build_sections_compact(
    root: Node,
    path: list[str],
    pipe_field: str,
    selected_value: Optional[str] = None,
) -> list:
    """Compact mode: collapse navigated levels to a single button each."""
    def btns(nodes, depth, nav_name, sv=None):
        return _make_buttons(nodes, pipe_field, depth, nav_name, sv)

    sections = []
    current_node = root

    def _add(buttons: list) -> None:
        if sections:
            sections.append(dmc.Box(DashIconify(icon="tabler:chevron-down", width=16, color="gray"), pl="xs", style={"lineHeight": 0, "display": "block"}))
        sections.append(dmc.Group(buttons, gap="xs", wrap="wrap"))

    for depth, name in enumerate(path):
        child = current_node.find(name)
        if child is not None and child.is_leaf:
            _add(btns([child], depth, name, selected_value))
            return sections
        _add(btns([child] if child else [], depth, name, selected_value))
        if child is None:
            return sections
        current_node = child

    depth = len(path)
    if selected_value:
        selected_child = current_node.find(selected_value)
        if selected_child and selected_child.is_leaf:
            _add(btns([selected_child], depth, selected_value, selected_value))
            return sections

    _add(btns(current_node.children, depth, selected_value, selected_value))
    return sections
