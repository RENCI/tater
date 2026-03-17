"""Dash callback registrations for TaterApp."""
from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Optional

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
        Output("filter-flagged", "variant"),
        Input("timing-store", "data"),
        Input("status-store", "data"),
        Input("filter-flagged", "n_clicks"),
    )
    def update_menu_items(timing_data, status_data, n_clicks):
        flagged_only = bool((n_clicks or 0) % 2)
        return _build_menu_items(tater_app, flagged_only=flagged_only), "filled" if flagged_only else "outline"

    # Load flag and notes from metadata when the document changes.
    @app.callback(
        Output("flag-document", "checked"),
        Output("document-notes", "value"),
        Input("current-doc-id", "data"),
    )
    def load_flag_and_notes(doc_id):
        if not doc_id:
            return False, ""
        meta = tater_app.metadata.get(doc_id)
        if meta is None:
            return False, ""
        return meta.flagged, meta.notes or ""

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

    # Build empty_value lookup keyed by the template's pipe-encoded field_path.
    # This matches the ``tf`` component of each widget's schema_id, so the load
    # callbacks can look up the correct empty_value with ``wid["tf"]`` directly.
    # Keying by tf (e.g. "booleans|is_indoor" for a GroupWidget child) avoids
    # the collision that would arise from keying by the bare schema_field when
    # multiple sub-models have fields with the same name.
    empty_value_lookup = {
        w.field_path.replace(".", "|"): w.empty_value
        for w in _collect_all_control_templates(tater_app.widgets)
    }
    # --- Capture: value prop (all non-boolean ControlWidgets) ---
    @app.callback(
        Output("status-store", "data", allow_duplicate=True),
        Output("auto-advance-store", "data", allow_duplicate=True),
        Input({"type": "tater-control", "ld": ALL, "path": ALL, "tf": ALL}, "value"),
        State("current-doc-id", "data"),
        State("auto-advance-store", "data"),
        prevent_initial_call=True,
    )
    def capture_values(all_values, doc_id, advance_count):
        return _do_capture(doc_id, advance_count, tater_app, auto_advance_fields, convert_empty_str=True)

    # --- Capture: checked prop (BooleanWidgets) ---
    @app.callback(
        Output("status-store", "data", allow_duplicate=True),
        Output("auto-advance-store", "data", allow_duplicate=True),
        Input({"type": "tater-bool-control", "ld": ALL, "path": ALL, "tf": ALL}, "checked"),
        State("current-doc-id", "data"),
        State("auto-advance-store", "data"),
        prevent_initial_call=True,
    )
    def capture_checked(all_values, doc_id, advance_count):
        return _do_capture(doc_id, advance_count, tater_app, auto_advance_fields, advance_requires_value=False)

    # --- Load: value prop --- push annotation values to widgets on doc change
    @app.callback(
        Output({"type": "tater-control", "ld": ALL, "path": ALL, "tf": ALL}, "value"),
        Input("current-doc-id", "data"),
        State({"type": "tater-control", "ld": ALL, "path": ALL, "tf": ALL}, "id"),
        prevent_initial_call="initial_duplicate",
    )
    def load_values(doc_id, all_ids):
        return _do_load(doc_id, all_ids, tater_app, empty_value_lookup)

    # --- Load: checked prop ---
    @app.callback(
        Output({"type": "tater-bool-control", "ld": ALL, "path": ALL, "tf": ALL}, "checked"),
        Input("current-doc-id", "data"),
        State({"type": "tater-bool-control", "ld": ALL, "path": ALL, "tf": ALL}, "id"),
        prevent_initial_call="initial_duplicate",
    )
    def load_checked(doc_id, all_ids):
        return _do_load(doc_id, all_ids, tater_app, empty_value_lookup, as_bool=True)


def _do_capture(
    doc_id: str,
    advance_count,
    tater_app,
    auto_advance_fields: set,
    convert_empty_str: bool = False,
    advance_requires_value: bool = True,
):
    """Shared body for capture_values and capture_checked.

    ``convert_empty_str`` normalises empty strings to None (needed for text
    widgets where Dash reports ``""`` when the user clears a field).

    ``advance_requires_value`` keeps the auto-advance guard ``value is not None``
    used for non-boolean widgets; pass ``False`` for boolean widgets where a
    toggle back to ``False`` should also trigger auto-advance.
    """
    if not doc_id or not ctx.triggered_id:
        return no_update, no_update
    tid = ctx.triggered_id
    field_path = _decode_field_path(tid["ld"], tid["path"], tid["tf"])
    value = ctx.triggered[0]["value"]
    if convert_empty_str and value == "":
        value = None
    annotation = tater_app.annotations.get(doc_id)
    if annotation is None:
        return no_update, no_update
    old_value = value_helpers.get_model_value(annotation, field_path)
    value_helpers.set_model_value(annotation, field_path, value)
    update_status_for_doc(tater_app, doc_id)
    status = tater_app.metadata[doc_id].status if doc_id in tater_app.metadata else "not_started"
    if field_path in auto_advance_fields:
        changed = value != old_value
        if changed and (not advance_requires_value or value is not None):
            return status, (advance_count or 0) + 1
    return status, no_update


def _do_load(doc_id: str, all_ids: list, tater_app, empty_value_lookup: dict, as_bool: bool = False) -> list:
    """Shared body for load_values and load_checked.

    ``as_bool`` wraps each value in ``bool()`` (needed for boolean widgets).
    """
    annotation = tater_app.annotations.get(doc_id) if doc_id else None
    result = []
    for wid in (all_ids or []):
        field = _decode_field_path(wid["ld"], wid["path"], wid["tf"])
        v = value_helpers.get_model_value(annotation, field) if annotation else None
        if v is None:
            v = empty_value_lookup.get(wid["tf"])
        result.append(bool(v) if (as_bool and v is not None) else (False if as_bool else v))
    return result


def _decode_field_path(ld: str, path: str, tf: str) -> str:
    """Reconstruct a dot-notation field path from schema_id components.

    For standalone widgets (``ld == ""``), ``tf`` holds the full pipe-encoded
    path and is simply decoded.

    For repeater items, ``ld`` is the pipe-joined list-field path
    (e.g. ``"pets"`` or ``"findings|annotations"``), ``path`` is the
    dot-joined index chain (e.g. ``"0"`` or ``"0.2"``), and ``tf`` is the
    widget's schema_field within the item (e.g. ``"kind"``).  The three parts
    are interleaved to reconstruct the full path.
    """
    if not ld:
        return tf.replace("|", ".")
    list_fields = ld.split("|")
    indices = path.split(".")
    parts: list[str] = []
    for seg, idx in zip(list_fields, indices):
        parts.extend([seg, idx])
    # tf may itself be pipe-encoded when the widget is a GroupWidget child
    # (e.g. "booleans|is_indoor" → "booleans.is_indoor").
    parts.append(tf.replace("|", "."))
    return ".".join(parts)



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

    When any SpanAnnotationWidget is present, also registers a relay that increments
    span-any-change whenever a list item is deleted so the doc viewer re-renders.
    """
    from tater.widgets.repeater import RepeaterWidget
    from tater.widgets.base import ContainerWidget, ControlWidget
    from dash.exceptions import PreventUpdate

    if not any(isinstance(w, RepeaterWidget) for w in tater_app._all_widgets):
        return

    app = tater_app.app

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
            if not ctx.triggered or not any(t.get("value") for t in ctx.triggered):
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



def setup_hl_callbacks(tater_app: TaterApp) -> None:
    """Register a single MATCH callback handling all HierarchicalLabel instances.

    Works for standalone and repeater-embedded widgets at any nesting depth.
    Component IDs use pipe-encoded field paths so the ``field`` key uniquely
    identifies each HL instance without per-widget registration.
    """
    from tater.widgets.hierarchical_label import HierarchicalLabelWidget, HierarchicalLabelTagsWidget, _find_path, _make_buttons, _section, _node_at

    hl_templates = [w for w in _collect_hl_templates(tater_app.widgets)
                    if not isinstance(w, HierarchicalLabelTagsWidget)]
    if not hl_templates:
        return

    app = tater_app.app

    def _get_widget(field_path: str) -> Optional[HierarchicalLabelWidget]:
        return _find_hl_template(tater_app.widgets, field_path)

    # ---- 1a. Show/hide clear button ----
    @app.callback(
        Output({"type": "hier-search-clear", "field": MATCH}, "style"),
        Input({"type": "hier-search", "field": MATCH}, "value"),
        prevent_initial_call=False,
    )
    def toggle_clear(value):
        return {} if value else {"display": "none"}

    # ---- 1b. Clear search on button click ----
    @app.callback(
        Output({"type": "hier-search", "field": MATCH}, "value", allow_duplicate=True),
        Input({"type": "hier-search-clear", "field": MATCH}, "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_search(_):
        return ""

    # ---- 2. Reset navigation when document changes ----
    @app.callback(
        Output({"type": "hier-nav", "field": MATCH}, "data"),
        Input("current-doc-id", "data"),
        prevent_initial_call=True,
    )
    def reset_nav(doc_id):
        pipe_field = ctx.outputs_list[0]["id"]["field"]
        field_path = pipe_field.replace("|", ".")
        widget = _get_widget(field_path)
        if widget is None:
            return []
        annotation = tater_app.annotations.get(doc_id) if doc_id else None
        selected_value = value_helpers.get_model_value(annotation, field_path) if annotation else None
        if selected_value:
            computed_path = _find_path(widget.root, selected_value)
            if computed_path:
                node = _node_at(widget.root, computed_path)
                return computed_path[:-1] if node.is_leaf else computed_path
        return []

    # ---- 3. Handle node button click → update path, write if leaf ----
    @app.callback(
        Output({"type": "hier-nav", "field": MATCH}, "data", allow_duplicate=True),
        Output({"type": "hier-search", "field": MATCH}, "value", allow_duplicate=True),
        Input({"type": "hier-node-btn", "field": MATCH, "depth": ALL, "name": ALL}, "n_clicks"),
        State({"type": "hier-nav", "field": MATCH}, "data"),
        State("current-doc-id", "data"),
        prevent_initial_call=True,
    )
    def handle_click(node_clicks, current_path, doc_id):
        if not ctx.triggered_id:
            return no_update, no_update
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict) or triggered.get("type") != "hier-node-btn":
            return no_update, no_update
        if not ctx.triggered or not ctx.triggered[0].get("value"):
            return no_update, no_update

        pipe_field = triggered["field"]
        field_path = pipe_field.replace("|", ".")
        depth = triggered["depth"]
        node_name = triggered["name"]
        path = list(current_path or [])

        widget = _get_widget(field_path)
        if widget is None:
            return no_update, no_update
        root = widget.root

        parent = _node_at(root, path[:depth])
        clicked = parent.find(node_name)
        is_search_result = False
        if clicked is None:
            clicked = next((n for n in root.all_leaves() if n.name == node_name), None)
            if clicked is None:
                return no_update, no_update
            is_search_result = True

        if clicked.is_leaf:
            current_value = None
            annotation = None
            if doc_id:
                annotation = tater_app.annotations.get(doc_id)
                if annotation is not None:
                    current_value = value_helpers.get_model_value(annotation, field_path)

            if is_search_result:
                full_path = _find_path(root, node_name)
                new_path = full_path[:-1]
            else:
                new_path = path[:depth]

            if current_value == node_name:
                if annotation is not None:
                    value_helpers.set_model_value(annotation, field_path, None)
                    tater_app._save_annotations_to_file(doc_id=doc_id)
            else:
                if annotation is not None:
                    value_helpers.set_model_value(annotation, field_path, node_name)
                    tater_app._save_annotations_to_file(doc_id=doc_id)

            return new_path, ("" if is_search_result else no_update)
        else:
            if depth < len(path) and path[depth] == node_name:
                # Back: parent is non-leaf; only selectable if allow_non_leaf=True, else clear
                new_value = (path[depth - 1] if depth > 0 else None) if widget.allow_non_leaf else None
                if doc_id:
                    annotation = tater_app.annotations.get(doc_id)
                    if annotation is not None:
                        value_helpers.set_model_value(annotation, field_path, new_value)
                        tater_app._save_annotations_to_file(doc_id=doc_id)
                return path[:depth], no_update
            # Forward: navigate into non-leaf; only select if allow_non_leaf=True
            new_path = path[:depth] + [node_name]
            if widget.allow_non_leaf and doc_id:
                annotation = tater_app.annotations.get(doc_id)
                if annotation is not None:
                    value_helpers.set_model_value(annotation, field_path, node_name)
                    tater_app._save_annotations_to_file(doc_id=doc_id)
            return new_path, no_update

    # ---- 4. Rebuild sections from nav state / search / doc change ----
    @app.callback(
        Output({"type": "hier-sections", "field": MATCH}, "children"),
        Output({"type": "hier-breadcrumb", "field": MATCH}, "children"),
        Input({"type": "hier-nav", "field": MATCH}, "data"),
        Input({"type": "hier-search", "field": MATCH}, "value"),
        Input("current-doc-id", "data"),
        prevent_initial_call=False,
    )
    def update_display(current_path, search_query, doc_id):
        pipe_field = ctx.outputs_list[0]["id"]["field"]
        field_path = pipe_field.replace("|", ".")
        path = list(current_path or [])

        widget = _get_widget(field_path)
        if widget is None:
            return no_update, no_update
        root = widget.root

        selected_value = None
        if doc_id:
            annotation = tater_app.annotations.get(doc_id)
            if annotation is not None:
                selected_value = value_helpers.get_model_value(annotation, field_path)

        breadcrumb = " → ".join(path) if path else "None selected"

        if search_query and search_query.strip():
            q = search_query.strip().lower()
            matches = [n for n in root.all_leaves() if q in n.name.lower()]
            return [_section("Search results", _make_buttons(matches, pipe_field, 0, selected_value=selected_value))], breadcrumb

        return widget._render_sections(path, pipe_field, selected_value), breadcrumb


def setup_hl_tags_callbacks(tater_app: TaterApp) -> None:
    """Register MATCH callbacks for all HierarchicalLabelTagsWidget instances."""
    from tater.widgets.hierarchical_label import (
        HierarchicalLabelTagsWidget, _find_path, _node_at, _make_tags_option_buttons, _make_tags_pill,
    )

    tags_templates = [w for w in _collect_hl_templates(tater_app.widgets)
                      if isinstance(w, HierarchicalLabelTagsWidget)]
    if not tags_templates:
        return

    app = tater_app.app

    def _get_widget(field_path: str):
        w = _find_hl_template(tater_app.widgets, field_path)
        return w if isinstance(w, HierarchicalLabelTagsWidget) else None

    # 1. Reset nav + search on doc change — initialise path from existing selection
    @app.callback(
        Output({"type": "hl-tags-nav", "field": MATCH}, "data", allow_duplicate=True),
        Output({"type": "hl-tags-search", "field": MATCH}, "value", allow_duplicate=True),
        Input("current-doc-id", "data"),
        prevent_initial_call=True,
    )
    def reset_nav(doc_id):
        pipe_field = ctx.outputs_list[0]["id"]["field"]
        field_path = pipe_field.replace("|", ".")
        widget = _get_widget(field_path)
        if widget is None:
            return [], ""
        annotation = tater_app.annotations.get(doc_id) if doc_id else None
        selected_value = value_helpers.get_model_value(annotation, field_path) if annotation else None
        if selected_value:
            computed_path = _find_path(widget.root, selected_value)
            if computed_path:
                return computed_path, ""  # Tags: full path including selected node
        return [], ""

    # 2. Handle option tag click — always a forward selection
    @app.callback(
        Output({"type": "hl-tags-nav", "field": MATCH}, "data", allow_duplicate=True),
        Output({"type": "hl-tags-search", "field": MATCH}, "value", allow_duplicate=True),
        Input({"type": "hl-tags-node-btn", "field": MATCH, "depth": ALL, "name": ALL}, "n_clicks"),
        State({"type": "hl-tags-nav", "field": MATCH}, "data"),
        State("current-doc-id", "data"),
        prevent_initial_call=True,
    )
    def handle_option_click(node_clicks, current_path, doc_id):
        if not ctx.triggered_id:
            return no_update, no_update
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict) or triggered.get("type") != "hl-tags-node-btn":
            return no_update, no_update
        if not ctx.triggered or not ctx.triggered[0].get("value"):
            return no_update, no_update

        pipe_field = triggered["field"]
        field_path = pipe_field.replace("|", ".")
        node_name = triggered["name"]
        path = list(current_path or [])

        widget = _get_widget(field_path)
        if widget is None:
            return no_update, no_update
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
            return no_update, no_update

        clicked_node = _node_at(root, new_path)
        annotation = tater_app.annotations.get(doc_id) if doc_id else None
        if annotation is not None and (clicked_node.is_leaf or widget.allow_non_leaf):
            value_helpers.set_model_value(annotation, field_path, node_name)
            tater_app._save_annotations_to_file(doc_id=doc_id)

        return new_path, ""

    # 3. Handle pill click → navigate back, selecting parent
    @app.callback(
        Output({"type": "hl-tags-nav", "field": MATCH}, "data", allow_duplicate=True),
        Input({"type": "hl-tags-pill", "field": MATCH, "idx": ALL}, "n_clicks"),
        State({"type": "hl-tags-nav", "field": MATCH}, "data"),
        State("current-doc-id", "data"),
        prevent_initial_call=True,
    )
    def handle_pill_click(n_clicks_list, current_nav, doc_id):
        if not ctx.triggered_id:
            return no_update
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict) or triggered.get("type") != "hl-tags-pill":
            return no_update
        if not ctx.triggered or not ctx.triggered[0].get("value"):
            return no_update

        idx = triggered["idx"]
        pipe_field = triggered["field"]
        field_path = pipe_field.replace("|", ".")
        path = list(current_nav or [])

        widget = _get_widget(field_path)
        # Parent is non-leaf; only selectable if allow_non_leaf=True, else clear
        parent_name = (path[idx - 1] if idx > 0 else None) if (widget and widget.allow_non_leaf) else None
        annotation = tater_app.annotations.get(doc_id) if doc_id else None
        if annotation is not None:
            value_helpers.set_model_value(annotation, field_path, parent_name)
            tater_app._save_annotations_to_file(doc_id=doc_id)

        return path[:idx]

    # 4. Rebuild pills + option tags on nav/search/doc change
    @app.callback(
        Output({"type": "hl-tags-pills", "field": MATCH}, "children"),
        Output({"type": "hl-tags-search", "field": MATCH}, "value", allow_duplicate=True),
        Output({"type": "hl-tags-options", "field": MATCH}, "children"),
        Input({"type": "hl-tags-nav", "field": MATCH}, "data"),
        Input({"type": "hl-tags-search", "field": MATCH}, "value"),
        Input("current-doc-id", "data"),
        prevent_initial_call="initial_duplicate",
    )
    def update_display(current_path, search_query, doc_id):
        pipe_field = ctx.outputs_list[0]["id"]["field"]
        field_path = pipe_field.replace("|", ".")
        path = list(current_path or [])

        triggered = ctx.triggered_id
        if triggered == "current-doc-id" or (
            isinstance(triggered, dict) and triggered.get("type") == "hl-tags-nav"
        ):
            clear_search = ""
        else:
            clear_search = no_update

        widget = _get_widget(field_path)
        if widget is None:
            return no_update, no_update, no_update
        root = widget.root

        annotation = tater_app.annotations.get(doc_id) if doc_id else None
        selected_value = value_helpers.get_model_value(annotation, field_path) if annotation else None

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
            matches = [n for n in root.all_nodes() if n is not root and q in n.name.lower()]
            option_tags = _make_tags_option_buttons(matches, pipe_field, len(path), selected_value)
        else:
            current_node = _node_at(root, path)
            option_tags = _make_tags_option_buttons(current_node.children, pipe_field, len(path), selected_value)

        return pills, clear_search, option_tags


def _collect_hl_templates(widgets: list) -> list:
    """Recursively collect all HierarchicalLabelWidget templates at any nesting depth."""
    from tater.widgets.hierarchical_label import HierarchicalLabelWidget
    from tater.widgets.repeater import RepeaterWidget
    from tater.widgets.base import ContainerWidget
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
    from tater.widgets.hierarchical_label import HierarchicalLabelWidget
    from tater.widgets.repeater import RepeaterWidget
    from tater.widgets.base import ContainerWidget
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
