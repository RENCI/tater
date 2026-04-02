"""Core navigation, save, timing, and value-capture callbacks."""
from __future__ import annotations

import json
import time
import flask
from datetime import datetime
from typing import TYPE_CHECKING

from dash import Input, Output, State, ALL, ctx, no_update, html, ClientsideFunction
import dash_mantine_components as dmc

from tater.ui import value_helpers
from tater.ui.callbacks.helpers import (
    _get_ann,
    _get_meta,
    _build_menu_items,
    _perform_navigation,
    update_status_for_doc,
)
from tater.ui.callbacks.span import _render_document_content

if TYPE_CHECKING:
    from tater.ui.tater_app import TaterApp


_STATUS_LABELS = {"not_started": "Not Started", "in_progress": "In Progress", "complete": "Complete"}
_STATUS_COLORS = {"not_started": "gray", "in_progress": "blue", "complete": "teal"}


def setup_callbacks(tater_app: TaterApp) -> None:
    """Register document and navigation callbacks on the Dash app."""
    app = tater_app.app
    has_instructions = bool(tater_app.instructions and tater_app.instructions.strip())

    # In hosted mode, each HTTP request carries a Flask session cookie identifying
    # the user's session. _ta() resolves the correct TaterApp for that session so
    # callbacks work correctly when multiple users share the same Dash process.
    _get_current_app_fn = tater_app._get_current_app

    def _ta() -> TaterApp:
        if _get_current_app_fn is not None:
            result = _get_current_app_fn()
            if result is not None:
                return result
        return tater_app

    # Scroll to top on document navigation.
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="autoScrollTop"),
        Input("current-doc-id", "data"),
        prevent_initial_call=True,
    )

    # Setup timing callbacks
    _setup_timing_callbacks(tater_app, _ta)

    # Update document display and info on navigation.
    @app.callback(
        Output("document-content", "children", allow_duplicate=True),
        Output("document-title", "children"),
        Output("document-metadata", "children"),
        Output("document-progress", "value"),
        Output("btn-prev", "disabled"),
        Output("btn-next", "disabled"),
        Input("current-doc-id", "data"),
        State("annotations-store", "data"),
        prevent_initial_call="initial_duplicate",
    )
    def update_document(doc_id, annotations_data):
        if not doc_id:
            return "No document loaded", "No document", "", 0, True, True

        ta = _ta()
        doc = next((d for d in ta.documents if d.id == doc_id), None)
        if not doc:
            return "Document not found", "Error", "", 0, True, True

        try:
            raw_text = doc.load_content()
        except Exception as e:
            raw_text = f"Error loading file: {e}"

        content = _render_document_content(raw_text, doc_id, ta, annotations_data)

        doc_index = next((i for i, d in enumerate(ta.documents) if d.id == doc_id), 0)
        title = f"{doc_index + 1} / {len(ta.documents)}"

        metadata_parts = []
        if doc.info:
            for key, value in doc.info.items():
                metadata_parts.append(f"{key}: {value}")
        metadata = " | ".join(metadata_parts) if metadata_parts else ""

        progress = ((doc_index + 1) / len(ta.documents)) * 100 if ta.documents else 0

        is_first = doc_index == 0
        is_last = doc_index == len(ta.documents) - 1
        return content, title, metadata, progress, is_first, is_last

    # Re-render document content only when a span is added or deleted.
    # Separated from update_document to avoid recomputing title/metadata/progress/nav
    # on every span change.
    @app.callback(
        Output("document-content", "children", allow_duplicate=True),
        Input("span-any-change", "data"),
        State("current-doc-id", "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )
    def update_document_spans(_, doc_id, annotations_data):
        if not doc_id:
            return no_update
        ta = _ta()
        doc = next((d for d in ta.documents if d.id == doc_id), None)
        if not doc:
            return no_update
        try:
            raw_text = doc.load_content()
        except Exception as e:
            raw_text = f"Error loading file: {e}"
        return _render_document_content(raw_text, doc_id, ta, annotations_data)

    # Button navigation
    # NOTE: Multiple callbacks write to "current-doc-id" and "timing-store".
    # Every callback that writes to these outputs MUST use allow_duplicate=True,
    # except this one (the first registered). Omitting it on any subsequent
    # callback will cause a Dash duplicate-output error at startup.
    @app.callback(
        Output("current-doc-id", "data"),
        Output("timing-store", "data"),
        Output("metadata-store", "data", allow_duplicate=True),
        [Input("btn-prev", "n_clicks"),
         Input("btn-next", "n_clicks")],
        State("current-doc-id", "data"),
        State("timing-store", "data"),
        State("annotations-store", "data"),
        State("metadata-store", "data"),
        prevent_initial_call=True
    )
    def navigate_buttons(prev_clicks, next_clicks, current_doc_id, timing_data, annotations_data, metadata_data):
        ta = _ta()
        if not ctx.triggered or not ta.documents:
            return no_update, no_update, no_update

        current_index = next((i for i, d in enumerate(ta.documents) if d.id == current_doc_id), 0)

        if ctx.triggered_id == "btn-prev" and current_index > 0:
            current_index -= 1
        elif ctx.triggered_id == "btn-next" and current_index < len(ta.documents) - 1:
            current_index += 1
        else:
            return no_update, no_update, no_update

        doc_id, new_timing, new_metadata = _perform_navigation(
            ta, current_doc_id, current_index, timing_data, annotations_data, metadata_data
        )
        return doc_id, new_timing, new_metadata

    # Menu item navigation (allow_duplicate=True required — see note above)
    @app.callback(
        Output("current-doc-id", "data", allow_duplicate=True),
        Output("timing-store", "data", allow_duplicate=True),
        Output("metadata-store", "data", allow_duplicate=True),
        Input({"type": "document-menu-item", "index": ALL}, "n_clicks"),
        State("current-doc-id", "data"),
        State("timing-store", "data"),
        State("annotations-store", "data"),
        State("metadata-store", "data"),
        prevent_initial_call=True
    )
    def navigate_menu_item(menu_clicks, current_doc_id, timing_data, annotations_data, metadata_data):
        ta = _ta()
        if not ctx.triggered or not ta.documents:
            return no_update, no_update, no_update

        if not ctx.triggered[0]["value"]:
            return no_update, no_update, no_update

        new_index = ctx.triggered_id["index"]

        doc_id, new_timing, new_metadata = _perform_navigation(
            ta, current_doc_id, new_index, timing_data, annotations_data, metadata_data
        )
        return doc_id, new_timing, new_metadata

    # Auto-advance: navigate to next doc when an auto_advance widget gets a value.
    # (allow_duplicate=True required — see note above)
    @app.callback(
        Output("current-doc-id", "data", allow_duplicate=True),
        Output("timing-store", "data", allow_duplicate=True),
        Output("metadata-store", "data", allow_duplicate=True),
        Input("auto-advance-store", "data"),
        State("current-doc-id", "data"),
        State("timing-store", "data"),
        State("annotations-store", "data"),
        State("metadata-store", "data"),
        prevent_initial_call=True,
    )
    def navigate_auto_advance(trigger, current_doc_id, timing_data, annotations_data, metadata_data):
        if not trigger:
            return no_update, no_update, no_update
        ta = _ta()
        current_index = next(
            (i for i, d in enumerate(ta.documents) if d.id == current_doc_id), 0
        )
        if current_index >= len(ta.documents) - 1:
            return no_update, no_update, no_update
        doc_id, new_timing, new_metadata = _perform_navigation(
            ta, current_doc_id, current_index + 1, timing_data, annotations_data, metadata_data
        )
        return doc_id, new_timing, new_metadata

    # Refresh menu dropdown with status badges after any navigation or status change
    @app.callback(
        Output("document-menu-dropdown", "children"),
        Output("filter-flagged", "variant"),
        Input("timing-store", "data"),
        Input("status-store", "data"),
        Input("filter-flagged", "n_clicks"),
        State("metadata-store", "data"),
    )
    def update_menu_items(timing_data, status_data, n_clicks, metadata_data):
        flagged_only = bool((n_clicks or 0) % 2)
        return _build_menu_items(_ta(), metadata_data, flagged_only=flagged_only), "filled" if flagged_only else "outline"

    # Load flag and notes from metadata when the document changes.
    @app.callback(
        Output("flag-document", "checked"),
        Output("document-notes", "value"),
        Input("current-doc-id", "data"),
        State("metadata-store", "data"),
    )
    def load_flag_and_notes(doc_id, metadata_data):
        if not doc_id:
            return False, ""
        meta = _get_meta(metadata_data, doc_id)
        return meta.get("flagged", False), meta.get("notes", "") or ""

    # Handle flag-document changes
    # Outputs to timing-store so update_menu_items re-runs after metadata is updated.
    @app.callback(
        Output("timing-store", "data", allow_duplicate=True),
        Output("metadata-store", "data", allow_duplicate=True),
        Input("flag-document", "checked"),
        State("current-doc-id", "data"),
        State("timing-store", "data"),
        State("metadata-store", "data"),
        prevent_initial_call=True,
    )
    def save_flag(checked, doc_id, timing_data, metadata_data):
        if not doc_id:
            return no_update, no_update

        metadata_data = dict(metadata_data or {})
        meta = dict(_get_meta(metadata_data, doc_id))
        meta["flagged"] = checked
        metadata_data[doc_id] = meta

        if timing_data is None:
            timing_data = {}
        timing_data["last_save_time"] = time.time()
        return timing_data, metadata_data

    # Handle document-notes changes
    @app.callback(
        Output("metadata-store", "data", allow_duplicate=True),
        Input("document-notes", "value"),
        State("current-doc-id", "data"),
        State("metadata-store", "data"),
        prevent_initial_call=True
    )
    def save_notes(notes, doc_id, metadata_data):
        if not doc_id:
            return no_update

        metadata_data = dict(metadata_data or {})
        meta = dict(_get_meta(metadata_data, doc_id))
        meta["notes"] = notes if notes else ""
        metadata_data[doc_id] = meta
        return metadata_data

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

    is_hosted = tater_app.annotations_path is None

    if is_hosted:
        # Download annotations as JSON
        @app.callback(
            Output("download-annotations", "data"),
            Input("btn-download", "n_clicks"),
            State("annotations-store", "data"),
            State("metadata-store", "data"),
            prevent_initial_call=True,
        )
        def download_annotations(n_clicks, annotations_data, metadata_data):
            if not n_clicks:
                return no_update
            save_dict = {}
            all_ids = set(annotations_data or {}) | set(metadata_data or {})
            for d_id in all_ids:
                save_dict[d_id] = {
                    "annotations": (annotations_data or {}).get(d_id, {}),
                    "metadata": (metadata_data or {}).get(d_id, {}),
                }
            return {"content": json.dumps(save_dict, indent=2), "filename": "annotations.json"}

        # Start over: open confirmation modal
        @app.callback(
            Output("modal-start-over", "opened"),
            Input("btn-start-over", "n_clicks"),
            Input("btn-start-over-cancel", "n_clicks"),
            prevent_initial_call=True,
        )
        def toggle_start_over_modal(open_clicks, cancel_clicks):
            return ctx.triggered_id == "btn-start-over"

        # Confirm start over: clear Flask session and redirect
        @app.callback(
            Output("annotate-location", "href"),
            Input("btn-start-over-confirm", "n_clicks"),
            prevent_initial_call=True,
        )
        def start_over(n_clicks):
            if not n_clicks:
                return no_update
            flask.session.pop("tater_session", None)
            return "/"

    # Auto-save: write to file whenever annotations or metadata store changes.
    @app.callback(
        Output("timing-store", "data", allow_duplicate=True),
        Input("annotations-store", "data"),
        Input("metadata-store", "data"),
        State("current-doc-id", "data"),
        State("timing-store", "data"),
        prevent_initial_call=True,
    )
    def auto_save(annotations_data, metadata_data, doc_id, timing_data):
        ta = _ta()
        if not ta.annotations_path:
            return no_update
        ta._save_stores_to_file(annotations_data or {}, metadata_data or {}, doc_id=doc_id)
        now = time.time()
        timing_data = dict(timing_data or {})
        timing_data["last_save_time"] = now
        return timing_data


def _setup_timing_callbacks(tater_app: TaterApp, _ta=None) -> None:
    """Setup callbacks for save time and document timing display."""
    app = tater_app.app
    if _ta is None:
        def _ta():
            return tater_app

    # Manual save button — flush timing into metadata, update last_save_time.
    # Auto-save callback handles the actual file write when metadata-store changes.
    @app.callback(
        Output("timing-store", "data", allow_duplicate=True),
        Output("metadata-store", "data", allow_duplicate=True),
        Input("btn-save", "n_clicks"),
        State("current-doc-id", "data"),
        State("timing-store", "data"),
        State("metadata-store", "data"),
        prevent_initial_call=True,
    )
    def on_save_click(n_clicks, current_doc_id, timing_data, metadata_data):
        if not n_clicks:
            return no_update, no_update
        now = time.time()
        if timing_data is None:
            timing_data = {}
        metadata_data = dict(metadata_data or {})
        # Flush elapsed time into metadata before saving, then reset the start
        # so the clientside timer continues without double-counting.
        paused = timing_data.get("paused", False)
        if not paused:
            start = timing_data.get("doc_start_time")
            if start and current_doc_id:
                meta = dict(_get_meta(metadata_data, current_doc_id))
                meta["annotation_seconds"] = meta.get("annotation_seconds", 0.0) + (now - start)
                metadata_data[current_doc_id] = meta
            timing_data["doc_start_time"] = now
            meta = _get_meta(metadata_data, current_doc_id)
            timing_data["annotation_seconds_at_load"] = meta.get("annotation_seconds", 0.0)
        timing_data["last_save_time"] = now
        return timing_data, metadata_data

    # Handle document changes to initialize timing
    @app.callback(
        Output("timing-store", "data", allow_duplicate=True),
        Output("status-store", "data", allow_duplicate=True),
        Output("metadata-store", "data", allow_duplicate=True),
        Input("current-doc-id", "data"),
        State("timing-store", "data"),
        State("annotations-store", "data"),
        State("metadata-store", "data"),
        prevent_initial_call='initial_duplicate',
    )
    def on_doc_change(doc_id, timing_data, annotations_data, metadata_data):
        metadata_data = dict(metadata_data or {})
        if doc_id:
            meta = dict(_get_meta(metadata_data, doc_id))
            meta["visited"] = True
            metadata_data[doc_id] = meta
            update_status_for_doc(_ta(), doc_id, annotations_data, metadata_data)

        if timing_data is None:
            timing_data = {}
        timing_data["doc_start_time"] = time.time()
        timing_data["paused"] = False
        if "session_start_time" not in timing_data or timing_data["session_start_time"] is None:
            timing_data["session_start_time"] = time.time()
        meta = _get_meta(metadata_data, doc_id) if doc_id else {}
        timing_data["annotation_seconds_at_load"] = meta.get("annotation_seconds", 0.0)

        status = metadata_data.get(doc_id, {}).get("status", "not_started") if doc_id else "not_started"
        return timing_data, status, metadata_data

    # Update save status and pause icon whenever timing-store changes (i.e. on every save,
    # navigation, or pause toggle) — no interval needed, no "Updating..." flicker.
    @app.callback(
        Output("save-status-text", "children"),
        Output("save-status-text", "c"),
        Input("timing-store", "data"),
    )
    def update_save_status(timing_data):
        if _ta()._save_error:
            save_text = f"Save failed: {tater_app._save_error}"
            save_color = "red"
        elif timing_data and timing_data.get("last_save_time"):
            dt = datetime.fromtimestamp(timing_data["last_save_time"])
            save_text = f"Last saved: {dt.strftime('%H:%M:%S')}"
            save_color = "dimmed"
        else:
            save_text = "Never saved"
            save_color = "dimmed"
        return save_text, save_color

    # Update the doc timer display every second — runs entirely in the browser so
    # there is no server round-trip and no "Updating..." tab-title flicker.
    # Reads annotation_seconds_at_load from timing-store (written on doc load,
    # navigation, and pause) so it never needs to call back to Python.
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="updateTimer"),
        Output("timing-text", "children"),
        Output("btn-pause-timer-icon", "icon"),
        Input("clock-interval", "n_intervals"),
        Input("timing-store", "data"),
    )

    @app.callback(
        Output("timing-store", "data", allow_duplicate=True),
        Output("metadata-store", "data", allow_duplicate=True),
        Input("btn-pause-timer", "n_clicks"),
        State("timing-store", "data"),
        State("current-doc-id", "data"),
        State("metadata-store", "data"),
        prevent_initial_call=True,
    )
    def toggle_pause(n_clicks, timing_data, doc_id, metadata_data):
        if not n_clicks:
            return no_update, no_update
        if timing_data is None:
            timing_data = {}
        metadata_data = dict(metadata_data or {})
        now = time.time()
        currently_paused = timing_data.get("paused", False)
        if not currently_paused:
            # Flush elapsed into metadata so time isn't lost
            start = timing_data.get("doc_start_time")
            if start and doc_id:
                meta = dict(_get_meta(metadata_data, doc_id))
                meta["annotation_seconds"] = meta.get("annotation_seconds", 0.0) + (now - start)
                metadata_data[doc_id] = meta
            timing_data["doc_start_time"] = None
            timing_data["paused"] = True
            # Update baseline so the clientside timer shows the correct accumulated total
            meta = _get_meta(metadata_data, doc_id) if doc_id else {}
            timing_data["annotation_seconds_at_load"] = meta.get("annotation_seconds", 0.0)
        else:
            timing_data["doc_start_time"] = now
            timing_data["paused"] = False
        return timing_data, metadata_data

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

    _get_current_app_fn = tater_app._get_current_app

    def _ta() -> TaterApp:
        if _get_current_app_fn is not None:
            result = _get_current_app_fn()
            if result is not None:
                return result
        return tater_app

    # --- Capture: value prop (all non-boolean ControlWidgets) ---
    @app.callback(
        Output("status-store", "data", allow_duplicate=True),
        Output("auto-advance-store", "data", allow_duplicate=True),
        Output("annotations-store", "data", allow_duplicate=True),
        Output("metadata-store", "data", allow_duplicate=True),
        Input({"type": "tater-control", "ld": ALL, "path": ALL, "tf": ALL}, "value"),
        State("current-doc-id", "data"),
        State("auto-advance-store", "data"),
        State("annotations-store", "data"),
        State("metadata-store", "data"),
        prevent_initial_call=True,
    )
    def capture_values(all_values, doc_id, advance_count, annotations_data, metadata_data):
        ta = _ta()
        return _do_capture(doc_id, advance_count, ta, ta._aa_fields,
                           annotations_data, metadata_data, convert_empty_str=True)

    # --- Capture: checked prop (BooleanWidgets) ---
    @app.callback(
        Output("status-store", "data", allow_duplicate=True),
        Output("auto-advance-store", "data", allow_duplicate=True),
        Output("annotations-store", "data", allow_duplicate=True),
        Output("metadata-store", "data", allow_duplicate=True),
        Input({"type": "tater-bool-control", "ld": ALL, "path": ALL, "tf": ALL}, "checked"),
        State("current-doc-id", "data"),
        State("auto-advance-store", "data"),
        State("annotations-store", "data"),
        State("metadata-store", "data"),
        prevent_initial_call=True,
    )
    def capture_checked(all_values, doc_id, advance_count, annotations_data, metadata_data):
        ta = _ta()
        return _do_capture(doc_id, advance_count, ta, ta._aa_fields,
                           annotations_data, metadata_data, advance_requires_value=False)

    # --- Load: value prop --- push annotation values to widgets on doc change
    # empty_value_lookup is computed at call time so that hosted-mode sessions
    # with different schemas all get the correct fallback values for their widgets.
    @app.callback(
        Output({"type": "tater-control", "ld": ALL, "path": ALL, "tf": ALL}, "value"),
        Input("current-doc-id", "data"),
        State({"type": "tater-control", "ld": ALL, "path": ALL, "tf": ALL}, "id"),
        State("annotations-store", "data"),
        prevent_initial_call="initial_duplicate",
    )
    def load_values(doc_id, all_ids, annotations_data):
        ta = _ta()
        return _do_load(doc_id, all_ids, annotations_data, ta._ev_lookup)

    # --- Load: checked prop ---
    @app.callback(
        Output({"type": "tater-bool-control", "ld": ALL, "path": ALL, "tf": ALL}, "checked"),
        Input("current-doc-id", "data"),
        State({"type": "tater-bool-control", "ld": ALL, "path": ALL, "tf": ALL}, "id"),
        State("annotations-store", "data"),
        prevent_initial_call="initial_duplicate",
    )
    def load_checked(doc_id, all_ids, annotations_data):
        ta = _ta()
        return _do_load(doc_id, all_ids, annotations_data, ta._ev_lookup, as_bool=True)


def _do_capture(
    doc_id: str,
    advance_count,
    tater_app,
    auto_advance_fields: set,
    annotations_data: dict | None,
    metadata_data: dict | None,
    convert_empty_str: bool = False,
    advance_requires_value: bool = True,
):
    """Shared body for capture_values and capture_checked.

    Returns (status, advance_count_or_no_update, new_annotations_data, new_metadata_data).
    """
    no_store = no_update, no_update, no_update, no_update
    if not doc_id or not ctx.triggered_id:
        return no_store
    tid = ctx.triggered_id
    field_path = _decode_field_path(tid["ld"], tid["path"], tid["tf"])
    value = ctx.triggered[0]["value"]
    if convert_empty_str and value == "":
        value = None
    ann = _get_ann(annotations_data, doc_id)
    if ann is None:
        return no_store
    old_value = value_helpers.get_model_value(ann, field_path)
    value_helpers.set_model_value(ann, field_path, value)
    new_annotations_data = {**(annotations_data or {}), doc_id: ann}
    metadata_data = dict(metadata_data or {})
    update_status_for_doc(tater_app, doc_id, new_annotations_data, metadata_data)
    status = metadata_data.get(doc_id, {}).get("status", "not_started")
    if field_path in auto_advance_fields:
        changed = value != old_value
        if changed and (not advance_requires_value or value is not None):
            return status, (advance_count or 0) + 1, new_annotations_data, metadata_data
    return status, no_update, new_annotations_data, metadata_data


def _do_load(doc_id: str, all_ids: list, annotations_data: dict | None, empty_value_lookup: dict, as_bool: bool = False) -> list:
    """Shared body for load_values and load_checked."""
    ann = _get_ann(annotations_data, doc_id) if doc_id else None
    result = []
    for wid in (all_ids or []):
        field = _decode_field_path(wid["ld"], wid["path"], wid["tf"])
        v = value_helpers.get_model_value(ann, field) if ann is not None else None
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
