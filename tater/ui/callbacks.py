"""Dash callback registrations for TaterApp."""
from __future__ import annotations

import copy
from typing import TYPE_CHECKING

import json
import time
from datetime import datetime

from dash import Input, Output, State, ALL, MATCH, ctx, no_update, html
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from tater.ui import value_helpers

if TYPE_CHECKING:
    from tater.ui.tater_app import TaterApp
    from tater.widgets.base import TaterWidget


def setup_callbacks(tater_app: TaterApp) -> None:
    # Removed clientside keyboard navigation callback
    """Register document and navigation callbacks on the Dash app."""
    app = tater_app.app
    has_instructions = bool(tater_app.instructions and tater_app.instructions.strip())

    # Setup timing callbacks
    _setup_timing_callbacks(tater_app)

    # Update document display and info.
    # span-any-change fires whenever a span is added or deleted, causing re-render.
    span_trigger_inputs = (
        [Input("span-any-change", "data")] if _has_any_span(tater_app.widgets) else []
    )

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

        content = _render_document_content(raw_text, doc_id, tater_app)

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

        if ctx.triggered_id == "btn-prev" and current_index > 0:
            current_index -= 1
        elif ctx.triggered_id == "btn-next" and current_index < len(tater_app.documents) - 1:
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

        if not ctx.triggered[0]["value"]:
            return no_update, no_update

        new_index = ctx.triggered_id["index"]

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
    """Setup unified callbacks to capture all ControlWidget value changes."""
    app = tater_app.app

    # Build auto-advance field set at registration time
    auto_advance_fields = {
        w.field_path
        for w in _collect_value_capture_widgets(tater_app.widgets)
        if w.auto_advance
    }

    # Build empty_value lookup keyed by schema_field (last path segment).
    # Used by load callbacks to return widget-appropriate defaults instead of None.
    # Keying by last segment handles list-item widgets (e.g. "pets.0.weight" → "weight").
    empty_value_lookup = {
        w.schema_field: w.empty_value
        for w in _collect_all_control_templates(tater_app.widgets)
    }
    print(f"[TATER:register] setup_value_capture_callbacks: auto_advance_fields={auto_advance_fields!r}")
    print(f"[TATER:register] setup_value_capture_callbacks: empty_value_lookup={empty_value_lookup!r}")

    # --- Capture: value prop (all non-boolean ControlWidgets) ---
    @app.callback(
        Output("status-store", "data", allow_duplicate=True),
        Output("auto-advance-store", "data", allow_duplicate=True),
        Input({"type": "tater-control", "field": ALL}, "value"),
        State("current-doc-id", "data"),
        State("auto-advance-store", "data"),
        prevent_initial_call=True,
    )
    def capture_values(all_values, doc_id, advance_count):
        if not doc_id or not ctx.triggered_id:
            return no_update, no_update
        field_path = ctx.triggered_id["field"].replace("|", ".")  # decode pipe-encoded dot path
        value = ctx.triggered[0]["value"]
        if value == "":
            value = None
        annotation = tater_app.annotations.get(doc_id)
        if annotation is None:
            return no_update, no_update
        old_value = value_helpers.get_model_value(annotation, field_path)
        print(f"[TATER:fire] capture_values: doc={doc_id!r} field={field_path!r} old={old_value!r} → new={value!r}")
        value_helpers.set_model_value(annotation, field_path, value)
        update_status_for_doc(tater_app, doc_id)
        status = tater_app.metadata[doc_id].status if doc_id in tater_app.metadata else "not_started"
        if field_path in auto_advance_fields:
            if value != old_value and value is not None:
                return status, (advance_count or 0) + 1
        return status, no_update

    # --- Capture: checked prop (BooleanWidgets) ---
    @app.callback(
        Output("status-store", "data", allow_duplicate=True),
        Output("auto-advance-store", "data", allow_duplicate=True),
        Input({"type": "tater-bool-control", "field": ALL}, "checked"),
        State("current-doc-id", "data"),
        State("auto-advance-store", "data"),
        prevent_initial_call=True,
    )
    def capture_checked(all_values, doc_id, advance_count):
        if not doc_id or not ctx.triggered_id:
            return no_update, no_update
        field_path = ctx.triggered_id["field"].replace("|", ".")  # decode pipe-encoded dot path
        value = ctx.triggered[0]["value"]
        annotation = tater_app.annotations.get(doc_id)
        if annotation is None:
            return no_update, no_update
        old_value = value_helpers.get_model_value(annotation, field_path)
        print(f"[TATER:fire] capture_checked: doc={doc_id!r} field={field_path!r} old={old_value!r} → new={value!r}")
        value_helpers.set_model_value(annotation, field_path, value)
        update_status_for_doc(tater_app, doc_id)
        status = tater_app.metadata[doc_id].status if doc_id in tater_app.metadata else "not_started"
        if field_path in auto_advance_fields:
            if value != old_value:
                return status, (advance_count or 0) + 1
        return status, no_update

    # --- Load: value prop --- push annotation values to widgets on doc change
    @app.callback(
        Output({"type": "tater-control", "field": ALL}, "value"),
        Input("current-doc-id", "data"),
        State({"type": "tater-control", "field": ALL}, "id"),
        prevent_initial_call="initial_duplicate",
    )
    def load_values(doc_id, all_ids):
        annotation = tater_app.annotations.get(doc_id) if doc_id else None
        print(f"[TATER:fire] load_values: doc={doc_id!r} {len(all_ids or [])} fields")
        result = []
        for wid in (all_ids or []):
            field = wid["field"].replace("|", ".")  # decode pipe-encoded dot path
            v = value_helpers.get_model_value(annotation, field) if annotation else None
            if v is None:
                v = empty_value_lookup.get(field.split(".")[-1])
            print(f"[TATER:fire]   load_values field={field!r} → {v!r}")
            result.append(v)
        return result

    # --- Load: checked prop ---
    @app.callback(
        Output({"type": "tater-bool-control", "field": ALL}, "checked"),
        Input("current-doc-id", "data"),
        State({"type": "tater-bool-control", "field": ALL}, "id"),
        prevent_initial_call="initial_duplicate",
    )
    def load_checked(doc_id, all_ids):
        annotation = tater_app.annotations.get(doc_id) if doc_id else None
        print(f"[TATER:fire] load_checked: doc={doc_id!r} {len(all_ids or [])} fields")
        result = []
        for wid in (all_ids or []):
            field = wid["field"].replace("|", ".")  # decode pipe-encoded dot path
            v = value_helpers.get_model_value(annotation, field) if annotation else None
            out = bool(v) if v is not None else False
            print(f"[TATER:fire]   load_checked field={field!r} → {out!r}")
            result.append(out)
        return result


def setup_span_callbacks(tater_app: TaterApp) -> None:
    """Register unified MATCH-based callbacks for all SpanAnnotationWidgets."""
    from tater.widgets.span import SpanAnnotationWidget
    from dash import MATCH, ALL

    span_templates = _collect_all_span_templates(tater_app.widgets)
    if not span_templates:
        return

    app = tater_app.app
    # Map schema_field → widget template so entity buttons can be rebuilt
    span_by_schema_field = {w.schema_field: w for w in span_templates}

    # ---- Clientside: relay pending delete from global proxy to delete store ----
    app.clientside_callback(
        "window.dash_clientside.tater.captureDelete",
        Output("span-delete-store", "data"),
        Input("span-delete-proxy", "n_clicks"),
        prevent_initial_call=True,
    )

    # ---- Clientside: capture text selection → per-item selection store ----
    app.clientside_callback(
        "window.dash_clientside.tater.captureSelection",
        Output({"type": "span-selection", "field": MATCH}, "data"),
        Input({"type": "span-add-btn", "field": MATCH, "tag": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )

    # ---- Server: add span → increment per-item trigger (MATCH-only output) ----
    # Dash disallows mixing MATCH dict-ID outputs with static string-ID outputs
    # in the same callback.  add_span therefore writes only to the per-item
    # span-trigger store; a separate relay_span_triggers callback converts the
    # ALL pattern to the global span-any-change store so the doc viewer refreshes.
    @app.callback(
        Output({"type": "span-trigger", "field": MATCH}, "data"),
        Input({"type": "span-selection", "field": MATCH}, "data"),
        State("current-doc-id", "data"),
        State({"type": "span-trigger", "field": MATCH}, "data"),
        prevent_initial_call=True,
    )
    def add_span(selection, doc_id, trigger_count):
        if not selection or not doc_id:
            return no_update

        pipe_field = ctx.triggered_id["field"]
        field_path = pipe_field.replace("|", ".")

        start_js = selection.get("start")
        end_js = selection.get("end")
        tag = selection.get("tag")

        if start_js is None or end_js is None or not tag:
            return no_update

        doc = next((d for d in tater_app.documents if d.id == doc_id), None)
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

        from tater.models.span import SpanAnnotation
        annotation = tater_app.annotations[doc_id]
        current_spans = value_helpers.get_model_value(annotation, field_path) or []

        for existing in current_spans:
            if start < existing.end and end > existing.start:
                return no_update

        new_spans = list(current_spans) + [SpanAnnotation(start=start, end=end, text=text, tag=tag)]
        value_helpers.set_model_value(annotation, field_path, new_spans)
        tater_app._save_annotations_to_file(doc_id=doc_id)

        return (trigger_count or 0) + 1

    # ---- Server: relay any per-item trigger → global span-any-change ----
    # This is the first writer of span-any-change (no allow_duplicate needed).
    @app.callback(
        Output("span-any-change", "data"),
        Input({"type": "span-trigger", "field": ALL}, "data"),
        State("span-any-change", "data"),
        prevent_initial_call=True,
    )
    def relay_span_triggers(all_triggers, global_count):
        if not ctx.triggered or not ctx.triggered[0].get("value"):
            return no_update
        return (global_count or 0) + 1

    # ---- Server: refresh entity-button counts on add, delete, or doc navigation ----
    @app.callback(
        Output({"type": "span-entity-buttons", "field": MATCH}, "children"),
        Input({"type": "span-trigger", "field": MATCH}, "data"),
        Input("span-any-change", "data"),
        Input("current-doc-id", "data"),
    )
    def update_entity_counts(item_trigger, any_change, doc_id):
        pipe_field = ctx.outputs_list["id"]["field"]
        field_path = pipe_field.replace("|", ".")
        schema_field = field_path.split(".")[-1]
        widget = span_by_schema_field.get(schema_field)
        if widget is None:
            return no_update
        counts = {}
        if doc_id:
            annotation = tater_app.annotations.get(doc_id)
            if annotation:
                spans = value_helpers.get_model_value(annotation, field_path) or []
                for span in spans:
                    counts[span.tag] = counts.get(span.tag, 0) + 1
        return widget._make_buttons(pipe_field, counts)

    # ---- Server: delete span → increment global span-any-change ----
    # Must be registered AFTER relay_span_triggers (which is the first writer).
    @app.callback(
        Output("span-any-change", "data", allow_duplicate=True),
        Input("span-delete-store", "data"),
        State("current-doc-id", "data"),
        State("span-any-change", "data"),
        prevent_initial_call=True,
    )
    def delete_span(delete_data, doc_id, global_count):
        if not delete_data or not doc_id:
            return no_update

        pipe_field = delete_data.get("field")
        del_start = delete_data.get("start")
        del_end = delete_data.get("end")
        if not pipe_field or del_start is None or del_end is None:
            return no_update

        field_path = pipe_field.replace("|", ".")
        annotation = tater_app.annotations.get(doc_id)
        if not annotation:
            return no_update

        current_spans = value_helpers.get_model_value(annotation, field_path) or []
        new_spans = [s for s in current_spans if not (s.start == del_start and s.end == del_end)]
        value_helpers.set_model_value(annotation, field_path, new_spans)
        tater_app._save_annotations_to_file(doc_id=doc_id)

        return (global_count or 0) + 1


def setup_repeater_callbacks(tater_app: TaterApp) -> None:
    """Register a single MATCH callback handling all repeaters at every nesting depth.

    Also registers HierarchicalLabel repeater callbacks (which need per-ld registration)
    and, when any SpanAnnotationWidget is present, a relay that increments
    span-any-change whenever a list item is deleted so the doc viewer re-renders.
    """
    from tater.widgets.repeater import RepeaterWidget
    from tater.widgets.base import ContainerWidget, ControlWidget
    from dash.exceptions import PreventUpdate

    if not any(isinstance(w, RepeaterWidget) for w in tater_app._all_widgets):
        return

    app = tater_app.app

    # --- Register HierarchicalLabel callbacks for all HL items inside repeaters ---
    for hl_widget, ld, field_segments in _collect_hl_in_repeaters(tater_app.widgets):
        hl_widget.register_repeater_callbacks(app, ld, field_segments)

    # --- Annotation sync helpers ---
    def _sync_annotation_add(widget_template, field_path, doc_id, new_index):
        annotation = tater_app.annotations.get(doc_id)
        if annotation is None:
            return
        extended = False
        for iw in widget_template.item_widgets:
            if isinstance(iw, ContainerWidget):
                extended = True
                continue
            if not isinstance(iw, ControlWidget):
                continue
            try:
                tater_app._set_model_value(
                    annotation,
                    f"{field_path}.{new_index}.{iw.schema_field}",
                    iw.empty_value,
                )
                extended = True
            except Exception:
                pass
        if not extended:
            try:
                tater_app._set_model_value(annotation, f"{field_path}.{new_index}", None)
            except Exception:
                pass
        tater_app._save_annotations_to_file(doc_id=doc_id)

    def _sync_annotation_delete(field_path, doc_id, del_position):
        annotation = tater_app.annotations.get(doc_id)
        if annotation is None:
            return
        current_list = value_helpers.get_model_value(annotation, field_path)
        if isinstance(current_list, list) and del_position < len(current_list):
            current_list.pop(del_position)
        tater_app._save_annotations_to_file(doc_id=doc_id)

    # --- Unified MATCH callback ---
    @app.callback(
        [Output({"type": "repeater-store",  "field": MATCH}, "data"),
         Output({"type": "repeater-items",  "field": MATCH}, "children"),
         Output({"type": "repeater-change", "field": MATCH}, "data")],
        [Input({"type": "repeater-add",    "field": MATCH}, "n_clicks"),
         Input({"type": "repeater-delete", "field": MATCH, "index": ALL}, "n_clicks"),
         Input("current-doc-id", "data")],
        [State({"type": "repeater-store",  "field": MATCH}, "data"),
         State({"type": "repeater-change", "field": MATCH}, "data")],
    )
    def update_repeater(add_clicks, delete_clicks, doc_id, store_data, change_count):
        pipe_field = ctx.outputs_list[0]["id"]["field"]
        field_path = pipe_field.replace("|", ".")

        # Find the template and finalize its field_path for rendering.
        template = _find_repeater_template(tater_app.widgets, field_path)
        if template is None:
            raise PreventUpdate
        widget = copy.deepcopy(template)
        parts = field_path.rsplit(".", 1)
        widget._finalize_paths(parent_path=parts[0] if len(parts) > 1 else "")

        # Doc navigation / initial load: reload indices from annotation.
        if not ctx.triggered_id or ctx.triggered_id == "current-doc-id":
            indices = []
            if doc_id:
                annotation = tater_app.annotations.get(doc_id)
                if annotation is not None:
                    lst = value_helpers.get_model_value(annotation, field_path)
                    if isinstance(lst, list):
                        indices = list(range(len(lst)))
            store_data = {"indices": indices, "next_index": len(indices)}
            return store_data, widget._render_items(indices, tater_app, doc_id), no_update

        if not ctx.triggered or not ctx.triggered[0].get("value"):
            raise PreventUpdate

        if store_data is None:
            store_data = {"indices": [], "next_index": 0}

        indices = list(store_data.get("indices", []))
        active_value = None
        is_delete = False

        if isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get("type") == "repeater-add":
            new_index = len(indices)
            indices = list(range(new_index + 1))
            active_value = str(new_index)
            if doc_id and doc_id in tater_app.annotations:
                _sync_annotation_add(widget, field_path, doc_id, new_index)

        elif isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get("type") == "repeater-delete":
            delete_index = ctx.triggered_id.get("index")
            if delete_index in indices:
                del_position = indices.index(delete_index)
                if doc_id and doc_id in tater_app.annotations:
                    _sync_annotation_delete(field_path, doc_id, del_position)
                indices = list(range(len(indices) - 1))
                active_value = str(indices[0]) if indices else None
                is_delete = True

        new_data = {"indices": indices, "next_index": len(indices)}
        new_change = (change_count or 0) + 1 if is_delete else no_update
        return new_data, widget._render_items(indices, tater_app, doc_id, active_value=active_value), new_change

    # --- Relay repeater deletes → span-any-change so doc viewer re-renders ---
    if _has_any_span(tater_app.widgets):
        @app.callback(
            Output("span-any-change", "data", allow_duplicate=True),
            Input({"type": "repeater-change", "field": ALL}, "data"),
            State("span-any-change", "data"),
            prevent_initial_call=True,
        )
        def relay_repeater_changes(all_changes, global_count):
            if not ctx.triggered or not ctx.triggered[0].get("value"):
                return no_update
            return (global_count or 0) + 1


def _find_repeater_template(widgets: list, field_path: str):
    """Find the RepeaterWidget template for a (possibly nested) field path.

    Strips numeric segments so ``"findings.0.annotations"`` resolves the same
    template as ``"findings.annotations"``.
    """
    segments = [s for s in field_path.split(".") if not s.isdigit()]
    return _find_by_segments(widgets, segments)


def _find_by_segments(widgets: list, segments: list):
    from tater.widgets.repeater import RepeaterWidget
    if not segments:
        return None
    for w in widgets:
        if w.schema_field == segments[0]:
            if len(segments) == 1:
                return w if isinstance(w, RepeaterWidget) else None
            if isinstance(w, RepeaterWidget):
                return _find_by_segments(w.item_widgets, segments[1:])
    return None


def _collect_hl_in_repeaters(widgets: list, field_segments: list | None = None):
    """Yield (hl_widget, ld, field_segments) for every HierarchicalLabel inside a repeater.

    ``ld`` is the dash-joined schema-field path used as the MATCH discriminator in
    ``register_repeater_callbacks``; ``field_segments`` is the list of field names
    from the outermost list down to the HL widget.
    """
    from tater.widgets.repeater import RepeaterWidget
    from tater.widgets.hierarchical_label import HierarchicalLabelWidget
    from tater.widgets.base import ContainerWidget
    if field_segments is None:
        field_segments = []
    for w in widgets:
        if isinstance(w, RepeaterWidget):
            outer_segments = field_segments + [w.schema_field]
            for item_w in w.item_widgets:
                if isinstance(item_w, HierarchicalLabelWidget):
                    segs = outer_segments + [item_w.schema_field]
                    yield item_w, "-".join(segs), segs
                elif isinstance(item_w, RepeaterWidget):
                    yield from _collect_hl_in_repeaters([item_w], outer_segments)
        elif isinstance(w, ContainerWidget) and hasattr(w, "children"):
            yield from _collect_hl_in_repeaters(w.children, field_segments)


def _has_any_span(widgets: list) -> bool:
    """Return True if any SpanAnnotationWidget exists at any nesting depth."""
    from tater.widgets.span import SpanAnnotationWidget
    from tater.widgets.repeater import RepeaterWidget
    from tater.widgets.base import ContainerWidget
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
    from tater.widgets.span import SpanAnnotationWidget
    from tater.widgets.repeater import RepeaterWidget
    from tater.widgets.base import ContainerWidget
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
    from tater.widgets.span import SpanAnnotationWidget
    from tater.widgets.repeater import RepeaterWidget
    from tater.widgets.base import ContainerWidget
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


def _collect_value_capture_widgets(widgets: list[TaterWidget]) -> list[TaterWidget]:
    """Recursively collect all ControlWidget instances (non-containers).

    Used to build the auto-advance field set and to find required widgets
    for status checking. Skips RepeaterWidget children (their items are
    handled dynamically via unified ALL callbacks).
    """
    from tater.widgets.base import ControlWidget
    from tater.widgets.group import GroupWidget
    from tater.widgets.repeater import RepeaterWidget

    captured = []
    for widget in widgets:
        if isinstance(widget, RepeaterWidget):
            continue
        elif isinstance(widget, GroupWidget):
            if hasattr(widget, "children") and widget.children:
                captured.extend(_collect_value_capture_widgets(widget.children))
        elif isinstance(widget, ControlWidget):
            captured.append(widget)
    return captured


def _collect_all_control_templates(widgets: list[TaterWidget]) -> list[TaterWidget]:
    """Recursively collect all ControlWidget templates, including inside repeaters.

    Used to build empty_value lookups for load callbacks.
    """
    from tater.widgets.base import ControlWidget
    from tater.widgets.group import GroupWidget
    from tater.widgets.repeater import RepeaterWidget

    captured = []
    for widget in widgets:
        if isinstance(widget, RepeaterWidget):
            captured.extend(_collect_all_control_templates(widget.item_widgets))
        elif isinstance(widget, GroupWidget):
            if hasattr(widget, "children") and widget.children:
                captured.extend(_collect_all_control_templates(widget.children))
        elif isinstance(widget, ControlWidget):
            captured.append(widget)
    return captured


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


def _render_document_content(text: str, doc_id: str, tater_app) -> list | str:
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

    annotation = tater_app.annotations.get(doc_id)

    # Collect (span, pipe_field, color) for all span instances in the annotation
    all_spans = []
    for widget_template, field_path in _collect_span_instances(tater_app.widgets, annotation):
        if annotation is None:
            continue
        spans = value_helpers.get_model_value(annotation, field_path) or []
        pipe_field = field_path.replace(".", "|")
        for span in spans:
            color = widget_template.get_color_for_tag(span.tag)
            all_spans.append((span, pipe_field, color))

    if not all_spans:
        return text

    # Sort by start position; skip overlapping spans
    all_spans.sort(key=lambda x: x[0].start)

    components = []
    pos = 0
    for span, pipe_field, color in all_spans:
        if span.start < pos:
            continue  # overlapping — skip
        if span.start > pos:
            components.append(text[pos:span.start])

        components.append(
            html.Mark(
                span.text,
                style={"backgroundColor": color, "padding": "1px 0"},
                **{
                    "data-tag": span.tag,
                    "data-start": str(span.start),
                    "data-end": str(span.end),
                    "data-field": pipe_field,
                    "data-color": color,
                },
            )
        )
        pos = span.end

    if pos < len(text):
        components.append(text[pos:])

    return components
