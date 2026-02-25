"""Core Tater Dash application."""
import json
import os
from pathlib import Path
from typing import Optional
from dash import Dash, html, dcc, Input, Output, State, ctx, ClientsideFunction, no_update
import dash_mantine_components as dmc

from ..models.document import DocumentList
from ..models.spec import AnnotationSpec
from ..loaders import load_document_text
from .components import (
    create_document_viewer,
    create_document_navigation,
    create_document_info
)
from .widgets import RadioGroupWidget, SegmentedControlWidget, TaterWidget


class TaterApp:
    """Main Tater annotation application.
    
    This class provides a Dash-based annotation interface that can be
    configured with schemas and documents either programmatically or
    via JSON/YAML configuration files.
    
    Example:
        >>> app = TaterApp(title="My Annotation Project")
        >>> app.load_documents("documents.json")
        >>> app.run(debug=True, port=8050)
    """
    
    def __init__(
        self,
        title: str = "Tater Annotation Tool",
        theme: str = "light",
        external_stylesheets: Optional[list] = None,
        annotations_path: Optional[str] = None,
    ):
        """Initialize the Tater application.
        
        Args:
            title: Application title shown in browser tab
            theme: UI theme ('light' or 'dark')
            external_stylesheets: Additional CSS stylesheets to include
            annotations_path: Path to save annotations JSON on navigation
        """
        self.title = title
        self.theme = theme
        self.documents: Optional[DocumentList] = None
        self.spec: Optional[AnnotationSpec] = None
        self.annotation_widgets: Optional[list[TaterWidget]] = None
        self.annotations: dict[int, dict] = {}  # doc_index -> {field_id: value}
        self.current_index = 0
        self._annotation_callbacks_set = False
        self.annotations_path = annotations_path
        
        # Initialize Dash app
        self.app = Dash(
            __name__,
            title=title,
            external_stylesheets=external_stylesheets or [],
            suppress_callback_exceptions=True
        )
        
        # Build layout
        self._setup_layout()
        self._setup_callbacks()
        
    def load_documents(self, source: str) -> bool:
        """Load documents from a file.
        
        Args:
            source: Path to JSON or CSV file with documents
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if source.endswith('.json'):
                self.documents = DocumentList.from_json_file(source)
            elif source.endswith('.csv'):
                self.documents = DocumentList.from_csv_file(source)
            else:
                print(f"✗ Unsupported file format: {source}")
                return False
            
            # Set default annotations path if not provided
            if self.annotations_path is None:
                doc_path = Path(source)
                self.annotations_path = str(doc_path.parent / f"{doc_path.stem}_annotations.json")
            
            print(f"✓ Loaded {len(self.documents.documents)} documents from {source}")
            return True
        except FileNotFoundError:
            print(f"✗ File not found: {source}")
            return False
        except Exception as e:
            print(f"✗ Error loading documents: {e}")
            return False
    
    def load_schema(self, source: str) -> bool:
        """Load annotation schema from a file.
        
        Args:
            source: Path to JSON schema file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.spec = AnnotationSpec.from_file(source)
            print(f"✓ Loaded schema with {len(self.spec.data_schema)} fields from {source}")
            
            # Generate widgets from schema so both paths result in same state
            self.annotation_widgets = []
            for field in self.spec.data_schema:
                widget_config = self.spec.get_widget_config(field.id)
                if field.type == "single_choice":
                    widget_type = widget_config.widget if widget_config else "segmented_control"
                    if widget_type == "radio_group":
                        widget = RadioGroupWidget.from_field(field, widget_config)
                    else:
                        widget = SegmentedControlWidget.from_field(field, widget_config)
                    self.annotation_widgets.append(widget)

            self._setup_annotation_callbacks()
            
            return True
        except FileNotFoundError:
            print(f"✗ Schema file not found: {source}")
            return False
        except Exception as e:
            print(f"✗ Error loading schema: {e}")
            return False

    def set_annotation_widgets(self, widgets: list[TaterWidget]) -> None:
        """Set custom annotation widgets for the right panel.

        Args:
            widgets: List of TaterWidget instances to render
        """
        self.annotation_widgets = widgets
        
        # Create schema from the widgets so both paths result in having self.spec
        fields = [widget.to_field() for widget in widgets]
        self.spec = AnnotationSpec(data_schema=fields)
        self._setup_annotation_callbacks()
        
    def _setup_layout(self):
        """Set up the basic application layout."""
        # Create main content (static layout structure)
        main_content = self._create_main_content()
        
        self.app.layout = dmc.MantineProvider(
            theme={"colorScheme": self.theme},
            forceColorScheme=self.theme,
            children=[
                dcc.Store(id="current-index-store", data=0),
                dcc.Store(id="documents-store", data=None),
                dcc.Store(id="annotations-store", data={}),
                dcc.Interval(id="save-status-timer", interval=2500, n_intervals=0, disabled=True),
                
                dmc.Container([
                    dmc.Stack([
                        dmc.Center(
                            dmc.Title(
                                self.title,
                                order=1,
                                mt="xl"
                            )
                        ),
                        
                        # Main content area - rendered once at initialization
                        main_content,
                        
                    ], gap="lg")
                ], size="xl", py="xl", id="main-container", fluid=True)
            ]
        )
    
    def _create_annotation_panel(self):
        """Create the annotation panel with widgets based on schema."""
        if not self.annotation_widgets:
            return None

        # Build widgets with dividers between them
        components = []
        has_required = any(getattr(widget, "required", False) for widget in self.annotation_widgets)
        for i, widget in enumerate(self.annotation_widgets):
            components.append(widget.component())
            if i < len(self.annotation_widgets) - 1:
                components.append(dmc.Divider())

        if has_required:
            components.append(dmc.Text("[* Required]", size="xs", c="red"))
        
        return dmc.Paper([
            dmc.Stack(components, gap="md")
        ], p="md", withBorder=True, shadow="sm")
    
    def _create_main_content(self):
        """Create main content layout (document viewer + optional annotation panel)."""
        # Document viewer only (without info and navigation)
        document_viewer_only = html.Div(id="document-viewer")

        document_controls = dmc.Stack([
            dmc.Checkbox(id="flag-document", label="Flag document", checked=False),
            dmc.Textarea(
                id="document-notes",
                label="Notes",
                autosize=True,
                minRows=3,
                placeholder="Add notes about this document"
            )
        ], gap="sm")
        
        # Two-column layout with document viewer and annotation panel
        content_grid = dmc.Grid([
            dmc.GridCol([
                dmc.Stack([
                    document_viewer_only,
                    document_controls
                ], gap="md")
            ], span={"base": 12, "md": 7}),
            dmc.GridCol([html.Div(id="annotation-panel")], span={"base": 12, "md": 5}),
        ], gutter="xl")
        
        # Stack everything with full-width info and navigation
        return dmc.Stack([
            create_document_info(),
            content_grid,
            html.Div(id="save-status", style={"position": "fixed", "top": "20px", "right": "20px", "zIndex": 1000}),
            create_document_navigation(),
        ], gap="lg")

    def _setup_annotation_callbacks(self) -> None:
        """Set up callbacks that persist and restore annotation values."""
        if self._annotation_callbacks_set or not self.annotation_widgets:
            return

        self._annotation_callbacks_set = True
        widget_inputs = [Input(widget.component_id, widget.value_prop) for widget in self.annotation_widgets]
        widget_outputs = [Output(widget.component_id, widget.value_prop) for widget in self.annotation_widgets]

        @self.app.callback(
            Output("annotations-store", "data"),
            Input("flag-document", "checked"),
            Input("document-notes", "value"),
            *widget_inputs,
            State("current-index-store", "data"),
            State("annotations-store", "data"),
            prevent_initial_call=True
        )
        def save_annotations(*args):
            checked = args[0]
            notes = args[1]
            values = list(args[2:2 + len(self.annotation_widgets)])
            current_index = args[2 + len(self.annotation_widgets)]
            annotations_data = args[3 + len(self.annotation_widgets)] or {}

            if current_index is None:
                return no_update

            doc_key = str(current_index)
            new_doc_annotations = dict(annotations_data.get(doc_key, {}))

            if ctx.triggered_id == "flag-document":
                new_doc_annotations["_flagged"] = bool(checked)
            elif ctx.triggered_id == "document-notes":
                new_doc_annotations["_notes"] = notes
            else:
                for widget, value in zip(self.annotation_widgets, values):
                    new_doc_annotations[widget.schema_id] = value

            if annotations_data.get(doc_key) == new_doc_annotations:
                return no_update

            updated = dict(annotations_data)
            updated[doc_key] = new_doc_annotations
            return updated


        @self.app.callback(
            widget_outputs,
            Input("current-index-store", "data"),
            State("annotations-store", "data"),
        )
        def restore_annotations(current_index, annotations_data):
            if current_index is None:
                return [None] * len(self.annotation_widgets)

            doc_key = str(current_index)
            doc_annotations = (annotations_data or {}).get(doc_key, {})
            return [doc_annotations.get(widget.schema_id) for widget in self.annotation_widgets]

        @self.app.callback(
            Output("flag-document", "checked"),
            Input("current-index-store", "data"),
            State("annotations-store", "data"),
        )
        def restore_flag(current_index, annotations_data):
            if current_index is None:
                return False

            doc_key = str(current_index)
            doc_annotations = (annotations_data or {}).get(doc_key, {})
            return bool(doc_annotations.get("_flagged", False))

        @self.app.callback(
            Output("document-notes", "value"),
            Input("current-index-store", "data"),
            State("annotations-store", "data"),
        )
        def restore_notes(current_index, annotations_data):
            if current_index is None:
                return ""

            doc_key = str(current_index)
            doc_annotations = (annotations_data or {}).get(doc_key, {})
            return doc_annotations.get("_notes", "")

        @self.app.callback(
            Output("save-status", "children"),
            Output("save-status-timer", "disabled"),
            Input("current-index-store", "data"),
            State("annotations-store", "data"),
            prevent_initial_call=True
        )
        def autosave_on_navigation(current_index, annotations_data):
            if current_index is None or not self.annotations_path:
                return no_update, True

            path = Path(self.annotations_path)
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("w", encoding="utf-8") as f:
                    json.dump(annotations_data or {}, f, indent=2)
                alert = dmc.Alert(
                    "Annotations saved successfully",
                    title="Saved",
                    color="teal",
                    withCloseButton=False,
                    icon=dmc.Text("✓", size="lg")
                )
                return alert, False
            except Exception as exc:
                alert = dmc.Alert(
                    str(exc),
                    title="Save failed",
                    color="red",
                    withCloseButton=False,
                    icon=dmc.Text("✗", size="lg")
                )
                return alert, False

        @self.app.callback(
            Output("save-status", "children", allow_duplicate=True),
            Output("save-status-timer", "disabled", allow_duplicate=True),
            Input("save-status-timer", "n_intervals"),
            prevent_initial_call=True
        )
        def clear_save_status(_):
            return "", True

    
    def _setup_callbacks(self):
        """Set up Dash callbacks for document navigation and display."""
        
        @self.app.callback(
            Output("annotation-panel", "children"),
            Input("current-index-store", "data")
        )
        def render_annotation_panel(_):
            """Render the annotation panel if widgets are loaded."""
            if self.annotation_widgets:
                return self._create_annotation_panel()
            return None
        
        @self.app.callback(
            [Output("document-viewer", "children"),
             Output("document-title", "children"),
             Output("document-metadata", "children"),
             Output("prev-button", "disabled"),
             Output("next-button", "disabled"),
             Output("document-selector", "data"),
             Output("document-progress", "value")],
            Input("current-index-store", "data")
        )
        def update_document_display(current_index):
            """Update the document display when index changes."""
            if not self.documents or not self.documents.documents:
                return (
                    dmc.Text("No documents loaded", c="red"),
                    "No Document",
                    "",
                    True,
                    True,
                    [],
                    0
                )
            
            doc = self.documents.documents[current_index]
            
            # Load document content
            content, success = load_document_text(doc.file_path)
            if not success:
                viewer = dmc.Text(content, c="red")
            else:
                viewer = create_document_viewer(content)
            
            # Document title
            title = f"Document {current_index + 1} of {len(self.documents.documents)}"
            
            # Metadata
            metadata_text = ""
            if doc.metadata:
                if isinstance(doc.metadata, dict):
                    metadata_items = [f"{k}: {v}" for k, v in doc.metadata.items()]
                    metadata_text = " | ".join(metadata_items)
                else:
                    metadata_text = str(doc.metadata)
            
            # Navigation options
            dropdown_options = [
                {
                    "label": f"{i + 1}. {doc.file_path.split('/')[-1]}",
                    "value": str(i)
                }
                for i, doc in enumerate(self.documents.documents)
            ]
            
            # Progress percentage
            progress = ((current_index + 1) / len(self.documents.documents)) * 100
            
            prev_disabled = current_index <= 0
            next_disabled = current_index >= len(self.documents.documents) - 1
            
            return (
                viewer,
                title,
                metadata_text,
                prev_disabled,
                next_disabled,
                dropdown_options,
                progress
            )
        
        @self.app.callback(
            Output("current-index-store", "data"),
            [Input("prev-button", "n_clicks"),
             Input("next-button", "n_clicks"),
             Input("document-selector", "value")],
            prevent_initial_call=True
        )
        def handle_navigation(prev_clicks, next_clicks, selected_value):
            """Handle document navigation."""
            if not self.documents:
                return 0
            
            # Determine new index based on which input triggered
            if ctx.triggered_id == "prev-button" and self.current_index > 0:
                self.current_index -= 1
            elif ctx.triggered_id == "next-button" and self.current_index < len(self.documents.documents) - 1:
                self.current_index += 1
            elif ctx.triggered_id == "document-selector" and selected_value:
                self.current_index = int(selected_value)
            
            return self.current_index
        
        # Clientside callback for direct keyboard handling
        self.app.clientside_callback(
            ClientsideFunction("tater", "setupKeyboardNav"),
            Output("main-container", "style"),
            Input("current-index-store", "data")
        )
    
    def run(
        self,
        debug: Optional[bool] = None,
        port: int = 8050,
        host: str = "127.0.0.1",
        **kwargs
    ):
        """Run the Dash development server.
        
        Args:
            debug: Enable debug mode with hot reloading. If None, uses TATER_DEBUG env var
            port: Port to run server on
            host: Host to bind to
            **kwargs: Additional arguments passed to app.run()
        """
        # Use environment variable if debug not explicitly set
        if debug is None:
            debug = os.getenv("TATER_DEBUG", "").lower() in ("true", "1", "yes")
        
        print(f"Starting Tater application...")
        print(f"  Title: {self.title}")
        print(f"  Theme: {self.theme}")
        print(f"  Debug: {debug}")
        print(f"  Documents: {len(self.documents.documents) if self.documents else 0}")
        print(f"  URL: http://{host}:{port}")
        print()
        
        self.app.run(
            debug=debug,
            port=port,
            host=host,
            **kwargs
        )
    
    def get_server(self):
        """Get the underlying Flask server.
        
        Useful for deployment with guuncorn or other WSGI servers.
        
        Returns:
            Flask server instance
        """
        return self.app.server
