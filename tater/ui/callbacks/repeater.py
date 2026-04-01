"""Repeater and nested-repeater callbacks."""
from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from dash import Input, Output, State, ALL, MATCH, ctx, no_update
from dash.exceptions import PreventUpdate

from tater.ui import value_helpers
from tater.ui.callbacks.helpers import _get_ann
from tater.widgets.base import ContainerWidget, ControlWidget
from tater.widgets.repeater import (
    RepeaterWidget,
    _NESTED_ADD_TYPE,
    _NESTED_DELETE_TYPE,
    _NESTED_STORE_TYPE,
    _NESTED_ITEMS_TYPE,
)

if TYPE_CHECKING:
    from tater.ui.tater_app import TaterApp


# ---------------------------------------------------------------------------
# Widget-tree helpers
# ---------------------------------------------------------------------------

def _find_repeater_template(widgets: list, field_path: str):
    """Find the RepeaterWidget template for a (possibly nested) field path.

    Strips numeric segments so ``"findings.0.annotations"`` resolves the same
    template as ``"findings.annotations"``.
    """
    segments = [s for s in field_path.split(".") if not s.isdigit()]
    return _find_by_segments(widgets, segments)


def _find_by_segments(widgets: list, segments: list):
    if not segments:
        return None
    for w in widgets:
        if w.schema_field == segments[0]:
            if len(segments) == 1:
                return w if isinstance(w, RepeaterWidget) else None
            if isinstance(w, RepeaterWidget):
                return _find_by_segments(w.item_widgets, segments[1:])
    return None


# ---------------------------------------------------------------------------
# Callback registration
# ---------------------------------------------------------------------------

def setup_repeater_callbacks(tater_app: TaterApp) -> None:
    """Register a single MATCH callback handling all repeaters at every nesting depth.

    When any SpanAnnotationWidget is present, also registers a relay that increments
    span-any-change whenever a list item is deleted so the doc viewer re-renders.
    """
    app = tater_app.app
    _get_current_app_fn = tater_app._get_current_app

    def _ta() -> TaterApp:
        if _get_current_app_fn is not None:
            result = _get_current_app_fn()
            if result is not None:
                return result
        return tater_app

    # --- Annotation sync helpers ---
    def _sync_annotation_add(widget_template, field_path, annotations_data, doc_id, new_index):
        ann = _get_ann(annotations_data, doc_id)
        if ann is None:
            return annotations_data
        extended = False
        for iw in widget_template.item_widgets:
            if isinstance(iw, ContainerWidget):
                extended = True
                continue
            if not isinstance(iw, ControlWidget):
                continue
            try:
                value_helpers.set_model_value(
                    ann,
                    f"{field_path}.{new_index}.{iw.schema_field}",
                    iw.empty_value,
                )
                extended = True
            except Exception:
                pass
        if not extended:
            try:
                value_helpers.set_model_value(ann, f"{field_path}.{new_index}", None)
            except Exception:
                pass
        return {**(annotations_data or {}), doc_id: ann}

    def _sync_annotation_delete(field_path, annotations_data, doc_id, del_position):
        ann = _get_ann(annotations_data, doc_id)
        if ann is None:
            return annotations_data
        current_list = value_helpers.get_model_value(ann, field_path)
        if isinstance(current_list, list) and del_position < len(current_list):
            current_list.pop(del_position)
        return {**(annotations_data or {}), doc_id: ann}

    # --- Unified MATCH callback ---
    # Uses repeater-ann-relay (MATCH) instead of annotations-store (static) to avoid
    # Dash's prohibition on mixing MATCH and static string outputs in one callback.
    @app.callback(
        [Output({"type": "repeater-store",     "field": MATCH}, "data"),
         Output({"type": "repeater-items",     "field": MATCH}, "children"),
         Output({"type": "repeater-change",    "field": MATCH}, "data"),
         Output({"type": "repeater-ann-relay", "field": MATCH}, "data")],
        [Input({"type": "repeater-add",    "field": MATCH}, "n_clicks"),
         Input({"type": "repeater-delete", "field": MATCH, "index": ALL}, "n_clicks"),
         Input("current-doc-id", "data")],
        [State({"type": "repeater-store",  "field": MATCH}, "data"),
         State({"type": "repeater-change", "field": MATCH}, "data"),
         State("annotations-store", "data")],
        prevent_initial_call="initial_duplicate",
    )
    def update_repeater(add_clicks, delete_clicks, doc_id, store_data, change_count, annotations_data):
        pipe_field = ctx.outputs_list[0]["id"]["field"]
        field_path = pipe_field.replace("|", ".")

        # Find the template and finalize its field_path for rendering.
        ta = _ta()
        template = _find_repeater_template(ta.widgets, field_path)
        if template is None:
            raise PreventUpdate
        widget = copy.deepcopy(template)
        parts = field_path.rsplit(".", 1)
        widget._finalize_paths(parent_path=parts[0] if len(parts) > 1 else "")

        # Doc navigation / initial load: reload indices from annotation.
        if not ctx.triggered_id or ctx.triggered_id == "current-doc-id":
            indices = []
            if doc_id:
                ann = _get_ann(annotations_data, doc_id)
                if ann is not None:
                    lst = value_helpers.get_model_value(ann, field_path)
                    if isinstance(lst, list):
                        indices = list(range(len(lst)))
            store_data = {"indices": indices, "next_index": len(indices)}
            return store_data, widget._render_items(indices, ta, doc_id, annotations_data=annotations_data), no_update, no_update

        if not ctx.triggered or not ctx.triggered[0].get("value"):
            raise PreventUpdate

        if store_data is None:
            store_data = {"indices": [], "next_index": 0}

        indices = list(store_data.get("indices", []))
        active_value = None
        is_delete = False
        ann_relay = no_update

        if isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get("type") == "repeater-add":
            new_index = len(indices)
            indices = list(range(new_index + 1))
            active_value = str(new_index)
            if doc_id and _get_ann(annotations_data, doc_id) is not None:
                ann_relay = _sync_annotation_add(widget, field_path, annotations_data, doc_id, new_index)

        elif isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get("type") == "repeater-delete":
            delete_index = ctx.triggered_id.get("index")
            if delete_index in indices:
                del_position = indices.index(delete_index)
                if doc_id and _get_ann(annotations_data, doc_id) is not None:
                    ann_relay = _sync_annotation_delete(field_path, annotations_data, doc_id, del_position)
                indices = list(range(len(indices) - 1))
                active_value = str(indices[0]) if indices else None
                is_delete = True

        # Use updated annotations_data for rendering if we modified it
        render_annotations = ann_relay if ann_relay is not no_update else annotations_data
        new_data = {"indices": indices, "next_index": len(indices)}
        new_change = (change_count or 0) + 1 if is_delete else no_update
        return new_data, widget._render_items(indices, ta, doc_id, active_value=active_value, annotations_data=render_annotations), new_change, ann_relay

    # --- Relay repeater-ann-relay → annotations-store (static outputs only) ---
    @app.callback(
        Output("annotations-store", "data", allow_duplicate=True),
        Input({"type": "repeater-ann-relay", "field": ALL}, "data"),
        prevent_initial_call=True,
    )
    def relay_repeater_ann(all_updates):
        if not ctx.triggered or not ctx.triggered[0].get("value"):
            return no_update
        return ctx.triggered[0]["value"]

    # --- Relay repeater deletes → span-any-change so doc viewer re-renders ---
    @app.callback(
        Output("span-any-change", "data", allow_duplicate=True),
        Input({"type": "repeater-change", "field": ALL}, "data"),
        State("span-any-change", "data"),
        prevent_initial_call=True,
    )
    def relay_repeater_changes(all_changes, global_count):
        if not ctx.triggered or not any(t.get("value") for t in ctx.triggered):
            return no_update
        return (global_count or 0) + 1


def setup_nested_repeater_callbacks(tater_app: TaterApp) -> None:
    """Register a single generic MATCH callback for all nested repeater instances.

    Replaces the per-instance ``register_list_callbacks`` approach so that a
    single callback handles any depth of repeater-inside-repeater without
    knowing field names at registration time.  ``ld`` in the component ID
    encodes the nesting structure as dash-joined field names
    (e.g. ``"findings-annotations"``).
    """
    app = tater_app.app
    _get_current_app_fn = tater_app._get_current_app

    def _ta() -> TaterApp:
        if _get_current_app_fn is not None:
            result = _get_current_app_fn()
            if result is not None:
                return result
        return tater_app

    def _find_nested_template(ld: str):
        """Locate the inner RepeaterWidget from a dash-joined ld string.

        e.g. ``"findings-annotations"`` walks tater_app.widgets → finds the
        RepeaterWidget at ``findings`` then ``annotations`` in its item_widgets.
        Returns ``(template, outer_list_field, item_field)`` or ``(None, None, None)``.
        """
        segments = ld.split("-")
        search_in = _ta().widgets
        current = None
        for seg in segments:
            found = next((w for w in search_in if w.schema_field == seg), None)
            if found is None:
                return None, None, None
            current = found
            search_in = getattr(current, "item_widgets", [])
        if not isinstance(current, RepeaterWidget):
            return None, None, None
        return current, segments[0], segments[-1]

    @app.callback(
        [
            Output({"type": _NESTED_STORE_TYPE, "ld": MATCH, "li": MATCH}, "data"),
            Output({"type": _NESTED_ITEMS_TYPE, "ld": MATCH, "li": MATCH}, "children"),
            Output({"type": "nested-repeater-ann-relay", "ld": MATCH, "li": MATCH}, "data"),
        ],
        [
            Input({"type": _NESTED_ADD_TYPE, "ld": MATCH, "li": MATCH}, "n_clicks"),
            Input(
                {"type": _NESTED_DELETE_TYPE, "ld": MATCH, "li": MATCH, "inner_li": ALL},
                "n_clicks",
            ),
        ],
        [
            State({"type": _NESTED_STORE_TYPE, "ld": MATCH, "li": MATCH}, "data"),
            State("current-doc-id", "data"),
            State("annotations-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def _update_nested_items(add_clicks, delete_clicks, store_data, doc_id, annotations_data):
        ld = ctx.outputs_list[0]["id"]["ld"]
        outer_li = ctx.outputs_list[0]["id"]["li"]

        template, outer_list_field, item_field = _find_nested_template(ld)
        if template is None:
            raise PreventUpdate

        if not ctx.triggered or not ctx.triggered[0].get("value"):
            raise PreventUpdate

        if store_data is None:
            store_data = {"indices": [], "next_index": 0}

        ta = _ta()
        indices = list(store_data.get("indices", []))
        ann_relay = no_update

        if isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get("type") == _NESTED_ADD_TYPE:
            new_index = len(indices)
            indices = list(range(new_index + 1))
            ann = _get_ann(annotations_data, doc_id)
            if doc_id and ann is not None:
                for iw in template.item_widgets:
                    if isinstance(iw, ContainerWidget):
                        continue
                    if not isinstance(iw, ControlWidget):
                        continue
                    try:
                        value_helpers.set_model_value(
                            ann,
                            f"{outer_list_field}.{outer_li}.{item_field}.{new_index}.{iw.schema_field}",
                            iw.empty_value,
                        )
                    except Exception:
                        pass
                ann_relay = {**(annotations_data or {}), doc_id: ann}

        elif isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get("type") == _NESTED_DELETE_TYPE:
            inner_li_del = ctx.triggered_id.get("inner_li")
            if inner_li_del in indices:
                del_position = indices.index(inner_li_del)
                ann = _get_ann(annotations_data, doc_id)
                if doc_id and ann is not None:
                    full_path = f"{outer_list_field}.{outer_li}.{item_field}"
                    inner_list = value_helpers.get_model_value(ann, full_path)
                    if isinstance(inner_list, list) and del_position < len(inner_list):
                        inner_list.pop(del_position)
                    ann_relay = {**(annotations_data or {}), doc_id: ann}
                indices = list(range(len(indices) - 1))

        render_ann = ann_relay if ann_relay is not no_update else annotations_data
        new_data = {"indices": indices, "next_index": len(indices)}
        return new_data, template._render_nested_items(
            indices, ld, outer_li, outer_list_field, item_field, ta, doc_id, render_ann
        ), ann_relay

    # ---- Relay nested-repeater-ann-relay → annotations-store (static outputs only) ----
    @app.callback(
        Output("annotations-store", "data", allow_duplicate=True),
        Input({"type": "nested-repeater-ann-relay", "ld": ALL, "li": ALL}, "data"),
        prevent_initial_call=True,
    )
    def relay_nested_ann(all_updates):
        if not ctx.triggered or not ctx.triggered[0].get("value"):
            return no_update
        return ctx.triggered[0]["value"]
