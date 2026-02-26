"""Main TaterApp application class."""
from typing import Optional, Type, Any
from pathlib import Path
import json

from dash import Dash, html, dcc, Input, Output, State, callback
import dash_mantine_components as dmc
from pydantic import BaseModel, ValidationError

from tater.models import Document, DocumentMetadata
from tater.widgets.base import TaterWidget


class TaterApp:
    """Main Tater application for document annotation."""

    def __init__(
        self,
        title: str = "Tater",
        theme: str = "light",
        annotations_path: str = "annotations.json"
    ):
        """
        Initialize the Tater app.

        Args:
            title: Application title
            theme: Color theme ("light" or "dark")
            annotations_path: Path to save/load annotations
        """
        self.title = title
        self.theme = theme
        self.annotations_path = annotations_path
        self.app = Dash(__name__, suppress_callback_exceptions=True)
        self.widgets: list[TaterWidget] = []
        self.documents: list[Document] = []
        self.current_doc_index = 0
        self.annotations: dict[str, dict] = {}

    def load_documents(self, source: str) -> bool:
        """
        Load documents from a JSON file.

        Args:
            source: Path to documents JSON file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(source, 'r') as f:
                data = json.load(f)
            
            # Handle both formats: {"documents": [...]} and [...]
            if isinstance(data, dict) and "documents" in data:
                doc_dicts = data["documents"]
            elif isinstance(data, list):
                doc_dicts = data
            else:
                print(f"Error: Invalid document format in {source}")
                return False
            
            # Parse into Document instances
            documents = []
            for idx, doc_dict in enumerate(doc_dicts):
                try:
                    doc = Document.from_dict(doc_dict, index=idx)
                    documents.append(doc)
                except ValidationError as e:
                    print(f"Error validating document at index {idx}: {e}")
                    return False
            
            self.documents = documents
            print(f"Loaded {len(self.documents)} documents from {source}")
            return True
        except Exception as e:
            print(f"Error loading documents: {e}")
            return False

    def set_annotation_widgets(self, widgets: list[TaterWidget]) -> None:
        """
        Set the widgets for annotation.

        Args:
            widgets: List of TaterWidget instances
        """
        self.widgets = widgets
        self._setup_layout()
        self._setup_callbacks()

    def _setup_layout(self) -> None:
        """Create the Dash layout with navigation and annotation panel."""
        # Create annotation fields from widgets
        annotation_fields = []
        for widget in self.widgets:
            field_container = dmc.Stack([
                dmc.Text(widget.label, fw=500, size="sm"),
                widget.component(),
                dmc.Text(widget.description or "", size="xs", c="dimmed") if widget.description else None,
            ], gap="xs", mt="md")
            annotation_fields.append(field_container)

        self.app.layout = dmc.MantineProvider(
            theme={"colorScheme": self.theme},
            children=[
                dmc.Container([
                    # Header
                    dmc.Paper([
                        dmc.Group([
                            dmc.Title(self.title, order=2),
                            dmc.Badge(
                                f"Document {self.current_doc_index + 1} of {len(self.documents)}",
                                id="doc-counter",
                                color="blue"
                            ),
                        ], justify="space-between"),
                    ], p="md", mb="md", withBorder=True),
                    
                    # Navigation
                    dmc.Card([
                        dmc.Group([
                            dmc.Button("Previous", id="btn-prev", variant="outline"),
                            dmc.Button("Next", id="btn-next", variant="outline"),
                        ], justify="space-between"),
                    ], withBorder=True, p="md", mb="md"),

                    # Document viewer
                    dmc.Card([
                        dmc.Title("Document", order=4, mb="sm"),
                        dmc.ScrollArea(
                            html.Div(
                                id="document-content",
                                style={"whiteSpace": "pre-wrap"}
                            ),
                            h=300
                        ),
                    ], withBorder=True, p="md", mb="md"),

                    # Annotation panel
                    dmc.Card([
                        dmc.Title("Annotations", order=4, mb="sm"),
                        dmc.Stack(annotation_fields, gap="md"),
                    ], withBorder=True, p="md"),

                    # Hidden store for state
                    dcc.Store(id="current-doc-index", data=0),
                    dcc.Store(id="annotations-store", data={}),
                ], size="lg", pt="md")
            ]
        )

    def _setup_callbacks(self) -> None:
        """Setup Dash callbacks for interactivity."""
        
        # Update document content when index changes
        @self.app.callback(
            [Output("document-content", "children"),
             Output("doc-counter", "children")],
            Input("current-doc-index", "data")
        )
        def update_document(doc_index):
            if not self.documents or doc_index >= len(self.documents):
                return "No document loaded", "No documents"
            
            doc = self.documents[doc_index]
            
            # Load document content
            try:
                content = doc.load_content()
            except Exception as e:
                content = f"Error loading file: {e}"
            
            counter_text = f"Document {doc_index + 1} of {len(self.documents)}"
            return content, counter_text

        # Navigation buttons
        @self.app.callback(
            Output("current-doc-index", "data"),
            [Input("btn-prev", "n_clicks"),
             Input("btn-next", "n_clicks")],
            State("current-doc-index", "data"),
            prevent_initial_call=True
        )
        def navigate(prev_clicks, next_clicks, current_index):
            from dash import ctx
            
            if not ctx.triggered:
                return current_index
            
            button_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            if button_id == "btn-prev" and current_index > 0:
                return current_index - 1
            elif button_id == "btn-next" and current_index < len(self.documents) - 1:
                return current_index + 1
            
            return current_index

    def run(self, debug: bool = False, port: int = 8050, host: str = "127.0.0.1") -> None:
        """
        Start the Dash development server.

        Args:
            debug: Enable debug mode
            port: Port number
            host: Host address
        """
        self.app.run(debug=debug, port=port, host=host)
