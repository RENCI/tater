"""Span annotation callbacks."""
from __future__ import annotations

from typing import TYPE_CHECKING

from dash import Input, Output, State, ALL, MATCH, ctx, no_update, html, ClientsideFunction

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

    # ---- Clientside: add span → span-trigger store (MATCH) ----
    # Whitespace trimming, overlap check, and annotation update all run in the
    # browser.  The relay callback unpacks the annotation update.
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="addSpan"),
        Output({"type": "span-trigger", "field": MATCH}, "data"),
        Input({"type": "span-selection", "field": MATCH}, "data"),
        State("current-doc-id", "data"),
        State({"type": "span-trigger", "field": MATCH}, "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )

    # ---- Clientside: relay span-trigger → span-any-change + annotations-store ----
    # First writer of span-any-change (no allow_duplicate needed).
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="relaySpanTriggers"),
        Output("span-any-change", "data"),
        Output("annotations-store", "data", allow_duplicate=True),
        Input({"type": "span-trigger", "field": ALL}, "data"),
        State("span-any-change", "data"),
        prevent_initial_call=True,
    )

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

    # ---- Clientside: delete span → span-any-change + annotations-store ----
    # Must be registered AFTER relaySpanTriggers (which is the first writer of span-any-change).
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="deleteSpan"),
        Output("span-any-change", "data", allow_duplicate=True),
        Output("annotations-store", "data", allow_duplicate=True),
        Input("span-delete-store", "data"),
        State("current-doc-id", "data"),
        State("span-any-change", "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )

    # ---- Clientside: re-render document marks on span change ----
    # Reads raw text and color map from stores; no server round-trip needed.
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="renderDocumentSpans"),
        Output("document-content", "children", allow_duplicate=True),
        Input("span-any-change", "data"),
        State("current-doc-id", "data"),
        State("annotations-store", "data"),
        State("document-text-store", "data"),
        State("span-color-map", "data"),
        prevent_initial_call=True,
    )
