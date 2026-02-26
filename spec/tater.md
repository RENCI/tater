# Tater 2.0: Pydantic-First Architecture Specification

## Overview

Tater is a Dash-based web application for document annotation with arbitrary, user-defined data models. The redesigned architecture centers on **Pydantic models as the sole source of truth for data**, eliminating the intermediate `DataField`/`AnnotationSpec` abstraction.

**Key principles:**
- Use arbitrary Pydantic models (flat or deeply nested)
- Validation happens via Pydantic, not via schema layer
- Widget configuration lives in widget classes, not separate config files
- System metadata (flagged, notes, visited) is separate from user data
- Persists as a structured format with document, annotations, and metadata grouped per document

---

## Data Model: Pydantic-First

### User-Provided Data Model

The user defines a Pydantic model representing what they want to annotate:

```python
from pydantic import BaseModel, Field
from typing import Literal

class ReviewAnnotation(BaseModel):
    """User model for annotating reviews."""
    sentiment: Literal["positive", "negative", "neutral"]
    entity_count: int = Field(ge=0, le=100)
    entities: list[str] = Field(default_factory=list)
    notes: str = ""
    needs_review: bool = False
```

**Constraints:**
- Can be arbitrarily nested (e.g., `Address(street: str, city: str)`)
- Can include lists (flat: `list[str]`, or nested: `list[Address]`)
- Can include optional/union types
- System metadata fields (flagged, notes, visited) are **not** part of this model

### System Metadata

Always present, managed by Tater:
```python
class DocumentMetadata(BaseModel):
    flagged: bool = False
    notes: str = ""
    visited: bool = False
```

---

## File Format

**Single JSON file per annotation session**, containing document references, user annotations, and system metadata.

```json
[
  {
    "document": {
      "id": "doc_001",
      "file_path": "data/note_001.txt",
      "name": "Note 1",
      "metadata": null
    },
    "annotations": {
      "sentiment": "positive",
      "entity_count": 5,
      "entities": ["product", "price"],
      "notes": "",
      "needs_review": false
    },
    "document_metadata": {
      "flagged": false,
      "notes": "Good review",
      "visited": true
    }
  },
  {
    "document": {...},
    "annotations": {...},
    "document_metadata": {...}
  }
]
```

---

## Widget System

### Base Widget Class

All widgets are self-contained, configurable in Python:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class TaterWidget(ABC):
    """Base class for all Tater widgets."""
    field_path: str              # e.g., "sentiment", "address.street"
    label: str
    description: Optional[str] = None
    required: bool = False
    
    @property
    def component_id(self) -> str:
        """Return unique component ID for this field."""
        return f"annotation-{self.field_path}"
    
    @abstractmethod
    def component(self) -> Any:
        """Return Dash component (dmc.*)."""
        pass
    
    @abstractmethod
    def to_python_type(self) -> type:
        """Return the Python type this widget produces."""
        pass
```

### Concrete Widget Examples

```python
class SegmentedControlWidget(TaterWidget):
    """Single-choice selection widget."""
    options: list[str]
    
    def __init__(self, field_path: str, label: str, options: list[str], **kwargs):
        super().__init__(field_path=field_path, label=label, **kwargs)
        self.options = options
    
    def component(self):
        return dmc.SegmentedControl(
            id=self.component_id,
            data=[{"label": opt, "value": opt} for opt in self.options],
            value=None,
            fullWidth=True
        )
    
    def to_python_type(self):
        return str

class TextAreaWidget(TaterWidget):
    """Multi-line text input widget."""
    min_rows: int = 3
    max_rows: int = 10
    
    def component(self):
        return dmc.Textarea(
            id=self.component_id,
            label=self.label,
            description=self.description,
            placeholder=f"Enter {self.label.lower()}",
            minRows=self.min_rows,
            maxRows=self.max_rows,
            autosize=True,
            value=""
        )
    
    def to_python_type(self):
        return str

class NumberFieldWidget(TaterWidget):
    """Numeric input with optional min/max."""
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    
    def component(self):
        return dmc.NumberInput(
            id=self.component_id,
            label=self.label,
            description=self.description,
            min=self.min_value,
            max=self.max_value,
            value=0
        )
    
    def to_python_type(self):
        return int

class CheckboxWidget(TaterWidget):
    """Boolean checkbox widget."""
    
    def component(self):
        return dmc.Checkbox(
            id=self.component_id,
            label=self.label,
            description=self.description,
            checked=False
        )
    
    def to_python_type(self):
        return bool
```

### Widget Grouping (Nested Models)

For nested Pydantic models, a `GroupWidget` composes child widgets:

```python
class GroupWidget(TaterWidget):
    """Container for nested model fields."""
    children: list[TaterWidget]
    
    def component(self):
        return dmc.Card(
            [
                dmc.Title(self.label, order=4),
                dmc.Stack([widget.component() for widget in self.children], gap="md")
            ],
            withBorder=True,
            p="md"
        )
```

---

## Application API

### Usage Flow 1: Provide Pydantic Model + Manual Widgets

```python
from tater import TaterApp
from pydantic import BaseModel
from typing import Literal

# Define data model
class ReviewAnnotation(BaseModel):
    sentiment: Literal["positive", "negative", "neutral"]
    entity_count: int
    entities: list[str] = []

# Define widgets manually
widgets = [
    SegmentedControlWidget(
        field_path="sentiment",
        label="Sentiment",
        options=["positive", "negative", "neutral"],
        description="Overall sentiment of the review",
        required=True
    ),
    NumberFieldWidget(
        field_path="entity_count",
        label="Entity Count",
        min_value=0,
        max_value=100,
        required=True
    ),
    TextAreaWidget(
        field_path="entities",
        label="Entities Found",
        description="Comma-separated list of entities"
    )
]

# Create app
app = TaterApp(title="Review Annotation")
app.set_data_model(ReviewAnnotation, widgets=widgets)
app.load_documents("documents.json")
app.run(debug=True, port=8050)
```

### Usage Flow 2: Provide Pydantic Model + Auto-Generate Widgets

```python
app = TaterApp(title="Review Annotation")
app.set_data_model(ReviewAnnotation)  # Auto-generates widgets from model
app.load_documents("documents.json")
app.run(debug=True, port=8050)
```

### TaterApp Interface

```python
class TaterApp:
    """Main Tater application."""
    
    def __init__(self, title: str = "Tater", theme: str = "light"):
        """Initialize the app."""
        self.title = title
        self.theme = theme
        self.app = Dash(__name__)
        self.data_model: Optional[Type[BaseModel]] = None
        self.documents: Optional[DocumentList] = None
        self.widgets: list[TaterWidget] = []
    
    def set_data_model(
        self,
        model_class: Type[BaseModel],
        widgets: Optional[list[TaterWidget]] = None
    ) -> None:
        """
        Set the Pydantic model and optional widget configuration.
        
        Args:
            model_class: Pydantic model class for annotations
            widgets: List of TaterWidget instances. If None, auto-generate.
        """
        self.data_model = model_class
        if widgets is None:
            self.widgets = self._auto_generate_widgets(model_class)
        else:
            self.widgets = widgets
        self._setup_layout_and_callbacks()
    
    def load_documents(self, source: str) -> bool:
        """Load documents and annotations from file or directory."""
        pass
    
    def load_annotations(self, file_path: str) -> bool:
        """Load existing annotations from JSON file."""
        pass
    
    def save_annotations(self, file_path: str) -> bool:
        """Save annotations to JSON file."""
        pass
    
    def run(self, debug: bool = False, port: int = 8050) -> None:
        """Start the development server."""
        pass
    
    def get_current_annotation(self) -> BaseModel:
        """Get the current document's annotation as a validated Pydantic instance."""
        pass
    
    def get_all_annotations(self) -> dict[str, BaseModel]:
        """Get all document annotations keyed by doc ID."""
        pass
    
    def _auto_generate_widgets(self, model_class: Type[BaseModel]) -> list[TaterWidget]:
        """Introspect Pydantic model and generate default widgets."""
        pass
```

---

## Data Flow

### Load Annotations

1. **Read JSON file** → list of {document, annotations, document_metadata} dicts
2. **Split per document:**
   - `document` → (passed to DocumentList)
   - `annotations` → dict, stored in `annotations-store`
   - `document_metadata` → dict, stored in `document-metadata-store`
3. **On navigation:**
   - Restore widgets from `annotations-store[doc_id]`
   - Restore metadata (flagged, notes) from `document-metadata-store[doc_id]`
   - **Validate** user annotations via `data_model.model_validate()`

### Save Annotations

1. **Collect from all stores:**
   - `annotations-store[doc_id]` (user data)
   - `document-metadata-store[doc_id]` (system metadata)
   - `documents` (document info)
2. **Validate:** `data_model.model_validate(annotations-store[doc_id])`
3. **Merge:** Reconstruct {document, annotations, document_metadata} triples
4. **Write JSON file**

### Validation

- **On save:** Pydantic validates user annotations via `model_validate()`
- **On load**: Similar validation when restoring from disk
- **On navigation:** Separate callbacks for annotations vs. metadata (no cross-validation needed)

---

## UI Components

### Navigation & Document Selection

- **Previous/Next buttons**: Navigate by index
- **Document menu**: Dropdown with status badges (Not Started, In Progress, Complete)
- **Hide completed checkbox**: Filter menu to exclude completed documents

### Annotation Panel

- Dynamically generated from `self.widgets`
- For nested models: grouped layout with cards/sections
- Flag checkbox and notes textarea are **always** present (system metadata)

### Status Computation

Status is computed from the Pydantic model validation:
- **Not Started**: Empty/no annotations
- **In Progress**: Some fields filled, or visited
- **Complete**: All required fields have values, validated

---

## Nested Model Example

```python
from pydantic import BaseModel
from typing import Optional

class Address(BaseModel):
    street: str
    city: str
    postal_code: Optional[str] = None

class Entity(BaseModel):
    name: str
    type: str

class DocumentAnnotation(BaseModel):
    entities: list[Entity] = []
    author_location: Optional[Address] = None
    sentiment: Literal["positive", "negative", "neutral"] = "neutral"
```

**Widget structure:**
```python
widgets = [
    # Top-level sentiment
    SegmentedControlWidget(
        field_path="sentiment",
        label="Sentiment",
        options=["positive", "negative", "neutral"]
    ),
    # Nested group: author location
    GroupWidget(
        field_path="author_location",
        label="Author Location",
        children=[
            TextFieldWidget(field_path="author_location.street", label="Street"),
            TextFieldWidget(field_path="author_location.city", label="City"),
            TextFieldWidget(field_path="author_location.postal_code", label="Postal Code")
        ]
    ),
    # List of entities (repeater)
    RepeaterWidget(
        field_path="entities",
        label="Entities",
        child_widgets=[
            TextFieldWidget(field_path="entities.$.name", label="Entity Name"),
            SegmentedControlWidget(
                field_path="entities.$.type",
                label="Entity Type",
                options=["person", "place", "organization"]
            )
        ]
    )
]
```

---

## Callback Structure

### Save Annotations Callback

```python
@app.callback(
    Output("annotations-store", "data"),
    [Input("annotation-sentiment", "value"),
     Input("annotation-entity-count", "value"),
     ...],
    State("current-index-store", "data"),
    State("annotations-store", "data"),
    prevent_initial_call=True
)
def save_annotations(*args):
    """Save user annotations to store, validating against model."""
    values = args[:-2]  # Widget values
    current_index = args[-2]
    annotations_data = args[-1] or {}
    
    doc_key = str(current_index)
    new_annotations = dict(annotations_data.get(doc_key, {}))
    
    for widget, value in zip(self.widgets, values):
        new_annotations[widget.field_path] = value
    
    # Validate via Pydantic
    try:
        self.data_model.model_validate(new_annotations)
    except ValidationError as e:
        # Show error to user, don't update store
        return no_update
    
    updated = dict(annotations_data)
    updated[doc_key] = new_annotations
    return updated
```

### Restore Annotations Callback

```python
@app.callback(
    [Output(widget.component_id, "value") for widget in self.widgets],
    Input("current-index-store", "data"),
    State("annotations-store", "data")
)
def restore_annotations(current_index, annotations_data):
    """Restore widget values from store on navigation."""
    if current_index is None:
        return [None] * len(self.widgets)
    
    doc_key = str(current_index)
    doc_annotations = (annotations_data or {}).get(doc_key, {})
    
    # Validate on load
    try:
        validated = self.data_model.model_validate(doc_annotations)
    except ValidationError:
        # If invalid, return empty
        return [None] * len(self.widgets)
    
    return [doc_annotations.get(widget.field_path) for widget in self.widgets]
```

### Save Document Metadata Callback

```python
@app.callback(
    Output("document-metadata-store", "data"),
    [Input("flag-document", "checked"),
     Input("document-notes", "value")],
    State("current-index-store", "data"),
    State("document-metadata-store", "data"),
    prevent_initial_call=True
)
def save_document_metadata(flagged, notes, current_index, metadata_data):
    """Save system metadata (separate from user annotations)."""
    if current_index is None:
        return no_update
    
    doc_key = str(current_index)
    new_metadata = dict(metadata_data or {})
    new_metadata[doc_key] = {
        "flagged": flagged,
        "notes": notes,
        "visited": True
    }
    return new_metadata
```

---

## Migration Path (V1 → V2)

1. **Archive current code** → `tater_old/`
2. **Create new structure:**
   - `tater/models/` → `annotation_file.py`, `document.py` (unchanged)
   - `tater/widgets/` → Refactored base + widget types
   - `tater/ui/` → Rewritten around new data model
   - `tater/loaders/` → File I/O for new JSON format
3. **Implement in stages:**
   - Stage 1: Widget system + Pydantic support
   - Stage 2: File I/O (merge/split logic)
   - Stage 3: UI callbacks (restore/save)
   - Stage 4: Auto-widget generation
   - Stage 5: Nested model support
4. **Testing:** Unit tests for all widget types, loaders, validation

---

## File Structure (Target)

```
tater/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── document.py          # DocumentList (unchanged)
│   ├── annotation_file.py   # AnnotationFile (new) for JSON format
│   └── __pycache__/
├── widgets/
│   ├── __init__.py
│   ├── base.py              # TaterWidget ABC
│   ├── text_field.py
│   ├── text_area.py
│   ├── number_field.py
│   ├── segmented_control.py
│   ├── radio_group.py
│   ├── checkbox.py
│   ├── group.py             # GroupWidget (nested models)
│   ├── repeater.py          # RepeaterWidget (lists)
│   └── __pycache__/
├── loaders/
│   ├── __init__.py
│   └── annotation_loader.py # Handle merge/split logic
├── ui/
│   ├── __init__.py
│   ├── app.py               # TaterApp (rewritten)
│   ├── cli.py               # CLI interface (might simplify)
│   ├── components.py        # UI components (nav, panels)
│   ├── assets/
│   │   ├── menu_target.css
│   │   └── keyboard_nav.js
│   └── __pycache__/
└── __pycache__/
```

---

## Next Steps

1. **Create `AnnotationFile` model** for JSON persistence
2. **Refactor widget base class** for Pydantic introspection
3. **Implement loader** with merge/split logic
4. **Rewrite TaterApp** callbacks around new structure
5. **Add nested model support** (GroupWidget, RepeaterWidget)
6. **Test with example nested models**
