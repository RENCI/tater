# Tater — Developer Notes for Claude

## Project overview

Tater is a Python library for building document annotation UIs. Users provide a config file
(Python or JSON) defining a Pydantic schema and optional widget overrides, then run the `tater`
CLI to launch a Dash web app.

Key stack: Python 3.10+, Dash, **Dash Mantine Components (DMC) v2.6 / Mantine v7**, Pydantic v2.

## Directory layout

```
tater/                  # Library package
  __init__.py           # Public API: SpanAnnotation, SpanAnnotationWidget,
                        #   EntityType, load_schema, parse_schema, widgets_from_model
  models/               # Pydantic data models (Document, SpanAnnotation)
  ui/                   # App machinery (TaterApp, layout, callbacks, value_helpers)
  widgets/              # All widget classes
    base.py             # Widget base class hierarchy (see Widget conventions)
    repeater.py         # RepeaterWidget (abstract), ListableWidget, TabsWidget
    hierarchical_label.py  # HierarchicalLabel* widgets + Node tree utilities
    ...                 # One file per concrete widget (see Widget conventions)
apps/
  examples/
    config/             # Python config-file examples (simple, hooks, span, span_in_list, tabs, …)
    schema/             # JSON schema-file examples
    data/               # Sample documents
  pathology/            # Domain-specific example apps
data/                   # Additional sample documents and ontologies
spec/                   # Design documents (see below)
```

## Running examples

Apps are run via the `tater` CLI, which requires either `--config` (Python) or `--schema` (JSON):

```bash
tater --config apps/examples/config/simple.py --documents data/documents.json
tater --config apps/examples/config/hooks.py  --documents data/documents.json
tater --schema apps/examples/schema/simple.json --documents data/documents.json
```

CLI flags: `--documents` (required), `--config` or `--schema` (one required),
`--annotations`, `--port`, `--host`, `--debug` (also via `TATER_DEBUG` / `TATER_PORT` / `TATER_HOST` env vars).

## Architecture

- **Pydantic-first**: options for choice widgets are inferred from `Literal` types at
  `bind_schema()` time; no manual option lists needed.
- **Widget binding**: each widget has a `schema_field` (dot-path into the model) and a
  `component_id` derived from it. `bind_schema(model)` is called by TaterApp to validate and
  extract metadata.
- **Callbacks**: each widget registers its own Dash callbacks in `register_callbacks(app)`.
  The central `callbacks.py` handles navigation, doc loading, and metadata (flag/notes/status).
- **Persistence**: `TaterApp._save_annotations_to_file()` is called eagerly on every change.
  Format: `{doc_id: {annotations: {...}, metadata: {...}}}`.
- **value_helpers**: `get_model_value` / `set_model_value` in `tater/ui/value_helpers.py`
  handle dot-path reads/writes into nested Pydantic model instances.
- **Flag/notes loading**: `load_flag_and_notes` in `callbacks.py` fires on `current-doc-id`
  change and populates both `flag-document` (checked) and `document-notes` (value) from
  `tater_app.metadata`. This is the only callback that writes to these outputs on navigation —
  the corresponding `save_flag` / `save_notes` callbacks only write on user interaction.

## DMC version constraints

DMC is pinned at **v2.6 (Mantine v7)**. Before using a DMC component, verify it exists in
this version:

- `dmc.TabsTab` is the tab trigger (v2.x API) — `dmc.Tab` does not exist.
- `dmc.Badge(circle=True)` clips double-digit numbers — avoid `circle=True`.
- Component prop names follow Mantine v7 conventions (e.g. `leftSection`/`rightSection`, not
  `icon`).

## Dash callback gotchas

**Pattern-matching phantom fires**: when a callback uses `Input({...}, ALL)` pattern matching,
Dash re-fires the callback when matching components are re-rendered (e.g. after another callback
updates the component tree). Guard against this by checking that the triggered value is non-zero:

```python
if not ctx.triggered or not ctx.triggered[0].get("value"):
    return no_update
```

**`allow_duplicate` must be consistent**: if *any* callback uses
`Output(component_id, prop, allow_duplicate=True)`, then *all* callbacks writing to that same
output must also use `allow_duplicate=True`. Missing it on one will cause Dash to raise a
`DuplicateCallback` error at startup. Two specific outputs in this codebase are affected:

- **`current-doc-id` / `data`** — written by the prev/next buttons and the document-menu
  selector. All three already use `allow_duplicate=True`; any new navigation callback must too.
  See the comment block on the first such callback in `callbacks.py`.

- **Widget value props** (e.g. `annotation-<field>` / `value` or `checked`) — when a widget
  has `_condition` set, two callbacks both write to its value prop: `update_widget_value`
  (in `_register_widget_value_capture`, triggered by doc load) and `_clear_when_hidden` (in
  `TaterWidget._register_conditional_callbacks`, triggered by the controlling field). Both
  use `allow_duplicate=True`; `prevent_initial_call='initial_duplicate'` is also required on
  the doc-load callback because `allow_duplicate=True` normally forbids initial calls.
  This is enforced automatically in `_register_widget_value_capture` when `widget._condition
  is not None` — don't remove that branch.

**`prevent_initial_call=True` does not suppress pattern-matching fires** caused by component
re-renders — only the very first page load. Use the value guard above instead.

## Widget conventions

Widget base class hierarchy in `base.py`:
- `TaterWidget` — abstract root; all widgets inherit from this
- `ControlWidget(TaterWidget)` — leaf widgets that capture a value; adds `required`, `auto_advance`, `value_prop`, `empty_value`
  - `ChoiceWidget` — single `Literal[...]` field; derives `options` from schema
    - `SegmentedControlWidget`, `RadioGroupWidget`, `SelectWidget`, `ChipGroupWidget`
  - `MultiChoiceWidget` — `List[Literal[...]]` field; derives `options` from schema
    - `MultiSelectWidget`
  - `BooleanWidget` — `bool` field; `value_prop = "checked"`
    - `CheckboxWidget`, `SwitchWidget`
  - `NumericWidget` — numeric field
    - `NumberInputWidget`, `SliderWidget`, `RangeSliderWidget`
  - `TextWidget` — string field
    - `TextInputWidget`, `TextAreaWidget`
- `ContainerWidget(TaterWidget)` — widgets that contain other widgets
  - `GroupWidget` — groups widgets for a nested sub-model (`schema_field` is a dot-path prefix)
  - `RepeaterWidget` (abstract, in `repeater.py`) — manages a `List[ItemModel]` field; subclasses:
    - `ListableWidget` — items as a vertical stack of bordered cards
    - `TabsWidget` — items as switchable tabs

- Constructor signature: `(schema_field, label="", description=None, ...)`.
- `renders_own_label` property: if `True`, the widget renders its own label (skips the outer
  wrapper label in layout). Most widgets return `False`; GroupWidget/RepeaterWidget subclasses return `True`.
- `bind_schema(model)` should raise `TypeError` / `ValueError` with a clear message if the field
  type doesn't match what the widget expects.
- `register_callbacks(app)` captures `self` fields into the closure — don't rely on `self` inside
  callback functions (capture to local variables before the `@app.callback` decorator).
- **Escape-hatch callbacks**: for cross-field rules that can't be expressed as widget declarations,
  assign widgets to named variables and use `widget.component_id` in `Output`/`Input` — avoids
  hard-coding ID strings. See `apps/examples/config/hooks.py` for the pattern. The `configure(app)` function
  in a config module is the right place for these; it is called after `set_annotation_widgets` so
  all component IDs are finalised.
- `required=True` is **UI-only**: it shows a `*` indicator and drives the `in_progress` /
  `complete` status badge, but does not prevent saving an empty value. This is intentional —
  annotation tools need to support partial saves so annotators can leave fields blank and
  return later. Pydantic-level enforcement would break loading incomplete annotation files.

## HierarchicalLabel specifics

- `HierarchicalLabelCompactWidget`: shows only the selected node per navigated level; uses
  `tabler:chevron-right` icon separators between levels; wraps sections in `dmc.Stack(gap=2)`.
- `HierarchicalLabelFullWidget`: shows all siblings at every expanded level; shows path breadcrumb
  below search bar.
- `_find_path(root, name)` does a DFS from root returning the full path list to a node.
- Search result buttons all have `idx=0`; the fallback in `handle_click` searches `root.all_leaves()`
  and sets `is_search_result=True` to navigate via `_find_path` and clear the search box.

## What is and isn't implemented

**Implemented:**
- All widgets listed in README
- Manual widget definition (user provides widget list)
- Nested models via GroupWidget (dot-path `schema_field`)
- Repeatable lists via ListableWidget (card stack) and TabsWidget (tab UI)
- Span annotation, including SpanAnnotationWidget nested inside ListableWidget/TabsWidget
- Hierarchical label (compact + full)
- Auto-save, progress tracking, flag/notes, annotation timing
- Conditional visibility (`conditional_on`)
- Full widget suite: SegmentedControlWidget, RadioGroupWidget, SelectWidget, ChipGroupWidget,
  MultiSelectWidget, CheckboxWidget, SwitchWidget, NumberInputWidget, SliderWidget,
  RangeSliderWidget, TextInputWidget, TextAreaWidget

## Tests

Tests live in `tests/`. Run with:

```bash
python -m pytest tests/ --ignore=tests/test_browser.py   # fast, no browser
python -m pytest tests/test_browser.py --headless         # browser tests
python -m pytest tests/ --headless                        # full suite
```

**Test files:**
- `test_value_helpers.py` — `get_model_value` / `set_model_value` and dict variants
- `test_has_value.py` — `_has_value` predicate
- `test_bind_schema.py` — `bind_schema` for all widget types (happy path + error cases)
- `test_component_id.py` — `component_id` and `conditional_wrapper_id` derivation
- `test_decode_field_path.py` — `_decode_field_path` for standalone, single-repeater, and doubly-nested cases
- `test_save_load.py` — `TaterApp` save/load round-trip (no browser): flat fields, nested models, `SpanAnnotation` lists, metadata, schema-mismatch warnings
- `test_browser.py` — `dash.testing` browser tests: navigation, flag, notes

**Browser test setup** requires Google Chrome (`.deb`, not snap) and `webdriver-manager`. The `pytest_setup_options` hook in `conftest.py` auto-installs a matching ChromeDriver via `webdriver-manager` on first run.

**`conftest.py`** defines shared Pydantic model fixtures (`Schema`, `Pet`, `Finding`, `Measurements`, etc.) used across unit tests, and the `pytest_setup_options` hook for browser driver configuration.

## spec/ files

- `spec/tater.md` — Pydantic-first redesign spec; fully implemented including RepeaterWidget.
- `spec/app.md` — Original v1 spec with JSON schema files; obsolete.
- `spec/STAND_LIBRARY_SPECIFICATION.md` — Spec for a Streamlit-based predecessor (STAND);
  kept as reference only.
