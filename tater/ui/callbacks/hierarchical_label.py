"""Hierarchical label callbacks."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from dash import Input, Output, State, ALL, MATCH, ctx, no_update, ClientsideFunction

from tater.ui import value_helpers
from tater.ui.callbacks.helpers import _get_ann
from tater.widgets.base import ContainerWidget
from tater.widgets.hierarchical_label import (
    HierarchicalLabelWidget,
    HierarchicalLabelTagsWidget,
    _find_path,
    _make_buttons,
    _make_tags_option_buttons,
    _make_tags_pill,
    _node_at,
    _section,
)
from tater.widgets.repeater import RepeaterWidget

if TYPE_CHECKING:
    from tater.ui.tater_app import TaterApp


# ---------------------------------------------------------------------------
# Widget-tree helpers
# ---------------------------------------------------------------------------

def _collect_hl_templates(widgets: list) -> list:
    """Recursively collect all HierarchicalLabelWidget templates at any nesting depth."""
    result = []
    for w in widgets:
        if isinstance(w, HierarchicalLabelWidget):
            result.append(w)
        elif isinstance(w, RepeaterWidget):
            result.extend(_collect_hl_templates(w.item_widgets))
        elif isinstance(w, ContainerWidget) and hasattr(w, "children"):
            result.extend(_collect_hl_templates(w.children))
    return result


def _find_hl_template(widgets: list, field_path: str):
    """Find a HierarchicalLabelWidget template for a (possibly nested) field path.

    Strips numeric segments so ``"findings.0.label"`` resolves the same template
    as ``"findings.label"``.
    """
    segments = [s for s in field_path.split(".") if not s.isdigit()]
    if not segments:
        return None
    for w in widgets:
        if w.schema_field == segments[0]:
            if len(segments) == 1:
                return w if isinstance(w, HierarchicalLabelWidget) else None
            if isinstance(w, RepeaterWidget):
                return _find_hl_template(w.item_widgets, ".".join(segments[1:]))
            if isinstance(w, ContainerWidget) and hasattr(w, "children"):
                return _find_hl_template(w.children, ".".join(segments[1:]))
    return None


# ---------------------------------------------------------------------------
# Callback registration
# ---------------------------------------------------------------------------

def setup_hl_callbacks(tater_app: TaterApp) -> None:
    """Register a single MATCH callback handling all HierarchicalLabel instances.

    Works for standalone and repeater-embedded widgets at any nesting depth.
    Component IDs use pipe-encoded field paths so the ``field`` key uniquely
    identifies each HL instance without per-widget registration.
    """
    app = tater_app.app
    _get_current_app_fn = tater_app._get_current_app

    def _ta() -> TaterApp:
        if _get_current_app_fn is not None:
            result = _get_current_app_fn()
            if result is not None:
                return result
        return tater_app

    def _get_widget(field_path: str) -> Optional[HierarchicalLabelWidget]:
        return _find_hl_template(_ta().widgets, field_path)

    # ---- 1a. Show/hide clear button ----
    app.clientside_callback(
        '(v) => v ? {} : {"display": "none"}',
        Output({"type": "hier-search-clear", "field": MATCH}, "style"),
        Input({"type": "hier-search", "field": MATCH}, "value"),
        prevent_initial_call=False,
    )

    # ---- 1b. Clear search on button click ----
    app.clientside_callback(
        '() => ""',
        Output({"type": "hier-search", "field": MATCH}, "value", allow_duplicate=True),
        Input({"type": "hier-search-clear", "field": MATCH}, "n_clicks"),
        prevent_initial_call=True,
    )

    # ---- 2. Reset navigation when document changes or repeater ops run ----
    # Also listens on repeater-load-trigger so hier-nav is refreshed after
    # add/delete ops, mirroring how loadValues works for standard widgets.
    @app.callback(
        Output({"type": "hier-nav", "field": MATCH}, "data"),
        Input("current-doc-id", "data"),
        Input("repeater-load-trigger", "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )
    def reset_nav(doc_id, _load_trigger, annotations_data):
        pipe_field = ctx.outputs_list["id"]["field"]
        field_path = pipe_field.replace("|", ".")
        widget = _get_widget(field_path)
        if widget is None:
            return no_update
        ann = _get_ann(annotations_data, doc_id) if doc_id else None
        selected_value = value_helpers.get_model_value(ann, field_path) if ann is not None else None
        if selected_value:
            computed_path = _find_path(widget.root, selected_value)
            if computed_path:
                return computed_path  # update_display trims leaf tip when rendering
        return []

    # ---- 3. Handle node button click → update path, write if leaf ----
    # Uses hier-ann-relay (MATCH) instead of annotations-store (static) to avoid
    # Dash's prohibition on mixing MATCH and static string outputs in one callback.
    @app.callback(
        Output({"type": "hier-nav", "field": MATCH}, "data", allow_duplicate=True),
        Output({"type": "hier-search", "field": MATCH}, "value", allow_duplicate=True),
        Output({"type": "hier-ann-relay", "field": MATCH}, "data"),
        Input({"type": "hier-node-btn", "field": MATCH, "depth": ALL, "name": ALL}, "n_clicks"),
        State({"type": "hier-nav", "field": MATCH}, "data"),
        State("current-doc-id", "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )
    def handle_click(node_clicks, current_path, doc_id, annotations_data):
        if not ctx.triggered_id:
            return no_update, no_update, no_update
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict) or triggered.get("type") != "hier-node-btn":
            return no_update, no_update, no_update
        if not ctx.triggered or not ctx.triggered[0].get("value"):
            return no_update, no_update, no_update

        pipe_field = triggered["field"]
        field_path = pipe_field.replace("|", ".")
        depth = triggered["depth"]
        node_name = triggered["name"]
        path = list(current_path or [])

        widget = _get_widget(field_path)
        if widget is None:
            return no_update, no_update, no_update
        root = widget.root

        parent = _node_at(root, path[:depth])
        clicked = parent.find(node_name)
        is_search_result = False
        if clicked is None:
            clicked = next((n for n in root.all_leaves() if n.name == node_name), None)
            if clicked is None:
                return no_update, no_update, no_update
            is_search_result = True

        ann = _get_ann(annotations_data, doc_id) if doc_id else None

        if clicked.is_leaf:
            current_value = value_helpers.get_model_value(ann, field_path) if ann is not None else None
            is_deselect = (current_value == node_name)

            # Include the leaf in the path when selecting so update_display can derive
            # selected_value from the path itself, avoiding a race with annotations-store.
            # On deselect, navigate back to the parent (exclude leaf).
            if is_search_result:
                full_path = _find_path(root, node_name)
                new_path = full_path[:-1] if is_deselect else full_path
            else:
                new_path = path[:depth] if is_deselect else path[:depth] + [node_name]

            ann_relay = no_update
            if ann is not None:
                ann_relay = {"field": field_path, "value": None if is_deselect else node_name}

            return new_path, ("" if is_search_result else no_update), ann_relay
        else:
            if depth < len(path) and path[depth] == node_name:
                # Back: parent is non-leaf; only selectable if allow_non_leaf=True, else clear
                new_value = (path[depth - 1] if depth > 0 else None) if widget.allow_non_leaf else None
                ann_relay = no_update
                if ann is not None:
                    ann_relay = {"field": field_path, "value": new_value}
                return path[:depth], no_update, ann_relay
            # Forward: navigate into non-leaf; only select if allow_non_leaf=True
            new_path = path[:depth] + [node_name]
            ann_relay = no_update
            if widget.allow_non_leaf and ann is not None:
                ann_relay = {"field": field_path, "value": node_name}
            return new_path, no_update, ann_relay

    # ---- Clientside: apply hier-ann-relay descriptor → annotations-store ----
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="applyFieldOp"),
        Output("annotations-store", "data", allow_duplicate=True),
        Input({"type": "hier-ann-relay", "field": ALL}, "data"),
        State("current-doc-id", "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )

    # ---- 4. Rebuild sections from nav state / search ----
    # current-doc-id is now an Input so this fires immediately on navigation,
    # one round-trip earlier than waiting for reset_nav → hier-nav.
    # reset_nav is kept so hier-nav stays in sync for handle_click's State.
    # The double-fire on navigation (once from current-doc-id, once from hier-nav
    # after reset_nav) is harmless — both produce the same output.
    @app.callback(
        Output({"type": "hier-sections", "field": MATCH}, "children"),
        Output({"type": "hier-breadcrumb", "field": MATCH}, "children"),
        Input("current-doc-id", "data"),
        Input({"type": "hier-nav", "field": MATCH}, "data"),
        Input({"type": "hier-search", "field": MATCH}, "value"),
        State("annotations-store", "data"),
        prevent_initial_call=False,
    )
    def update_display(doc_id, current_path, search_query, annotations_data):
        pipe_field = ctx.outputs_list[0]["id"]["field"]
        field_path = pipe_field.replace("|", ".")

        widget = _get_widget(field_path)
        if widget is None:
            return no_update, no_update
        root = widget.root

        # When triggered directly by doc navigation, derive the path from the
        # annotation without waiting for reset_nav to update hier-nav first.
        if ctx.triggered_id == "current-doc-id":
            ann = _get_ann(annotations_data, doc_id) if doc_id else None
            selected_value = value_helpers.get_model_value(ann, field_path) if ann is not None else None
            path = (_find_path(root, selected_value) or []) if selected_value else []
        else:
            path = list(current_path or [])

        # If the path tip is a leaf it encodes the current selection — derive
        # selected_value directly so we don't race against annotations-store.
        # Trim it off for rendering (the parent level shows the leaf's siblings).
        selected_value = None
        render_path = path
        if path:
            tip = _node_at(root, path)
            if tip and tip.is_leaf:
                selected_value = path[-1]
                render_path = path[:-1]

        # Fall back to annotations-store for initial load and deselected state.
        if selected_value is None and doc_id:
            ann = _get_ann(annotations_data, doc_id)
            if ann is not None:
                selected_value = value_helpers.get_model_value(ann, field_path)
                # If hier-nav is empty (e.g. reset_nav fired before update_repeater
                # baked in the correct path), derive render_path from the tree so
                # compact/full widgets show the selection in context rather than
                # rendering from root with nothing highlighted.
                if selected_value and not render_path:
                    full_path = _find_path(root, selected_value)
                    if full_path:
                        render_path = full_path[:-1]

        breadcrumb = " → ".join(path) if path else "None selected"

        if search_query and search_query.strip():
            q = search_query.strip().lower()
            candidates = root.all_nodes()[1:] if widget.allow_non_leaf else root.all_leaves()
            matches = [n for n in candidates if q in n.name.lower()]
            return [_section("Search results", _make_buttons(matches, pipe_field, 0, selected_value=selected_value))], breadcrumb

        return widget._render_sections(render_path, pipe_field, selected_value), breadcrumb


def setup_hl_tags_callbacks(tater_app: TaterApp) -> None:
    """Register MATCH callbacks for all HierarchicalLabelTagsWidget instances."""
    app = tater_app.app
    _get_current_app_fn = tater_app._get_current_app

    def _ta() -> TaterApp:
        if _get_current_app_fn is not None:
            result = _get_current_app_fn()
            if result is not None:
                return result
        return tater_app

    def _get_widget(field_path: str):
        w = _find_hl_template(_ta().widgets, field_path)
        return w if isinstance(w, HierarchicalLabelTagsWidget) else None

    # 1. Reset nav + search on doc change or repeater ops
    @app.callback(
        Output({"type": "hl-tags-nav", "field": MATCH}, "data", allow_duplicate=True),
        Output({"type": "hl-tags-search", "field": MATCH}, "value", allow_duplicate=True),
        Input("current-doc-id", "data"),
        Input("repeater-load-trigger", "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )
    def reset_nav(doc_id, _load_trigger, annotations_data):
        pipe_field = ctx.outputs_list[0]["id"]["field"]
        field_path = pipe_field.replace("|", ".")
        widget = _get_widget(field_path)
        if widget is None:
            return no_update, no_update
        ann = _get_ann(annotations_data, doc_id) if doc_id else None
        selected_value = value_helpers.get_model_value(ann, field_path) if ann is not None else None
        if selected_value:
            computed_path = _find_path(widget.root, selected_value)
            if computed_path:
                return computed_path, ""  # Tags: full path including selected node
        return [], ""

    # 2. Handle option tag click — always a forward selection
    # Uses hl-tags-ann-relay (MATCH) instead of annotations-store (static) to avoid
    # Dash's prohibition on mixing MATCH and static string outputs in one callback.
    @app.callback(
        Output({"type": "hl-tags-nav", "field": MATCH}, "data", allow_duplicate=True),
        Output({"type": "hl-tags-search", "field": MATCH}, "value", allow_duplicate=True),
        Output({"type": "hl-tags-ann-relay", "field": MATCH}, "data"),
        Input({"type": "hl-tags-node-btn", "field": MATCH, "depth": ALL, "name": ALL}, "n_clicks"),
        State({"type": "hl-tags-nav", "field": MATCH}, "data"),
        State("current-doc-id", "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )
    def handle_option_click(node_clicks, current_path, doc_id, annotations_data):
        if not ctx.triggered_id:
            return no_update, no_update, no_update
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict) or triggered.get("type") != "hl-tags-node-btn":
            return no_update, no_update, no_update
        if not ctx.triggered or not ctx.triggered[0].get("value"):
            return no_update, no_update, no_update

        pipe_field = triggered["field"]
        field_path = pipe_field.replace("|", ".")
        node_name = triggered["name"]
        path = list(current_path or [])

        widget = _get_widget(field_path)
        if widget is None:
            return no_update, no_update, no_update
        root = widget.root

        # Determine new nav path: full path to clicked node (includes the node itself)
        # Search results are not children of the current nav node — detect by checking the tree
        current_node = _node_at(root, path)
        is_search_result = current_node.find(node_name) is None
        if is_search_result:
            new_path = _find_path(root, node_name)
        else:
            new_path = path[:triggered["depth"]] + [node_name]

        # Verify the node exists
        if not new_path:
            return no_update, no_update, no_update

        clicked_node = _node_at(root, new_path)
        ann = _get_ann(annotations_data, doc_id) if doc_id else None
        ann_relay = no_update
        if ann is not None and (clicked_node.is_leaf or widget.allow_non_leaf):
            ann_relay = {"field": field_path, "value": node_name}

        return new_path, "", ann_relay

    # 3. Handle pill click → navigate back, selecting parent
    @app.callback(
        Output({"type": "hl-tags-nav", "field": MATCH}, "data", allow_duplicate=True),
        Output({"type": "hl-tags-ann-relay", "field": MATCH}, "data", allow_duplicate=True),
        Input({"type": "hl-tags-pill", "field": MATCH, "idx": ALL}, "n_clicks"),
        State({"type": "hl-tags-nav", "field": MATCH}, "data"),
        State("current-doc-id", "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )
    def handle_pill_click(n_clicks_list, current_nav, doc_id, annotations_data):
        if not ctx.triggered_id:
            return no_update, no_update
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict) or triggered.get("type") != "hl-tags-pill":
            return no_update, no_update
        if not ctx.triggered or not ctx.triggered[0].get("value"):
            return no_update, no_update

        idx = triggered["idx"]
        pipe_field = triggered["field"]
        field_path = pipe_field.replace("|", ".")
        path = list(current_nav or [])

        widget = _get_widget(field_path)
        # Parent is non-leaf; only selectable if allow_non_leaf=True, else clear
        parent_name = (path[idx - 1] if idx > 0 else None) if (widget and widget.allow_non_leaf) else None
        ann = _get_ann(annotations_data, doc_id) if doc_id else None
        ann_relay = no_update
        if ann is not None:
            ann_relay = {"field": field_path, "value": parent_name}

        return path[:idx], ann_relay

    # ---- Clientside: apply hl-tags-ann-relay descriptor → annotations-store ----
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="applyFieldOp"),
        Output("annotations-store", "data", allow_duplicate=True),
        Input({"type": "hl-tags-ann-relay", "field": ALL}, "data"),
        State("current-doc-id", "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )

    # 4. Rebuild pills + option tags on nav/search change
    # current-doc-id is now an Input so this fires immediately on navigation,
    # one round-trip earlier than waiting for reset_nav → hl-tags-nav.
    # reset_nav is kept so hl-tags-nav stays in sync for handle_option_click's State.
    @app.callback(
        Output({"type": "hl-tags-pills", "field": MATCH}, "children"),
        Output({"type": "hl-tags-search", "field": MATCH}, "value", allow_duplicate=True),
        Output({"type": "hl-tags-options", "field": MATCH}, "children"),
        Input("current-doc-id", "data"),
        Input({"type": "hl-tags-nav", "field": MATCH}, "data"),
        Input({"type": "hl-tags-search", "field": MATCH}, "value"),
        State("annotations-store", "data"),
        prevent_initial_call="initial_duplicate",
    )
    def update_display(doc_id, current_path, search_query, annotations_data):
        pipe_field = ctx.outputs_list[0]["id"]["field"]
        field_path = pipe_field.replace("|", ".")

        triggered = ctx.triggered_id

        # When triggered directly by doc navigation, derive the path from the
        # annotation without waiting for reset_nav to update hl-tags-nav first.
        if triggered == "current-doc-id":
            widget = _get_widget(field_path)
            if widget is None:
                return no_update, no_update, no_update
            ann = _get_ann(annotations_data, doc_id) if doc_id else None
            selected_value = value_helpers.get_model_value(ann, field_path) if ann is not None else None
            if selected_value:
                path = _find_path(widget.root, selected_value) or []
            else:
                path = []
            clear_search = ""
        else:
            path = list(current_path or [])
            if isinstance(triggered, dict) and triggered.get("type") == "hl-tags-nav":
                clear_search = ""
            else:
                clear_search = no_update

        widget = _get_widget(field_path)
        if widget is None:
            return no_update, no_update, no_update
        root = widget.root

        ann = _get_ann(annotations_data, doc_id) if doc_id else None
        selected_value = value_helpers.get_model_value(ann, field_path) if ann is not None else None

        # If hl-tags-nav is empty but there's a saved annotation value (e.g. a
        # phantom fire from a freshly-mounted store before reset_nav corrects it),
        # recover the path from the tree so pills render correctly.
        if not path and selected_value:
            recovered = _find_path(root, selected_value)
            if recovered:
                path = recovered

        # Pills = nav path; last pill gets selected style only if it's the saved value
        # (leaf always; non-leaf only when allow_non_leaf=True)
        last_node = _node_at(root, path) if path else None
        last_is_selected = bool(last_node and (last_node.is_leaf or widget.allow_non_leaf))
        pills = [
            _make_tags_pill(name, pipe_field, i, is_selected=(i == len(path) - 1 and last_is_selected))
            for i, name in enumerate(path)
        ]

        # Options = children of current nav level; empty when at a leaf
        use_search = clear_search is no_update and bool(search_query and search_query.strip())
        if use_search:
            q = search_query.strip().lower()
            candidates = root.all_nodes()[1:] if widget.allow_non_leaf else root.all_leaves()
            matches = [n for n in candidates if q in n.name.lower()]
            option_tags = _make_tags_option_buttons(matches, pipe_field, len(path), selected_value)
        else:
            current_node = _node_at(root, path)
            option_tags = _make_tags_option_buttons(current_node.children, pipe_field, len(path), selected_value)

        return pills, clear_search, option_tags
