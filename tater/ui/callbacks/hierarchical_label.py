"""Hierarchical label callbacks."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional

from dash import Input, Output, State, ALL, MATCH, ctx, no_update, ClientsideFunction

from tater.ui import value_helpers
from tater.ui.callbacks.helpers import _get_ann
from tater.widgets.base import ContainerWidget
from tater.widgets.hierarchical_label import (
    HierarchicalLabelWidget,
    HierarchicalLabelSelectWidget,
    HierarchicalLabelMultiWidget,
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

def setup_hl_select_callbacks(tater_app: TaterApp) -> None:
    """Register MATCH callbacks for all HierarchicalLabelSelectWidget instances."""
    app = tater_app.app
    _get_current_app_fn = tater_app._get_current_app

    def _ta() -> TaterApp:
        if _get_current_app_fn is not None:
            result = _get_current_app_fn()
            if result is not None:
                return result
        return tater_app

    def _get_widget(field_path: str) -> Optional[HierarchicalLabelSelectWidget]:
        w = _find_hl_template(_ta().widgets, field_path)
        return w if isinstance(w, HierarchicalLabelSelectWidget) else None

    # 1. Load value on doc change or repeater reload
    @app.callback(
        Output({"type": "hl-select", "field": MATCH}, "value"),
        Input("current-doc-id", "data"),
        Input("repeater-load-trigger", "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )
    def load_select(doc_id, _trigger, annotations_data):
        pipe_field = ctx.outputs_list["id"]["field"]
        field_path = pipe_field.replace("|", ".")
        ann = _get_ann(annotations_data, doc_id) if doc_id else None
        stored = value_helpers.get_model_value(ann, field_path) if ann is not None else None
        if stored:
            return json.dumps(stored, separators=(",", ":"))
        return None

    # 2. On selection change, write path to relay store
    @app.callback(
        Output({"type": "hl-select-relay", "field": MATCH}, "data"),
        Input({"type": "hl-select", "field": MATCH}, "value"),
        State("current-doc-id", "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )
    def handle_select_change(selected_value, doc_id, annotations_data):
        ann = _get_ann(annotations_data, doc_id) if doc_id else None
        if ann is None:
            return no_update
        path = json.loads(selected_value) if selected_value else None
        pipe_field = ctx.outputs_list["id"]["field"]
        field_path = pipe_field.replace("|", ".")
        return {"field": field_path, "value": path}

    # 3. Clientside: apply relay → annotations-store
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="applyFieldOp"),
        Output("annotations-store", "data", allow_duplicate=True),
        Input({"type": "hl-select-relay", "field": ALL}, "data"),
        State("current-doc-id", "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )


def setup_hl_multi_callbacks(tater_app: TaterApp) -> None:
    """Register MATCH callbacks for all HierarchicalLabelMultiWidget instances."""
    app = tater_app.app
    _get_current_app_fn = tater_app._get_current_app

    def _ta() -> TaterApp:
        if _get_current_app_fn is not None:
            result = _get_current_app_fn()
            if result is not None:
                return result
        return tater_app

    def _get_widget(field_path: str) -> Optional[HierarchicalLabelMultiWidget]:
        w = _find_hl_template(_ta().widgets, field_path)
        return w if isinstance(w, HierarchicalLabelMultiWidget) else None

    # 1. Load values on doc change or repeater reload
    @app.callback(
        Output({"type": "hl-multi", "field": MATCH}, "value"),
        Input("current-doc-id", "data"),
        Input("repeater-load-trigger", "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )
    def load_multi(doc_id, _trigger, annotations_data):
        pipe_field = ctx.outputs_list["id"]["field"]
        field_path = pipe_field.replace("|", ".")
        ann = _get_ann(annotations_data, doc_id) if doc_id else None
        stored = value_helpers.get_model_value(ann, field_path) if ann is not None else None
        if stored:
            return [json.dumps(p, separators=(",", ":")) for p in stored]
        return []

    # 2. On selection change, write full paths to relay store
    @app.callback(
        Output({"type": "hl-multi-relay", "field": MATCH}, "data"),
        Input({"type": "hl-multi", "field": MATCH}, "value"),
        State("current-doc-id", "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )
    def handle_multi_change(selected_values, doc_id, annotations_data):
        if not ctx.triggered or not ctx.triggered[0].get("value") is not None:
            pass  # allow empty list through — that's a deliberate clear
        ann = _get_ann(annotations_data, doc_id) if doc_id else None
        if ann is None:
            return no_update
        paths = [json.loads(v) for v in (selected_values or [])]
        pipe_field = ctx.outputs_list["id"]["field"]
        field_path = pipe_field.replace("|", ".")
        return {"field": field_path, "value": paths if paths else None}

    # 3. Clientside: apply relay → annotations-store
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="applyFieldOp"),
        Output("annotations-store", "data", allow_duplicate=True),
        Input({"type": "hl-multi-relay", "field": ALL}, "data"),
        State("current-doc-id", "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )
