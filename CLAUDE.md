# Tater — Developer Notes for Claude

## Project overview

Tater is a Python library for building document annotation UIs. Users provide a config file
(Python or JSON) defining a Pydantic schema and optional widget overrides, then run the `tater`
CLI to launch a Dash web app.

Key stack: Python 3.10+, Dash, **Dash Mantine Components (DMC) v2.6 / Mantine v7**, Pydantic v2.

DMC LLM-friendly documentation can be found [here](https://www.dash-mantine-components.com/assets/llms.txt).

## Directory layout

```
tater/                  # Library package
  __init__.py           # Public API: SpanAnnotation, SpanAnnotationWidget,
                        #   EntityType, load_schema, parse_schema, widgets_from_model
  models/               # Pydantic data models (Document, SpanAnnotation)
  loaders/              # Schema loaders
    model_loader.py     # WIDGET_CLASS, DEFAULT_WIDGET, widgets_from_model,
                        #   _widget_from_field_type, _humanize
    json_loader.py      # JSON schema → (Pydantic model, partial widget list)
  ui/                   # App machinery (TaterApp, layout, callbacks, value_helpers)
    upload_layout.py    # Hosted-mode upload page layout + callbacks
  examples/             # Built-in example sets for hosted mode "Browse examples" tab
    simple/             # meta.json + schema.json + documents.json
    gallery/            # meta.json + schema.json + documents.json
    hierarchical/       # meta.json + schema.json + documents.json + pet_ontology.yaml
    coarse_breast_label/ # meta.json + schema.json + documents.json + breast_fdx_ontology.yaml
  widgets/              # All widget classes
    base.py             # Widget base class hierarchy (see Widget conventions)
    repeater.py         # RepeaterWidget (abstract), ListableWidget, TabsWidget
    hierarchical_label.py  # HierarchicalLabel* widgets + Node tree utilities
    ...                 # One file per concrete widget (see Widget conventions)
apps/
  examples/
    config/             # Python config-file examples (simple, hooks, span, span_in_list, …)
    schema/             # JSON schema-file examples
    data/               # Sample documents and ontologies (e.g. pet_ontology.yaml)
spec/                   # Design documents (see below)
```

## Running examples

Apps are run via the `tater` CLI, which requires either `--config` (Python) or `--schema` (JSON):

```bash
tater --config apps/examples/config/simple.py --documents data/documents.json
tater --config apps/examples/config/hooks.py  --documents data/documents.json
tater --schema apps/examples/schema/simple.json --documents data/documents.json
```

Hosted mode (upload page at `/`, annotation UI at `/annotate`):

```bash
tater --hosted [--port 8050] [--host 0.0.0.0]
```

CLI flags: `--documents` (required in single mode), `--config` or `--schema` (one required in single mode),
`--annotations`, `--port`, `--host`, `--debug`, `--hosted`
(also via `TATER_DEBUG` / `TATER_PORT` / `TATER_HOST` env vars).

## Architecture

- **Pydantic-first**: options for choice widgets are inferred from `Literal` types at
  `bind_schema()` time; no manual option lists needed.
- **Widget binding**: each widget has a `schema_field` (dot-path into the model) and a
  `component_id` derived from it. `bind_schema(model)` is called by TaterApp to validate and
  extract metadata.
- **Loader design**: `model_loader.py` is the primary path — `widgets_from_model(model)`
  auto-generates widgets from Pydantic type hints. `json_loader.py` parses a JSON schema into
  a Pydantic model and a *partial* widget list (only fields with a `widget` block). `runner.py`
  calls `widgets_from_model(model, overrides=widgets)` to fill the gaps — the same flow used
  by the Python config path.
- **Callbacks**: each widget registers its own Dash callbacks in `register_callbacks(app)`.
  The central `callbacks.py` handles navigation, doc loading, and metadata (flag/notes/status).
- **Persistence**: `TaterApp._save_annotations_to_file()` is called eagerly on every change
  in single mode. In hosted mode `annotations_path` is `None` — no auto-save; annotations live
  in `dcc.Store` client-side and the user downloads them explicitly.
  Format: `{doc_id: {annotations: {...}, metadata: {...}}}`.
- **value_helpers**: `get_model_value` / `set_model_value` in `tater/ui/value_helpers.py`
  handle dot-path reads/writes into nested Pydantic model instances.
- **Flag/notes loading**: `load_flag_and_notes` in `callbacks.py` fires on `current-doc-id`
  change and populates both `flag-document` (checked) and `document-notes` (value) from
  `tater_app.metadata`. This is the only callback that writes to these outputs on navigation —
  the corresponding `save_flag` / `save_notes` callbacks only write on user interaction.

## Hosted mode

`--hosted` launches a multi-user server. The Dash app is shared; per-user state is isolated
via Flask session cookies and a server-side `_session_cache` dict.

**Upload page:** two tabs — "Upload files" and "Browse examples".
- *Upload files*: schema JSON + documents JSON + optional existing annotations JSON. If the
  schema has file-path `hierarchies` references, per-file ontology upload zones appear
  automatically. Each zone has a status icon (grey outline → filled blue check on success).
- *Browse examples*: clickable cards for built-in example sets in `tater/examples/`. Clicking
  a card immediately creates a session and redirects — no submit button needed.

**Session flow (upload tab):** user uploads schema + documents (+ optional ontology files +
optional annotations) → files written to `tempfile.mkdtemp` → paths stored in
`flask.session["tater_session"]` → redirect to `/annotate` → `serve_layout()` reads the
session, retrieves or builds the `TaterApp`, returns the annotation layout.

**Session flow (examples tab):** user clicks a card → `load_example` callback reads the
example's files directly from `tater/examples/<name>/`, resolves hierarchy paths to the same
temp dir, creates session, redirects.

**Adding a built-in example:** create a subfolder under `tater/examples/` with at minimum
`meta.json` (`name`, `description`, `order`), `schema.json`, and `documents.json`. Ontology
YAML files referenced in the schema should be placed alongside and referenced by filename only
(not relative path). The example is discovered automatically at layout-build time.

**Annotations preload in hosted mode:** if `session_info["annotations_path"]` is set (from
an uploaded annotations file), `_build_session_app` temporarily sets `tater_app.annotations_path`,
calls `_load_annotations_from_file()`, then clears it back to `None` so no auto-save occurs.

**Ontology files in hosted mode:** `hierarchies` entries in a JSON schema that reference
external YAML files (e.g. `"ontology": "../data/pets.yaml"`) cannot be resolved from temp
storage. The upload page detects these file-path references, shows a compact per-file upload
zone for each, and rewrites the paths in the schema to absolute temp paths before writing
`schema.json`. Inline hierarchy dicts work without any upload.

**Always-register callbacks:** span, repeater, nested-repeater, hierarchical-label, and
hierarchical-label-tags callbacks are registered once at server startup (not per-session).
They use a `_ta()` runtime resolver — `app._tater_get_current_app` is a function stored on
the Dash app that looks up the calling user's `TaterApp` from `_session_cache` via
`flask.session` at callback invocation time. This avoids re-registering callbacks for each
upload session (Dash only allows each output to be registered once).

**`_tater_app` vs `_tater_get_current_app`:** two different mechanisms are used to give
callbacks access to the right `TaterApp` instance, depending on mode:
- *Single mode*: `TaterApp.set_annotation_widgets` stores `self` directly on the Dash app as
  `app._tater_app`. Callbacks capture it via closure at registration time — safe because there
  is only one `TaterApp` for the lifetime of the process.
- *Hosted mode*: the Dash app is shared across sessions, so a single `_tater_app` reference
  would always point to the last session's app. Instead, `runner.py` stores a callable on the
  Dash app as `app._tater_get_current_app`. This callable does a per-request lookup:
  `flask.session["tater_session"]["session_id"]` → `_session_cache[session_id]`. Callbacks
  that must be session-aware capture this callable at registration time and call it inside the
  callback body (i.e. at request time, not at registration time).

**Relay store pattern:** Dash prohibits mixing MATCH dict-ID outputs with static string
outputs in the same callback (e.g. `{"type": "span-trigger", "field": MATCH}` + `"annotations-store"`).
The reason is that MATCH callbacks fire once per matched component instance, while a static
output is a single component — Dash cannot fan-in multiple MATCH firings into one static write
within a single callback. The solution used throughout: embed the annotation update in the
MATCH relay store data, then a separate ALL-input relay callback reads from all relay stores
and writes to `annotations-store`. Simple (non-MATCH) widgets write directly to
`annotations-store` and do not need a relay store.
Widgets that use this pattern each include a relay store in their rendered output:
- Repeater: `{"type": "repeater-ann-relay", "field": pipe_field}`
- Nested repeater: `{"type": "nested-repeater-ann-relay", "ld": ld, "li": li}`
- HierarchicalLabel (full/compact): `{"type": "hier-ann-relay", "field": pipe_field}`
- HierarchicalLabelTags: `{"type": "hl-tags-ann-relay", "field": pipe_field}`
- Span: span-trigger store data carries `{"count": N, "annotations_update": {...}}`

## DMC version constraints

DMC is pinned at **v2.6 (Mantine v7)**. Before using a DMC component, verify it exists in
this version:

- `dmc.TabsTab` is the tab trigger (v2.x API) — `dmc.Tab` does not exist.
- `dmc.Tabs` uses `value` (not `defaultValue`) for the initially active tab.
- `dmc.Badge(circle=True)` clips double-digit numbers — avoid `circle=True`.
- `dmc.ColorSchemeToggle` handles dark/light toggling and persists the choice in `localStorage`.
  Both pages use `defaultColorScheme="auto"` on their `dmc.MantineProvider`; the toggle is
  consistent across pages without server-side coordination. There is no `theme` parameter on
  `TaterApp` or in config files.
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
`DuplicateCallback` error at startup. Outputs in this codebase that use `allow_duplicate=True`:

- **`current-doc-id` / `data`** — written by the prev/next buttons and the document-menu
  selector. All three already use `allow_duplicate=True`; any new navigation callback must too.
  See the comment block on the first such callback in `callbacks.py`.

- **`annotations-store` / `data`** — written by the main save callback and by multiple relay
  callbacks (repeater, nested repeater, HL, HL tags, span). All use `allow_duplicate=True`.
  New callbacks writing to `annotations-store` must also use it.

- **`upload-location` / `href`** — written by both `handle_submit` (upload tab) and
  `load_example` (examples tab) in `upload_layout.py`. Both use `allow_duplicate=True`.

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
    - `SegmentedControlWidget`, `RadioGroupWidget`, `SelectWidget`, `ChipRadioWidget`
  - `MultiChoiceWidget` — `List[Literal[...]]` field; derives `options` from schema
    - `MultiSelectWidget`, `CheckboxGroupWidget`
  - `BooleanWidget` — `bool` field; `value_prop = "checked"`
    - `CheckboxWidget`, `SwitchWidget`, `ChipWidget`
  - `NumericWidget` — numeric field
    - `NumberInputWidget`, `SliderWidget`, `RangeSliderWidget`
  - `TextWidget` — string field
    - `TextInputWidget`, `TextAreaWidget`
  - `SpanAnnotationWidget` — `List[SpanAnnotation]` field (in `span.py`)
  - `HierarchicalLabelWidget` (abstract, in `hierarchical_label.py`) — `str` / `Optional[str]` field
    - `HierarchicalLabelTagsWidget`, `HierarchicalLabelCompactWidget`, `HierarchicalLabelFullWidget`
- `ContainerWidget(TaterWidget)` — widgets that contain other widgets
  - `GroupWidget` — groups widgets for a nested sub-model (`schema_field` is a dot-path prefix)
  - `RepeaterWidget` (abstract, in `repeater.py`) — manages a `List[ItemModel]` field; subclasses:
    - `ListableWidget` — items as a vertical stack of bordered cards
    - `TabsWidget` — items as switchable tabs
    - `AccordionWidget` — items as collapsible accordion panels
- `DividerWidget` — structural only; no schema field, no value capture

- Constructor signature: `(schema_field, label="", description=None, ...)`.
- `renders_own_label` property: if `True`, the widget renders its own label (skips the outer
  wrapper label in layout). Most widgets return `False`; GroupWidget/RepeaterWidget subclasses return `True`.
- `bind_schema(model)` should raise `TypeError` / `ValueError` with a clear message if the field
  type doesn't match what the widget expects.
- `register_callbacks(app)` captures `self` fields into the closure — don't rely on `self` inside
  callback functions (capture to local variables before the `@app.callback` decorator).
- **Escape-hatch callbacks**: for cross-field rules that can't be expressed as widget declarations,
  assign widgets to named variables and use `widget.component_id` in `Output`/`Input` — avoids
  hard-coding ID strings. See `apps/examples/config/hooks.py` for the pattern. The `register_callbacks(app)` function
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
- Repeatable lists via ListableWidget (card stack), TabsWidget (tabs), AccordionWidget (accordion)
- Span annotation, including SpanAnnotationWidget nested inside ListableWidget/TabsWidget
- Hierarchical label (tags, compact, full)
- Auto-save, progress tracking, flag/notes, annotation timing
- Conditional visibility (`conditional_on`)
- Full widget suite: SegmentedControlWidget, RadioGroupWidget, SelectWidget, ChipRadioWidget,
  MultiSelectWidget, CheckboxGroupWidget, CheckboxWidget, SwitchWidget, ChipWidget,
  NumberInputWidget, SliderWidget, RangeSliderWidget, TextInputWidget, TextAreaWidget,
  SpanAnnotationWidget, HierarchicalLabelTagsWidget, HierarchicalLabelCompactWidget,
  HierarchicalLabelFullWidget, DividerWidget

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
- `test_widgets_from_model.py` — `widgets_from_model`, `WIDGET_CLASS`, `DEFAULT_WIDGET`; auto-gen for all field types, nested models, overrides
- `test_parse_schema.py` — `parse_schema`, `_build_pydantic_field`, `_build_widget_from_spec`; no-widget-block → absent from list, containers, dividers, conditionals, unknown type errors
- `test_browser.py` — `dash.testing` browser tests: navigation, flag, notes

**Browser test setup** requires Google Chrome (`.deb`, not snap) and `webdriver-manager`. The `pytest_setup_options` hook in `conftest.py` auto-installs a matching ChromeDriver via `webdriver-manager` on first run.

**`conftest.py`** defines shared Pydantic model fixtures (`Schema`, `Pet`, `Finding`, `Measurements`, etc.) used across unit tests, and the `pytest_setup_options` hook for browser driver configuration.

## spec/ files

- `spec/tater.md` — Pydantic-first redesign spec; fully implemented including RepeaterWidget.
- `spec/app.md` — Original v1 spec with JSON schema files; obsolete.
- `spec/STAND_LIBRARY_SPECIFICATION.md` — Spec for a Streamlit-based predecessor (STAND);
  kept as reference only.
