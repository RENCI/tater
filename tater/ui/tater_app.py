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
        annotations_path: str = "annotations.json",
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
        # Create annotation fields from widgets
        annotation_fields = []
        for widget in self.widgets:
            if widget.renders_own_label:
                field_container = widget.component()
            else:
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
                    dcc.Store(id="current-doc-id", data=self.documents[0].id if self.documents else ""),
                ], size="lg", pt="md")
            ]
        )

    def _setup_callbacks(self) -> None:
        """Setup Dash callbacks for interactivity."""
        
        # Update document display
        @self.app.callback(
            [Output("document-content", "children"),
             Output("doc-counter", "children")],
            Input("current-doc-id", "data")
        )
        def update_document(doc_id):
            if not doc_id:
                return "No document loaded", "No documents"
            
            # Find document by ID
            doc = next((d for d in self.documents if d.id == doc_id), None)
            if not doc:
                return "Document not found", "Error"
            
            # Load document content
            try:
                content = doc.load_content()
            except Exception as e:
                content = f"Error loading file: {e}"
            
            doc_index = next((i for i, d in enumerate(self.documents) if d.id == doc_id), 0)
            counter_text = f"Document {doc_index + 1} of {len(self.documents)}"
            return content, counter_text

        # Navigation buttons
        @self.app.callback(
            [Output("current-doc-index", "data"),
             Output("current-doc-id", "data")],
            [Input("btn-prev", "n_clicks"),
             Input("btn-next", "n_clicks")],
            State("current-doc-index", "data"),
            prevent_initial_call=True
        )
        def navigate(prev_clicks, next_clicks, current_index):
            from dash import ctx
            
            if not ctx.triggered:
                return current_index, ""
            
            button_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            if button_id == "btn-prev" and current_index > 0:
                current_index -= 1
            elif button_id == "btn-next" and current_index < len(self.documents) - 1:
                current_index += 1
            
            doc_id = self.documents[current_index].id if self.documents and current_index < len(self.documents) else ""
            return current_index, doc_id

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
