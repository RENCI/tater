# Tater

![tater-icon](tater/ui/assets/tater-icon-128x128.png)

A Python library for building document annotation interfaces with [Pydantic](https://docs.pydantic.dev/) and [Dash](https://dash.plotly.com/).

Define your annotation schema as a Pydantic model, pick widgets, and get a web-based annotation app with auto-save, progress tracking, and document navigation.

## Installation
Install via `pip`, or `uv` (recommended)

### pip

```bash
pip install .
```

For development (editable install):

```bash
pip install -e .
```

### uv

```bash
uv sync
```
By default, uv will create a virtual environment in `.venv`. To activiate it:
```
source .venv/bin/activate
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
    {"id": "sentiment", "type": "choice", "options": ["positive", "negative", "neutral"], "required": true},
    {"id": "is_relevant", "type": "boolean"}
  ]
}
```

```bash
tater --schema my_schema.json --documents data/documents.json
```

Example configs and schemas are in [apps/](apps/).

## Python config reference

A config file is a plain Python module. The `tater` CLI looks for these names:

| Name | Required | Description |
|------|----------|-------------|
| `Schema` | **yes** | Pydantic `BaseModel` subclass defining the annotation fields |
| `widgets` | no | List of `TaterWidget` instances. Omit to auto-generate all; supply a partial list to override specific fields and auto-generate the rest |
| `title` | no | App window title (default: `"tater - document annotation"`) |
| `description` | no | Subtitle shown below the title |
| `theme` | no | `"light"` or `"dark"` (default: `"light"`) |
| `on_save` | no | Callable `(doc_id: str, annotation: BaseModel) -> None` called after each auto-save |
| `configure` | no | Callable `(app: TaterApp) -> None` called after widgets are registered; use for custom Dash callbacks |

## JSON schema reference

A JSON schema file has this top-level structure:

```json
{
  "spec_version": "1.0",
  "title": "My Annotator",
  "description": "Optional subtitle",
  "hierarchies": {
    "ontology": "path/to/ontology.yaml"
  },
  "data_schema": [ ... ]
}
```

| Key | Required | Description |
|-----|----------|-------------|
| `spec_version` | **yes** | Must be `"1.0"` |
| `data_schema` | **yes** | Array of field definitions |
| `title` | no | App window title |
| `description` | no | Subtitle shown below the title |
| `hierarchies` | no | Map of named hierarchies (YAML file path or inline dict) used by `hierarchical_label` fields |

### Field definition

Every entry in `data_schema` (and `item_fields` / `fields` for list/group types) has:

| Key | Required | Description |
|-----|----------|-------------|
| `id` | **yes** | Field name (used as Pydantic field name and widget ID) |
| `type` | **yes** | Field type — see table below |
| `label` | no | Display label (defaults to humanized `id`) |
| `description` | no | Help text shown below the widget |
| `required` | no | `true` marks the field as required for completion tracking |
| `widget` | no | Object with widget-type overrides — see per-type notes below |

### Field types

| `type` | Schema type | Default widget | Widget overrides (`widget.type`) |
|--------|-------------|----------------|----------------------------------|
| `choice` | `Literal[...]` | `SegmentedControlWidget` | `radio_group`, `select`, `chip_radio` |
| `multi_choice` | `list[Literal[...]]` | `MultiSelectWidget` | `checkbox_group` |
| `text` | `str` | `TextInputWidget` | `text_area` |
| `boolean` | `bool` | `CheckboxWidget` | `switch`, `chip_boolean` |
| `numeric` | `float` | `NumberInputWidget` | `slider` |
| `range_slider` | `Optional[list[float]]` | `RangeSliderWidget` | — |
| `span_annotation` | `list[SpanAnnotation]` | `SpanAnnotationWidget` | — |
| `hierarchical_label` | `Optional[str]` | `HierarchicalLabelCompactWidget` | `hierarchical_label_full`, `hierarchical_label_tags` |
| `group` | nested model | `GroupWidget` | — |
| `listable` | `list[model]` | `ListableWidget` | `tabs`, `accordion` |
| `divider` | — | `DividerWidget` | — |

**`choice` / `multi_choice`** — requires `options` array.

**`numeric` / `range_slider`** — `widget` may include `min_value`, `max_value`, `step`.

**`text`** — `widget` may include `placeholder`.

**`radio_group`** — `widget.orientation`: `"vertical"` or `"horizontal"`.

**`hierarchical_label`** — requires `hierarchy_ref` matching a key in `hierarchies`. `widget` may include `searchable` (default `true`).

**`span_annotation`** — requires `entity_types` array of strings.

**`group`** — requires `fields` array of child field definitions.

**`listable`** — requires `item_fields` array of child field definitions. `widget` may include `add_label`, `delete_label`, `initial_count`. Use `widget.type: "tabs"` or `"accordion"` for alternative layouts.

**`divider`** — no `id` required. Optional `label` and `description`. Does not contribute to the annotation model.

## Widgets

Widgets are linked to Pydantic model fields by `schema_field`. Options for choice widgets are
inferred from the field's `Literal` type — no manual list needed.

All widgets accept `label`, `description`, and most accept `required`.

### Boolean

| Widget | Schema type | Notes |
|--------|-------------|-------|
| `CheckboxWidget` | `bool` | |
| `SwitchWidget` | `bool` | Toggle switch |
| `ChipWidget` | `bool` | Single toggleable chip |

### Single choice

| Widget | Schema type | Notes |
|--------|-------------|-------|
| `SegmentedControlWidget` | `Literal[...]` | Horizontal button group |
| `RadioGroupWidget` | `Literal[...]` | Radio buttons; `vertical=True` supported |
| `SelectWidget` | `Literal[...]` | Searchable dropdown |
| `ChipRadioWidget` | `Literal[...]` | Chip-style radio buttons; `vertical=True` supported |

### Multiple choice

| Widget | Schema type | Notes |
|--------|-------------|-------|
| `MultiSelectWidget` | `list[Literal[...]]` | Searchable multi-select dropdown |
| `CheckboxGroupWidget` | `list[Literal[...]]` | Checkbox group; `vertical=True` supported |

### Numeric

| Widget | Schema type | Extra params |
|--------|-------------|--------------|
| `NumberInputWidget` | `int` / `float` | `min_value`, `max_value`, `step` |
| `SliderWidget` | `int` / `float` | `min_value`, `max_value`, `step` |
| `RangeSliderWidget` | `Optional[list[float]]` | `min_value`, `max_value`, `step` |

### Text

| Widget | Schema type | Extra params |
|--------|-------------|--------------|
| `TextInputWidget` | `str` | `placeholder` |
| `TextAreaWidget` | `str` | `placeholder` |

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

**`ListableWidget`** — repeatable list of sub-widgets for `list[SomeModel]` fields, rendered as a vertical stack of cards:
```python
ListableWidget("findings", label="Findings", item_label="Finding", item_widgets=[
    RadioGroupWidget("label", label="Label"),
])
```

**`TabsWidget`** — same as `ListableWidget` but items are shown as switchable tabs.

**`AccordionWidget`** — same as `ListableWidget` but items are shown as collapsible accordion panels.

### Divider

**`DividerWidget`** — a labeled horizontal rule for visually separating sections. Has no schema field and contributes nothing to the annotation model:
```python
DividerWidget(label="Clinical Findings")
DividerWidget(label="Demographics", description="Patient background info")
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
from tater.widgets import (
    HierarchicalLabelCompactWidget,
    HierarchicalLabelFullWidget,
    HierarchicalLabelTagsWidget,
    load_hierarchy_from_yaml,
)

ontology = load_hierarchy_from_yaml("data/ontology.yaml")

# Shows only the selected node at each level (compact breadcrumb-style)
HierarchicalLabelCompactWidget("diagnosis", label="Diagnosis", hierarchy=ontology)

# Shows all siblings at every expanded level with a breadcrumb below the search bar
HierarchicalLabelFullWidget("diagnosis", label="Diagnosis", hierarchy=ontology)

# Multi-select: chosen leaves appear as removable pills (field must be Optional[str] per tag)
HierarchicalLabelTagsWidget("tags", label="Tags", hierarchy=ontology)
```

All three accept `searchable=True` (default). Build a tree programmatically with `build_tree(dict_or_list)` or from a YAML file with `load_hierarchy_from_yaml(path)`.

## Document format

JSON file listing documents to annotate:

```json
[
  {"file_path": "data/note_001.txt"},
  {"file_path": "data/note_002.txt", "name": "Patient 2", "info": {"date": "2024-01-15"}}
]
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

## Testing

### Setup

Install dev dependencies (includes `pytest`, `dash[testing]`, and `webdriver-manager`):

```bash
uv sync --group dev
source .venv/bin/activate
```

Browser tests require Google Chrome. Install it once via the `.deb` package:

```bash
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt-get install -f   # resolve any missing dependencies
```

`webdriver-manager` automatically downloads a matching ChromeDriver on first run — no manual driver install needed.

### Running tests

```bash
# Unit and integration tests (fast, no browser)
python -m pytest tests/ --ignore=tests/test_browser.py

# Browser tests (headless Chrome, ~45s)
python -m pytest tests/test_browser.py --headless

# Full suite
python -m pytest tests/ --headless

# With coverage
python -m pytest tests/ --ignore=tests/test_browser.py --cov=tater --cov-report=term-missing
```
