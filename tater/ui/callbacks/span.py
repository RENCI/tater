"""Span annotation callbacks."""
from __future__ import annotations

from typing import TYPE_CHECKING

from dash import Input, Output, State, ALL, MATCH, ctx, no_update, html, ClientsideFunction
import dash_mantine_components as dmc

from tater.models.span import SpanAnnotation
from tater.ui import value_helpers
from tater.ui.callbacks.helpers import _get_ann
from tater.widgets.base import ContainerWidget
from tater.widgets.repeater import RepeaterWidget
from tater.widgets.span import SpanAnnotationWidget

if TYPE_CHECKING:
    from tater.ui.tater_app import TaterApp


# ---------------------------------------------------------------------------
# Widget-tree helpers
# ---------------------------------------------------------------------------

def _has_any_span(widgets: list) -> bool:
    """Return True if any SpanAnnotationWidget exists at any nesting depth."""
    for w in widgets:
        if isinstance(w, SpanAnnotationWidget):
            return True
        if isinstance(w, RepeaterWidget) and _has_any_span(w.item_widgets):
            return True
        if isinstance(w, ContainerWidget) and hasattr(w, "children") and _has_any_span(w.children):
            return True
    return False


def _collect_all_span_templates(widgets: list) -> list:
    """Recursively collect all unique SpanAnnotationWidget templates."""
    result = []
    for w in widgets:
        if isinstance(w, SpanAnnotationWidget):
            result.append(w)
        elif isinstance(w, RepeaterWidget):
            result.extend(_collect_all_span_templates(w.item_widgets))
        elif isinstance(w, ContainerWidget) and hasattr(w, "children"):
            result.extend(_collect_all_span_templates(w.children))
    return result


def _collect_span_instances(widgets: list, annotation, path_prefix: str = ""):
    """Yield (span_widget_template, actual_field_path) for every span list in the annotation.

    Traverses the widget tree, expanding repeater items based on the annotation's
    actual list length.  Supports arbitrary nesting depth.
    """
    for w in widgets:
        w_path = f"{path_prefix}.{w.schema_field}" if path_prefix else w.schema_field
        if isinstance(w, SpanAnnotationWidget):
            yield w, w_path
        elif isinstance(w, RepeaterWidget):
            n = 0
            if annotation is not None:
                lst = value_helpers.get_model_value(annotation, w_path)
                n = len(lst) if isinstance(lst, list) else 0
            for i in range(n):
                yield from _collect_span_instances(w.item_widgets, annotation, f"{w_path}.{i}")
        elif isinstance(w, ContainerWidget) and hasattr(w, "children"):
            yield from _collect_span_instances(w.children, annotation, w_path)


# ---------------------------------------------------------------------------
# Document content renderer
# ---------------------------------------------------------------------------

def _render_document_content(text: str, doc_id: str, tater_app, annotations_data: dict | None) -> list | str:
    """
    Return Dash component children for the document viewer.

    When no SpanAnnotationWidgets are present, returns the raw text string.
    Otherwise builds a list of strings and highlighted html.Mark components.

    Each mark's ``data-field`` is the full pipe-encoded field path
    (e.g. ``"findings|0|spans"``), which the JS uses for delete routing
    and active-entity tracking.
    """
    if not doc_id or not _has_any_span(tater_app.widgets):
        return text

    ann = _get_ann(annotations_data, doc_id)

    # Collect (span, pipe_field, color) for all span instances in the annotation
    all_spans = []
    for widget_template, field_path in _collect_span_instances(tater_app.widgets, ann):
        if ann is None:
            continue
        spans = value_helpers.get_model_value(ann, field_path) or []
        pipe_field = field_path.replace(".", "|")
        for span in spans:
            tag = span.tag if hasattr(span, "tag") else span.get("tag")
            color = widget_template.get_color_for_tag(tag)
            all_spans.append((span, pipe_field, color))

    if not all_spans:
        return text

    # Sort by start position; skip overlapping spans
    def _span_start(item):
        s = item[0]
        return s.start if hasattr(s, "start") else s.get("start", 0)

    all_spans.sort(key=_span_start)

    components = []
    pos = 0
    for span, pipe_field, color in all_spans:
        s_start = span.start if hasattr(span, "start") else span.get("start")
        s_end = span.end if hasattr(span, "end") else span.get("end")
        s_text = span.text if hasattr(span, "text") else span.get("text", "")
        tag = span.tag if hasattr(span, "tag") else span.get("tag")

        if s_start < pos:
            continue  # overlapping — skip
        if s_start > pos:
            components.append(text[pos:s_start])

        components.append(
            html.Mark(
                s_text,
                **{
                    "data-start": s_start,
                    "data-end": s_end,
                    "data-field": pipe_field,
                    "data-tag": tag,
                    "data-color": color,
                    "style": { "backgroundColor": color },
                },
            )
        )
        pos = s_end

    if pos < len(text):
        components.append(text[pos:])

    return components


# ---------------------------------------------------------------------------
# Callback registration
# ---------------------------------------------------------------------------

def setup_span_callbacks(tater_app: TaterApp) -> None:
    """Register unified MATCH-based callbacks for all SpanAnnotationWidgets."""
    app = tater_app.app
    _get_current_app_fn = tater_app._get_current_app

    def _ta() -> TaterApp:
        if _get_current_app_fn is not None:
            result = _get_current_app_fn()
            if result is not None:
                return result
        return tater_app

    # ---- Clientside: relay pending delete from global proxy to delete store ----
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="captureDelete"),
        Output("span-delete-store", "data"),
        Input("span-delete-proxy", "n_clicks"),
        prevent_initial_call=True,
    )

    # ---- Clientside: capture text selection → per-item selection store ----
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="captureSelection"),
        Output({"type": "span-selection", "field": MATCH}, "data"),
        Input({"type": "span-add-btn", "field": MATCH, "tag": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )

    # ---- Server: add span → MATCH-only output ----
    # Dash disallows mixing MATCH dict-ID outputs with static string-ID outputs
    # in the same callback.  add_span therefore writes only to the per-item
    # span-trigger store (embedding the annotation update in the store data).
    # relay_span_triggers then unpacks the annotation update and writes to
    # annotations-store (both static string outputs — no MATCH mixing issue).
    @app.callback(
        Output({"type": "span-trigger", "field": MATCH}, "data"),
        Input({"type": "span-selection", "field": MATCH}, "data"),
        State("current-doc-id", "data"),
        State({"type": "span-trigger", "field": MATCH}, "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )
    def add_span(selection, doc_id, trigger_data, annotations_data):
        if not selection or not doc_id:
            return no_update

        pipe_field = ctx.triggered_id["field"]
        field_path = pipe_field.replace("|", ".")

        start_js = selection.get("start")
        end_js = selection.get("end")
        tag = selection.get("tag")

        if start_js is None or end_js is None or not tag:
            return no_update

        doc = next((d for d in _ta().documents if d.id == doc_id), None)
        if not doc:
            return no_update

        full_text = doc.load_content()
        if not (0 <= start_js < end_js <= len(full_text)):
            return no_update

        raw_slice = full_text[start_js:end_js]
        text = raw_slice.strip()
        if not text:
            return no_update

        trim_start = raw_slice.find(text)
        start = start_js + trim_start
        end = start + len(text)

        ann = _get_ann(annotations_data, doc_id)
        if ann is None:
            return no_update
        current_spans = value_helpers.get_model_value(ann, field_path) or []

        for existing in current_spans:
            ex_start = existing.start if hasattr(existing, "start") else existing.get("start")
            ex_end = existing.end if hasattr(existing, "end") else existing.get("end")
            if start < ex_end and end > ex_start:
                return no_update

        new_span = SpanAnnotation(start=start, end=end, text=text, tag=tag)
        new_spans = list(current_spans) + [new_span.model_dump()]
        value_helpers.set_model_value(ann, field_path, new_spans)
        new_annotations_data = {**(annotations_data or {}), doc_id: ann}

        prev_count = trigger_data.get("count", 0) if isinstance(trigger_data, dict) else (trigger_data or 0)
        return {"count": prev_count + 1, "annotations_update": new_annotations_data}

    # ---- Server: relay any per-item trigger → global span-any-change + annotations-store ----
    # This is the first writer of span-any-change (no allow_duplicate needed).
    # Both outputs are static string IDs — no MATCH mixing issue.
    @app.callback(
        Output("span-any-change", "data"),
        Output("annotations-store", "data", allow_duplicate=True),
        Input({"type": "span-trigger", "field": ALL}, "data"),
        State("span-any-change", "data"),
        prevent_initial_call=True,
    )
    def relay_span_triggers(all_triggers, global_count):
        if not ctx.triggered or not ctx.triggered[0].get("value"):
            return no_update, no_update
        triggered_value = ctx.triggered[0]["value"]
        annotations_update = (
            triggered_value.get("annotations_update")
            if isinstance(triggered_value, dict)
            else None
        )
        new_count = (global_count or 0) + 1
        return new_count, (annotations_update if annotations_update is not None else no_update)

    # ---- Server: refresh entity-button counts on add, delete, or doc navigation ----
    @app.callback(
        Output({"type": "span-entity-buttons", "field": MATCH}, "children"),
        Input({"type": "span-trigger", "field": MATCH}, "data"),
        Input("span-any-change", "data"),
        Input("current-doc-id", "data"),
        State("annotations-store", "data"),
    )
    def update_entity_counts(item_trigger, any_change, doc_id, annotations_data):
        pipe_field = ctx.outputs_list["id"]["field"]
        field_path = pipe_field.replace("|", ".")
        span_templates = _collect_all_span_templates(_ta().widgets)
        span_by_schema_field = {w.schema_field: w for w in span_templates}
        schema_field = field_path.split(".")[-1]
        widget = span_by_schema_field.get(schema_field)
        if widget is None:
            return no_update
        counts = {}
        if doc_id:
            ann = _get_ann(annotations_data, doc_id)
            if ann is not None:
                spans = value_helpers.get_model_value(ann, field_path) or []
                for span in spans:
                    tag = span.tag if hasattr(span, "tag") else span.get("tag")
                    counts[tag] = counts.get(tag, 0) + 1
        return widget._make_buttons(pipe_field, counts)

    # ---- Server: delete span → increment global span-any-change ----
    # Must be registered AFTER relay_span_triggers (which is the first writer).
    @app.callback(
        Output("span-any-change", "data", allow_duplicate=True),
        Output("annotations-store", "data", allow_duplicate=True),
        Input("span-delete-store", "data"),
        State("current-doc-id", "data"),
        State("span-any-change", "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )
    def delete_span(delete_data, doc_id, global_count, annotations_data):
        if not delete_data or not doc_id:
            return no_update, no_update

        pipe_field = delete_data.get("field")
        del_start = delete_data.get("start")
        del_end = delete_data.get("end")
        if not pipe_field or del_start is None or del_end is None:
            return no_update, no_update

        field_path = pipe_field.replace("|", ".")
        ann = _get_ann(annotations_data, doc_id)
        if ann is None:
            return no_update, no_update

        current_spans = value_helpers.get_model_value(ann, field_path) or []
        new_spans = [
            s for s in current_spans
            if not (
                (s.start if hasattr(s, "start") else s.get("start")) == del_start
                and (s.end if hasattr(s, "end") else s.get("end")) == del_end
            )
        ]
        value_helpers.set_model_value(ann, field_path, new_spans)
        new_annotations_data = {**(annotations_data or {}), doc_id: ann}

        return (global_count or 0) + 1, new_annotations_data
