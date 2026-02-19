# STAND Library Specification

## Executive Summary

**STAND** (STreamlit ANotate Documents) is a Python framework for building customized document annotation applications with arbitrary schemas. It provides a transparent connection between Pydantic data models and Streamlit widgets, enabling rapid development of annotation interfaces with built-in features like widget persistence, timing tracking, document navigation, and annotation export/import.

**Version**: 0.0.0  
**Author**: Iain Carmichael (iain@unc.edu)  
**License**: MIT

---

## 1. Project Structure

### 1.1 Directory Layout

```
stand/
├── setup.py                          # Package installation configuration
├── requirements.txt                  # Python dependencies
├── README.md                         # User-facing documentation
├── stand/                            # Main library package
│   ├── __init__.py                  
│   ├── base.py                       # Core data models (Document, TaskInfo, etc.)
│   ├── load_input.py                 # Document loading and upload functionality
│   ├── load_task.py                  # Task definition loading from .py files
│   ├── download_output.py            # Annotation export functionality
│   ├── doc_navigation.py             # Document navigation controls
│   ├── st_utils.py                   # Streamlit utilities and initialization
│   ├── st_app_widget_utils.py        # Widget setup and annotation schema connection
│   ├── app_layouts.py                # Layout configurations (vertical/side-by-side)
│   ├── app_settings.py               # Application settings models
│   ├── hierarchical_label_utils.py   # Tree/DAG structure for hierarchical labels
│   ├── pause_timer.py                # Timer pause/resume functionality
│   ├── utils.py                      # General utilities
│   ├── local_http_server.py          # Local server utilities
│   ├── open_html_in_browser.py       # Browser integration
│   ├── widgets/                      # Widget components
│   │   ├── __init__.py
│   │   ├── base.py                   # BaseWidget, BaseDataWidget, DataStoreEntry
│   │   ├── simple.py                 # Simple input widgets (text, checkbox, etc.)
│   │   ├── containers.py             # Container widgets (PDMConnectedWidgets, Listable)
│   │   ├── hierarchical_labels.py    # Hierarchical label selection widgets
│   │   ├── text_elements.py          # Text display widgets
│   │   ├── toggle_button.py          # Toggle button widget
│   │   ├── dynamic_widgets.py        # Dynamic widget creation
│   │   └── utils.py                  # Widget utilities
│   └── text_tools/                   # Text processing utilities
│       ├── __init__.py
│       ├── span_processing.py        # Span manipulation (highlight, replace, etc.)
│       ├── span_compare.py           # Span comparison utilities
│       ├── doc_by_section.py         # Document sectioning
│       ├── split_document.py         # Document splitting
│       └── spans/                    # Additional span utilities
├── apps/                             # Example applications
│   ├── annotate_documents/           # Main annotation app
│   │   ├── app.py                    # Primary Streamlit application
│   │   ├── README.md                 # App documentation
│   │   ├── commands.txt              # Common commands
│   │   ├── example_tasks/            # Simple task examples
│   │   │   ├── doc_label_few_categories.py
│   │   │   └── label_doc_complex_schema.py
│   │   ├── pathology/                # Pathology domain tasks
│   │   │   ├── breast_fdx_ontology.yaml
│   │   │   ├── coarse_breast_label_fdx.py
│   │   │   ├── granular_breast_fdx.py
│   │   │   ├── ihc.py
│   │   │   └── spans.py
│   │   └── toy_data/                 # Example data files
│   ├── edit_doc_clf_org_by_label/    # Document classification editor
│   ├── edit_taxonomy/                # Taxonomy editor app
│   ├── label_all_docs_displayed_together/
│   ├── manage_tasks/                 # Task management app
│   └── search_docs/                  # Document search app
├── docs/                             # Documentation and examples
│   ├── simple_doc_annotation_app.py  # Minimal example
│   ├── pydantic_model_connected_to_widgets.py
│   ├── connecting_widgets_to_datastore.py
│   └── widget_persistence.py
└── images/                           # Documentation images
```

---

## 2. Core Dependencies

```
pandas==2.2.3
numpy==2.2.4
matplotlib==3.10.1
pydantic==2.11.3
PyYAML==6.0.2
markdown==3.8
seaborn==0.13.2
openpyxl==3.1.5
streamlit==1.44.1
text_highlighter==0.0.15
streamlit_shortcuts==0.1.9
```

---

## 3. Core Architecture

### 3.1 Design Principles

1. **Pydantic-Streamlit Bridge**: Transparent connection between Pydantic models (annotation schema) and Streamlit widgets (UI)
2. **Widget Persistence**: Solve Streamlit's widget state loss when widgets aren't rendered
3. **Task Definition Pattern**: Each annotation task defined by a single `.py` file with `Schema` and `init_and_connect_widgets()`
4. **Separation of Concerns**: Documents, annotations, extra info (timing, flags) stored separately
5. **Modularity**: Reusable widget components that can be composed for complex schemas

### 3.2 Data Flow

```
User uploads documents (JSON/Excel/JSONL)
            ↓
Load into st.session_state['documents']
            ↓
For each document:
    - Initialize or load Schema (Pydantic model)
    - Create widgets via init_and_connect_widgets()
    - Connect widgets to Schema via DataStoreEntry
            ↓
User interacts with widgets
            ↓
Widget callbacks update Schema automatically
            ↓
Download annotations as JSON (includes documents, annotations, timing, flags)
```

---

## 4. Core Data Models

### 4.1 Base Models (`stand/base.py`)

#### Document
```python
class Document(BaseModel):
    """Represents a single document to annotate"""
    name: Union[str, int]           # Unique identifier
    text: str                        # Document content
    extra_context: Optional[str]     # Additional context (hideable in UI)
```

#### DocumentExtraInfo
```python
class DocumentExtraInfo(BaseModel):
    """Metadata for each document"""
    flag: bool = False               # Mark document for review
    notes: Optional[str] = None      # Annotator notes
    timing: List[dict]               # List of {start, end} timestamp pairs
    has_been_seen: bool = False      # Track if document viewed
```

#### TaskInfo
```python
class TaskInfo(BaseModel):
    """Global task metadata"""
    upload_time: Optional[float]
    n_documents: Optional[int]
    download_time: Optional[float]
    annotator: Optional[str]
    doc_idx_leftoff: Optional[int]   # Resume from this index
```

---

## 5. Widget System

### 5.1 Widget Hierarchy

```
BaseWidget (abstract)
├── BaseDataWidget (abstract)
│   ├── SimpleDataWidget (abstract)
│   │   ├── TextInputWidget
│   │   ├── TextAreaWidget
│   │   ├── NumberInputWidget
│   │   ├── CheckboxWidget
│   │   ├── ToggleButtonWidget
│   │   ├── SelectboxWidget
│   │   ├── MultiselectWidget
│   │   ├── RadioWidget
│   │   ├── SegmentedControlWidget
│   │   ├── SliderWidget
│   │   └── DateInputWidget
│   └── Container Widgets
│       ├── PDMConnectedWidgets      # Connect Pydantic model to multiple widgets
│       ├── Listable                # Arbitrary-length list of sub-widgets
│       ├── Expander                # Collapsible container
│       ├── Columns                 # Multi-column layout
│       └── Tabs                    # Tabbed interface
└── Special Widgets
    ├── HierarchicalLabelWidget     # Tree-based label selection
    ├── SpanAnnotationWidget        # Text span tagging
    └── TextDisplayWidget           # Read-only text display
```

### 5.2 Widget Base Classes (`stand/widgets/base.py`)

#### BaseWidget
```python
@dataclass
class BaseWidget:
    """Abstract base for all widgets"""
    
    def render_widget(self):
        """Render the widget in Streamlit"""
        raise NotImplementedError
    
    def set_parent_widget(self, parent: 'BaseWidget'):
        """Set parent container widget"""
        self._parent_widget = parent
    
    def get_parent_widget(self) -> 'BaseWidget':
        """Get parent container widget"""
        return getattr(self, '_parent_widget', None)
```

#### BaseDataWidget
```python
@dataclass
class BaseDataWidget(BaseWidget):
    """Widget that stores/modifies data"""
    # label: str
    # value: Any
    
    def connect_to_store(self, store: Union[BaseModel, dict, list], key: str):
        """Connect widget to data store entry"""
        self._store = DataStoreEntry(store=store, key=key)
        self.value = self._store.get()
        return self
```

#### DataStoreEntry
```python
@dataclass
class DataStoreEntry:
    """Wraps a specific entry in a data store (Pydantic/dict/list)"""
    store: Union[BaseModel, dict, list]
    key: Union[str, int]
    
    def get(self):
        """Get current value from store"""
        if isinstance(self.store, (dict, list)):
            return self.store[self.key]
        elif isinstance(self.store, BaseModel):
            return getattr(self.store, self.key)
    
    def update_set(self, value: Any):
        """Update store with new value"""
        if isinstance(self.store, (dict, list)):
            self.store[self.key] = value
        elif isinstance(self.store, BaseModel):
            setattr(self.store, self.key, value)
```

### 5.3 Widget Persistence Mechanism

**Problem**: Streamlit widgets lose state when not rendered (e.g., switching between documents).

**Solution**: Store widget values in `st.session_state` with unique keys.

```python
def register_widget_key(stub: Optional[str] = None) -> str:
    """Generate unique widget key using global counter"""
    overall_widget_idx = st.session_state['_widget_count']
    st.session_state['_widget_count'] += 1
    widget_key = f'widget_{overall_widget_idx}'
    if stub:
        widget_key = f'{widget_key}_{stub}'
    return widget_key

class SimpleDataWidget(BaseDataWidget):
    def store_widget_value_for_persist(self):
        """Callback: store widget value when changed"""
        self.value = st.session_state[self._widget_key]
        if hasattr(self, '_store'):
            self._store.update_set(self.value)
        if self.callback:
            self.callback(self)
    
    def load_widget_value_from_persist(self):
        """Load persisted value before rendering"""
        st.session_state[self._widget_key] = self.value
```

### 5.4 Simple Widgets (`stand/widgets/simple.py`)

Each simple widget follows this pattern:

```python
@dataclass
class TextInputWidget(SimpleDataWidget):
    label: str
    value: str | None = None
    placeholder: str | None = None
    help: str | None = None
    disabled: bool = False
    label_visibility: LabelVisibility = "visible"
    callback: Optional[Callable] = None
    
    def render_widget(self):
        self.register_if_unregistered()      # Create unique key
        self.load_widget_value_from_persist() # Load persisted value
        
        st.text_input(
            label=self.label,
            placeholder=self.placeholder,
            help=self.help,
            disabled=self.disabled,
            label_visibility=self.label_visibility,
            key=self._widget_key,
            on_change=self.store_widget_value_for_persist
        )
```

Implementation for all standard Streamlit input widgets:
- `TextInputWidget`, `TextAreaWidget`
- `NumberInputWidget`, `SliderWidget`
- `CheckboxWidget`, `ToggleButtonWidget`
- `SelectboxWidget`, `MultiselectWidget`, `RadioWidget`
- `SegmentedControlWidget` (custom UI for single/multi-select)
- `DateInputWidget`, `TimeInputWidget`

### 5.5 Container Widgets (`stand/widgets/containers.py`)

#### PDMConnectedWidgets

Connects a Pydantic model to multiple widgets for complex schemas.

```python
@dataclass
class PDMConnectedWidgets(BaseDataWidget):
    """Connect Pydantic model to multiple widgets"""
    widgets: Union[Dict[str, Any], List[Tuple[str, Any]]]
    value: BaseModel
    non_data_widget_keys: List[str] = field(default_factory=list)
    exclude_render_widget_keys: List[str] = field(default_factory=list)
    widget_spacing: WidgetSpacing = field(default_factory=WidgetSpacing)
    indent_prop: Optional[float] = None
    label: Optional[str] = None
    
    def __post_init__(self):
        """Connect each widget to corresponding Pydantic field"""
        for name, widget in self.iter_names_and_widgets():
            widget.set_parent_widget(parent=self)
            if name not in self.non_data_widget_keys:
                widget.connect_to_store(store=self.value, key=name)
    
    def render_widget(self):
        """Render all contained widgets with spacing"""
        if self.label:
            st.markdown(self.label)
        
        render_spacing = self.widget_spacing.get_render_except_first()
        
        for name, widget in self.iter_names_and_widgets():
            if name in self.exclude_render_widget_keys:
                continue
            render_spacing()
            widget.render_widget()
```

**Example Usage**:
```python
class Schema(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    is_active: bool = False

schema = Schema()
widget = PDMConnectedWidgets(
    widgets={
        'name': TextInputWidget(label="Name"),
        'age': NumberInputWidget(label="Age", min_value=0),
        'is_active': CheckboxWidget(label="Active")
    },
    value=schema
)
widget.render_widget()
# schema.name, schema.age, schema.is_active automatically updated
```

#### Listable

Creates arbitrary-length lists of sub-widgets (e.g., multiple pets, multiple tests).

```python
@dataclass
class Listable(BaseDataWidget):
    """Container for arbitrary-length list of sub-widgets"""
    widget: BaseWidget                    # Template widget
    value: List = field(default_factory=list)
    label: Optional[str] = None
    add_label: str = "Add"
    delete_label: str = "Delete"
    min_count: int = 0
    max_count: Optional[int] = None
    render_order_reversed: bool = False
    widget_spacing: WidgetSpacing = field(default_factory=WidgetSpacing)
    
    def render_widget(self):
        """Render add button and all list items"""
        # Add button
        if len(self.value) < self.max_count:
            if st.button(self.add_label):
                new_item = deepcopy(self.widget.value)
                self.value.append(new_item)
                self._store.update_set(self.value)
        
        # Render each list item
        items = reversed(self.value) if self.render_order_reversed else self.value
        for idx, item in enumerate(items):
            widget_copy = deepcopy(self.widget)
            widget_copy.connect_to_store(store=self.value, key=idx)
            widget_copy.render_widget()
            
            # Delete button
            if len(self.value) > self.min_count:
                if st.button(f"{self.delete_label} {idx+1}"):
                    del self.value[idx]
                    self._store.update_set(self.value)
```

**Example Usage**:
```python
class Pet(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None

class Schema(BaseModel):
    pets: List[Pet] = Field(default_factory=list)

pet_widget = PDMConnectedWidgets(
    widgets={
        'name': TextInputWidget(label="Pet Name"),
        'age': NumberInputWidget(label="Pet Age")
    },
    value=Pet()
)

pets_list_widget = Listable(
    widget=pet_widget,
    label="Pets",
    add_label="Add Pet",
    delete_label="Delete Pet"
)
pets_list_widget.connect_to_store(store=schema, key='pets')
```

#### Other Containers

- `Expander`: Collapsible section using `st.expander()`
- `Columns`: Multi-column layout using `st.columns()`
- `Tabs`: Tabbed interface using `st.tabs()`

### 5.6 Hierarchical Label Widget (`stand/widgets/hierarchical_labels.py`)

For tasks with many categories organized in a tree/DAG structure.

```python
@dataclass
class HierarchicalLabelWidget(BaseDataWidget):
    """Tree-based label selection with progressive disclosure"""
    graph: Node                          # Root node of hierarchy
    value: Optional[str] = None          # Selected leaf label
    search_bar: bool = True
    show_leaves_only: bool = True
    
    def render_widget(self):
        """Render hierarchical selection interface"""
        # Start at root, progressively show children
        # Use breadcrumb navigation
        # Support search across all labels
```

Hierarchy defined in YAML:
```yaml
Animals:
  - Mammals:
      - Dogs:
          - Labrador
          - Poodle
      - Cats:
          - Persian
          - Siamese
  - Birds:
      - Parrot
      - Eagle
```

Loaded into `Node` graph structure defined in `stand/hierarchical_label_utils.py`.

---

## 6. Task Definition System

### 6.1 Task File Format

Each annotation task defined by a `.py` file with required components:

```python
# Required imports
from pydantic import BaseModel
from typing import Optional
from stand.base import Document
from stand.widgets.base import BaseWidget
from stand.widgets.simple import *
from stand.widgets.containers import *

# 1. REQUIRED: Define Schema (Pydantic model)
class Schema(BaseModel):
    """Annotation schema - all fields must have defaults"""
    label: Optional[str] = None
    confidence: Optional[int] = None

# 2. REQUIRED: Define init_and_connect_widgets function
def init_and_connect_widgets(schema: Schema, document: Document) -> BaseWidget:
    """
    Create and connect widgets for this task.
    
    Args:
        schema: Instantiated Schema (fresh or from uploaded annotations)
        document: Document being annotated
    
    Returns:
        Widget (or widget tree) connected to schema
    """
    label_widget = SelectboxWidget(
        label="Label",
        options=["positive", "negative", "neutral"]
    )
    label_widget.connect_to_store(store=schema, key='label')
    
    confidence_widget = SliderWidget(
        label="Confidence",
        min_value=1,
        max_value=5
    )
    confidence_widget.connect_to_store(store=schema, key='confidence')
    
    return PDMConnectedWidgets(
        widgets={'label': label_widget, 'confidence': confidence_widget},
        value=schema
    )

# 3. OPTIONAL: Define instructions (string)
instructions = """
Label each document as positive, negative, or neutral.
Rate your confidence from 1 (low) to 5 (high).
"""

# 4. OPTIONAL: Define instructions_func (callable)
def instructions_func(document: Document) -> str:
    """Dynamic instructions based on document"""
    return f"Annotate document: {document.name}"
```

### 6.2 Task Loading (`stand/load_task.py`)

```python
def load_task_from_py_file(file: Union[str, PathLike, BytesIO]):
    """
    Load task from .py file.
    
    Returns:
        Schema: Pydantic model class
        init_and_connect_widgets: Function to create widgets
        task_instructions: Optional string instructions
        task_instructions_func: Optional function for instructions
    
    Raises:
        TaskPyFileFormatError: If required components missing
    """
    module = load_module(file=file, module_name='task')
    
    # Validate Schema exists and is Pydantic model
    Schema = getattr(module, 'Schema')
    assert issubclass(Schema, BaseModel)
    
    # Validate init_and_connect_widgets exists and is function
    init_and_connect_widgets = getattr(module, 'init_and_connect_widgets')
    assert inspect.isfunction(init_and_connect_widgets)
    
    # Optional components
    instructions = getattr(module, 'instructions', None)
    instructions_func = getattr(module, 'instructions_func', None)
    
    return Schema, init_and_connect_widgets, instructions, instructions_func
```

---

## 7. Document Loading and Management

### 7.1 Input Formats (`stand/load_input.py`)

#### Excel (.xlsx)
```
| Name       | Text                          |
|------------|-------------------------------|
| doc1       | This is the first document    |
| doc2       | This is the second document   |
```

#### JSONL (.jsonl)
```json
{"name": "doc1", "text": "This is the first document"}
{"name": "doc2", "text": "This is the second document"}
```

#### JSON (.json)
```json
{
  "documents": [
    {"name": "doc1", "text": "This is the first document", "extra_context": "..."},
    {"name": "doc2", "text": "This is the second document"}
  ],
  "annotations": [
    {"label": "positive", "confidence": 5},
    null
  ],
  "doc_extra_infos": [
    {"flag": false, "notes": null, "timing": [], "has_been_seen": true},
    {"flag": false, "notes": null, "timing": [], "has_been_seen": false}
  ],
  "task_info": {
    "annotator": "john@example.com",
    "doc_idx_leftoff": 1
  }
}
```

#### Plain Text (.txt)
Single document with name "document".

### 7.2 Document Upload Flow

```python
def render_upload():
    """Render upload interface"""
    st.file_uploader(
        label="Upload documents",
        type=['xlsx', 'json', 'txt', 'jsonl'],
        key="documents_uploader",
        on_change=load_from_st_upload
    )
    st.button(
        label="Load example documents",
        on_click=load_example_docs
    )

def load_from_st_upload():
    """Handle file upload"""
    file = st.session_state['documents_uploader']
    documents, annotations, doc_extra_infos, task_info = load(file)
    initialize_st_session_state(documents, annotations, doc_extra_infos, task_info)

def initialize_st_session_state(documents, annotations, doc_extra_infos, task_info):
    """Initialize session state after upload"""
    # Convert to Pydantic models
    documents = [Document.parse_obj(doc) for doc in documents]
    doc_extra_infos = [DocumentExtraInfo.parse_obj(dei) if dei else DocumentExtraInfo() 
                       for dei in doc_extra_infos]
    task_info = TaskInfo.parse_obj(task_info) if task_info else TaskInfo()
    
    # Store in session state
    st.session_state['documents'] = documents
    st.session_state['annotations'] = annotations
    st.session_state['doc_extra_infos'] = doc_extra_infos
    st.session_state['task_info'] = task_info
    st.session_state['first_render'] = [True] * len(documents)
```

---

## 8. Document Navigation

### 8.1 Navigation Controls (`stand/doc_navigation.py`)

```python
def render_current_doc_navigation(
    on_change_callback: Optional[Callable] = None,
    doc_timing: bool = True
):
    """Render navigation controls for current document"""
    
    # Three columns: Previous | Dropdown | Next
    prev_col, select_col, next_col = st.columns(3, gap='large')
    
    with prev_col:
        button(
            label="Previous document (←)",
            shortcut='ArrowLeft',
            disabled=st.session_state.doc_idx == 0,
            on_click=on_click_prev_doc_button,
            args=(on_change_callback, doc_timing)
        )
    
    with select_col:
        st.selectbox(
            label="Select a document",
            options=st.session_state['doc_names'],
            format_func=lambda name: f"({doc_idx+1}/{n_docs}) {name}",
            on_change=on_change_select_doc_menu,
            args=(on_change_callback, doc_timing)
        )
    
    with next_col:
        button(
            label="Next document (→)",
            shortcut='ArrowRight',
            disabled=st.session_state.doc_idx == len(st.session_state.documents) - 1,
            on_click=on_click_next_doc_button,
            args=(on_change_callback, doc_timing)
        )

def on_click_next_doc_button(on_change_callback=None, doc_timing=True):
    """Navigate to next document"""
    if doc_timing:
        end_doc_timer(st.session_state.doc_idx)
    
    st.session_state.doc_idx += 1
    st.session_state.selector_idx += 1  # Force dropdown re-render
    
    if on_change_callback:
        on_change_callback()
    
    if doc_timing:
        start_doc_timer(st.session_state.doc_idx)
```

### 8.2 Document Timing

```python
def start_doc_timer(doc_idx: int):
    """Start timing annotation for document"""
    from time import time
    st.session_state['doc_extra_infos'][doc_idx].timing.append({'start': time()})
    st.session_state['doc_extra_infos'][doc_idx].has_been_seen = True

def end_doc_timer(doc_idx: int):
    """End timing for document"""
    from time import time
    timing_list = st.session_state['doc_extra_infos'][doc_idx].timing
    if timing_list and 'end' not in timing_list[-1]:
        timing_list[-1]['end'] = time()

def pause_annotating_current_document():
    """Pause annotation (stop timer, hide content)"""
    end_doc_timer(st.session_state.doc_idx)
    st.session_state['app_is_paused'] = True
    st.button("Resume annotating", on_click=resume_annotating_current_document)

def resume_annotating_current_document():
    """Resume annotation"""
    st.session_state['app_is_paused'] = False
    start_doc_timer(st.session_state.doc_idx)
```

---

## 9. Annotation Download and Export

### 9.1 Download Interface (`stand/download_output.py`)

```python
def render_download(end_current_doc_timer: bool = True, add_timestamp: bool = True):
    """Render download interface"""
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Create download", disabled=st.session_state.get('download_enabled')):
            if end_current_doc_timer:
                end_doc_timer(st.session_state.doc_idx)
            download_enabled = True
    
    if download_enabled:
        download = create_download(exclude_docs=False)
        download_fname = get_download_fname(add_timestamp=add_timestamp)
    
    with col3:
        st.download_button(
            label="Download",
            data=download,
            file_name=download_fname,
            mime="application/json",
            disabled=not download_enabled
        )

def create_download(exclude_docs: bool = False) -> str:
    """Create JSON string for download"""
    
    # Convert Pydantic models to dicts
    documents = [doc.model_dump() for doc in st.session_state['documents']]
    doc_extra_infos = [dei.model_dump() for dei in st.session_state['doc_extra_infos']]
    task_info = st.session_state['task_info'].model_dump()
    task_info['download_time'] = time()
    task_info['doc_idx_leftoff'] = st.session_state['doc_idx']
    
    annotations = []
    for annot in st.session_state['annotations']:
        if isinstance(annot, BaseModel):
            annotations.append(annot.model_dump())
        else:
            annotations.append(annot)
    
    output = {
        'annotations': annotations,
        'doc_extra_infos': doc_extra_infos,
        'task_info': task_info
    }
    
    if not exclude_docs:
        output['documents'] = documents
    
    return json.dumps(output, indent=2)
```

### 9.2 Save to Disk

```python
def save_to_disk(save_fpath: str, end_current_doc_timer: bool = True):
    """Save annotations to file"""
    if end_current_doc_timer:
        end_doc_timer(st.session_state.doc_idx)
    
    download = create_download(exclude_docs=False)
    
    with open(save_fpath, 'w') as f:
        f.write(download)
```

---

## 10. Main Application Flow

### 10.1 App Entry Point (`apps/annotate_documents/app.py`)

```python
import streamlit as st
import argparse
from stand.load_input import render_upload, load_from_fpath
from stand.download_output import render_download
from stand.doc_navigation import render_current_doc_navigation
from stand.load_task import load_task_from_py_file
from stand.st_utils import initialze_states
from stand.st_app_widget_utils import setup_annotation_schema_and_connected_widgets

# 1. PARSE COMMAND LINE ARGUMENTS (once)
if '_has_been_initialized' not in st.session_state:
    parser = argparse.ArgumentParser()
    parser.add_argument('--task_fpath', default='example_tasks/doc_label_few_categories.py')
    parser.add_argument('--docs_fpath', default=None)
    parser.add_argument('--save_fpath', default=None)
    parser.add_argument('--annotator', default=None)
    parser.add_argument('--font_size', type=int, default=None)
    parser.add_argument('--scrollable', action='store_true')
    parser.add_argument('--start_from_leftoff', action='store_true')
    args = st_parse_args(parser)
    
    # Load task
    Schema, init_and_connect_widgets, instructions, instructions_func = \
        load_task_from_py_file(args.task_fpath)
    st.session_state['Schema'] = Schema
    st.session_state['init_and_connect_widgets'] = init_and_connect_widgets
    
    # Load documents if provided
    if args.docs_fpath:
        load_from_fpath(args.docs_fpath)

# 2. INITIALIZE SESSION STATE (once)
initialze_states(states_init={
    'doc_idx': 0,
    'next_doc_idx': None,
    'selector_idx': 0,
    'initialized_after_upload': False,
    'app_is_paused': False
})

# 3. UPLOAD DOCUMENTS (if not already done)
if 'documents' not in st.session_state:
    render_upload()
    st.stop()

# 4. INITIALIZE AFTER UPLOAD (once)
if not st.session_state['initialized_after_upload']:
    st.session_state['initialized_after_upload'] = True
    
    # Resume from leftoff if requested
    if args.start_from_leftoff:
        doc_idx_leftoff = st.session_state['task_info'].doc_idx_leftoff
        if doc_idx_leftoff is not None:
            st.session_state['doc_idx'] = doc_idx_leftoff
    
    # Start timer for first document
    start_doc_timer(st.session_state['doc_idx'])

# 5. SETUP ANNOTATION SCHEMA AND WIDGETS FOR CURRENT DOC
if st.session_state['first_render'][st.session_state.doc_idx]:
    setup_annotation_schema_and_connected_widgets(
        doc_idx=st.session_state.doc_idx,
        Schema=st.session_state['Schema'],
        init_and_connect_widgets=st.session_state['init_and_connect_widgets'],
        document=st.session_state['documents'][st.session_state.doc_idx]
    )
    st.session_state['first_render'][st.session_state.doc_idx] = False

# 6. RENDER CURRENT DOCUMENT
current_doc = st.session_state['documents'][st.session_state.doc_idx]
st.header(f"Document: {current_doc.name}", divider=True)

# 7. RENDER LAYOUT (document text + annotation widgets)
current_widget = st.session_state['annotation_widgets'][st.session_state.doc_idx]

if st.session_state['app_settings'].layout == 'side_by_side':
    render_doc_and_annot_side_by_side(current_doc, current_widget)
elif st.session_state['app_settings'].layout == 'vertical':
    render_doc_and_annot_vertical(current_doc, current_widget)

# 8. RENDER NAVIGATION
render_current_doc_navigation(on_change_callback=save_callback, doc_timing=True)

# 9. RENDER DOWNLOAD
render_download(end_current_doc_timer=True, add_timestamp=True)
```

### 10.2 Schema Setup Utility (`stand/st_app_widget_utils.py`)

```python
def setup_annotation_schema_and_connected_widgets(
    doc_idx: int,
    Schema: type[BaseModel],
    init_and_connect_widgets: Callable,
    document: Document
):
    """
    Initialize or load annotation schema and create connected widgets.
    Only called once per document.
    """
    
    # Initialize or load schema
    if st.session_state['annotations'][doc_idx] is None:
        # Fresh annotation
        schema = Schema()
    else:
        # Load existing annotation
        schema = Schema.parse_obj(st.session_state['annotations'][doc_idx])
    
    # Store schema
    st.session_state['annotations'][doc_idx] = schema
    
    # Create and connect widgets
    widget = init_and_connect_widgets(schema=schema, document=document)
    
    # Store widget
    if 'annotation_widgets' not in st.session_state:
        st.session_state['annotation_widgets'] = [None] * len(st.session_state['documents'])
    st.session_state['annotation_widgets'][doc_idx] = widget
```

---

## 11. Layout System

### 11.1 Layout Configurations (`stand/app_layouts.py`)

```python
class DisplayTextConfig(BaseModel):
    """Configuration for text display"""
    font_size: Optional[int] = None
    scrollable: bool = False
    scrollable_min_char: Optional[int] = 5000
    max_height: int = 800
    border: int = 2
    padding: int = 10
    border_radius: int = 1
    
    def get_html(self, text: str) -> str:
        """Generate HTML for styled text display"""
        font_size_style = f"font-size: {self.font_size}px;" if self.font_size else ""
        
        if self.scrollable and len(text) > self.scrollable_min_char:
            scrollable_style = f"""
                max-height: {self.max_height}px;
                overflow-y: auto;
                border: {self.border}px solid #ccc;
                padding: {self.padding}px;
                background-color: #f9f9f9;
                border-radius: {self.border_radius}px;
            """
        else:
            scrollable_style = ""
        
        return f'<div style="{font_size_style} {scrollable_style}">{text}</div>'

def render_doc_and_annot_side_by_side(document, widget):
    """Side-by-side layout"""
    text_col, annot_col = st.columns(spec=st.session_state.app_settings.side_by_side_cols)
    
    with text_col:
        display_text_with_font_size(document.text, st.session_state.app_settings.display_text)
    
    with annot_col:
        widget.render_widget()

def render_doc_and_annot_vertical(document, widget):
    """Vertical layout"""
    display_text_with_font_size(document.text, st.session_state.app_settings.display_text)
    st.divider()
    widget.render_widget()
```

---

## 12. Text Processing Tools

### 12.1 Span Processing (`stand/text_tools/span_processing.py`)

```python
def replace_spans(
    text: str,
    spans: List[Dict],
    replace: Union[Callable, List[str]],
    normalizer: Optional[Callable] = None
) -> Tuple[str, List[Dict]]:
    """
    Replace spans in text with new content.
    
    Args:
        text: Original text
        spans: List of {'start': int, 'end': int, 'text': str} dicts
        replace: Replacement strings or callable(span_text) -> str
        normalizer: Function to normalize text (e.g., html.escape)
    
    Returns:
        new_text: Modified text
        new_spans: Updated span positions
    """
    # Sort spans by start position
    sorted_spans = sorted(spans, key=lambda s: s['start'])
    
    # Validate non-overlapping
    for i in range(len(sorted_spans) - 1):
        assert sorted_spans[i]['end'] <= sorted_spans[i+1]['start']
    
    # Build new text
    new_text_parts = []
    new_spans = []
    offset = 0
    
    for i, span in enumerate(sorted_spans):
        # Add text before span
        new_text_parts.append(text[offset:span['start']])
        
        # Get replacement
        if callable(replace):
            replacement = replace(text[span['start']:span['end']])
        else:
            replacement = replace[i]
        
        # Add replacement
        start_new = len(''.join(new_text_parts))
        new_text_parts.append(replacement)
        end_new = len(''.join(new_text_parts))
        
        new_spans.append({
            'start': start_new,
            'end': end_new,
            'text': replacement
        })
        
        offset = span['end']
    
    # Add remaining text
    new_text_parts.append(text[offset:])
    
    return ''.join(new_text_parts), new_spans

def highlight_spans_html_background_color(
    text: str,
    spans: List[Dict],
    color: Union[str, List[str]] = 'red'
) -> str:
    """Highlight spans with HTML background color"""
    
    def highlight(s: str) -> str:
        return f"<span style='background-color:{color}; color:white;'>{s}</span>"
    
    return replace_spans(
        text=text,
        spans=spans,
        replace=highlight,
        normalizer=html.escape
    )[0]
```

### 12.2 Span Comparison (`stand/text_tools/span_compare.py`)

```python
def compute_span_iou(span1: Dict, span2: Dict) -> float:
    """Compute intersection-over-union for two spans"""
    start_max = max(span1['start'], span2['start'])
    end_min = min(span1['end'], span2['end'])
    
    intersection = max(0, end_min - start_max)
    union = (span1['end'] - span1['start']) + (span2['end'] - span2['start']) - intersection
    
    return intersection / union if union > 0 else 0.0

def match_spans(
    spans_pred: List[Dict],
    spans_true: List[Dict],
    iou_threshold: float = 0.5
) -> Tuple[List, List, List]:
    """
    Match predicted spans to true spans.
    
    Returns:
        matched: List of (pred_idx, true_idx, iou) tuples
        unmatched_pred: Indices of unmatched predictions
        unmatched_true: Indices of unmatched true spans
    """
    # Implementation...
```

---

## 13. Hierarchical Label System

### 13.1 Graph Structure (`stand/hierarchical_label_utils.py`)

```python
class Node(BaseModel):
    """Node in a directed acyclic graph (tree for hierarchical labels)"""
    name: str
    depth: int
    path_to_root: list
    child_nodes: list
    subgraph: Union[list, dict, str]
    bfs_idx: int
    is_leaf: bool
    
    def children_by_name(self) -> dict:
        """Get children as {name: node} dict"""
        return {node.name: node for node in self.child_nodes}
    
    def names_of_children(self) -> List[str]:
        """Get list of child names"""
        return [node.name for node in self.child_nodes]
    
    def subgraph_nodes_bfs_order(self, nodes_to_prune: Optional[List[str]] = None) -> list:
        """Get all nodes in subgraph (BFS order)"""
        nodes_bfs = []
        queue = deque([self])
        
        while queue:
            node = queue.popleft()
            
            if nodes_to_prune and node.name in nodes_to_prune:
                continue
            
            nodes_bfs.append(node)
            queue.extend(node.child_nodes)
        
        return nodes_bfs

def build_graph_from_yaml(yaml_file: str) -> Node:
    """
    Build hierarchical graph from YAML file.
    
    YAML format:
        Root:
          - Child1:
              - Grandchild1
              - Grandchild2
          - Child2:
              - Grandchild3
    """
    with open(yaml_file) as f:
        data = yaml.safe_load(f)
    
    return build_graph_recursive(data, depth=0, path_to_root=[])
```

### 13.2 Hierarchical Widget

```python
@dataclass
class HierarchicalLabelWidget(BaseDataWidget):
    """Progressive disclosure widget for hierarchical labels"""
    graph: Node
    value: Optional[str] = None
    search_bar: bool = True
    show_leaves_only: bool = True
    breadcrumb_navigation: bool = True
    
    def render_widget(self):
        """Render hierarchical selection interface"""
        # Initialize navigation state
        if not hasattr(self, '_current_node'):
            self._current_node = self.graph
        
        # Optional search bar
        if self.search_bar:
            search_query = st.text_input("Search labels")
            if search_query:
                self._render_search_results(search_query)
                return
        
        # Breadcrumb navigation
        if self.breadcrumb_navigation:
            self._render_breadcrumbs()
        
        # Current level options
        children = self._current_node.child_nodes
        for child in children:
            if child.is_leaf or not self.show_leaves_only:
                if st.button(child.name):
                    if child.is_leaf:
                        self.value = child.name
                        self._store.update_set(self.value)
                    else:
                        self._current_node = child
```

---

## 14. Session State Management

### 14.1 Initialization (`stand/st_utils.py`)

```python
def initialze_states(states_init: dict = {}):
    """
    Initialize session state once at app start.
    
    Default initialized states:
        _has_been_initialized: bool
        _persist_widget_store: dict
        _widget_count: int
    """
    if '_has_been_initialized' not in st.session_state:
        st.session_state['_has_been_initialized'] = True
        st.session_state['_persist_widget_store'] = {}
        st.session_state['_widget_count'] = 0
        
        for key, value in states_init.items():
            st.session_state[key] = value

def reset_app():
    """Reset entire app by clearing session state"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
```

### 14.2 Key Session State Variables

```python
# Document data
st.session_state['documents']          # List[Document]
st.session_state['doc_names']          # List[str/int]
st.session_state['doc_name2idx']       # Dict[str/int, int]

# Annotation data
st.session_state['annotations']        # List[Schema | None]
st.session_state['annotation_widgets'] # List[BaseWidget]
st.session_state['doc_extra_infos']    # List[DocumentExtraInfo]
st.session_state['task_info']          # TaskInfo

# Navigation state
st.session_state['doc_idx']            # int - current document index
st.session_state['next_doc_idx']       # int | None
st.session_state['selector_idx']       # int - forces dropdown re-render

# App configuration
st.session_state['Schema']             # Type[BaseModel]
st.session_state['init_and_connect_widgets']  # Callable
st.session_state['app_settings']       # AppSettings
st.session_state['app_is_paused']      # bool

# Widget system
st.session_state['_widget_count']      # int - global widget counter
st.session_state['_persist_widget_store']  # dict - persisted widget values
st.session_state['first_render']       # List[bool] - track first render per doc
```

---

## 15. Advanced Features

### 15.1 Span Annotation

```python
# Task file for span annotation
from text_highlighter import text_highlighter

class Span(BaseModel):
    start: int
    end: int
    text: str
    tag: str

class Schema(BaseModel):
    spans: List[Span] = Field(default_factory=list)

def init_and_connect_widgets(schema: Schema, document: Document) -> BaseWidget:
    # Load span tags from file/session_state
    span_tags = st.session_state.get('span_tags', ['PII', 'SENSITIVE'])
    
    # Render text highlighter
    selected_spans = text_highlighter(
        text=document.text,
        labels=span_tags,
        annotations=schema.spans
    )
    
    # Update schema
    schema.spans = selected_spans
    
    return TextDisplayWidget(value="Use mouse to select text and tag it")
```

### 15.2 Multi-Document Display

```python
# Display multiple documents together for comparison
def render_all_docs_together():
    st.header("All Documents")
    
    for idx, doc in enumerate(st.session_state['documents']):
        with st.expander(f"{doc.name}"):
            st.text(doc.text)
            
            widget = st.session_state['annotation_widgets'][idx]
            widget.render_widget()
```

### 15.3 Dynamic Instructions

```python
# Task file with dynamic instructions
def instructions_func(document: Document) -> str:
    """Generate document-specific instructions"""
    word_count = len(document.text.split())
    
    if word_count < 50:
        return "This is a short document. Label carefully."
    elif word_count > 500:
        return "This is a long document. You may flag for review."
    else:
        return "Standard document. Apply normal labeling criteria."
```

### 15.4 Conditional Widgets

```python
# Show/hide widgets based on other widget values
def init_and_connect_widgets(schema: Schema, document: Document) -> BaseWidget:
    has_pets = CheckboxWidget(label="Has pets?")
    has_pets.connect_to_store(store=schema, key='has_pets')
    
    # Conditional pet list
    widgets = {'has_pets': has_pets}
    
    if schema.has_pets:
        pet_widget = Listable(...)
        pet_widget.connect_to_store(store=schema, key='pets')
        widgets['pets'] = pet_widget
    
    return PDMConnectedWidgets(widgets=widgets, value=schema)
```

---

## 16. App Variants

### 16.1 Edit Taxonomy (`apps/edit_taxonomy/`)

Interactive taxonomy editor:
- Load taxonomy from YAML
- Add/remove/rename nodes
- Reorganize hierarchy
- Export updated YAML

### 16.2 Manage Tasks (`apps/manage_tasks/`)

Multi-task, multi-annotator management:
- Assign tasks to annotators
- Track progress across tasks
- Compute inter-annotator agreement
- Aggregate annotations

### 16.3 Search Documents (`apps/search_docs/`)

Search and filter document corpus:
- Keyword search
- Filter by metadata
- Export filtered subset

---

## 17. Testing and Quality Assurance

### 17.1 Widget Unit Tests

```python
# tests/test_widgets.py
def test_text_input_widget():
    widget = TextInputWidget(label="Test", value="initial")
    
    # Test store connection
    store = {'field': 'old_value'}
    widget.connect_to_store(store=store, key='field')
    assert widget.value == 'old_value'
    
    # Test update
    widget._store.update_set('new_value')
    assert store['field'] == 'new_value'

def test_pdm_connected_widgets():
    class TestSchema(BaseModel):
        name: Optional[str] = None
        age: Optional[int] = None
    
    schema = TestSchema()
    widget = PDMConnectedWidgets(
        widgets={
            'name': TextInputWidget(label="Name"),
            'age': NumberInputWidget(label="Age")
        },
        value=schema
    )
    
    # Verify connections
    assert widget.widgets['name'].value is None
    assert widget.widgets['age'].value is None
```

### 17.2 Integration Tests

```python
# tests/test_app_flow.py
def test_document_upload_and_annotation():
    # Mock file upload
    test_data = {
        'documents': [
            {'name': 'doc1', 'text': 'Test document 1'},
            {'name': 'doc2', 'text': 'Test document 2'}
        ]
    }
    
    # Simulate upload
    documents, annotations, doc_extra_infos, task_info = load(test_data)
    
    assert len(documents) == 2
    assert annotations == [None, None]
    
    # Simulate annotation
    Schema = type('Schema', (BaseModel,), {'label': Optional[str]})
    schema = Schema(label='positive')
    annotations[0] = schema
    
    # Simulate download
    output = create_download(...)
    assert 'annotations' in json.loads(output)
```

---

## 18. Deployment

### 18.1 Local Development

```bash
# Install package
cd /path/to/stand
pip install -e .

# Run app
cd apps/annotate_documents
streamlit run app.py -- --task_fpath example_tasks/doc_label_few_categories.py
```

### 18.2 Streamlit Cloud

```toml
# .streamlit/config.toml
[server]
maxUploadSize = 200

[theme]
primaryColor = "#F63366"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

### 18.3 Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN pip install -e .

EXPOSE 8501

CMD ["streamlit", "run", "apps/annotate_documents/app.py"]
```

---

## 19. Extension Points

### 19.1 Custom Widgets

```python
# my_custom_widget.py
from stand.widgets.base import SimpleDataWidget
import streamlit as st
from dataclasses import dataclass

@dataclass
class ColorPickerWidget(SimpleDataWidget):
    label: str
    value: str = "#000000"
    
    def render_widget(self):
        self.register_if_unregistered()
        self.load_widget_value_from_persist()
        
        st.color_picker(
            label=self.label,
            key=self._widget_key,
            on_change=self.store_widget_value_for_persist
        )
```

### 19.2 Custom Layouts

```python
# my_layout.py
def render_triple_column_layout(document, widget1, widget2):
    doc_col, annot1_col, annot2_col = st.columns(3)
    
    with doc_col:
        st.text(document.text)
    
    with annot1_col:
        widget1.render_widget()
    
    with annot2_col:
        widget2.render_widget()
```

### 19.3 Custom Text Processing

```python
# my_text_processor.py
def preprocess_medical_text(text: str) -> str:
    """Custom preprocessing for medical documents"""
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Expand abbreviations
    abbrev_map = {'pt': 'patient', 'dx': 'diagnosis', ...}
    for abbrev, full in abbrev_map.items():
        text = re.sub(rf'\b{abbrev}\b', full, text, flags=re.IGNORECASE)
    
    return text
```

---

## 20. Performance Optimization

### 20.1 Widget Rendering

- Use `@st.cache_data` for expensive computations
- Minimize widget re-renders via `st.session_state` tracking
- Lazy-load widgets only when document is viewed

### 20.2 Large Document Sets

```python
# Pagination for 1000+ documents
PAGE_SIZE = 50

def get_document_page(page_idx: int) -> List[Document]:
    start = page_idx * PAGE_SIZE
    end = start + PAGE_SIZE
    return st.session_state['all_documents'][start:end]

# Only load current page's widgets
current_page = st.session_state['doc_idx'] // PAGE_SIZE
st.session_state['documents'] = get_document_page(current_page)
```

### 20.3 Caching

```python
@st.cache_data
def load_large_taxonomy(yaml_file: str) -> Node:
    """Cache taxonomy loading"""
    return build_graph_from_yaml(yaml_file)

@st.cache_data
def preprocess_all_documents(documents: List[Dict]) -> List[str]:
    """Cache expensive text preprocessing"""
    return [preprocess_text(doc['text']) for doc in documents]
```

---

## 21. Security Considerations

### 21.1 File Upload Validation

```python
def validate_upload(file):
    """Validate uploaded file"""
    # Check file size
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    if file.size > MAX_FILE_SIZE:
        raise ValueError("File too large")
    
    # Check file type
    allowed_extensions = ['.json', '.xlsx', '.txt', '.jsonl']
    if not any(file.name.endswith(ext) for ext in allowed_extensions):
        raise ValueError("Invalid file type")
    
    # Validate JSON structure
    if file.name.endswith('.json'):
        data = json.load(file)
        if 'documents' not in data:
            raise ValueError("Missing 'documents' key")
```

### 21.2 Data Sanitization

```python
def sanitize_document(doc: dict) -> dict:
    """Sanitize document data"""
    # Strip HTML tags from text
    doc['text'] = strip_tags(doc['text'])
    
    # Validate document name
    doc['name'] = str(doc['name'])[:100]  # Limit length
    
    return doc
```

---

## 22. Accessibility

### 22.1 Keyboard Shortcuts

- Left/Right arrows: Previous/Next document
- Ctrl+S: Create download
- Esc: Pause annotation
- Accessible via `streamlit_shortcuts` library

### 22.2 Screen Reader Support

- Use semantic HTML labels
- Provide `help` text for all widgets
- Use `label_visibility` to control label display

---

## 23. Common Patterns and Best Practices

### 23.1 Task File Template

```python
"""
Task: [Brief description]
Author: [Name]
Date: [Date]
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from stand.base import Document
from stand.widgets.base import BaseWidget
from stand.widgets.simple import *
from stand.widgets.containers import *

# Define schema
class Schema(BaseModel):
    """
    [Description of annotation schema]
    """
    field1: Optional[str] = None
    field2: Optional[int] = None

# Define widget creation
def init_and_connect_widgets(schema: Schema, document: Document) -> BaseWidget:
    """
    [Description of widget interface]
    """
    widget1 = TextInputWidget(label="Field 1")
    widget2 = NumberInputWidget(label="Field 2")
    
    return PDMConnectedWidgets(
        widgets={'field1': widget1, 'field2': widget2},
        value=schema
    )

# Define instructions
instructions = """
[Clear, concise annotation instructions]
"""
```

### 23.2 Error Handling

```python
# In task files
try:
    widget = init_and_connect_widgets(schema, document)
except Exception as e:
    st.error(f"Error creating widgets: {e}")
    widget = TextDisplayWidget(value="Error occurred")

# In app.py
try:
    Schema, init_and_connect_widgets, instructions, instructions_func = \
        load_task_from_py_file(args.task_fpath)
except TaskPyFileFormatError as e:
    st.error(f"Invalid task file: {e}")
    st.stop()
```

### 23.3 Logging

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def on_click_next_doc_button(...):
    logger.info(f"Navigating from doc {st.session_state.doc_idx} to {st.session_state.doc_idx + 1}")
    # ... rest of function
```

---

## 24. Migration and Versioning

### 24.1 Schema Evolution

```python
def migrate_schema_v1_to_v2(old_annotations: List[dict]) -> List[dict]:
    """Migrate annotations from v1 to v2 schema"""
    new_annotations = []
    for annot in old_annotations:
        if annot is None:
            new_annotations.append(None)
            continue
        
        # Add new field with default
        annot['new_field'] = None
        
        # Rename old field
        if 'old_field' in annot:
            annot['new_field_name'] = annot.pop('old_field')
        
        new_annotations.append(annot)
    
    return new_annotations
```

### 24.2 Version Tracking

```python
# In task file
SCHEMA_VERSION = "2.0"

class Schema(BaseModel):
    _version: str = SCHEMA_VERSION
    # ... fields

# In download
output = {
    'schema_version': SCHEMA_VERSION,
    'stand_version': stand.__version__,
    'annotations': annotations,
    # ...
}
```

---

## 25. Future Enhancements

### 25.1 Planned Features

1. **Real-time Collaboration**: Multiple annotators on same document set
2. **Annotation Comparison View**: Side-by-side comparison of annotations
3. **Active Learning Integration**: Prioritize uncertain documents
4. **Export Formats**: CSV, Excel, BRAT, CoNLL
5. **Annotation Statistics Dashboard**: Progress tracking, IAA metrics
6. **Version Control Integration**: Git-based annotation versioning
7. **API Mode**: Headless API for programmatic access

### 25.2 Plugin System

```python
# Future plugin architecture
class StandPlugin:
    def on_document_load(self, document: Document):
        pass
    
    def on_annotation_change(self, annotation: BaseModel):
        pass
    
    def on_download(self, output: dict):
        pass

# Register plugins
st.session_state['plugins'] = [
    AutoSavePlugin(interval=60),
    ValidationPlugin(rules=...),
    AuditLogPlugin(output_file='audit.log')
]
```

---

## 26. Troubleshooting

### 26.1 Common Issues

**Widget not persisting between documents**
- Ensure `register_if_unregistered()` called in `render_widget()`
- Check `store_widget_value_for_persist()` is set as `on_change` callback

**Schema not updating**
- Verify `connect_to_store()` called on widget
- Check Pydantic model field names match widget keys in `PDMConnectedWidgets`

**Task file not loading**
- Ensure `Schema` class and `init_and_connect_widgets` function exist
- Check `Schema()` can be instantiated without arguments

**Navigation not working**
- Verify `doc_navigation_states_init` passed to `initialze_states()`
- Check `start_doc_timer()` called for initial document

### 26.2 Debug Mode

```python
# Enable debug logging
st.session_state['debug_mode'] = True

if st.session_state.get('debug_mode'):
    st.sidebar.write("Debug Info")
    st.sidebar.write(f"doc_idx: {st.session_state.doc_idx}")
    st.sidebar.write(f"widget_count: {st.session_state._widget_count}")
    st.sidebar.write(f"Current annotation: {st.session_state['annotations'][st.session_state.doc_idx]}")
```

---

## 27. Code Organization Guidelines

### 27.1 Module Responsibilities

- `base.py`: Core data models only
- `load_*.py`: Loading/initialization logic
- `download_output.py`: Export logic
- `*_navigation.py`: UI navigation controls
- `widgets/`: Widget components (no business logic)
- `text_tools/`: Pure functions for text processing
- `apps/`: Application entry points

### 27.2 Naming Conventions

- Widgets: `*Widget` (e.g., `TextInputWidget`)
- Data models: Descriptive noun (e.g., `Document`, `TaskInfo`)
- Session state keys: snake_case (e.g., `doc_idx`, `annotation_widgets`)
- Functions: verb_noun (e.g., `load_task`, `render_widget`)

### 27.3 Import Structure

```python
# Standard library
import os
import json
from typing import Optional, List

# Third-party
import streamlit as st
import pandas as pd
from pydantic import BaseModel

# Local - absolute imports from stand
from stand.base import Document
from stand.widgets.simple import TextInputWidget
```

---

## 28. Example: Complete Task File

```python
"""
Task: Medical Report Annotation
Author: Stand Team
Date: 2024-01-15

Annotate medical reports with:
1. Primary diagnosis
2. Severity (1-5 scale)
3. Recommended follow-up actions
4. Confidence in annotation
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from stand.base import Document
from stand.widgets.base import BaseWidget
from stand.widgets.simple import (
    SelectboxWidget, SliderWidget, CheckboxWidget, TextAreaWidget
)
from stand.widgets.containers import PDMConnectedWidgets, Listable, WidgetSpacing

# Define all possible diagnoses
DIAGNOSES = [
    "Hypertension",
    "Diabetes Type 2",
    "Coronary Artery Disease",
    "COPD",
    "Asthma",
    "Other"
]

# Follow-up action schema
class FollowUpAction(BaseModel):
    action: Optional[Literal["Lab Test", "Imaging", "Referral", "Medication Change"]] = None
    description: Optional[str] = None
    urgent: bool = False

# Main annotation schema
class Schema(BaseModel):
    primary_diagnosis: Optional[str] = None
    severity: int = 3
    follow_up_actions: List[FollowUpAction] = Field(default_factory=list)
    notes: Optional[str] = None
    annotation_confidence: int = 3

def init_and_connect_widgets(schema: Schema, document: Document) -> BaseWidget:
    
    # Primary diagnosis dropdown
    diagnosis_widget = SelectboxWidget(
        label="Primary Diagnosis",
        options=DIAGNOSES,
        help="Select the main diagnosis from the report"
    )
    
    # Severity slider
    severity_widget = SliderWidget(
        label="Severity",
        min_value=1,
        max_value=5,
        help="1 = Mild, 5 = Critical"
    )
    
    # Follow-up actions list
    follow_up_action_widget = PDMConnectedWidgets(
        widgets={
            'action': SelectboxWidget(
                label="Action Type",
                options=["Lab Test", "Imaging", "Referral", "Medication Change"]
            ),
            'description': TextAreaWidget(
                label="Description",
                placeholder="Details about this action..."
            ),
            'urgent': CheckboxWidget(
                label="Urgent?"
            )
        },
        value=FollowUpAction(),
        label="Follow-up Action"
    )
    
    follow_up_list_widget = Listable(
        widget=follow_up_action_widget,
        label="Follow-up Actions",
        add_label="Add Action",
        delete_label="Remove Action",
        min_count=0,
        max_count=5,
        widget_spacing=WidgetSpacing(n_breaks=2, divider=True)
    )
    
    # Notes
    notes_widget = TextAreaWidget(
        label="Additional Notes",
        placeholder="Any additional observations...",
        height=150
    )
    
    # Confidence
    confidence_widget = SliderWidget(
        label="Annotation Confidence",
        min_value=1,
        max_value=5,
        help="How confident are you in this annotation?"
    )
    
    # Combine all widgets
    return PDMConnectedWidgets(
        widgets={
            'primary_diagnosis': diagnosis_widget,
            'severity': severity_widget,
            'follow_up_actions': follow_up_list_widget,
            'notes': notes_widget,
            'annotation_confidence': confidence_widget
        },
        value=schema,
        widget_spacing=WidgetSpacing(n_breaks=2, divider=False)
    )

instructions = """
## Medical Report Annotation Instructions

1. **Primary Diagnosis**: Select the main condition discussed in the report
2. **Severity**: Rate from 1 (mild) to 5 (critical)
3. **Follow-up Actions**: List all recommended next steps
   - Mark urgent if time-sensitive
   - Provide clear descriptions
4. **Notes**: Any additional context or uncertainty
5. **Confidence**: Rate your confidence in the annotation (1-5)

**Tips**:
- Read the entire report before annotating
- Check for multiple diagnoses (select primary one)
- Flag uncertain cases for review
"""

def instructions_func(document: Document) -> str:
    """Add document-specific context to instructions"""
    word_count = len(document.text.split())
    return f"Document length: {word_count} words. {'Long report - take your time.' if word_count > 500 else ''}"
```

---

## 29. Conclusion

The STAND library provides a robust, extensible framework for building document annotation applications. Key strengths:

1. **Transparent Schema-Widget Binding**: Pydantic ↔ Streamlit bridge
2. **Widget Persistence**: Solves Streamlit's state management challenges
3. **Modular Design**: Reusable components for complex UIs
4. **Task Definition Pattern**: Single-file task specification
5. **Rich Features**: Timing, navigation, hierarchical labels, span annotation

By following this specification, developers can recreate the STAND library or build compatible extensions and applications.

---

## Appendix A: File-by-File Summary

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `stand/base.py` | Core data models | `Document`, `DocumentExtraInfo`, `TaskInfo` |
| `stand/widgets/base.py` | Widget base classes | `BaseWidget`, `BaseDataWidget`, `DataStoreEntry` |
| `stand/widgets/simple.py` | Simple input widgets | `TextInputWidget`, `SelectboxWidget`, etc. |
| `stand/widgets/containers.py` | Container widgets | `PDMConnectedWidgets`, `Listable` |
| `stand/load_input.py` | Document loading | `load()`, `render_upload()` |
| `stand/load_task.py` | Task loading | `load_task_from_py_file()` |
| `stand/download_output.py` | Export functionality | `create_download()`, `render_download()` |
| `stand/doc_navigation.py` | Navigation controls | `render_current_doc_navigation()` |
| `stand/st_utils.py` | Streamlit utilities | `initialze_states()` |
| `stand/hierarchical_label_utils.py` | Hierarchical labels | `Node`, `build_graph_from_yaml()` |
| `stand/text_tools/span_processing.py` | Span manipulation | `replace_spans()`, `highlight_spans_html_background_color()` |
| `apps/annotate_documents/app.py` | Main application | App entry point |

---

## Appendix B: Glossary

- **Schema**: Pydantic model defining annotation structure
- **Widget**: Streamlit UI component connected to data store
- **Task**: Annotation project defined by Schema + widgets
- **Document**: Text to be annotated
- **Span**: Character range within document text
- **Session State**: Streamlit's persistent storage across reruns
- **Widget Persistence**: Maintaining widget values when not rendered
- **Data Store**: Object holding annotation data (Pydantic/dict/list)
- **Container Widget**: Widget that contains other widgets
- **PDM**: Pydantic Data Model

---

**End of Specification**
