"""Main TaterApp application class."""
from typing import Optional, Type, Any
from pathlib import Path
import json

from dash import Dash
from tater.ui import layout
from pydantic import BaseModel, ValidationError

from tater.models import Document
from tater.widgets.base import TaterWidget
from tater.ui import callbacks
from tater.ui import value_helpers


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
        self.app.layout = layout.build_layout(self)

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
        callbacks.setup_callbacks(self)

    def _setup_value_capture_callbacks(self) -> None:
        """Setup callbacks to capture widget value changes to annotations store."""
        callbacks.setup_value_capture_callbacks(self)

    def _collect_value_capture_widgets(self, widgets: list[TaterWidget]) -> list[TaterWidget]:
        """
        Recursively collect all widgets that capture values (non-containers).
        
        Skips GroupWidget children (processes them recursively instead).
        Skips ListableWidget item widgets - ListableWidget handles its own value capture.
        """
        return callbacks._collect_value_capture_widgets(widgets)

    def _register_widget_value_capture(self, widget: TaterWidget) -> None:
        """Register a callback to capture a widget's value changes."""
        callbacks._register_widget_value_capture(self, widget)
    
    def _set_model_value(self, model: BaseModel | dict, path: str, value: Any) -> None:
        """Set a value in a Pydantic model/dict using dot notation."""
        value_helpers.set_model_value(model, path, value)
    
    def _create_list_item(self, list_parent: list, navigation_stack: list) -> Any:
        """Determine list item type for nested model path expansion."""
        return value_helpers.create_list_item(navigation_stack)
    
    def _get_model_value(self, model: BaseModel | dict, path: str) -> Any:
        """Get a value from a Pydantic model/dict using dot notation."""
        return value_helpers.get_model_value(model, path)
    
    def _get_nested_value(self, obj: Any, path: str) -> Any:
        """Get a value from a nested structure using dot notation."""
        return value_helpers.get_nested_value(obj, path)
    
    def _set_nested_value(self, obj: dict, path: str, value: Any) -> None:
        """Set a value in a nested dict/list structure using dot notation."""
        value_helpers.set_nested_value(obj, path, value)

    def run(self, debug: bool = False, port: int = 8050, host: str = "127.0.0.1") -> None:
        """
        Start the Dash development server.

        Args:
            debug: Enable debug mode
            port: Port number
            host: Host address
        """
        self.app.run(debug=debug, port=port, host=host)
