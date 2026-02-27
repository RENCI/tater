"""Dash callback registrations for TaterApp."""
from __future__ import annotations

from typing import TYPE_CHECKING

from dash import Input, Output, State
import dash_mantine_components as dmc
from tater.ui import value_helpers

if TYPE_CHECKING:
    from tater.ui.tater_app import TaterApp
    from tater.widgets.base import TaterWidget


def setup_callbacks(tater_app: TaterApp) -> None:
    """Register document and navigation callbacks on the Dash app."""
    app = tater_app.app

    # Setup timing callbacks
    _setup_timing_callbacks(tater_app)

    # Update document display and info
    @app.callback(
        [Output("document-content", "children"),
         Output("document-title", "children"),
         Output("document-metadata", "children"),
         Output("document-progress", "value")],
        Input("current-doc-id", "data")
    )
    def update_document(doc_id):
        if not doc_id:
            return "No document loaded", "No document", "", 0

        # Find document by ID
        doc = next((d for d in tater_app.documents if d.id == doc_id), None)
        if not doc:
            return "Document not found", "Error", "", 0

        # Load document content
        try:
            content = doc.load_content()
        except Exception as e:
            content = f"Error loading file: {e}"

        doc_index = next((i for i, d in enumerate(tater_app.documents) if d.id == doc_id), 0)
        title = f"Document {doc_index + 1} of {len(tater_app.documents)}"

        # Format metadata from document info dict (without document count)
        metadata_parts = []
        if doc.info:
            for key, value in doc.info.items():
                metadata_parts.append(f"{key}: {value}")
        metadata = " | ".join(metadata_parts) if metadata_parts else ""

        progress = ((doc_index + 1) / len(tater_app.documents)) * 100 if tater_app.documents else 0

        return content, title, metadata, progress

    # Autosave and navigation buttons
    @app.callback(
        Output("current-doc-id", "data"),
        Output("timing-store", "data"),
        [Input("btn-prev", "n_clicks"),
         Input("btn-next", "n_clicks")],
        State("current-doc-id", "data"),
        State("timing-store", "data"),
        prevent_initial_call=True
    )
    def navigate(prev_clicks, next_clicks, current_doc_id, timing_data):
        from dash import ctx, no_update
        import time

        if not ctx.triggered or not tater_app.documents:
            return current_doc_id, no_update

        # Find current index from current doc_id
        current_index = next((i for i, d in enumerate(tater_app.documents) if d.id == current_doc_id), 0)
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if button_id == "btn-prev" and current_index > 0:
            current_index -= 1
        elif button_id == "btn-next" and current_index < len(tater_app.documents) - 1:
            current_index += 1


        # Accumulate annotation_seconds for the document being left
        from tater.models.document import DocumentMetadata
        now = time.time()
        if current_doc_id:
            if current_doc_id not in tater_app.metadata:
                tater_app.metadata[current_doc_id] = DocumentMetadata()
            # Use timing_data["doc_start_time"] to know when user started viewing this doc
            start = None
            if timing_data and timing_data.get("doc_start_time"):
                start = timing_data["doc_start_time"]
            if start:
                elapsed = now - start
                tater_app.metadata[current_doc_id].annotation_seconds += elapsed

        # Determine new doc_id after navigation
        doc_id = tater_app.documents[current_index].id if current_index < len(tater_app.documents) else ""

        # No need to update annotation_seconds for the document being entered (will be tracked on next navigation)

        # Save annotations before navigating
        tater_app._save_annotations_to_file()

        # Update timing store with save time and reset doc timer
        if timing_data is None:
            timing_data = {}
        timing_data["last_save_time"] = time.time()
        timing_data["doc_start_time"] = time.time()  # Reset for new doc
        if "session_start_time" not in timing_data or timing_data["session_start_time"] is None:
            timing_data["session_start_time"] = time.time()

        doc_id = tater_app.documents[current_index].id if current_index < len(tater_app.documents) else ""
        return doc_id, timing_data

    # Handle flag-document changes
    @app.callback(
        Output("flag-document", "id"),  # Dummy output
        Input("flag-document", "checked"),
        State("current-doc-id", "data"),
        State("timing-store", "data"),
        prevent_initial_call=True
    )
    def save_flag(checked, doc_id, timing_data):
        import time
        if not doc_id:
            return "flag-document"
        
        # Ensure DocumentMetadata exists for this document
        from tater.models.document import DocumentMetadata
        if doc_id not in tater_app.metadata:
            tater_app.metadata[doc_id] = DocumentMetadata()
        # Save the flag value
        tater_app.metadata[doc_id].flagged = checked
        
        # Update save time
        if timing_data is None:
            timing_data = {}
        timing_data["last_save_time"] = time.time()
        return "flag-document"

    # Handle document-notes changes
    @app.callback(
        Output("document-notes", "id"),  # Dummy output
        Input("document-notes", "value"),
        State("current-doc-id", "data"),
        State("timing-store", "data"),
        prevent_initial_call=True
    )
    def save_notes(notes, doc_id, timing_data):
        import time
        if not doc_id:
            return "document-notes"
        
        # Ensure DocumentMetadata exists for this document
        from tater.models.document import DocumentMetadata
        if doc_id not in tater_app.metadata:
            tater_app.metadata[doc_id] = DocumentMetadata()
        # Save the notes value
        tater_app.metadata[doc_id].notes = notes if notes else ""
        
        # Update save time
        if timing_data is None:
            timing_data = {}
        timing_data["last_save_time"] = time.time()
        return "document-notes"


def _setup_timing_callbacks(tater_app: TaterApp) -> None:
    """Setup callbacks for save time and document timing display."""
    app = tater_app.app

    # Handle document changes to initialize timing
    @app.callback(
        Output("timing-store", "data", allow_duplicate=True),
        Input("current-doc-id", "data"),
        State("timing-store", "data"),
        prevent_initial_call='initial_duplicate',
    )
    def on_doc_change(doc_id, timing_data):
        import time
        if timing_data is None:
            timing_data = {}
        timing_data["doc_start_time"] = time.time()
        if "session_start_time" not in timing_data or timing_data["session_start_time"] is None:
            timing_data["session_start_time"] = time.time()
        return timing_data

    # Update footer text every second

    @app.callback(
        Output("save-status-text", "children"),
        Output("timing-text", "children"),
        Input("clock-interval", "n_intervals"),
        State("timing-store", "data"),
        State("current-doc-id", "data"),
        prevent_initial_call=False,
    )
    def update_footer(n_intervals, timing_data, doc_id):
        import time
        from datetime import datetime
        now = time.time()

        # Save status text - display timestamp of last save
        save_text = "Never saved"
        if timing_data and timing_data.get("last_save_time"):
            save_time = timing_data["last_save_time"]
            dt = datetime.fromtimestamp(save_time)
            save_text = f"Last saved: {dt.strftime('%H:%M:%S')}"

        # Doc time: show total annotation_seconds for current doc, plus current session time if viewing
        from tater.models.document import DocumentMetadata
        total_seconds = 0.0
        meta = tater_app.metadata.get(doc_id)
        if meta:
            total_seconds = meta.annotation_seconds
        # If currently viewing, add time since doc_start_time
        if timing_data and timing_data.get("doc_start_time"):
            # Only add if this doc is the one being viewed
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

        return save_text, timing_text


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
    Skips ListableWidget item widgets - ListableWidget handles its own value capture.
    """
    from tater.widgets.group import GroupWidget
    from tater.widgets.listable import ListableWidget

    captured = []
    for widget in widgets:
        if isinstance(widget, ListableWidget):
            # Skip ListableWidget items - it manages its own value capture
            continue
        elif isinstance(widget, GroupWidget):
            # Recursively process GroupWidget children
            if hasattr(widget, "children") and widget.children:
                captured.extend(_collect_value_capture_widgets(widget.children))
        else:
            # Regular value-capturing widget
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
        Input(widget_id, value_prop),
        State("current-doc-id", "data"),
        prevent_initial_call=True
    )
    def capture_value(value, doc_id):
        if not doc_id:
            return widget_id

        if tater_app.schema_model:
            # Using Pydantic models - get or create instance
            if doc_id not in tater_app.annotations:
                tater_app.annotations[doc_id] = tater_app.schema_model()

            # Write directly to the Pydantic instance using setattr
            model = tater_app.annotations[doc_id]
            value_helpers.set_model_value(model, field_path, value)
        else:
            # Using plain dicts (fallback)
            if doc_id not in tater_app.annotations:
                tater_app.annotations[doc_id] = {}
            value_helpers.set_nested_value(tater_app.annotations[doc_id], field_path, value)

        return widget_id

    # Callback for updating widget value when document changes
    @app.callback(
        Output(widget_id, value_prop),
        Input("current-doc-id", "data"),
        prevent_initial_call=True
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
