"""Main Dash application for clinical note annotation."""
import sys
import base64
import io
import json
import csv
from pathlib import Path
from dash import Dash, html, dcc, Input, Output, State, ALL, ctx, callback
import dash_bootstrap_components as dbc
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
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

app.title = "Clinical Note Annotation Tool"


def create_startup_screen() -> html.Div:
    """Create the initial startup screen for loading files."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2("Clinical Note Annotation Tool", className="text-center mt-5 mb-4"),
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Load Documents and Schema", className="mb-4"),
                        dbc.Label("Document List File (CSV or JSON):"),
                        dcc.Upload(
                            id="documents-file-upload",
                            children=dbc.Button(
                                "Choose Document List File",
                                color="secondary",
                                outline=True,
                                className="w-100"
                            ),
                            className="mb-2"
                        ),
                        html.Div(id="documents-file-name", className="text-muted small mb-3"),
                        dbc.Label("Annotation Schema File (JSON):"),
                        dcc.Upload(
                            id="schema-file-upload",
                            children=dbc.Button(
                                "Choose Schema File",
                                color="secondary",
                                outline=True,
                                className="w-100"
                            ),
                            className="mb-2"
                        ),
                        html.Div(id="schema-file-name", className="text-muted small mb-3"),
                        html.Div(id="load-error", className="text-danger mb-3"),
                        dbc.Button(
                            "Load and Start Annotating",
                            id="load-button",
                            color="primary",
                            className="w-100",
                            disabled=True
                        )
                    ])
                ], className="shadow")
            ], width=6)
        ], justify="center")
    ], fluid=True)


def create_annotation_screen() -> html.Div:
    """Create the main annotation interface."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                create_navigation_bar()
            ], width=12, className="mb-3")
        ]),
        dbc.Row([
            dbc.Col([
                create_document_viewer()
            ], width=7),
            dbc.Col([
                create_annotation_panel()
            ], width=5)
        ])
    ], fluid=True, className="p-3")


# Main app layout
app.layout = html.Div([
    dcc.Store(id="app-state", data={"loaded": False}),
    dcc.Store(id="documents-store", data=[]),
    dcc.Store(id="schema-store", data=None),
    dcc.Store(id="annotations-store", data=None),
    dcc.Store(id="current-index-store", data=0),
    dcc.Store(id="dirty-state-store", data=False),
    dcc.Store(id="documents-file-content", data=None),
    dcc.Store(id="schema-file-content", data=None),
    dcc.Store(id="selected-text-store", data=None),
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
    [Output("main-content", "children"),
     Output("app-state", "data"),
     Output("documents-store", "data"),
     Output("schema-store", "data"),
     Output("annotations-store", "data"),
     Output("load-error", "children")],
    Input("load-button", "n_clicks"),
    [State("documents-file-content", "data"),
     State("schema-file-content", "data"),
     State("documents-file-upload", "filename")],
    prevent_initial_call=True
)
def load_files(n_clicks, docs_content, schema_content, docs_filename):
    """Load documents and schema files from uploaded content."""
    if not docs_content or not schema_content:
        return (
            create_startup_screen(),
            {"loaded": False},
            [],
            None,
            None,
            "Please upload both files."
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
            ""
        )
    
    except Exception as e:
        return (
            create_startup_screen(),
            {"loaded": False},
            [],
            None,
            None,
            f"Error loading files: {str(e)}"
        )


@app.callback(
    [Output("current-index-store", "data"),
     Output("dirty-state-store", "data", allow_duplicate=True)],
    [Input("prev-button", "n_clicks"),
     Input("next-button", "n_clicks"),
     Input("document-selector", "value")],
    [State("current-index-store", "data"),
     State("documents-store", "data"),
     State("annotations-store", "data"),
     State("schema-store", "data"),
     State({"type": "annotation-input", "id": ALL}, "value"),
     State("flag-for-review", "value")],
    prevent_initial_call=True
)
def navigate_documents(prev_clicks, next_clicks, selector_value, current_index,
                       documents, annotations_data, schema_data, annotation_values, flagged):
    """Handle document navigation."""
    if not documents:
        return current_index, False
    
    # Determine new index based on trigger
    triggered_id = ctx.triggered_id
    
    new_index = current_index
    if triggered_id == "prev-button" and current_index > 0:
        new_index = current_index - 1
    elif triggered_id == "next-button" and current_index < len(documents) - 1:
        new_index = current_index + 1
    elif triggered_id == "document-selector" and selector_value is not None:
        new_index = selector_value
    
    # Save current document's annotations before navigating
    if new_index != current_index and annotations_data and schema_data:
        save_current_annotations(
            current_index, documents, annotations_data,
            schema_data, annotation_values, flagged
        )
    
    return new_index, False


@app.callback(
    [Output("document-text-container", "children"),
     Output("document-metadata", "children"),
     Output("annotation-controls-container", "children"),
     Output("flag-for-review", "value"),
     Output("span-annotations-list", "children"),
     Output("prev-button", "disabled"),
     Output("next-button", "disabled"),
     Output("document-selector", "options"),
     Output("document-selector", "value"),
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
            "value": i
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
        current_index,
        progress
    )


@app.callback(
    Output("dirty-state-store", "data"),
    [Input({"type": "annotation-input", "id": ALL}, "value"),
     Input("flag-for-review", "value")],
    prevent_initial_call=True
)
def mark_dirty(annotation_values, flagged):
    """Mark annotations as having unsaved changes."""
    return True


@app.callback(
    [Output({"type": "annotation-input", "id": ALL}, "data"),
     Output({"type": "span-status", "id": ALL}, "children"),
     Output({"type": "span-text-input", "id": ALL}, "value"),
     Output({"type": "entity-type-selector", "id": ALL}, "value"),
     Output("document-text-container", "children", allow_duplicate=True),
     Output("span-annotations-list", "children", allow_duplicate=True)],
    Input({"type": "add-span", "id": ALL}, "n_clicks"),
    [State({"type": "span-text-input", "id": ALL}, "value"),
     State({"type": "entity-type-selector", "id": ALL}, "value"),
     State({"type": "annotation-input", "id": ALL}, "data"),
     State("current-index-store", "data"),
     State("documents-store", "data"),
     State("schema-store", "data"),
     State("annotations-store", "data")],
    prevent_initial_call=True
)
def add_span_annotation(n_clicks_list, text_inputs, entity_types, span_data_list, 
                       current_index, documents, schema_data, annotations_data):
    """Add a span annotation when button is clicked."""
    if not ctx.triggered_id or not any(n_clicks_list):
        from dash.exceptions import PreventUpdate
        raise PreventUpdate
    
    # The triggered_id contains the annotation type ID
    annotation_type_id = ctx.triggered_id["id"]
    
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
    
    # Get input values for this specific span annotation type
    text_input = text_inputs[span_control_index] if span_control_index < len(text_inputs) else None
    entity_type = entity_types[span_control_index] if span_control_index < len(entity_types) else None
    current_spans = span_data_list[schema_index] if schema_index < len(span_data_list) else []
    
    # Validate inputs
    status_messages = ["" for _ in range(span_count)]
    clear_text_inputs = [text_inputs[i] if i < len(text_inputs) else "" for i in range(span_count)]
    clear_entity_selectors = [entity_types[i] if i < len(entity_types) else None for i in range(span_count)]
    
    if not text_input or not text_input.strip():
        status_messages[span_control_index] = html.Small("⚠ Please enter text to annotate", className="text-warning")
        # Get current document text for display
        doc_data = documents[current_index]
        file_path = doc_data['file_path']
        full_text, _ = load_document_text(file_path)
        formatted_text = format_document_text(full_text, current_spans)
        span_list = create_span_annotations_display(current_spans)
        return span_data_list, status_messages, clear_text_inputs, clear_entity_selectors, formatted_text, span_list
    
    if not entity_type:
        status_messages[span_control_index] = html.Small("⚠ Please select an entity type", className="text-warning")
        # Get current document text for display
        doc_data = documents[current_index]
        file_path = doc_data['file_path']
        full_text, _ = load_document_text(file_path)
        formatted_text = format_document_text(full_text, current_spans)
        span_list = create_span_annotations_display(current_spans)
        return span_data_list, status_messages, clear_text_inputs, clear_entity_selectors, formatted_text, span_list
    
    # Get current document text to find the span
    doc_data = documents[current_index]
    file_path = doc_data['file_path']
    full_text, success = load_document_text(file_path)
    
    if not success:
        status_messages[span_control_index] = html.Small("⚠ Error loading document", className="text-danger")
        formatted_text = format_document_text(full_text, current_spans)
        span_list = create_span_annotations_display(current_spans)
        return span_data_list, status_messages, clear_text_inputs, clear_entity_selectors, formatted_text, span_list
    
    # Find the text in the document
    text_to_find = text_input.strip()
    start_pos = full_text.find(text_to_find)
    
    if start_pos == -1:
        status_messages[span_control_index] = html.Small("⚠ Text not found in document", className="text-warning")
        formatted_text = format_document_text(full_text, current_spans)
        span_list = create_span_annotations_display(current_spans)
        return span_data_list, status_messages, clear_text_inputs, clear_entity_selectors, formatted_text, span_list
    
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
    clear_text_inputs[span_control_index] = ""  # Clear the text input
    clear_entity_selectors[span_control_index] = None  # Clear the entity selector
    
    # Re-render document with highlights
    formatted_text = format_document_text(full_text, updated_spans)
    span_list = create_span_annotations_display(updated_spans)
    
    return new_span_data_list, status_messages, clear_text_inputs, clear_entity_selectors, formatted_text, span_list


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
     State("flag-for-review", "value"),
     State("dirty-state-store", "data")],
    prevent_initial_call=True
)
def save_annotations_callback(manual_click, auto_interval, current_index, documents,
                               annotations_data, schema_data, annotation_values,
                               flagged, is_dirty):
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
            if i < len(annotation_values):
                ann_dict[ann_type.id] = annotation_values[i]
        
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
                             schema_data, annotation_values, flagged):
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
            if i < len(annotation_values):
                ann_dict[ann_type.id] = annotation_values[i]
        
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
    
    except Exception as e:
        print(f"Error saving annotations: {e}")


if __name__ == "__main__":
    print("Starting Clinical Note Annotation Tool...")
    print(f"Annotations will be saved to: {config.annotations_path}")
    print(f"Annotator: {config.annotator}")
    print(f"\nOpen your browser to: http://localhost:{config.port}")
    
    app.run(debug=config.debug, port=config.port)
