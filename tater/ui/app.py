"""Core Tater Dash application."""
import os
from typing import Optional
from dash import Dash, html, dcc, Input, Output, ctx, ClientsideFunction
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
    ):
        """Initialize the Tater application.
        
        Args:
            title: Application title shown in browser tab
            theme: UI theme ('light' or 'dark')
            external_stylesheets: Additional CSS stylesheets to include
        """
        self.title = title
        self.theme = theme
        self.documents: Optional[DocumentList] = None
        self.spec: Optional[AnnotationSpec] = None
        self.annotation_widgets: Optional[list[TaterWidget]] = None
        self.annotation_panel_title = "Annotations"
        self.annotations: dict[int, dict] = {}  # doc_index -> {field_id: value}
        self.current_index = 0
        
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
            return True
        except FileNotFoundError:
            print(f"✗ Schema file not found: {source}")
            return False
        except Exception as e:
            print(f"✗ Error loading schema: {e}")
            return False

    def set_annotation_widgets(self, widgets: list[TaterWidget], title: str = "Annotations") -> None:
        """Set custom annotation widgets for the right panel.

        Args:
            widgets: List of TaterWidget instances to render
            title: Panel title shown above widgets
        """
        self.annotation_widgets = widgets
        self.annotation_panel_title = title
        
    def _setup_layout(self):
        """Set up the basic application layout."""
        # Create main content (static layout structure)
        main_content = self._create_main_content()
        
        self.app.layout = dmc.MantineProvider(
            theme={"colorScheme": self.theme},
            children=[
                dcc.Store(id="current-index-store", data=0),
                dcc.Store(id="documents-store", data=None),
                dcc.Store(id="annotations-store", data={}),
                
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
        if not self.spec and not self.annotation_widgets:
            return None

        if self.annotation_widgets is not None:
            widgets = [widget.component() for widget in self.annotation_widgets]
        else:
            widgets = []

            for field in self.spec.data_schema:
                widget_config = self.spec.get_widget_config(field.id)

                # Currently only supporting single_choice widgets
                if field.type == "single_choice":
                    widget_type = widget_config.widget if widget_config else "segmented_control"
                    if widget_type == "radio_group":
                        widget = RadioGroupWidget.from_field(field, widget_config).component()
                    else:
                        widget = SegmentedControlWidget.from_field(field, widget_config).component()
                    widgets.append(widget)
        
        return dmc.Paper([
            dmc.Stack([
                dmc.Title(self.annotation_panel_title, order=3, mb="md"),
                *widgets
            ], gap="md")
        ], p="md", withBorder=True, shadow="sm")
    
    def _create_main_content(self):
        """Create main content layout (document viewer + optional annotation panel)."""
        # Document viewer only (without info and navigation)
        document_viewer_only = html.Div(id="document-viewer")
        
        # Two-column layout with document viewer and annotation panel
        content_grid = dmc.Grid([
            dmc.GridCol([document_viewer_only], span={"base": 12, "md": 7}),
            dmc.GridCol([html.Div(id="annotation-panel")], span={"base": 12, "md": 5}),
        ], gutter="xl")
        
        # Stack everything with full-width info and navigation
        return dmc.Stack([
            create_document_info(),
            content_grid,
            create_document_navigation(),
        ], gap="lg")

    
    def _setup_callbacks(self):
        """Set up Dash callbacks for document navigation and display."""
        
        @self.app.callback(
            Output("annotation-panel", "children"),
            Input("current-index-store", "data")
        )
        def render_annotation_panel(_):
            """Render the annotation panel if schema is loaded."""
            if self.spec:
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
