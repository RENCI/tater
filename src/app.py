"""Main Dash application for clinical note annotation."""
import sys
import base64
import io
import json
import csv
from pathlib import Path
from dash import Dash, html, dcc, Input, Output, State, ALL, ctx, callback
import dash_mantine_components as dmc
from datetime import datetime
import pandas as pd

from data.loader import load_documents, load_schema, load_document_text
from data.storage import load_annotations, save_annotations, get_or_create_annotation
from data.validator import AnnotationSchema, Document, DocumentAnnotation, DocumentList
from components.document_viewer import (
    create_document_viewer, format_document_text, create_span_annotations_display
)
from components.annotation_panel import create_annotation_panel, create_annotation_controls
from components.navigation import create_navigation_bar, create_progress_display
from utils.config import config
from utils.constants import (
    STATUS_NOT_STARTED, STATUS_IN_PROGRESS, STATUS_COMPLETED,
    AUTO_SAVE_INTERVAL
)


# Initialize the Dash app
app = Dash(
    __name__,
    suppress_callback_exceptions=True
)

app.title = "Clinical Note Annotation Tool"


def create_startup_screen() -> html.Div:
    """Create the initial startup screen for loading files."""
    return dmc.Container([
        dmc.Stack([
            dmc.Title("Clinical Note Annotation Tool", order=2, ta="center", mt="xl", mb="lg"),
            # Load Previous section
            html.Div(id="load-previous-section"),
            # Hidden placeholders to satisfy callback outputs before annotation screen loads
            html.Div(id="document-text-container", style={"display": "none"}),
            html.Div(id="span-annotations-list", style={"display": "none"}),
            dmc.Paper([
                dmc.Stack([
                    dmc.Title("Load New Documents and Schema", order=5, mb="md"),
                    dmc.Text(
                        "Document list file (CSV or JSON):",
                        size="sm",
                        fw=500
                    ),
                    dcc.Upload(
                        id="documents-file-upload",
                        children=dmc.Button(
                            "Choose Document List File",
                            variant="default",
                            fullWidth=True
                        ),
                        className="mb-2"
                    ),
                    html.Div(id="documents-file-name", style={"color": "#666", "fontSize": "0.875rem", "marginBottom": "1rem"}),
                    dmc.Text(
                        "Annotation schema file (JSON):",
                        size="sm",
                        fw=500
                    ),
                    dcc.Upload(
                        id="schema-file-upload",
                        children=dmc.Button(
                            "Choose Schema File",
                            variant="default",
                            fullWidth=True
                        ),
                        className="mb-2"
                    ),
                    html.Div(id="schema-file-name", style={"color": "#666", "fontSize": "0.875rem", "marginBottom": "1rem"}),
                    html.Div(id="load-error", style={"color": "#fa5252", "marginBottom": "1rem"}),
                    dmc.Button(
                        "Load and Start Annotating",
                        id="load-button",
                        fullWidth=True,
                        disabled=True
                    )
                ], gap="sm")
            ], shadow="sm", p="lg", radius="md", style={"maxWidth": "500px", "margin": "0 auto"})
        ], align="center", justify="center", style={"minHeight": "100vh"})
    ], fluid=True)


def create_annotation_screen() -> html.Div:
    """Create the main annotation interface."""
    return dmc.Container([
        dmc.Stack([
            create_navigation_bar(),
            dmc.Grid([
                dmc.GridCol(create_document_viewer(), span=7),
                dmc.GridCol(create_annotation_panel(), span=5)
            ], gutter="md")
        ], gap="md")
    ], fluid=True, p="md")


# Main app layout
app.layout = dmc.MantineProvider([
    dcc.Store(id="app-state", data={"loaded": False}),
    dcc.Store(id="documents-store", data=[]),
    dcc.Store(id="schema-store", data=None),
    dcc.Store(id="annotations-store", data=None),
    dcc.Store(id="current-index-store", data=0),
    dcc.Store(id="dirty-state-store", data=False),
    dcc.Store(id="documents-file-content", data=None),
    dcc.Store(id="schema-file-content", data=None),
    dcc.Store(id="selected-text-store", data=None),
    dcc.Store(id="span-trigger-store", data=None),
    # Local storage for previous files
    dcc.Store(id="local-documents-file", storage_type="local", data=None),
    dcc.Store(id="local-schema-file", storage_type="local", data=None),
    dcc.Interval(id="auto-save-interval", interval=AUTO_SAVE_INTERVAL, n_intervals=0),
    html.Div(id="main-content", children=create_startup_screen())
])


@app.callback(
    [Output("documents-file-content", "data"),
     Output("documents-file-name", "children")],
    Input("documents-file-upload", "contents"),
    State("documents-file-upload", "filename"),
    prevent_initial_call=True
)
def upload_documents_file(contents, filename):
    """Handle documents file upload."""
    if contents is None:
        return None, ""
    return contents, f"✓ {filename}"


@app.callback(
    [Output("schema-file-content", "data"),
     Output("schema-file-name", "children")],
    Input("schema-file-upload", "contents"),
    State("schema-file-upload", "filename"),
    prevent_initial_call=True
)
def upload_schema_file(contents, filename):
    """Handle schema file upload."""
    if contents is None:
        return None, ""
    return contents, f"✓ {filename}"


@app.callback(
    Output("load-button", "disabled"),
    [Input("documents-file-content", "data"),
     Input("schema-file-content", "data")]
)
def enable_load_button(docs_content, schema_content):
    """Enable load button when both files are uploaded."""
    return not (docs_content is not None and schema_content is not None)


@app.callback(
    Output("load-previous-section", "children"),
    [Input("local-documents-file", "data"),
     Input("local-schema-file", "data")],
    prevent_initial_call=False
)
def show_load_previous(local_docs, local_schema):
    """Show continue annotating button if files exist in local storage."""
    if local_docs and local_schema:
        docs_filename = local_docs.get("filename", "cached files")
        schema_filename = local_schema.get("filename", "cached schema")
        return dmc.Paper([
            dmc.Stack([
                dmc.Title("Continue Previous Session", order=5, mb="md"),
                dmc.Text(
                    "Document list file:",
                    size="sm",
                    fw=500
                ),
                dmc.Text(
                    docs_filename,
                    size="sm",
                    c="dimmed",
                    mb="xs"
                ),
                dmc.Text(
                    "Annotation schema file:",
                    size="sm",
                    fw=500
                ),
                dmc.Text(
                    schema_filename,
                    size="sm",
                    c="dimmed",
                    mb="sm"
                ),
                dmc.Button(
                    "Continue annotating",
                    id="load-previous-button",
                    fullWidth=True,
                    n_clicks=0
                )
            ], gap="sm")
        ], shadow="sm", p="lg", radius="md", mb="md", style={"maxWidth": "500px", "margin": "0 auto"})
    return html.Div()


@app.callback(
    [Output("main-content", "children", allow_duplicate=True),
     Output("app-state", "data", allow_duplicate=True),
     Output("documents-store", "data", allow_duplicate=True),
     Output("schema-store", "data", allow_duplicate=True),
     Output("annotations-store", "data", allow_duplicate=True)],
    Input("load-previous-button", "n_clicks"),
    [State("local-documents-file", "data"),
     State("local-schema-file", "data")],
    prevent_initial_call=True
)
def load_previous_files(n_clicks, local_docs, local_schema):
    """Load previously uploaded files from local storage."""
    if not n_clicks or not local_docs or not local_schema:
        from dash.exceptions import PreventUpdate
        raise PreventUpdate
    
    try:
        docs_content = local_docs.get("contents")
        schema_content = local_schema.get("contents")
        docs_filename = local_docs.get("filename", "documents")
        
        # Decode documents file
        content_type, content_string = docs_content.split(',')
        decoded_docs = base64.b64decode(content_string)
        
        # Parse documents based on file extension
        documents = []
        if docs_filename.endswith('.json'):
            docs_data = json.loads(decoded_docs.decode('utf-8'))
            doc_list = DocumentList(**docs_data)
            documents = doc_list.documents
        elif docs_filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(decoded_docs.decode('utf-8')))
            if 'file_path' not in df.columns:
                raise ValueError("CSV must contain 'file_path' column")
            
            for _, row in df.iterrows():
                metadata = None
                if 'metadata' in df.columns and pd.notna(row['metadata']):
                    try:
                        metadata = json.loads(row['metadata'])
                    except json.JSONDecodeError:
                        metadata = None
                
                doc = Document(
                    file_path=row['file_path'],
                    metadata=metadata
                )
                documents.append(doc)
        else:
            raise ValueError("Document list must be .json or .csv file")
        
        # Decode and parse schema file
        content_type, content_string = schema_content.split(',')
        decoded_schema = base64.b64decode(content_string)
        schema_data = json.loads(decoded_schema.decode('utf-8'))
        schema = AnnotationSchema(**schema_data)
        
        # Load existing annotations
        annotations = load_annotations()
        
        # Update schema version if needed
        if annotations.schema_version != schema.schema_version:
            annotations.schema_version = schema.schema_version
        
        return (
            create_annotation_screen(),
            {"loaded": True},
            [doc.model_dump() for doc in documents],
            schema.model_dump(),
            annotations.model_dump()
        )
    
    except Exception as e:
        print(f"Error loading cached files: {e}")
        from dash.exceptions import PreventUpdate
        raise PreventUpdate


@app.callback(
    [Output("main-content", "children"),
     Output("app-state", "data"),
     Output("documents-store", "data"),
     Output("schema-store", "data"),
     Output("annotations-store", "data"),
     Output("load-error", "children"),
     Output("local-documents-file", "data"),
     Output("local-schema-file", "data")],
    Input("load-button", "n_clicks"),
    [State("documents-file-content", "data"),
     State("schema-file-content", "data"),
     State("documents-file-upload", "filename"),
     State("schema-file-upload", "filename")],
    prevent_initial_call=True
)
def load_files(n_clicks, docs_content, schema_content, docs_filename, schema_filename):
    """Load documents and schema files from uploaded content and save to local storage."""
    if not docs_content or not schema_content:
        return (
            create_startup_screen(),
            {"loaded": False},
            [],
            None,
            None,
            "Please upload both files.",
            None,
            None
        )
    
    try:
        # Decode documents file
        content_type, content_string = docs_content.split(',')
        decoded_docs = base64.b64decode(content_string)
        
        # Parse documents based on file extension
        documents = []
        if docs_filename.endswith('.json'):
            docs_data = json.loads(decoded_docs.decode('utf-8'))
            doc_list = DocumentList(**docs_data)
            documents = doc_list.documents
        elif docs_filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(decoded_docs.decode('utf-8')))
            if 'file_path' not in df.columns:
                raise ValueError("CSV must contain 'file_path' column")
            
            for _, row in df.iterrows():
                metadata = None
                if 'metadata' in df.columns and pd.notna(row['metadata']):
                    try:
                        metadata = json.loads(row['metadata'])
                    except json.JSONDecodeError:
                        metadata = None
                
                doc = Document(
                    file_path=row['file_path'],
                    metadata=metadata
                )
                documents.append(doc)
        else:
            raise ValueError("Document list must be .json or .csv file")
        
        if not documents:
            raise ValueError("No documents found in file")
        
        # Decode and parse schema file
        content_type, content_string = schema_content.split(',')
        decoded_schema = base64.b64decode(content_string)
        schema_data = json.loads(decoded_schema.decode('utf-8'))
        schema = AnnotationSchema(**schema_data)
        
        # Load existing annotations
        annotations = load_annotations()
        
        # Update schema version if needed
        if annotations.schema_version != schema.schema_version:
            annotations.schema_version = schema.schema_version
        
        return (
            create_annotation_screen(),
            {"loaded": True},
            [doc.model_dump() for doc in documents],
            schema.model_dump(),
            annotations.model_dump(),
            "",
            {"contents": docs_content, "filename": docs_filename},
            {"contents": schema_content, "filename": schema_filename}
        )
    
    except Exception as e:
        return (
            create_startup_screen(),
            {"loaded": False},
            [],
            None,
            None,
            f"Error loading files: {str(e)}",
            None,
            None
        )


@app.callback(
    Output("document-selector", "value"),
    [Input("prev-button", "n_clicks"),
     Input("next-button", "n_clicks")],
    [State("document-selector", "value"),
     State("documents-store", "data")],
    prevent_initial_call=True
)
def navigate_buttons(prev_clicks, next_clicks, selector_value, documents):
    """Update the document selector when navigation buttons are clicked."""
    if not documents:
        from dash.exceptions import PreventUpdate
        raise PreventUpdate

    current_index = int(selector_value) if selector_value is not None else 0
    triggered_id = ctx.triggered_id

    new_index = current_index
    if triggered_id == "prev-button" and current_index > 0:
        new_index = current_index - 1
    elif triggered_id == "next-button" and current_index < len(documents) - 1:
        new_index = current_index + 1

    return str(new_index)


@app.callback(
    [Output("current-index-store", "data"),
     Output("dirty-state-store", "data", allow_duplicate=True),
     Output("annotations-store", "data", allow_duplicate=True)],
    Input("document-selector", "value"),
    [State("current-index-store", "data"),
     State("documents-store", "data"),
     State("annotations-store", "data"),
     State("schema-store", "data"),
     State({"type": "annotation-input", "id": ALL}, "value"),
     State({"type": "annotation-input", "id": ALL}, "data"),
     State("flag-for-review", "checked")],
    prevent_initial_call=True
)
def sync_current_index(selector_value, current_index,
                       documents, annotations_data, schema_data,
                       annotation_values, annotation_data_values, flagged):
    """Sync current index to selector changes and save before switching."""
    if not documents or selector_value is None:
        return current_index, False, annotations_data

    new_index = int(selector_value)

    # Save current document's annotations before navigating
    if new_index != current_index and annotations_data and schema_data:
        annotations_data = save_current_annotations(
            current_index, documents, annotations_data,
            schema_data, annotation_values, annotation_data_values, flagged
        )

    return new_index, False, annotations_data


@app.callback(
    [Output("document-text-container", "children"),
     Output("document-metadata", "children"),
     Output("annotation-controls-container", "children"),
     Output("flag-for-review", "checked"),
     Output("span-annotations-list", "children"),
     Output("prev-button", "disabled"),
     Output("next-button", "disabled"),
     Output("document-selector", "data"),
     Output("progress-display", "children")],
    Input("current-index-store", "data"),
    [State("documents-store", "data"),
     State("schema-store", "data"),
     State("annotations-store", "data")],
    prevent_initial_call=True
)
def update_document_display(current_index, documents, schema_data, annotations_data):
    """Update the document display and annotation controls."""
    if not documents or schema_data is None:
        return ("", "", [], False, html.Div(), True, True, [], 0, html.Div())
    
    # Get current document
    doc_data = documents[current_index]
    file_path = doc_data['file_path']
    
    # Load document text
    text, success = load_document_text(file_path)
    
    # Get metadata
    metadata_str = Path(file_path).name
    if doc_data.get('metadata'):
        metadata_items = [f"{k}: {v}" for k, v in doc_data['metadata'].items()]
        if metadata_items:
            metadata_str += " | " + " | ".join(metadata_items)
    
    # Load schema
    from data.validator import AnnotationSchema
    schema = AnnotationSchema(**schema_data)
    
    # Get current annotations
    from data.validator import AnnotationCollection
    annotations = AnnotationCollection(**annotations_data)
    current_ann = annotations.get_annotation(file_path)
    
    # Extract values
    current_values = {}
    flagged = False
    span_anns = []
    
    if current_ann:
        current_values = current_ann.annotations
        flagged = current_ann.flagged_for_review
        
        # Extract span annotations
        for ann_type in schema.annotation_types:
            if ann_type.type == "span_annotation":
                span_anns = current_values.get(ann_type.id, [])
                break
    
    # Create annotation controls
    controls = create_annotation_controls(schema.annotation_types, current_values)
    
    # Format document text with highlights
    formatted_text = format_document_text(text, span_anns)
    
    # Create span annotations display
    span_display = create_span_annotations_display(span_anns)
    
    # Navigation state
    prev_disabled = current_index <= 0
    next_disabled = current_index >= len(documents) - 1
    
    # Dropdown options
    dropdown_options = []
    for i, doc in enumerate(documents):
        filename = Path(doc['file_path']).name
        dropdown_options.append({
            "label": f"{i + 1}. {filename}",
            "value": str(i)
        })
    
    # Calculate statistics
    completed = sum(1 for ann in annotations.annotations if ann.status == STATUS_COMPLETED)
    in_progress = sum(1 for ann in annotations.annotations if ann.status == STATUS_IN_PROGRESS)
    not_started = len(documents) - completed - in_progress
    flagged_count = sum(1 for ann in annotations.annotations if ann.flagged_for_review)
    
    progress = create_progress_display(
        len(documents), current_index, completed, in_progress, not_started, flagged_count
    )
    
    return (
        formatted_text,
        metadata_str,
        controls,
        flagged,
        span_display,
        prev_disabled,
        next_disabled,
        dropdown_options,
        progress
    )


# Clientside callback to capture selected text when button is clicked
app.clientside_callback(
    """
    function(n_clicks_list, app_state) {
        // Set up event listeners on first run
        if (!window.dash_selection_initialized) {
            window.dash_selection_initialized = true;
            window.dash_selection_store = '';
            
            console.log('Initializing text selection capture...');
            
            // Capture selection on mouseup anywhere in document
            document.addEventListener('mouseup', function() {
                setTimeout(function() {
                    const selection = window.getSelection();
                    const selectedText = selection ? selection.toString().trim() : '';
                    if (selectedText) {
                        window.dash_selection_store = selectedText;
                        console.log('Stored selection:', selectedText);
                    }
                }, 10);
            });
            
            // Also listen for button mousedown to capture selection before it's cleared
            document.addEventListener('mousedown', function() {
                const selection = window.getSelection();
                const selectedText = selection ? selection.toString().trim() : '';
                if (selectedText) {
                    window.dash_selection_store = selectedText;
                    console.log('Captured on mousedown:', selectedText);
                }
            });
        }
        
        // Only emit values when an add-span button was clicked
        if (n_clicks_list && n_clicks_list.some(n => n)) {
            const result = window.dash_selection_store || '';
            const triggeredId = dash_clientside.callback_context.triggered_id;
            console.log('Returning to callback:', result);
            return [result, triggeredId || null];
        }
        
        return [window.dash_clientside.no_update, window.dash_clientside.no_update];
    }
    """,
    [Output("selected-text-store", "data"),
     Output("span-trigger-store", "data")],
    [Input({"type": "add-span", "id": ALL, "entity": ALL}, "n_clicks"),
     Input("app-state", "data")],
    prevent_initial_call=False
)


@app.callback(
    Output("dirty-state-store", "data"),
    [Input({"type": "annotation-input", "id": ALL}, "value"),
     Input({"type": "annotation-input", "id": ALL}, "data"),
     Input("flag-for-review", "checked")],
    prevent_initial_call=True
)
def mark_dirty(annotation_values, annotation_data, flagged):
    """Mark annotations as having unsaved changes."""
    return True


@app.callback(
    [Output({"type": "annotation-input", "id": ALL}, "data"),
     Output({"type": "span-status", "id": ALL}, "children"),
     Output("document-text-container", "children", allow_duplicate=True),
     Output("span-annotations-list", "children", allow_duplicate=True),
     Output("selected-text-store", "data", allow_duplicate=True)],
    Input("span-trigger-store", "data"),
    [State("selected-text-store", "data"),
     State({"type": "annotation-input", "id": ALL}, "data"),
     State("app-state", "data"),
     State("current-index-store", "data"),
     State("documents-store", "data"),
     State("schema-store", "data"),
     State("annotations-store", "data")],
    prevent_initial_call=True
)
def add_span_annotation(span_trigger, selected_text, span_data_list, app_state,
                       current_index, documents, schema_data, annotations_data):
    """Add a span annotation when button is clicked."""
    if not app_state or not app_state.get("loaded"):
        from dash.exceptions import PreventUpdate
        raise PreventUpdate
    if not span_trigger or not isinstance(span_trigger, dict) or span_trigger.get("type") != "add-span":
        from dash.exceptions import PreventUpdate
        raise PreventUpdate
    
    # Debug logging
    print(f"DEBUG: Button clicked - entity type: {span_trigger.get('entity')}")
    print(f"DEBUG: Selected text from store: '{selected_text}'")
    
    # The triggered_id contains the annotation type ID and entity type
    annotation_type_id = span_trigger["id"]
    entity_type = span_trigger["entity"]  # Entity type from button ID
    
    # Find the index in the schema for this annotation type
    from data.validator import AnnotationSchema
    schema = AnnotationSchema(**schema_data)
    
    schema_index = None
    span_control_index = None
    span_count = 0
    
    for i, ann_type in enumerate(schema.annotation_types):
        if ann_type.type == "span_annotation":
            if ann_type.id == annotation_type_id:
                schema_index = i
                span_control_index = span_count
            span_count += 1
    
    if schema_index is None or span_control_index is None:
        from dash.exceptions import PreventUpdate
        raise PreventUpdate
    
    # Get current spans
    current_spans = span_data_list[schema_index] if schema_index < len(span_data_list) else []
    
    # Validate inputs
    status_messages = ["" for _ in range(span_count)]
    
    # Use selected text (from highlighting)
    if selected_text == "None":
        selected_text = ""
    text_to_annotate = selected_text or ""
    
    if not text_to_annotate or not text_to_annotate.strip():
        status_messages[span_control_index] = html.Small("⚠ Please highlight text in the document", className="text-warning")
        # Get current document text for display
        doc_data = documents[current_index]
        file_path = doc_data['file_path']
        full_text, _ = load_document_text(file_path)
        formatted_text = format_document_text(full_text, current_spans)
        span_list = create_span_annotations_display(current_spans)
        return span_data_list, status_messages, formatted_text, span_list, ""
    
    # Get current document text to find the span
    doc_data = documents[current_index]
    file_path = doc_data['file_path']
    full_text, success = load_document_text(file_path)
    
    if not success:
        status_messages[span_control_index] = html.Small("⚠ Error loading document", className="text-danger")
        formatted_text = format_document_text(full_text, current_spans)
        span_list = create_span_annotations_display(current_spans)
        return span_data_list, status_messages, formatted_text, span_list, ""
    
    # Find the text in the document
    text_to_find = text_to_annotate.strip()
    start_pos = full_text.find(text_to_find)
    
    if start_pos == -1:
        status_messages[span_control_index] = html.Small("⚠ Text not found in document", className="text-warning")
        formatted_text = format_document_text(full_text, current_spans)
        span_list = create_span_annotations_display(current_spans)
        return span_data_list, status_messages, formatted_text, span_list, ""
    
    # Create new span annotation
    new_span = {
        "text": text_to_find,
        "start": start_pos,
        "end": start_pos + len(text_to_find),
        "entity_type": entity_type
    }
    
    # Add to current spans
    if current_spans is None:
        current_spans = []
    updated_spans = current_spans + [new_span]
    
    # Update span data list (for ALL annotation types)
    new_span_data_list = [span_data_list[i] if i != schema_index else updated_spans 
                          for i in range(len(span_data_list))]
    
    # Update status and clear inputs
    status_messages[span_control_index] = html.Small(f"✓ Added: {entity_type}", className="text-success")
    # Re-render document with highlights
    formatted_text = format_document_text(full_text, updated_spans)
    span_list = create_span_annotations_display(updated_spans)
    
    # Clear the selected text store
    return new_span_data_list, status_messages, formatted_text, span_list, ""


@app.callback(
    [Output({"type": "annotation-input", "id": ALL}, "data", allow_duplicate=True),
     Output("document-text-container", "children", allow_duplicate=True),
     Output("span-annotations-list", "children", allow_duplicate=True)],
    Input({"type": "delete-span", "index": ALL}, "n_clicks"),
    [State({"type": "annotation-input", "id": ALL}, "data"),
     State("current-index-store", "data"),
     State("documents-store", "data"),
     State("schema-store", "data")],
    prevent_initial_call=True
)
def delete_span_annotation(delete_clicks, span_data_list, current_index, documents, schema_data):
    """Delete a span annotation."""
    if not ctx.triggered_id or not any(delete_clicks):
        from dash.exceptions import PreventUpdate
        raise PreventUpdate
    
    # Find which delete button was clicked
    delete_index = ctx.triggered_id["index"]
    
    # Find the span annotation storage (should be only one for span_annotation type)
    from data.validator import AnnotationSchema
    schema = AnnotationSchema(**schema_data)
    
    span_field_index = None
    for i, ann_type in enumerate(schema.annotation_types):
        if ann_type.type == "span_annotation":
            span_field_index = i
            break
    
    if span_field_index is None or span_field_index >= len(span_data_list):
        from dash.exceptions import PreventUpdate
        raise PreventUpdate
    
    # Get current spans and remove the one at delete_index
    current_spans = span_data_list[span_field_index] or []
    if delete_index < len(current_spans):
        updated_spans = [span for i, span in enumerate(current_spans) if i != delete_index]
    else:
        updated_spans = current_spans
    
    # Update span data list
    new_span_data_list = [span_data_list[i] if i != span_field_index else updated_spans 
                          for i in range(len(span_data_list))]
    
    # Re-render document with updated highlights
    doc_data = documents[current_index]
    file_path = doc_data['file_path']
    full_text, success = load_document_text(file_path)
    
    formatted_text = format_document_text(full_text, updated_spans)
    span_list = create_span_annotations_display(updated_spans)
    
    return new_span_data_list, formatted_text, span_list


@app.callback(
    [Output("annotations-store", "data", allow_duplicate=True),
     Output("save-status", "children")],
    [Input("manual-save-button", "n_clicks"),
     Input("auto-save-interval", "n_intervals")],
    [State("current-index-store", "data"),
     State("documents-store", "data"),
     State("annotations-store", "data"),
     State("schema-store", "data"),
     State({"type": "annotation-input", "id": ALL}, "value"),
     State({"type": "annotation-input", "id": ALL}, "data"),
     State("flag-for-review", "checked"),
     State("dirty-state-store", "data")],
    prevent_initial_call=True
)
def save_annotations_callback(manual_click, auto_interval, current_index, documents,
                               annotations_data, schema_data, annotation_values,
                               annotation_data_values, flagged, is_dirty):
    """Save annotations (manual or auto-save)."""
    # Only auto-save if dirty
    if ctx.triggered_id == "auto-save-interval" and not is_dirty:
        return annotations_data, ""
    
    if not documents or not annotations_data or not schema_data:
        return annotations_data, ""
    
    try:
        # Save current document annotations
        from data.validator import AnnotationCollection, AnnotationSchema
        annotations = AnnotationCollection(**annotations_data)
        schema = AnnotationSchema(**schema_data)
        
        doc_data = documents[current_index]
        file_path = doc_data['file_path']
        
        # Get or create annotation
        doc_ann = get_or_create_annotation(annotations, file_path, config.annotator)
        
        # Update annotations from inputs
        ann_dict = {}
        for i, ann_type in enumerate(schema.annotation_types):
            value = annotation_values[i] if i < len(annotation_values) else None
            if value is None and i < len(annotation_data_values):
                value = annotation_data_values[i]
            ann_dict[ann_type.id] = value
        
        doc_ann.annotations = ann_dict
        doc_ann.flagged_for_review = flagged
        
        # Determine status
        required_fields = [at.id for at in schema.annotation_types if at.required]
        all_required_filled = all(
            ann_dict.get(field) for field in required_fields
        )
        
        if all_required_filled:
            doc_ann.status = STATUS_COMPLETED
        elif any(ann_dict.values()):
            doc_ann.status = STATUS_IN_PROGRESS
        else:
            doc_ann.status = STATUS_NOT_STARTED
        
        # Update collection
        annotations.update_annotation(doc_ann)
        
        # Save to file
        success = save_annotations(annotations)
        
        status_msg = "✓ Saved" if success else "✗ Save failed"
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        return annotations.model_dump(), f"{status_msg} at {timestamp}"
    
    except Exception as e:
        return annotations_data, f"Error saving: {str(e)}"


def save_current_annotations(current_index, documents, annotations_data,
                             schema_data, annotation_values, annotation_data_values, flagged):
    """Helper to save current document's annotations."""
    try:
        from data.validator import AnnotationCollection, AnnotationSchema
        annotations = AnnotationCollection(**annotations_data)
        schema = AnnotationSchema(**schema_data)
        
        doc_data = documents[current_index]
        file_path = doc_data['file_path']
        
        doc_ann = get_or_create_annotation(annotations, file_path, config.annotator)
        
        ann_dict = {}
        for i, ann_type in enumerate(schema.annotation_types):
            value = annotation_values[i] if i < len(annotation_values) else None
            if value is None and i < len(annotation_data_values):
                value = annotation_data_values[i]
            ann_dict[ann_type.id] = value
        
        doc_ann.annotations = ann_dict
        doc_ann.flagged_for_review = flagged
        
        required_fields = [at.id for at in schema.annotation_types if at.required]
        all_required_filled = all(ann_dict.get(field) for field in required_fields)
        
        if all_required_filled:
            doc_ann.status = STATUS_COMPLETED
        elif any(ann_dict.values()):
            doc_ann.status = STATUS_IN_PROGRESS
        else:
            doc_ann.status = STATUS_NOT_STARTED
        
        annotations.update_annotation(doc_ann)
        save_annotations(annotations)
        return annotations.model_dump()
    except Exception as e:
        print(f"Error saving annotations: {e}")
        return annotations_data


if __name__ == "__main__":
    print("Starting Clinical Note Annotation Tool...")
    print(f"Annotations will be saved to: {config.annotations_path}")
    print(f"Annotator: {config.annotator}")
    print(f"\nOpen your browser to: http://localhost:{config.port}")
    
    app.run(debug=config.debug, port=config.port)
