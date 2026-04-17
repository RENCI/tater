"""Span annotation callbacks."""
from __future__ import annotations

from typing import TYPE_CHECKING

from dash import Input, Output, State, ALL, MATCH, ClientsideFunction

if TYPE_CHECKING:
    from tater.ui.tater_app import TaterApp


# ---------------------------------------------------------------------------
# Callback registration
# ---------------------------------------------------------------------------

def setup_span_callbacks(tater_app: TaterApp) -> None:
    """Register unified MATCH-based callbacks for all SpanAnnotationWidgets."""
    app = tater_app.app

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

    # ---- Clientside: update count badges on span add/delete/doc navigation ----
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="updateSpanCounts"),
        Output({"type": "span-count", "field": ALL, "tag": ALL}, "children"),
        Output({"type": "span-count", "field": ALL, "tag": ALL}, "className"),
        Input("span-any-change", "data"),
        Input("current-doc-id", "data"),
        State("annotations-store", "data"),
    )

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

    # ---- Clientside: re-render document marks on nav or span change ----
    # document-text-store triggers on nav; span-any-change triggers on span edits.
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="renderDocumentSpans"),
        Output("document-content", "children"),
        Input("document-text-store", "data"),
        Input("span-any-change", "data"),
        State("current-doc-id", "data"),
        State("annotations-store", "data"),
        State("span-color-map", "data"),
        prevent_initial_call=True,
    )

    # ---- Popup: read window._taterPopupPending and add span to annotations ----
    # Mirrors the captureDelete pattern: proxy n_clicks triggers the callback,
    # which drains window._taterPopupPending and writes directly to annotations.
    app.clientside_callback(
        ClientsideFunction(namespace="tater", function_name="addSpanFromPopup"),
        Output("span-any-change", "data", allow_duplicate=True),
        Output("annotations-store", "data", allow_duplicate=True),
        Input("span-popup-proxy", "n_clicks"),
        State("current-doc-id", "data"),
        State("span-any-change", "data"),
        State("annotations-store", "data"),
        prevent_initial_call=True,
    )
