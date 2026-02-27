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
        Output("save-status", "children"),
        [Input("btn-prev", "n_clicks"),
         Input("btn-next", "n_clicks")],
        State("current-doc-id", "data"),
        prevent_initial_call=True
    )
    def navigate(prev_clicks, next_clicks, current_doc_id):
        from dash import ctx, no_update

        if not ctx.triggered or not tater_app.documents:
            return current_doc_id, no_update

        # Find current index from current doc_id
        current_index = next((i for i, d in enumerate(tater_app.documents) if d.id == current_doc_id), 0)
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if button_id == "btn-prev" and current_index > 0:
            current_index -= 1
        elif button_id == "btn-next" and current_index < len(tater_app.documents) - 1:
            current_index += 1

        # Save annotations before navigating
        tater_app._save_annotations_to_file()

        # Show save status
        alert = dmc.Alert(
            "Annotations saved",
            title="Saved",
            color="teal",
            withCloseButton=False,
            icon=dmc.Text("\u2713", size="lg"),
            duration=2000
        )

        doc_id = tater_app.documents[current_index].id if current_index < len(tater_app.documents) else ""
        return doc_id, alert

    # Handle flag-document changes
    @app.callback(
        Output("flag-document", "id"),  # Dummy output
        Input("flag-document", "checked"),
        State("current-doc-id", "data"),
        prevent_initial_call=True
    )
    def save_flag(checked, doc_id):
        if not doc_id:
            return "flag-document"
        # Store flag state (optional - can be expanded if needed)
        return "flag-document"

    # Handle document-notes changes
    @app.callback(
        Output("document-notes", "id"),  # Dummy output
        Input("document-notes", "value"),
        State("current-doc-id", "data"),
        prevent_initial_call=True
    )
    def save_notes(notes, doc_id):
        if not doc_id:
            return "document-notes"
        # Store notes state (optional - can be expanded if needed)
        return "document-notes"


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

    # Callback for updating self.annotations when widget value changes
    @app.callback(
        Output(widget_id, "id"),  # Dummy output, just to trigger
        Input(widget_id, "value"),
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
        Output(widget_id, "value"),
        Input("current-doc-id", "data"),
        prevent_initial_call=True
    )
    def update_widget_value(doc_id):
        if not doc_id or doc_id not in tater_app.annotations:
            return None

        annotation = tater_app.annotations[doc_id]
        return value_helpers.get_model_value(annotation, field_path)
