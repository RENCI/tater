# Tater

A Python library for building document annotation interfaces with [Dash](https://dash.plotly.com/) and [Pydantic](https://docs.pydantic.dev/).

Define your annotation schema as a Pydantic model, pick widgets, and get a web-based annotation app with auto-save, progress tracking, and document navigation.

## Installation

```bash
uv sync
```

## Quick Start

Create a Python config file (`my_config.py`):

```python
from typing import Optional, Literal
from pydantic import BaseModel

class Schema(BaseModel):
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    is_relevant: bool = False
```

Run it — widgets are auto-generated from the schema:

```bash
tater --config my_config.py --documents data/documents.json
```

Or specify widgets explicitly:

```python
from typing import Optional, Literal
from pydantic import BaseModel
from tater.widgets import SegmentedControlWidget, CheckboxWidget

class Schema(BaseModel):
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    is_relevant: bool = False

title = "My Annotator"

widgets = [
    SegmentedControlWidget("sentiment", label="Sentiment", required=True),
    CheckboxWidget("is_relevant", label="Relevant?"),
]
```

Alternatively, use a JSON schema file (`my_schema.json`):

```json
{
  "spec_version": "1.0",
  "title": "My Annotator",
  "data_schema": [
    {"id": "sentiment", "type": "single_choice", "options": ["positive", "negative", "neutral"], "required": true},
    {"id": "is_relevant", "type": "boolean"}
  ]
}
```

```bash
tater --schema my_schema.json --documents data/documents.json
```

Example configs and schemas are in [apps/](apps/).

## Widgets

Widgets are linked to Pydantic model fields by `schema_field`. Options for choice widgets are
inferred from the field's `Literal` type — no manual list needed.

All widgets accept `label`, `description`, and most accept `required`.

### Single choice

| Widget | Schema type | Notes |
|--------|-------------|-------|
| `SegmentedControlWidget` | `Literal[...]` | Horizontal button group |
| `RadioGroupWidget` | `Literal[...]` | Radio buttons; `vertical=True` supported |
| `SelectWidget` | `Literal[...]` | Searchable dropdown |

### Multiple choice

| Widget | Schema type | Notes |
|--------|-------------|-------|
| `MultiSelectWidget` | `list[Literal[...]]` | Searchable multi-select dropdown |
| `ChipGroupWidget` | `list[Literal[...]]` | Clickable chip group; `vertical=True` supported |

### Boolean

| Widget | Schema type |
|--------|-------------|
| `CheckboxWidget` | `bool` |
| `SwitchWidget` | `bool` |

### Numeric

| Widget | Schema type | Extra params |
|--------|-------------|--------------|
| `NumberInputWidget` | `int` / `float` | `min_value`, `max_value`, `step` |
| `SliderWidget` | `int` / `float` | `min_value`, `max_value`, `step` |

### Text

| Widget | Schema type | Extra params |
|--------|-------------|--------------|
| `TextInputWidget` | `str` | `placeholder` |

### Containers

**`GroupWidget`** — groups child widgets under a nested Pydantic model field:
```python
class Address(BaseModel):
    city: str
    country: str

class Doc(BaseModel):
    address: Address

GroupWidget("address", label="Location", children=[
    TextInputWidget("address.city", label="City"),
    TextInputWidget("address.country", label="Country"),
])
```

**`ListableWidget`** — repeatable list of sub-widgets for `list[SomeModel]` fields:
```python
ListableWidget("tags", label="Tags", item_widgets=[
    TextInputWidget("tags.$.value", label="Tag"),
])
```

### Span annotation

**`SpanAnnotationWidget`** — highlight text spans and assign entity types. Schema field must be `list[SpanAnnotation]`:

```python
from tater import SpanAnnotation
from tater.widgets import SpanAnnotationWidget, EntityType

SpanAnnotationWidget(
    "entities",
    label="Entities",
    entity_types=[
        EntityType("Medication"),
        EntityType("Diagnosis"),
        EntityType("Symptom"),
    ],
)
```

### Hierarchical label

Navigate a tree hierarchy to select a leaf node. Schema field must be `str` or `Optional[str]`.

```python
from tater.widgets import HierarchicalLabelCompactWidget, HierarchicalLabelFullWidget, load_hierarchy_from_yaml

ontology = load_hierarchy_from_yaml("data/ontology.yaml")

HierarchicalLabelCompactWidget("diagnosis", label="Diagnosis", hierarchy=ontology, searchable=True)
HierarchicalLabelFullWidget("diagnosis", label="Diagnosis", hierarchy=ontology, searchable=True)
```

Build a tree programmatically with `build_tree(dict_or_list)` or from a YAML file with `load_hierarchy_from_yaml(path)`.

## TaterApp

```python
TaterApp(
    title="My App",                # Browser tab title
    theme="light",                 # "light" or "dark"
    schema_model=MyModel,          # Pydantic BaseModel subclass
    annotations_path="out.json",   # Where to save annotations (optional)
)
```

| Method | Description |
|--------|-------------|
| `load_documents(path)` | Load documents from a JSON file. Returns `False` on error. |
| `set_annotation_widgets(widgets)` | Set the widget list (must be called after `load_documents`). |
| `run(debug, port, host)` | Start the Dash server. |

## Document format

JSON file listing documents to annotate:

```json
[
  {"file_path": "data/note_001.txt"},
  {"file_path": "data/note_002.txt", "name": "Patient 2", "info": {"date": "2024-01-15"}}
]
```

Or with a top-level `"documents"` key:
```json
{"documents": [{"file_path": "data/note_001.txt"}]}
```

Each document may have:
- `file_path` (required) — path to a `.txt` file
- `id` — unique string ID (auto-generated as `doc_000`, `doc_001`, … if omitted)
- `name` — display name
- `info` — arbitrary metadata dict shown in the UI

## Annotations file format

Auto-saved JSON keyed by document ID:

```json
{
  "doc_000": {
    "annotations": {"sentiment": "positive", "summary": "Normal findings."},
    "metadata": {"flagged": false, "notes": "", "visited": true, "annotation_seconds": 42.0, "status": "complete"}
  }
}
```

Status values: `"not_started"`, `"in_progress"`, `"complete"`.

## CLI

```
tater --config CONFIG --documents PATH [options]
tater --schema SCHEMA --documents PATH [options]
```

| Flag | Description |
|------|-------------|
| `--config PATH` | Python config file (one of `--config` / `--schema` required) |
| `--schema PATH` | JSON schema file (one of `--config` / `--schema` required) |
| `--documents PATH` | Documents JSON file (required) |
| `--annotations PATH` | Annotations output file (default: `<documents>_annotations.json`) |
| `--port INT` | Server port (default: `8050`) |
| `--host STR` | Bind address (default: `127.0.0.1`) |
| `--debug` | Enable debug/hot-reload mode |

Environment variables: `TATER_PORT`, `TATER_HOST`, `TATER_DEBUG`.

## License

MIT
