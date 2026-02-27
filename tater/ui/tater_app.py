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
        annotations_path: Optional[str] = None,
        schema_model: Optional[Type[BaseModel]] = None
    ):
        """
        Initialize the Tater app.

        Args:
            title: Application title
            theme: Color theme ("light" or "dark")
            annotations_path: Path to save/load annotations
            schema_model: Optional Pydantic model class for annotations
        """
        self.title = title
        self.theme = theme
        self.annotations_path = annotations_path
        self.schema_model = schema_model
        self.app = Dash(__name__, suppress_callback_exceptions=True)
        self.widgets: list[TaterWidget] = []
        self.documents: list[Document] = []
        self.current_doc_index = 0
        # Store Pydantic model instances (or dicts if no schema_model)
        self.annotations: dict[str, BaseModel | dict] = {}

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
            
            # Set default annotations path if not provided
            if self.annotations_path is None:
                doc_path = Path(source)
                self.annotations_path = str(doc_path.parent / f"{doc_path.stem}_annotations.json")
            
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
        
        # Store reference to TaterApp in Dash app so widgets can access it
        self.app._tater_app = self
        
        # Finalize all field paths for nested widgets
        for widget in self.widgets:
            widget._finalize_paths()

        # Register any widget-specific callbacks
        for widget in self.widgets:
            widget.register_callbacks(self.app)
        
        self._setup_layout()
        self._setup_callbacks()
        self._setup_value_capture_callbacks()

    def _setup_layout(self) -> None:
        """Create the Dash layout with navigation and annotation panel."""
        # Create annotation fields from widgets with dividers between them
        annotation_components = []
        has_required = any(getattr(widget, "required", False) for widget in self.widgets)
        
        for i, widget in enumerate(self.widgets):
            if widget.renders_own_label:
                field_container = widget.component()
            else:
                components_list = [
                    dmc.Text(widget.label, fw=500, size="sm"),
                ]
                if widget.description:
                    components_list.append(
                        dmc.Text(widget.description, size="xs", c="dimmed")
                    )
                components_list.append(widget.component())
                
                field_container = dmc.Stack(components_list, gap="xs", mt="md")
            
            annotation_components.append(field_container)
            
            # Add divider between widgets (not after last one)
            if i < len(self.widgets) - 1:
                annotation_components.append(dmc.Divider())
        
        # Add required marker if any widgets are required
        if has_required:
            annotation_components.append(dmc.Text("[* Required]", size="xs", c="red"))

        # Document viewer component (wrapped in Paper)
        document_viewer = dmc.Paper(
            html.Pre(
                id="document-content",
                style={
                    "whiteSpace": "pre-wrap",
                    "wordWrap": "break-word",
                    "fontFamily": "monospace",
                    "fontSize": "0.9rem",
                    "lineHeight": "1.5",
                    "margin": 0,
                    "height": "500px",
                    "overflowY": "auto",
                }
            ),
            p="md",
            withBorder=True,
            shadow="sm"
        )

        # Document controls (flag and notes)
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

        # Navigation controls
        nav_controls = dmc.Flex([
            dmc.Button("← Previous", id="btn-prev", variant="outline", flex=1),
            dmc.Button("Next →", id="btn-next", variant="outline", flex=1),
        ], gap="md")

        # Two-column layout: left (document) and right (annotations)
        content_grid = dmc.Grid([
            dmc.GridCol([
                dmc.Stack([
                    document_viewer,
                    document_controls
                ], gap="md")
            ], span={"base": 12, "md": 7}),
            dmc.GridCol([
                dmc.Paper(
                    dmc.Stack(annotation_components, gap="md"),
                    p="md",
                    withBorder=True,
                    shadow="sm"
                )
            ], span={"base": 12, "md": 5}),
        ], gutter="xl")

        # Main layout
        self.app.layout = dmc.MantineProvider(
            theme={"colorScheme": self.theme},
            children=[
                # State stores
                dcc.Store(id="current-doc-id", data=self.documents[0].id if self.documents else ""),
                
                dmc.Container([
                    dmc.Stack([
                        # Title
                        dmc.Center(
                            dmc.Title(self.title, order=1, mt="xl")
                        ),

                        # Document info
                        dmc.Stack([
                            dmc.Text(
                                id="document-title",
                                fw=500,
                                size="lg",
                                mb="xs"
                            ),
                            dmc.Progress(
                                id="document-progress",
                                value=0,
                                size="sm",
                                mb="xs"
                            ),
                            dmc.Text(
                                id="document-metadata",
                                size="sm",
                                c="dimmed"
                            ),
                        ]),

                        # Main content grid
                        content_grid,

                        # Save status
                        html.Div(id="save-status", style={"position": "fixed", "top": "20px", "right": "20px", "zIndex": 1000}),

                        # Navigation
                        nav_controls,
                    ], gap="lg")
                ], size="xl", py="xl", fluid=True)
            ]
        )

    def _save_annotations_to_file(self) -> None:
        """Save all annotations to the annotations file."""
        try:
            path = Path(self.annotations_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert Pydantic models to dicts for JSON serialization
            annotations_dict = {}
            for doc_id, annotation in self.annotations.items():
                if isinstance(annotation, BaseModel):
                    annotations_dict[doc_id] = annotation.model_dump()
                else:
                    annotations_dict[doc_id] = annotation
            
            with open(path, 'w') as f:
                json.dump(annotations_dict, f, indent=2)
        except Exception as e:
            print(f"Error saving annotations: {e}")

    def _setup_callbacks(self) -> None:
        """Setup Dash callbacks for interactivity."""
        
        # Track previous doc_id for autosave on navigation
        previous_doc_id = [None]
        
        # Update document display and info
        @self.app.callback(
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
            doc = next((d for d in self.documents if d.id == doc_id), None)
            if not doc:
                return "Document not found", "Error", "", 0
            
            # Load document content
            try:
                content = doc.load_content()
            except Exception as e:
                content = f"Error loading file: {e}"
            
            doc_index = next((i for i, d in enumerate(self.documents) if d.id == doc_id), 0)
            title = f"Document {doc_index + 1} of {len(self.documents)}"
            
            # Format metadata from document info dict (without document count)
            metadata_parts = []
            if doc.info:
                for key, value in doc.info.items():
                    metadata_parts.append(f"{key}: {value}")
            metadata = " | ".join(metadata_parts) if metadata_parts else ""
            
            progress = ((doc_index + 1) / len(self.documents)) * 100 if self.documents else 0
            
            return content, title, metadata, progress

        # Autosave and navigation buttons
        @self.app.callback(
            Output("current-doc-id", "data"),
            Output("save-status", "children"),
            [Input("btn-prev", "n_clicks"),
             Input("btn-next", "n_clicks")],
            State("current-doc-id", "data"),
            prevent_initial_call=True
        )
        def navigate(prev_clicks, next_clicks, current_doc_id):
            from dash import ctx, no_update
            
            if not ctx.triggered or not self.documents:
                return current_doc_id, no_update
            
            # Find current index from current doc_id
            current_index = next((i for i, d in enumerate(self.documents) if d.id == current_doc_id), 0)
            button_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            if button_id == "btn-prev" and current_index > 0:
                current_index -= 1
            elif button_id == "btn-next" and current_index < len(self.documents) - 1:
                current_index += 1
            
            # Save annotations before navigating
            self._save_annotations_to_file()
            
            # Show save status
            alert = dmc.Alert(
                "Annotations saved",
                title="Saved",
                color="teal",
                withCloseButton=False,
                icon=dmc.Text("✓", size="lg"),
                duration=2000
            )
            
            doc_id = self.documents[current_index].id if current_index < len(self.documents) else ""
            return doc_id, alert

        # Handle flag-document changes
        @self.app.callback(
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
        @self.app.callback(
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

    def _setup_value_capture_callbacks(self) -> None:
        """Setup callbacks to capture widget value changes to annotations store."""
        from dash import ctx
        
        # Collect all widgets that need value capture
        widgets_to_capture = self._collect_value_capture_widgets(self.widgets)
        
        if not widgets_to_capture:
            return
        
        # Create callback for each widget
        for widget in widgets_to_capture:
            self._register_widget_value_capture(widget)

    def _collect_value_capture_widgets(self, widgets: list[TaterWidget]) -> list[TaterWidget]:
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
                if hasattr(widget, 'children') and widget.children:
                    captured.extend(self._collect_value_capture_widgets(widget.children))
            else:
                # Regular value-capturing widget
                captured.append(widget)
        
        return captured

    def _register_widget_value_capture(self, widget: TaterWidget) -> None:
        """Register a callback to capture a widget's value changes."""
        from dash import callback, Input, Output, State
        
        widget_id = widget.component_id
        field_path = widget.field_path
        
        # Callback for updating self.annotations when widget value changes
        @self.app.callback(
            Output(widget_id, "id"),  # Dummy output, just to trigger
            Input(widget_id, "value"),
            State("current-doc-id", "data"),
            prevent_initial_call=True
        )
        def capture_value(value, doc_id):
            if not doc_id:
                return widget_id
            
            if self.schema_model:
                # Using Pydantic models - get or create instance
                if doc_id not in self.annotations:
                    self.annotations[doc_id] = self.schema_model()
                
                # Write directly to the Pydantic instance using setattr
                model = self.annotations[doc_id]
                self._set_model_value(model, field_path, value)
            else:
                # Using plain dicts (fallback)
                if doc_id not in self.annotations:
                    self.annotations[doc_id] = {}
                self._set_nested_value(self.annotations[doc_id], field_path, value)
            
            return widget_id
        
        # Callback for updating widget value when document changes
        @self.app.callback(
            Output(widget_id, "value"),
            Input("current-doc-id", "data"),
            prevent_initial_call=True
        )
        def update_widget_value(doc_id):
            if not doc_id or doc_id not in self.annotations:
                return None
            
            annotation = self.annotations[doc_id]
            return self._get_model_value(annotation, field_path)
    
    def _set_model_value(self, model: BaseModel | dict, path: str, value: Any) -> None:
        """
        Set a value in a Pydantic model using dot notation with proper type handling.
        
        For paths like "pets.0.kind", creates Pet() instances in the list as needed.
        """
        if isinstance(model, dict):
            self._set_nested_value(model, path, value)
            return
        
        keys = path.split('.')
        root_model = model
        current = model
        navigation_stack = []  # Track (parent, key) for type inference
        
        # Navigate to the parent of the target field
        for i, key in enumerate(keys[:-1]):
            navigation_stack.append((current, key))
            
            if key.isdigit():
                # List indexing
                index = int(key)
                if not isinstance(current, list):
                    raise ValueError(f"Cannot index non-list at {'.'.join(keys[:i+1])}")
                
                # Extend list with proper model instances
                while len(current) <= index:
                    item_to_append = self._create_list_item(current, navigation_stack)
                    current.append(item_to_append)
                
                current = current[index]
            else:
                # Attribute access
                next_value = getattr(current, key, None)
                
                if next_value is None:
                    # Create the nested structure if the model field exists
                    if hasattr(current, 'model_fields'):
                        field_info = current.model_fields.get(key)
                        if field_info:
                            # Determine what type to create
                            if hasattr(field_info.annotation, '__args__'):
                                # It's a generic type like List, create empty list
                                setattr(current, key, [])
                                next_value = getattr(current, key)
                            else:
                                raise ValueError(f"Cannot create field {key}")
                        else:
                            raise ValueError(f"Field {key} not in model")
                    else:
                        raise ValueError(f"Cannot navigate through non-model")
                current = next_value
        
        # Now set the final value
        final_key = keys[-1]
        
        if final_key.isdigit():
            # Setting a list element
            index = int(final_key)
            if not isinstance(current, list):
                raise ValueError(f"Cannot index non-list")
            while len(current) <= index:
                current.append(None)
            current[index] = value
        else:
            # Setting a model/dict attribute
            if isinstance(current, BaseModel):
                setattr(current, final_key, value)
            elif isinstance(current, dict):
                current[final_key] = value
            else:
                raise ValueError(f"Cannot set attribute on {type(current)}")
    
    def _create_list_item(self, list_parent: list, navigation_stack: list) -> Any:
        """
        Determine what type of object should be appended to a list.
        
        Infers from parent model's field annotations if possible.
        """
        if not navigation_stack or not isinstance(navigation_stack[0][0], BaseModel):
            return {}  # Default to dict
        
        # Walk back to find the field that defines this list type
        root_model, first_key = navigation_stack[0]
        
        if hasattr(root_model, 'model_fields'):
            field_info = root_model.model_fields.get(first_key)
            if field_info and hasattr(field_info.annotation, '__args__'):
                # Get the inner type from List[ItemType]
                item_type = field_info.annotation.__args__[0]
                if isinstance(item_type, type) and issubclass(item_type, BaseModel):
                    try:
                        return item_type()  # Create instance of Pet, etc.
                    except Exception:
                        return {}
        
        return {}  # Fallback to dict
    
    def _get_model_value(self, model: BaseModel | dict, path: str) -> Any:
        """
        Get a value from a Pydantic model or dict using dot notation.
        
        For Pydantic models, uses getattr.
        """
        if isinstance(model, dict):
            return self._get_nested_value(model, path)
        
        keys = path.split('.')
        current = model
        
        for key in keys:
            if current is None:
                return None
            
            if key.isdigit():
                # List index
                index = int(key)
                if isinstance(current, list):
                    current = current[index] if index < len(current) else None
                else:
                    return None
            else:
                # Object attribute - use getattr for Pydantic
                if isinstance(current, BaseModel):
                    current = getattr(current, key, None)
                elif isinstance(current, dict):
                    current = current.get(key)
                elif isinstance(current, list):
                    # Shouldn't happen but handle gracefully
                    return None
                else:
                    return None
        
        return current
    
    def _get_nested_value(self, obj: Any, path: str) -> Any:
        """Get a value from a nested structure using dot notation (e.g., 'pets.0.kind')."""
        keys = path.split('.')
        current = obj
        
        for key in keys:
            if current is None:
                return None
            
            # Handle Pydantic model
            if isinstance(current, BaseModel):
                current = getattr(current, key, None)
            # Handle dict
            elif isinstance(current, dict):
                current = current.get(key)
            # Handle list
            elif isinstance(current, list):
                try:
                    index = int(key)
                    current = current[index] if index < len(current) else None
                except (ValueError, IndexError):
                    return None
            else:
                return None
        
        return current
    
    def _set_nested_value(self, obj: dict, path: str, value: Any) -> None:
        """Set a value in a nested dict structure using dot notation (e.g., 'pets.0.kind')."""
        keys = path.split('.')
        current = obj
        
        for i, key in enumerate(keys[:-1]):
            # Create intermediate structures if needed
            if key not in current:
                # Check if next key is numeric (list index)
                next_key = keys[i + 1]
                if next_key.isdigit():
                    current[key] = []
                else:
                    current[key] = {}
            
            current = current[key]
            
            # Handle list index
            if isinstance(current, list):
                next_key = keys[i + 1]
                if next_key.isdigit():
                    index = int(next_key)
                    # Extend list if needed
                    while len(current) <= index:
                        current.append({})
        
        # Set the final value
        final_key = keys[-1]
        if isinstance(current, list):
            index = int(final_key)
            while len(current) <= index:
                current.append(None)
            current[index] = value
        else:
            current[final_key] = value

    def run(self, debug: bool = False, port: int = 8050, host: str = "127.0.0.1") -> None:
        """
        Start the Dash development server.

        Args:
            debug: Enable debug mode
            port: Port number
            host: Host address
        """
        self.app.run(debug=debug, port=port, host=host)
