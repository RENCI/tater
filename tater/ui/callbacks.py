"""Dash callback registrations for TaterApp."""
from __future__ import annotations

from typing import TYPE_CHECKING

import json
import time
from datetime import datetime

from dash import Input, Output, State, ALL, ctx, no_update, html
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from tater.ui import value_helpers

if TYPE_CHECKING:
    from tater.ui.tater_app import TaterApp
    from tater.widgets.base import TaterWidget


def setup_callbacks(tater_app: TaterApp) -> None:
    # Removed clientside keyboard navigation callback
    """Register document and navigation callbacks on the Dash app."""
    from tater.widgets.span import SpanAnnotationWidget
    from tater.widgets.repeater import RepeaterWidget

    app = tater_app.app
    span_widgets = [w for w in tater_app.widgets if isinstance(w, SpanAnnotationWidget)]

    # Collect (span_widget, outer_field, span_field, ld) for span widgets inside repeaters
    list_span_pairs = []
    for w in tater_app.widgets:
        if isinstance(w, RepeaterWidget):
            for item_w in w.item_widgets:
                if isinstance(item_w, SpanAnnotationWidget):
                    ld = f"{w.field_path}-{item_w.schema_field}"
                    list_span_pairs.append((item_w, w.field_path, item_w.schema_field, ld))

    has_instructions = bool(tater_app.instructions and tater_app.instructions.strip())

    # Setup timing callbacks
    _setup_timing_callbacks(tater_app)

    # Update document display and info.
    # Span trigger stores are included as additional inputs so that adding or
    # deleting a span causes the document to re-render with updated highlights.
    span_trigger_inputs = [Input(f"span-trigger-{w.component_id}", "data") for w in span_widgets]
    # Also include list-mode span triggers (global list trigger per (cid, ld))
    for span_w, _, _, ld in list_span_pairs:
        list_trigger_id = f"span-list-trigger-{span_w.component_id}-{ld}"
        span_trigger_inputs.append(Input(list_trigger_id, "data"))

    @app.callback(
        [Output("document-content", "children"),
         Output("document-title", "children"),
         Output("document-metadata", "children"),
         Output("document-progress", "value"),
         Output("btn-prev", "disabled"),
         Output("btn-next", "disabled")],
        [Input("current-doc-id", "data")] + span_trigger_inputs,
    )
    def update_document(doc_id, *_span_triggers):
        if not doc_id:
            return "No document loaded", "No document", "", 0, True, True

        # Find document by ID
        doc = next((d for d in tater_app.documents if d.id == doc_id), None)
        if not doc:
            return "Document not found", "Error", "", 0, True, True

        # Load document content
        try:
            raw_text = doc.load_content()
        except Exception as e:
            raw_text = f"Error loading file: {e}"

        content = _render_document_content(raw_text, doc_id, span_widgets, tater_app, list_span_pairs)

        doc_index = next((i for i, d in enumerate(tater_app.documents) if d.id == doc_id), 0)
        title = f"Document {doc_index + 1} of {len(tater_app.documents)}"

        # Format metadata from document info dict (without document count)
        metadata_parts = []
        if doc.info:
            for key, value in doc.info.items():
                metadata_parts.append(f"{key}: {value}")
        metadata = " | ".join(metadata_parts) if metadata_parts else ""

        progress = ((doc_index + 1) / len(tater_app.documents)) * 100 if tater_app.documents else 0

        is_first = doc_index == 0
        is_last = doc_index == len(tater_app.documents) - 1
        return content, title, metadata, progress, is_first, is_last

    # Button navigation
    # NOTE: Multiple callbacks write to "current-doc-id" and "timing-store".
    # Every callback that writes to these outputs MUST use allow_duplicate=True,
    # except this one (the first registered). Omitting it on any subsequent
    # callback will cause a Dash duplicate-output error at startup.
    @app.callback(
        Output("current-doc-id", "data"),
        Output("timing-store", "data"),
        [Input("btn-prev", "n_clicks"),
         Input("btn-next", "n_clicks")],
        State("current-doc-id", "data"),
        State("timing-store", "data"),
        prevent_initial_call=True
    )
    def navigate_buttons(prev_clicks, next_clicks, current_doc_id, timing_data):
        if not ctx.triggered or not tater_app.documents:
            return no_update, no_update

        current_index = next((i for i, d in enumerate(tater_app.documents) if d.id == current_doc_id), 0)
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if button_id == "btn-prev" and current_index > 0:
            current_index -= 1
        elif button_id == "btn-next" and current_index < len(tater_app.documents) - 1:
            current_index += 1
        else:
            return no_update, no_update

        doc_id, new_timing = _perform_navigation(tater_app, current_doc_id, current_index, timing_data)
        return doc_id, new_timing

    # Menu item navigation (allow_duplicate=True required — see note above)
    @app.callback(
        Output("current-doc-id", "data", allow_duplicate=True),
        Output("timing-store", "data", allow_duplicate=True),
        Input({"type": "document-menu-item", "index": ALL}, "n_clicks"),
        State("current-doc-id", "data"),
        State("timing-store", "data"),
        prevent_initial_call=True
    )
    def navigate_menu_item(menu_clicks, current_doc_id, timing_data):
        if not ctx.triggered or not tater_app.documents:
            return no_update, no_update

        triggered = ctx.triggered[0]
        if not triggered["value"]:
            return no_update, no_update

        prop_id = triggered["prop_id"].split(".")[0]
        new_index = json.loads(prop_id)["index"]

        doc_id, new_timing = _perform_navigation(tater_app, current_doc_id, new_index, timing_data)
        return doc_id, new_timing

    # Auto-advance: navigate to next doc when an auto_advance widget gets a value.
    # (allow_duplicate=True required — see note above)
    @app.callback(
        Output("current-doc-id", "data", allow_duplicate=True),
        Output("timing-store", "data", allow_duplicate=True),
        Input("auto-advance-store", "data"),
        State("current-doc-id", "data"),
        State("timing-store", "data"),
        prevent_initial_call=True,
    )
    def navigate_auto_advance(trigger, current_doc_id, timing_data):
        if not trigger:
            return no_update, no_update
        current_index = next(
            (i for i, d in enumerate(tater_app.documents) if d.id == current_doc_id), 0
        )
        if current_index >= len(tater_app.documents) - 1:
            return no_update, no_update
        doc_id, new_timing = _perform_navigation(tater_app, current_doc_id, current_index + 1, timing_data)
        return doc_id, new_timing

    # Refresh menu dropdown with status badges after any navigation or status change
    @app.callback(
        Output("document-menu-dropdown", "children"),
        Input("timing-store", "data"),
        Input("status-store", "data"),
        Input("filter-flagged", "checked"),
    )
    def update_menu_items(timing_data, status_data, flagged_only):
        return _build_menu_items(tater_app, flagged_only=bool(flagged_only))

    # Handle flag-document changes
    # Outputs to timing-store so update_menu_items re-runs after metadata is updated.
    @app.callback(
        Output("timing-store", "data", allow_duplicate=True),
        Input("flag-document", "checked"),
        State("current-doc-id", "data"),
        State("timing-store", "data"),
        prevent_initial_call=True,
    )
    def save_flag(checked, doc_id, timing_data):
        if not doc_id:
            return no_update

        tater_app.metadata[doc_id].flagged = checked

        if timing_data is None:
            timing_data = {}
        timing_data["last_save_time"] = time.time()
        return timing_data

    # Handle document-notes changes
    @app.callback(
        Output("document-notes", "id"),  # Dummy output
        Input("document-notes", "value"),
        State("current-doc-id", "data"),
        State("timing-store", "data"),
        prevent_initial_call=True
    )
    def save_notes(notes, doc_id, timing_data):
        if not doc_id:
            return no_update

        tater_app.metadata[doc_id].notes = notes if notes else ""

        # Update save time
        if timing_data is None:
            timing_data = {}
        timing_data["last_save_time"] = time.time()
        return no_update

    if has_instructions:
        @app.callback(
            Output("instructions-drawer", "opened"),
            Input("btn-open-instructions", "n_clicks"),
            prevent_initial_call=True,
        )
        def open_instructions(n_clicks):
            if not n_clicks:
                return no_update
            return True


def _setup_timing_callbacks(tater_app: TaterApp) -> None:
    """Setup callbacks for save time and document timing display."""
    app = tater_app.app

    # Manual save button
    @app.callback(
        Output("timing-store", "data", allow_duplicate=True),
        Input("btn-save", "n_clicks"),
        State("current-doc-id", "data"),
        State("timing-store", "data"),
        prevent_initial_call=True,
    )
    def on_save_click(n_clicks, current_doc_id, timing_data):
        if not n_clicks:
            return no_update
        tater_app._save_annotations_to_file(doc_id=current_doc_id)
        if timing_data is None:
            timing_data = {}
        timing_data["last_save_time"] = time.time()
        return timing_data

    # Handle document changes to initialize timing
    @app.callback(
        Output("timing-store", "data", allow_duplicate=True),
        Output("status-store", "data", allow_duplicate=True),
        Input("current-doc-id", "data"),
        State("timing-store", "data"),
        prevent_initial_call='initial_duplicate',
    )
    def on_doc_change(doc_id, timing_data):
        if doc_id:
            tater_app.metadata[doc_id].visited = True
            update_status_for_doc(tater_app, doc_id)

        if timing_data is None:
            timing_data = {}
        timing_data["doc_start_time"] = time.time()
        timing_data["paused"] = False
        if "session_start_time" not in timing_data or timing_data["session_start_time"] is None:
            timing_data["session_start_time"] = time.time()

        status = tater_app.metadata[doc_id].status if doc_id and doc_id in tater_app.metadata else "not_started"
        return timing_data, status

    # Update footer text every second

    _STATUS_LABELS = {"not_started": "Not Started", "in_progress": "In Progress", "complete": "Complete"}
    _STATUS_COLORS = {"not_started": "gray", "in_progress": "blue", "complete": "teal"}

    @app.callback(
        Output("save-status-text", "children"),
        Output("save-status-text", "c"),
        Output("timing-text", "children"),
        Output("btn-pause-timer", "children"),
        Input("clock-interval", "n_intervals"),
        State("timing-store", "data"),
        State("current-doc-id", "data"),
        prevent_initial_call=False,
    )
    def update_footer(n_intervals, timing_data, doc_id):
        now = time.time()

        # Save status text - show error in red, or timestamp of last save
        if tater_app._save_error:
            save_text = f"Save failed: {tater_app._save_error}"
            save_color = "red"
        elif timing_data and timing_data.get("last_save_time"):
            save_time = timing_data["last_save_time"]
            dt = datetime.fromtimestamp(save_time)
            save_text = f"Last saved: {dt.strftime('%H:%M:%S')}"
            save_color = "dimmed"
        else:
            save_text = "Never saved"
            save_color = "dimmed"

        paused = timing_data.get("paused", False) if timing_data else False

        # Doc time: show total annotation_seconds for current doc, plus live elapsed if not paused
        total_seconds = 0.0
        meta = tater_app.metadata.get(doc_id)
        if meta:
            total_seconds = meta.annotation_seconds
        if not paused and timing_data and timing_data.get("doc_start_time"):
            total_seconds += now - timing_data["doc_start_time"]

        # Format as h/m/s
        total_seconds = int(total_seconds)
        if total_seconds < 60:
            timing_text = f"Doc time: {total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            timing_text = f"Doc time: {minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            timing_text = f"Doc time: {hours}h {minutes}m"

        if paused:
            timing_text += " (paused)"

        pause_icon = DashIconify(icon="tabler:player-play", width=16) if paused else DashIconify(icon="tabler:player-pause", width=16)
        return save_text, save_color, timing_text, pause_icon

    @app.callback(
        Output("timing-store", "data", allow_duplicate=True),
        Input("btn-pause-timer", "n_clicks"),
        State("timing-store", "data"),
        State("current-doc-id", "data"),
        prevent_initial_call=True,
    )
    def toggle_pause(n_clicks, timing_data, doc_id):
        if not n_clicks:
            return no_update
        if timing_data is None:
            timing_data = {}
        now = time.time()
        currently_paused = timing_data.get("paused", False)
        if not currently_paused:
            # Flush elapsed into metadata so time isn't lost
            start = timing_data.get("doc_start_time")
            if start and doc_id and doc_id in tater_app.metadata:
                tater_app.metadata[doc_id].annotation_seconds += now - start
            timing_data["doc_start_time"] = None
            timing_data["paused"] = True
        else:
            timing_data["doc_start_time"] = now
            timing_data["paused"] = False
        return timing_data

    @app.callback(
        Output("status-badge", "children"),
        Output("status-badge", "color"),
        Input("status-store", "data"),
    )
    def update_status_badge(status):
        label = _STATUS_LABELS.get(status, status)
        color = _STATUS_COLORS.get(status, "gray")
        return label, color

    @app.callback(
        Output("notification-container", "sendNotifications"),
        Input("schema-warnings-store", "data"),
    )
    def show_schema_warnings(warnings):
        if not warnings:
            return no_update

        _LABELS = {
            "extra": "In saved file, not in current schema (will be ignored):",
            "missing": "In current schema, not in saved file (will use default):",
        }

        sections = []
        for key in ("extra", "missing"):
            fields = warnings.get(key)
            if not fields:
                continue
            if sections:
                sections.append(html.Div(style={"height": "6px"}))
            sections.append(html.Div(_LABELS[key], style={"fontWeight": 600, "fontSize": "0.8rem"}))
            sections.append(html.Ul(
                [html.Li(f) for f in fields],
                style={"margin": "2px 0 0 0", "paddingLeft": "16px", "listStylePosition": "inside"},
            ))

        return [{
            "id": "schema-mismatch-notification",
            "title": "Schema mismatch",
            "message": html.Div(sections, style={"maxHeight": "200px", "overflowY": "auto"}),
            "color": "yellow",
            "action": "show",
            "autoClose": False,
        }]


def setup_value_capture_callbacks(tater_app: TaterApp) -> None:
    """Setup callbacks to capture widget value changes to annotations store."""
    # Collect all widgets that need value capture
    widgets_to_capture = _collect_value_capture_widgets(tater_app.widgets)

    if not widgets_to_capture:
        return

    # Create callback for each widget
    for widget in widgets_to_capture:
        _register_widget_value_capture(tater_app, widget)


def _collect_value_capture_widgets(widgets: list[TaterWidget]) -> list[TaterWidget]:
    """
    Recursively collect all widgets that capture values (non-containers).

    Skips GroupWidget children (processes them recursively instead).
    Skips RepeaterWidget subclasses — they manage their own value capture.
    """
    from tater.widgets.base import ControlWidget
    from tater.widgets.group import GroupWidget
    from tater.widgets.repeater import RepeaterWidget

    captured = []
    for widget in widgets:
        if isinstance(widget, RepeaterWidget):
            # Skip RepeaterWidget subclasses — they manage their own value capture
            continue
        elif isinstance(widget, GroupWidget):
            # Recursively process GroupWidget children
            if hasattr(widget, "children") and widget.children:
                captured.extend(_collect_value_capture_widgets(widget.children))
        elif isinstance(widget, ControlWidget):
            captured.append(widget)

    return captured


def _register_widget_value_capture(tater_app: TaterApp, widget: TaterWidget) -> None:
    """Register a callback to capture a widget's value changes."""
    app = tater_app.app
    widget_id = widget.component_id
    field_path = widget.field_path
    value_prop = widget.value_prop
    default_value = getattr(widget, "default", None)
    empty_value = widget.empty_value

    # Callback for updating self.annotations when widget value changes
    @app.callback(
        Output(widget_id, "id"),  # Dummy output, just to trigger
        Output("status-store", "data", allow_duplicate=True),
        Input(widget_id, value_prop),
        State("current-doc-id", "data"),
        prevent_initial_call=True
    )
    def capture_value(value, doc_id):
        if not doc_id:
            return widget_id, "not_started"

        value_helpers.set_model_value(tater_app.annotations[doc_id], field_path, value)

        update_status_for_doc(tater_app, doc_id)
        status = tater_app.metadata[doc_id].status if doc_id in tater_app.metadata else "not_started"
        return widget_id, status

    # Auto-advance: when this widget gets a non-empty value, increment the
    # auto-advance-store to trigger navigation to the next document.
    if getattr(widget, "auto_advance", False):
        _empty = widget.empty_value

        @app.callback(
            Output("auto-advance-store", "data", allow_duplicate=True),
            Input(widget_id, value_prop),
            State("auto-advance-store", "data"),
            prevent_initial_call=True,
        )
        def _trigger_auto_advance(value, current_count, _empty=_empty):
            if value is None or value == _empty:
                return no_update
            return (current_count or 0) + 1

    # Callback for updating widget value when document changes.
    # Always allow_duplicate=True so that escape-hatch callbacks registered by
    # app code can also write to widget outputs without a Dash conflict error.
    @app.callback(
        Output(widget_id, value_prop, allow_duplicate=True),
        Input("current-doc-id", "data"),
        prevent_initial_call="initial_duplicate",
    )
    def update_widget_value(doc_id):
        if not doc_id or doc_id not in tater_app.annotations:
            if value_prop == "checked":
                return bool(default_value) if default_value is not None else False
            if default_value is not None:
                return default_value
            return empty_value

        annotation = tater_app.annotations[doc_id]
        value = value_helpers.get_model_value(annotation, field_path)
        if value_prop == "checked":
            if value is None:
                return bool(default_value) if default_value is not None else False
            return bool(value)
        if value is None:
            if default_value is not None:
                return default_value
            return empty_value
        return value


def update_status_for_doc(tater_app: TaterApp, doc_id: str) -> None:
    """Compute and store the annotation status for a document."""
    if not doc_id:
        return
    meta = tater_app.metadata[doc_id]

    if not meta.visited:
        meta.status = "not_started"
        return

    # Booleans always have a value (True/False), so they cannot meaningfully gate completion.
    required_widgets = [
        w for w in _collect_value_capture_widgets(tater_app.widgets)
        if w.required and w.to_python_type() is not bool
    ]
    if not required_widgets:
        meta.status = "complete"
        return

    annotation = tater_app.annotations.get(doc_id)
    if not annotation:
        meta.status = "in_progress"
        return

    for widget in required_widgets:
        value = value_helpers.get_model_value(annotation, widget.field_path)
        if not _has_value(value):
            meta.status = "in_progress"
            return

    meta.status = "complete"


def _has_value(value) -> bool:
    """Return True if a field value is considered filled (non-empty, non-None)."""
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, list) and len(value) == 0:
        return False
    return True


def _build_menu_items(tater_app: TaterApp, flagged_only: bool = False) -> list:
    """Build document menu items with status badges and flag indicators."""
    status_labels = {"not_started": "Not Started", "in_progress": "In Progress", "complete": "Complete"}
    status_colors = {"not_started": "gray", "in_progress": "blue", "complete": "teal"}
    items = []
    for i, doc in enumerate(tater_app.documents):
        meta = tater_app.metadata.get(doc.id)
        flagged = meta.flagged if meta else False
        if flagged_only and not flagged:
            continue
        status = meta.status if meta else "not_started"
        right_children = []
        if flagged:
            right_children.append(DashIconify(icon="tabler:flag-filled", color="red", width=14))
        right_children.append(
            dmc.Badge(
                status_labels.get(status, status),
                color=status_colors.get(status, "gray"),
                variant="light",
                size="xs",
            )
        )
        items.append(
            dmc.MenuItem(
                dmc.Group(
                    [
                        dmc.Text(f"{i + 1}. {doc.display_name()}", size="sm"),
                        dmc.Group(right_children, gap="xs"),
                    ],
                    gap="xs",
                    wrap="nowrap",
                    justify="space-between",
                ),
                id={"type": "document-menu-item", "index": i},
            )
        )
    if not items:
        items.append(dmc.Text("No flagged documents", size="sm", c="dimmed", p="xs"))
    return items


def _perform_navigation(tater_app: TaterApp, current_doc_id: str, new_index: int, timing_data: dict) -> tuple:
    """Shared navigation logic: accumulate timing, save, and return new doc_id and timing."""
    now = time.time()
    if current_doc_id:
        start = timing_data.get("doc_start_time") if timing_data else None
        if start:
            tater_app.metadata[current_doc_id].annotation_seconds += now - start
        update_status_for_doc(tater_app, current_doc_id)

    doc_id = tater_app.documents[new_index].id if new_index < len(tater_app.documents) else ""
    tater_app._save_annotations_to_file(doc_id=current_doc_id)

    if timing_data is None:
        timing_data = {}
    timing_data["last_save_time"] = time.time()
    timing_data["doc_start_time"] = time.time()
    timing_data["paused"] = False
    if "session_start_time" not in timing_data or timing_data["session_start_time"] is None:
        timing_data["session_start_time"] = time.time()

    return doc_id, timing_data


def _render_document_content(
    text: str, doc_id: str, span_widgets: list, tater_app, list_span_pairs: list = ()
) -> list | str:
    """
    Return Dash component children for the document viewer.

    When no SpanAnnotationWidgets are present, returns the raw text string.
    Otherwise builds a list of strings and highlighted html.Mark components.

    ``list_span_pairs`` is a list of (span_widget, outer_field, span_field, ld)
    tuples for span widgets nested inside RepeaterWidgets.
    """
    if not span_widgets and not list_span_pairs or not doc_id:
        return text

    annotation = tater_app.annotations.get(doc_id)

    # Collect (span, widget_cid, color, item_index_or_minus1) for all spans
    # item_index == -1 means top-level (not inside a list)
    all_spans = []

    for widget in span_widgets:
        if annotation:
            spans = value_helpers.get_model_value(annotation, widget.field_path) or []
            for span in spans:
                color = widget.get_color_for_tag(span.tag)
                all_spans.append((span, widget.component_id, color, -1))

    for span_widget, outer_field, span_field, _ld in list_span_pairs:
        if annotation:
            outer_list = value_helpers.get_model_value(annotation, outer_field) or []
            for item_index in range(len(outer_list)):
                item_field_path = f"{outer_field}.{item_index}.{span_field}"
                spans = value_helpers.get_model_value(annotation, item_field_path) or []
                for span in spans:
                    color = span_widget.get_color_for_tag(span.tag)
                    all_spans.append((span, span_widget.component_id, color, item_index))

    if not all_spans:
        return text

    # Sort by start position; skip overlapping spans
    all_spans.sort(key=lambda x: x[0].start)

    components = []
    pos = 0
    for span, widget_cid, color, item_index in all_spans:
        if span.start < pos:
            continue  # overlapping — skip
        if span.start > pos:
            components.append(text[pos:span.start])

        mark_props = {
            "data-tag": span.tag,
            "data-start": str(span.start),
            "data-end": str(span.end),
            "data-field": widget_cid,
            "data-color": color,
        }
        if item_index >= 0:
            mark_props["data-index"] = str(item_index)

        components.append(
            html.Mark(
                span.text,
                style={"backgroundColor": color, "padding": "1px 0"},
                **mark_props,
            )
        )
        pos = span.end

    if pos < len(text):
        components.append(text[pos:])

    return components
