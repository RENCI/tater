"""Core navigation, save, timing, and value-capture callbacks."""
from __future__ import annotations

import json
import time
import flask
from datetime import datetime
from typing import TYPE_CHECKING

from dash import Input, Output, State, ALL, ctx, no_update, html, ClientsideFunction

from tater.ui.callbacks.helpers import (
    _get_ann,
    _get_meta,
    _build_menu_items,
    _perform_navigation,
    update_status_for_doc,
    _status_display,
)

if TYPE_CHECKING:
    from tater.ui.tater_app import TaterApp



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

    # Update document title, metadata, progress bar and nav-button states clientside.
    # Fires immediately on navigation — no server round-trip — using info preloaded
    # into doc-list-store at layout time.
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="updateNavInfo"),
        Output("document-title", "children"),
        Output("document-metadata", "children"),
        Output("document-progress", "value"),
        Output("btn-prev", "disabled"),
        Output("btn-next", "disabled"),
        Input("current-doc-id", "data"),
        State("doc-list-store", "data"),
        prevent_initial_call=False,
    )

    # Setup timing callbacks
    _setup_timing_callbacks(tater_app, _ta)

    # Load raw document text on navigation; rendering is handled clientside.
    @app.callback(
        Output("document-text-store", "data"),
        Input("current-doc-id", "data"),
    )
    def update_document(doc_id):
        if not doc_id:
            return no_update

        ta = _ta()
        doc = next((d for d in ta.documents if d.id == doc_id), None)
        if not doc:
            return no_update

        try:
            return doc.load_content()
        except Exception as e:
            return f"Error loading file: {e}"

    # Button navigation
    # NOTE: Multiple callbacks write to "current-doc-id" and "timing-store".
    # Every callback that writes to these outputs MUST use allow_duplicate=True,
    # except this one (the first registered). Omitting it on any subsequent
    # callback will cause a Dash duplicate-output error at startup.
    @app.callback(
        Output("current-doc-id", "data"),
        Output("timing-store", "data"),
        Output("metadata-store", "data", allow_duplicate=True),
        Output("status-store", "data", allow_duplicate=True),
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
            return no_update, no_update, no_update, no_update

        current_index = next((i for i, d in enumerate(ta.documents) if d.id == current_doc_id), 0)

        if ctx.triggered_id == "btn-prev" and current_index > 0:
            current_index -= 1
        elif ctx.triggered_id == "btn-next" and current_index < len(ta.documents) - 1:
            current_index += 1
        else:
            return no_update, no_update, no_update, no_update

        return _perform_navigation(ta, current_doc_id, current_index, timing_data, annotations_data, metadata_data)

    # Menu item navigation (allow_duplicate=True required — see note above)
    @app.callback(
        Output("current-doc-id", "data", allow_duplicate=True),
        Output("timing-store", "data", allow_duplicate=True),
        Output("metadata-store", "data", allow_duplicate=True),
        Output("status-store", "data", allow_duplicate=True),
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
            return no_update, no_update, no_update, no_update

        if not ctx.triggered[0]["value"]:
            return no_update, no_update, no_update, no_update

        new_index = ctx.triggered_id["index"]
        return _perform_navigation(ta, current_doc_id, new_index, timing_data, annotations_data, metadata_data)

    # Auto-advance: navigate to next doc when an auto_advance widget gets a value.
    # (allow_duplicate=True required — see note above)
    @app.callback(
        Output("current-doc-id", "data", allow_duplicate=True),
        Output("timing-store", "data", allow_duplicate=True),
        Output("metadata-store", "data", allow_duplicate=True),
        Output("status-store", "data", allow_duplicate=True),
        Input("auto-advance-store", "data"),
        State("current-doc-id", "data"),
        State("timing-store", "data"),
        State("annotations-store", "data"),
        State("metadata-store", "data"),
        prevent_initial_call=True,
    )
    def navigate_auto_advance(trigger, current_doc_id, timing_data, annotations_data, metadata_data):
        if not trigger:
            return no_update, no_update, no_update, no_update
        ta = _ta()
        current_index = next(
            (i for i, d in enumerate(ta.documents) if d.id == current_doc_id), 0
        )
        if current_index >= len(ta.documents) - 1:
            return no_update, no_update, no_update, no_update
        return _perform_navigation(ta, current_doc_id, current_index + 1, timing_data, annotations_data, metadata_data)

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
        app.clientside_callback(
            ClientsideFunction(namespace="tater", function_name="openOnClick"),
            Output("instructions-drawer", "opened"),
            Input("btn-open-instructions", "n_clicks"),
            prevent_initial_call=True,
        )

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
        # Navigation callbacks (_perform_navigation) already initialized timing,
        # metadata (visited=True), and status for this doc.  Just return the
        # status computed there and leave the stores untouched.
        if timing_data and timing_data.get("_nav_init"):
            status = (metadata_data or {}).get(doc_id, {}).get("status", "not_started") if doc_id else "not_started"
            return no_update, status, no_update

        # Initial page load path: no navigation callback has run yet.
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
            save_text = f"Save failed: {_ta()._save_error}"
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
        return _status_display(status)

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

    # --- Clientside capture: value prop (all non-boolean ControlWidgets) ---
    # Runs in the browser so annotations-store is always current — no stale-State
    # race with concurrent clientside span/repeater mutations.
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="captureValue"),
        Output("annotations-store", "data", allow_duplicate=True),
        Output("auto-advance-store", "data", allow_duplicate=True),
        Input({"type": "tater-control", "ld": ALL, "path": ALL, "tf": ALL}, "value"),
        State("current-doc-id", "data"),
        State("annotations-store", "data"),
        State("aa-fields-store", "data"),
        prevent_initial_call=True,
    )

    # --- Clientside capture: checked prop (BooleanWidgets) ---
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="captureChecked"),
        Output("annotations-store", "data", allow_duplicate=True),
        Output("auto-advance-store", "data", allow_duplicate=True),
        Input({"type": "tater-bool-control", "ld": ALL, "path": ALL, "tf": ALL}, "checked"),
        State("current-doc-id", "data"),
        State("annotations-store", "data"),
        State("aa-fields-store", "data"),
        prevent_initial_call=True,
    )

    # --- Downstream: recompute status whenever annotations change ---
    # Triggered by annotations-store as Input (always current after a clientside write).
    @app.callback(
        Output("status-store", "data", allow_duplicate=True),
        Output("metadata-store", "data", allow_duplicate=True),
        Input("annotations-store", "data"),
        State("current-doc-id", "data"),
        State("metadata-store", "data"),
        prevent_initial_call=True,
    )
    def update_status_from_annotations(annotations_data, doc_id, metadata_data):
        if not doc_id:
            return no_update, no_update
        ta = _ta()
        metadata_data = dict(metadata_data or {})
        update_status_for_doc(ta, doc_id, annotations_data, metadata_data)
        status = metadata_data.get(doc_id, {}).get("status", "not_started")
        return status, metadata_data

    # --- Clientside load: value prop --- push annotation values to widgets on doc change
    # or repeater delete.  ev-lookup-store supplies per-field empty values so the server
    # is not needed; hosted-mode sessions each write their own ev-lookup-store at layout time.
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="loadValues"),
        Output({"type": "tater-control", "ld": ALL, "path": ALL, "tf": ALL}, "value"),
        Input("current-doc-id", "data"),
        Input("repeater-load-trigger", "data"),
        State("annotations-store", "data"),
        State("ev-lookup-store", "data"),
        prevent_initial_call="initial_duplicate",
    )

    # --- Clientside load: checked prop ---
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="loadChecked"),
        Output({"type": "tater-bool-control", "ld": ALL, "path": ALL, "tf": ALL}, "checked"),
        Input("current-doc-id", "data"),
        Input("repeater-load-trigger", "data"),
        State("annotations-store", "data"),
        State("ev-lookup-store", "data"),
        prevent_initial_call="initial_duplicate",
    )



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
