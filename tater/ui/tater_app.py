"""Main TaterApp application class."""
from typing import Optional, Type, Any
from pathlib import Path
import json

from tater.models.document import DocumentMetadata

from dash import Dash
from tater.ui import layout
from pydantic import BaseModel, ValidationError

from tater.models import Document
from tater.widgets.base import TaterWidget
from tater.ui import callbacks
from tater.ui import value_helpers
from tater.ui.hooks import OnSaveHook
from tater.ui.callbacks.helpers import (
    _collect_all_control_templates,
    _collect_value_capture_widgets,
)


def _build_span_color_map(widgets: list, parent_pipe: str = "") -> dict:
    """Build {templatePipePath: {tagName: lightenedColor}} for all SpanAnnotationWidgets.

    templatePipePath has numeric index segments stripped, e.g. "tests|relevant_spans".
    Used by the clientside render callback to look up mark colors without a server call.
    """
    from tater.widgets.span import SpanAnnotationWidget, _lighten_hex
    from tater.widgets.repeater import RepeaterWidget
    from tater.widgets.base import ContainerWidget
    result = {}
    for w in widgets:
        w_pipe = f"{parent_pipe}|{w.schema_field}" if parent_pipe else w.schema_field
        if isinstance(w, SpanAnnotationWidget):
            result[w_pipe] = {et.name: _lighten_hex(et.color) for et in w.entity_types}
        elif isinstance(w, RepeaterWidget):
            result.update(_build_span_color_map(w.item_widgets, w_pipe))
        elif isinstance(w, ContainerWidget) and hasattr(w, "children"):
            result.update(_build_span_color_map(w.children, w_pipe))
    return result


class TaterApp:
    """Main Tater application for document annotation."""

    def __init__(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        annotations_path: Optional[str] = None,
        schema_model: Optional[Type[BaseModel]] = None,
        on_save: Optional[OnSaveHook] = None,
        is_hosted: bool = False,
        dash_app: Optional[Any] = None,
    ):
        """
        Initialize the Tater app.

        Args:
            title: Application title
            description: Optional subtitle shown below the title
            instructions: Optional markdown instructions shown in a help drawer
            annotations_path: Path to save/load annotations
            schema_model: Optional Pydantic model class for annotations
            is_hosted: If True, running in hosted mode (no auto-save, download button shown)
            dash_app: External Dash app to register callbacks on (hosted mode)
        """
        self.title = title or "tater - document annotation"
        self.description = description
        self.instructions = instructions
        self.annotations_path = annotations_path
        self.schema_model = schema_model
        self.on_save = on_save
        self.is_hosted = is_hosted
        self.app = dash_app if dash_app is not None else Dash(__name__, title="tater", suppress_callback_exceptions=True)
        # In hosted mode the shared Dash app carries a callable that resolves
        # the current user's TaterApp from the Flask session at callback runtime.
        self._get_current_app = getattr(self.app, '_tater_get_current_app', None)
        self.widgets: list[TaterWidget] = []
        self.documents: list[Document] = []
        self.current_doc_index = 0
        self.annotations: dict[str, BaseModel] = {}
        # Store metadata (DocumentMetadata) separately from annotations
        from tater.models.document import DocumentMetadata
        self.metadata: dict[str, DocumentMetadata] = {}
        self._save_error: str | None = None
        self._schema_warnings: dict[str, list[str]] = {}

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
            
            if not isinstance(data, list):
                print(f"Error: Invalid document format in {source}")
                return False
            doc_dicts = data
            
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
            
            # Set default annotations path if not provided (skip in hosted mode)
            if self.annotations_path is None and not self.is_hosted:
                doc_path = Path(source)
                self.annotations_path = str(doc_path.parent / f"{doc_path.stem}_annotations.json")
            
            # Load existing annotations if file exists
            self._load_annotations_from_file()

            # Ensure every document has annotation and metadata objects
            for doc in self.documents:
                if self.schema_model and doc.id not in self.annotations:
                    self.annotations[doc.id] = self.schema_model()
                if doc.id not in self.metadata:
                    self.metadata[doc.id] = DocumentMetadata()

            print(f"Loaded {len(self.documents)} documents from {source}")
            return True
        except Exception as e:
            print(f"Error loading documents: {e}")
            return False

    def _collect_all_widgets(self, widgets: list[TaterWidget]) -> list[TaterWidget]:
        """Recursively collect all widgets including nested ones from GroupWidget, ListableWidget, etc."""
        all_widgets = []
        for widget in widgets:
            all_widgets.append(widget)
            # If the widget has children (GroupWidget, ListableWidget), recurse into them
            if hasattr(widget, "children") and widget.children:
                all_widgets.extend(self._collect_all_widgets(widget.children))
        return all_widgets

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

        # Collect all widgets (including nested) for lookup by field_path
        self._all_widgets = self._collect_all_widgets(self.widgets)

        # Cache derived widget-tree lookups used in hot-path callbacks.
        # These are computed once here because the widget tree is immutable
        # after set_annotation_widgets() completes.
        self._ev_lookup: dict[str, object] = {
            w.field_path.replace(".", "|"): w.empty_value
            for w in _collect_all_control_templates(self.widgets)
        }
        self._aa_fields: set[str] = {
            w.field_path
            for w in _collect_value_capture_widgets(self.widgets)
            if w.auto_advance
        }
        self._required_widgets = [
            w for w in _collect_value_capture_widgets(self.widgets)
            if w.required and w.to_python_type() is not bool
        ]
        self._span_color_map: dict = _build_span_color_map(self.widgets)

        # Duplicate field check
        seen: set[str] = set()
        for widget in self._all_widgets:
            path = widget.field_path
            if not path:
                continue
            if path in seen:
                raise ValueError(f"Duplicate widget for schema field '{path}'")
            seen.add(path)

        # Enforce that all schema fields have defaults (required for safe annotation loading)
        if self.schema_model is not None:
            required_fields = [
                name for name, fi in self.schema_model.model_fields.items()
                if fi.is_required()
            ]
            if required_fields:
                raise ValueError(
                    f"All schema model fields must have default values. "
                    f"Fields without defaults: {', '.join(required_fields)}"
                )

        # Bind widgets against the schema model (validates types, derives options)
        if self.schema_model is not None:
            for widget in self.widgets:
                widget.bind_schema(self.schema_model)

        if not self.is_hosted:
            self._setup_layout()

        # In hosted mode the Dash app is shared across sessions; only register
        # callbacks once (the first session sets them up for the shared app).
        _already = self.is_hosted and getattr(self.app, '_tater_callbacks_registered', False)
        if not _already:
            for widget in self.widgets:
                widget.register_callbacks(self.app)
                widget._register_conditional_callbacks(self.app)
            self._setup_callbacks()
            self._setup_value_capture_callbacks()
            self._setup_span_callbacks()
            self._setup_repeater_callbacks()
            self._setup_hl_callbacks()
            if self.is_hosted:
                self.app._tater_callbacks_registered = True

    def _setup_layout(self) -> None:
        """Create the Dash layout with navigation and annotation panel."""
        self.app.layout = layout.build_layout(self)

    def _load_annotations_from_file(self) -> None:
        """Load existing annotations from the annotations file."""
        if not self.annotations_path:
            return
            
        path = Path(self.annotations_path)
        if not path.exists():
            return
            
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            from tater.models.document import DocumentMetadata
            extra_fields: set[str] = set()
            missing_fields: set[str] = set()

            for doc_id, doc_data in data.items():
                ann_data = doc_data.get("annotations", {})
                meta = doc_data.get("metadata", {})
                self.metadata[doc_id] = DocumentMetadata(
                    flagged=meta.get("flagged", False),
                    notes=meta.get("notes", ""),
                    annotation_seconds=meta.get("annotation_seconds", 0.0),
                    visited=meta.get("visited", False),
                    status=meta.get("status", "not_started"),
                )
                if self.schema_model and ann_data:
                    schema_fields = set(self.schema_model.model_fields.keys())
                    ann_fields = set(ann_data.keys())
                    extra_fields |= ann_fields - schema_fields
                    missing_fields |= schema_fields - ann_fields
                    self.annotations[doc_id] = self.schema_model(**ann_data)

            self._schema_warnings = {}
            if extra_fields:
                self._schema_warnings["extra"] = sorted(extra_fields)
            if missing_fields:
                self._schema_warnings["missing"] = sorted(missing_fields)

            print(f"Loaded existing annotations from {self.annotations_path}")
        except Exception as e:
            print(f"Error loading annotations: {e}")

    def _save_stores_to_file(
        self,
        annotations_data: dict,
        metadata_data: dict,
        doc_id: Optional[str] = None,
    ) -> None:
        """Save annotations and metadata from dcc.Store dicts to the annotations file.

        Args:
            annotations_data: {doc_id: annotation_dict} from annotations-store
            metadata_data: {doc_id: metadata_dict} from metadata-store
            doc_id: The document whose annotation triggered this save. When provided
                and an ``on_save`` hook is configured, the hook is called after writing.
        """
        try:
            path = Path(self.annotations_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            save_dict = {}
            all_doc_ids = set(annotations_data or {}) | set(metadata_data or {})
            for d_id in all_doc_ids:
                save_dict[d_id] = {
                    "annotations": (annotations_data or {}).get(d_id, {}),
                    "metadata": (metadata_data or {}).get(d_id, {}),
                }

            with open(path, "w") as f:
                json.dump(save_dict, f, indent=2)
            self._save_error = None

            if self.on_save and doc_id and (annotations_data or {}).get(doc_id) is not None:
                try:
                    if self.schema_model:
                        ann_obj = self.schema_model(**(annotations_data[doc_id]))
                        self.on_save(doc_id, ann_obj)
                except Exception as hook_err:
                    print(f"on_save hook error: {hook_err}")
        except Exception as e:
            self._save_error = str(e)
            print(f"Error saving annotations: {e}")

    def _save_annotations_to_file(self, doc_id: Optional[str] = None) -> None:
        """Save all annotations to the annotations file.

        Args:
            doc_id: The document whose annotation triggered this save.  When
                provided and an ``on_save`` hook is configured, the hook is
                called with this document's annotation after writing.
        """
        try:
            path = Path(self.annotations_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            # Combine annotations and metadata into save format
            save_dict = {}
            for d_id, annotation in self.annotations.items():
                meta: DocumentMetadata = self.metadata.get(d_id, DocumentMetadata())
                save_dict[d_id] = {
                    "annotations": annotation.model_dump(),
                    "metadata": meta.model_dump(),
                }

            with open(path, 'w') as f:
                json.dump(save_dict, f, indent=2)
            self._save_error = None

            if self.on_save and doc_id and doc_id in self.annotations:
                try:
                    self.on_save(doc_id, self.annotations[doc_id])
                except Exception as hook_err:
                    print(f"on_save hook error: {hook_err}")
        except Exception as e:
            self._save_error = str(e)
            print(f"Error saving annotations: {e}")

    def _setup_callbacks(self) -> None:
        """Setup Dash callbacks for interactivity."""
        callbacks.setup_callbacks(self)

    def _setup_value_capture_callbacks(self) -> None:
        """Setup callbacks to capture widget value changes to annotations store."""
        callbacks.setup_value_capture_callbacks(self)

    def _setup_span_callbacks(self) -> None:
        """Setup unified span annotation callbacks."""
        callbacks.setup_span_callbacks(self)

    def _setup_repeater_callbacks(self) -> None:
        """Setup unified MATCH-based repeater callbacks."""
        callbacks.setup_repeater_callbacks(self)
        callbacks.setup_nested_repeater_callbacks(self)

    def _setup_hl_callbacks(self) -> None:
        """Setup unified MATCH-based HierarchicalLabel callbacks."""
        callbacks.setup_hl_callbacks(self)
        callbacks.setup_hl_tags_callbacks(self)

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
    
    def _get_dict_value(self, obj: Any, path: str) -> Any:
        """Get a value from a nested dict/list structure using dot notation."""
        return value_helpers.get_dict_value(obj, path)

    def _set_dict_value(self, obj: dict, path: str, value: Any) -> None:
        """Set a value in a nested dict/list structure using dot notation."""
        value_helpers.set_dict_value(obj, path, value)

    def run(self, debug: bool = False, port: int = 8050, host: str = "127.0.0.1") -> None:
        """Start the Dash development server."""
        self.app.run(debug=debug, port=port, host=host)
