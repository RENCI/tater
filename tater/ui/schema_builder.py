"""No-code schema builder — modal form for hosted mode upload page."""
from __future__ import annotations

import re
from collections import defaultdict

from dash import ALL, Dash, Input, Output, State, ctx, dcc, html, no_update
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from tater.loaders.model_loader import DEFAULT_WIDGET, WIDGET_CLASS


SCHEMA_BUILDER_STORES = [
    dcc.Store(id="schema-builder-fields", data=[]),
    dcc.Store(id="schema-builder-store", data=None),
    dcc.Store(id="schema-builder-edit-index", data=None),
]

# Human-readable labels — the only thing that can't be derived from the widget system.
_FIELD_TYPE_LABELS: dict[str, str] = {
    "choice": "Choice (single select)",
    "multi_choice": "Multi-choice",
    "boolean": "Boolean",
    "text": "Text",
    "numeric": "Numeric",
    "range_slider": "Range slider",
    "span_annotation": "Span annotation",
    "hierarchical_label": "Hierarchical label",
    "divider": "Divider",
}

_WIDGET_TYPE_LABELS: dict[str, str] = {
    "segmented_control": "Segmented control",
    "radio_group": "Radio group",
    "select": "Select dropdown",
    "chip_radio": "Chip",
    "multi_select": "Multi-select dropdown",
    "checkbox_group": "Checkbox group",
    "checkbox": "Checkbox",
    "switch": "Switch",
    "chip_boolean": "Chip",
    "text_input": "Text input",
    "text_area": "Text area",
    "number_input": "Number input",
    "slider": "Slider",
    "range_slider": "Range slider",
    "span_annotation": "Inline",
    "span_popup": "Popup",
    "hierarchical_label_select": "Single select",
    "hierarchical_label_multi": "Multi-select",
}

# Derived from WIDGET_CLASS: group widget type strings by field_type.
# Excludes container/repeater/group widgets (those without a field_type on their class).
_WIDGET_OPTIONS: dict[str, list[dict]] = defaultdict(list)
for _wtype, _cls in WIDGET_CLASS.items():
    _ft = getattr(_cls, "field_type", None)
    if _ft and _ft in _FIELD_TYPE_LABELS:
        _WIDGET_OPTIONS[_ft].append({
            "value": _wtype,
            "label": _WIDGET_TYPE_LABELS.get(_wtype, _wtype),
        })
# Ensure ordering matches DEFAULT_WIDGET (default first), then stable remainder.
_inverted = {v: k for k, v in WIDGET_CLASS.items()}
for _ft in _WIDGET_OPTIONS:
    _default_cls = DEFAULT_WIDGET.get(_ft)
    _default_wtype = _inverted.get(_default_cls)
    if _default_wtype:
        opts = _WIDGET_OPTIONS[_ft]
        opts.sort(key=lambda o: (0 if o["value"] == _default_wtype else 1, o["label"]))
_WIDGET_OPTIONS = dict(_WIDGET_OPTIONS)
# Field types without widget choice (single option or structural)
for _ft in ("range_slider", "divider"):
    _WIDGET_OPTIONS.setdefault(_ft, [])

# Derived: field_type → default widget type string.
_DEFAULT_WIDGET_TYPE: dict[str, str] = {}
for _ft, _cls in DEFAULT_WIDGET.items():
    _wtype = _inverted.get(_cls)
    if _wtype:
        _DEFAULT_WIDGET_TYPE[_ft] = _wtype
_DEFAULT_WIDGET_TYPE.setdefault("range_slider", "range_slider")

# Derived: ordered list for the field-type picker, preserving label order.
_FIELD_TYPES = [
    {"value": ft, "label": label}
    for ft, label in _FIELD_TYPE_LABELS.items()
]

_TYPE_COLORS = {
    "choice": "blue",
    "multi_choice": "cyan",
    "boolean": "green",
    "text": "violet",
    "numeric": "orange",
    "range_slider": "yellow",
    "span_annotation": "red",
    "hierarchical_label": "teal",
    "divider": "gray",
}

_OPTIONS_CONFIG = {
    "choice": {
        "label": "Options",
        "description": "Comma-separated list of options.",
        "placeholder": "positive, negative, neutral",
    },
    "multi_choice": {
        "label": "Options",
        "description": "Comma-separated list of options.",
        "placeholder": "cat, dog, rabbit",
    },
    "span_annotation": {
        "label": "Entity types (optional)",
        "description": "Comma-separated entity type names. Leave blank for unlabeled spans.",
        "placeholder": "Person, Organization, Location",
    },
}

_SHOW = {}
_HIDE = {"display": "none"}


def build_schema_builder_modal() -> dmc.Modal:
    """Return the schema builder modal component."""
    _form_panel = html.Div(
        id="schema-builder-form-panel",
        style=_HIDE,
        children=[
            dmc.Divider(
                id="schema-builder-form-divider",
                label="Add field",
                labelPosition="left",
                mt="xs",
            ),
            dmc.SimpleGrid(
                [
                    dmc.Select(
                        id="schema-builder-field-type",
                        label="Field type",
                        data=_FIELD_TYPES,
                        value="choice",
                        allowDeselect=False,
                    ),
                    dmc.TextInput(
                        id="schema-builder-field-label",
                        label="Label",
                        placeholder="e.g. Sentiment",
                    ),
                ],
                cols=2,
            ),
            html.Div(
                dmc.Select(
                    id="schema-builder-widget-type",
                    label="Widget",
                    data=_WIDGET_OPTIONS["choice"],
                    value="segmented_control",
                    allowDeselect=False,
                ),
                id="schema-builder-widget-type-section",
            ),
            dmc.Checkbox(
                id="schema-builder-field-required",
                label="Required",
                checked=False,
                mt="sm",
                mb="sm",
            ),
            html.Div(
                dmc.Textarea(
                    id="schema-builder-options",
                    label="Options",
                    placeholder="positive, negative, neutral",
                    description="Comma-separated list of options.",
                    autosize=True,
                    minRows=2,
                ),
                id="schema-builder-options-section",
            ),
            html.Div(
                dmc.SimpleGrid(
                    [
                        dmc.NumberInput(id="schema-builder-min", label="Min", value=None),
                        dmc.NumberInput(id="schema-builder-max", label="Max", value=None),
                        dmc.NumberInput(id="schema-builder-step", label="Step", value=None),
                    ],
                    cols=3,
                ),
                id="schema-builder-numeric-section",
                style=_HIDE,
            ),
            html.Div(
                dmc.TextInput(
                    id="schema-builder-placeholder",
                    label="Placeholder",
                    placeholder="Optional hint text",
                ),
                id="schema-builder-text-section",
                style=_HIDE,
            ),
            html.Div(
                dmc.Stack(
                    [
                        dmc.TextInput(
                            id="schema-builder-hl-ref",
                            label="Hierarchy name",
                            description="Key for this ontology — fields sharing the same name use the same tree.",
                            placeholder="e.g. fauna",
                        ),
                        dmc.Textarea(
                            id="schema-builder-hl-yaml",
                            label="Hierarchy (YAML)",
                            description="Indent with spaces to create nested levels.",
                            placeholder="Animals:\n  - Cat\n  - Dog\nPlants:\n  - Oak\n  - Rose",
                            autosize=True,
                            minRows=4,
                            maxRows=12,
                            styles={"input": {"fontFamily": "monospace", "fontSize": "12px"}},
                        ),
                    ],
                    gap="xs",
                ),
                id="schema-builder-hl-section",
                style=_HIDE,
            ),
            dmc.Group(
                [
                    dmc.Button(
                        "Save",
                        id="schema-builder-save-btn",
                        leftSection=DashIconify(icon="tabler:check", width=16),
                        size="sm",
                    ),
                    dmc.Button(
                        "Cancel",
                        id="schema-builder-cancel-form-btn",
                        variant="subtle",
                        color="gray",
                        size="sm",
                    ),
                ],
                mt="xs",
            ),
            html.Div(id="schema-builder-add-feedback"),
        ],
    )

    return dmc.Modal(
        id="schema-builder-modal",
        title=dmc.Group(
            [
                DashIconify(icon="tabler:adjustments-horizontal", width=18),
                dmc.Text("Build schema", fw=600),
            ],
            gap="xs",
        ),
        opened=False,
        size="lg",
        closeOnEscape=True,
        children=[
            dmc.Stack(
                [
                    dmc.TextInput(
                        id="schema-builder-title",
                        label="Schema title",
                        placeholder="e.g. Document Review",
                        description="Displayed at the top of the annotation UI.",
                    ),
                    dmc.Divider(),
                    html.Div(id="schema-builder-field-list"),
                    dmc.Button(
                        "Add field",
                        id="schema-builder-add-btn",
                        leftSection=DashIconify(icon="tabler:plus", width=16),
                        variant="light",
                        size="sm",
                    ),
                    _form_panel,
                ],
                gap="sm",
            ),
            dmc.Divider(mt="sm"),
            dmc.Group(
                [
                    dmc.Button(
                        "Apply",
                        id="schema-builder-apply-btn",
                        disabled=True,
                        leftSection=DashIconify(icon="tabler:check", width=16),
                    ),
                    dmc.Button(
                        "Download JSON",
                        id="schema-builder-download-btn",
                        disabled=True,
                        variant="light",
                        leftSection=DashIconify(icon="tabler:download", width=16),
                    ),
                    dmc.Button(
                        "Cancel",
                        id="schema-builder-cancel-btn",
                        variant="subtle",
                        color="gray",
                    ),
                ],
                justify="flex-end",
                mt="md",
            ),
            dcc.Download(id="schema-builder-download"),
        ],
    )


def register_schema_builder_callbacks(app: Dash) -> None:
    """Register all schema builder callbacks on the given Dash app."""

    @app.callback(
        Output("schema-builder-modal", "opened"),
        Input("schema-builder-open-btn", "n_clicks"),
        Input("schema-builder-apply-btn", "n_clicks"),
        Input("schema-builder-cancel-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_modal(_open, _apply, _cancel):
        return ctx.triggered_id == "schema-builder-open-btn"

    # ---------- Form panel show/hide ----------

    @app.callback(
        Output("schema-builder-form-panel", "style"),
        Output("schema-builder-form-divider", "label"),
        Output("schema-builder-save-btn", "children"),
        Input("schema-builder-edit-index", "data"),
    )
    def toggle_form_panel(edit_index):
        if edit_index is None:
            return _HIDE, "Add field", "Save"
        if edit_index == -1:
            return _SHOW, "Add field", "Save"
        return _SHOW, "Edit field", "Save"

    # ---------- Open form (add or edit) ----------

    @app.callback(
        Output("schema-builder-edit-index", "data", allow_duplicate=True),
        Output("schema-builder-field-type", "value"),
        Output("schema-builder-field-label", "value"),
        Output("schema-builder-widget-type", "value", allow_duplicate=True),
        Output("schema-builder-options", "value"),
        Output("schema-builder-min", "value"),
        Output("schema-builder-max", "value"),
        Output("schema-builder-step", "value"),
        Output("schema-builder-placeholder", "value"),
        Output("schema-builder-hl-ref", "value"),
        Output("schema-builder-hl-yaml", "value"),
        Output("schema-builder-field-required", "checked"),
        Output("schema-builder-add-feedback", "children", allow_duplicate=True),
        Input("schema-builder-add-btn", "n_clicks"),
        Input({"type": "schema-field-edit", "index": ALL}, "n_clicks"),
        State("schema-builder-fields", "data"),
        prevent_initial_call=True,
    )
    def open_form(_add, _edits, fields):
        if not ctx.triggered or not ctx.triggered[0].get("value"):
            return (no_update,) * 13
        triggered = ctx.triggered_id

        if triggered == "schema-builder-add-btn":
            return -1, "choice", "", "segmented_control", "", None, None, None, "", "", "", False, ""

        index = triggered["index"]
        fields = fields or []
        if index < 0 or index >= len(fields):
            return (no_update,) * 13
        field = fields[index]
        ftype = field["type"]
        wtype = field.get("widget_type") or _DEFAULT_WIDGET_TYPE.get(ftype, ftype)

        options_val = ""
        if ftype in ("choice", "multi_choice"):
            options_val = ", ".join(field.get("options", []))
        elif ftype == "span_annotation":
            options_val = ", ".join(field.get("entity_types", []))

        is_hl = ftype == "hierarchical_label"
        return (
            index,
            ftype,
            field.get("label", ""),
            wtype,
            options_val,
            field.get("min_value"),
            field.get("max_value"),
            field.get("step"),
            field.get("placeholder", "") if ftype == "text" else "",
            field.get("hl_ref", "") if is_hl else "",
            field.get("hl_yaml", "") if is_hl else "",
            bool(field.get("required", False)),
            "",
        )

    @app.callback(
        Output("schema-builder-edit-index", "data", allow_duplicate=True),
        Input("schema-builder-cancel-form-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def cancel_form(_):
        return None

    # ---------- Section visibility / widget options ----------

    @app.callback(
        Output("schema-builder-options-section", "style"),
        Output("schema-builder-numeric-section", "style"),
        Output("schema-builder-text-section", "style"),
        Output("schema-builder-hl-section", "style"),
        Output("schema-builder-widget-type-section", "style"),
        Output("schema-builder-widget-type", "data"),
        Output("schema-builder-widget-type", "value", allow_duplicate=True),
        Output("schema-builder-options", "label"),
        Output("schema-builder-options", "description"),
        Output("schema-builder-options", "placeholder"),
        Input("schema-builder-field-type", "value"),
        State("schema-builder-edit-index", "data"),
        State("schema-builder-fields", "data"),
        prevent_initial_call=True,
    )
    def show_type_options(field_type, edit_index, fields):
        opts = _WIDGET_OPTIONS.get(field_type, [])
        cfg = _OPTIONS_CONFIG.get(field_type, _OPTIONS_CONFIG["choice"])

        # Preserve existing widget_type when editing a field whose type matches.
        # open_form sets field-type → this fires after with the new edit-index in State.
        wtype_value = opts[0]["value"] if opts else None
        if edit_index is not None and edit_index >= 0 and fields and edit_index < len(fields):
            field = fields[edit_index]
            if field.get("type") == field_type:
                existing = field.get("widget_type")
                if existing in {o["value"] for o in opts}:
                    wtype_value = existing

        return (
            _SHOW if field_type in ("choice", "multi_choice", "span_annotation") else _HIDE,
            _SHOW if field_type in ("numeric", "range_slider") else _HIDE,
            _SHOW if field_type == "text" else _HIDE,
            _SHOW if field_type == "hierarchical_label" else _HIDE,
            _SHOW if len(opts) > 1 else _HIDE,
            opts,
            wtype_value,
            cfg["label"],
            cfg["description"],
            cfg["placeholder"],
        )

    # ---------- Save (add or update) ----------

    @app.callback(
        Output("schema-builder-fields", "data", allow_duplicate=True),
        Output("schema-builder-edit-index", "data", allow_duplicate=True),
        Output("schema-builder-add-feedback", "children", allow_duplicate=True),
        Input("schema-builder-save-btn", "n_clicks"),
        State("schema-builder-edit-index", "data"),
        State("schema-builder-field-type", "value"),
        State("schema-builder-widget-type", "value"),
        State("schema-builder-field-label", "value"),
        State("schema-builder-field-required", "checked"),
        State("schema-builder-options", "value"),
        State("schema-builder-min", "value"),
        State("schema-builder-max", "value"),
        State("schema-builder-step", "value"),
        State("schema-builder-placeholder", "value"),
        State("schema-builder-hl-ref", "value"),
        State("schema-builder-hl-yaml", "value"),
        State("schema-builder-fields", "data"),
        prevent_initial_call=True,
    )
    def save_field(_, edit_index, field_type, widget_type, label, required,
                   options_text, min_val, max_val, step, placeholder, hl_ref, hl_yaml, fields):
        fields = list(fields or [])
        label = (label or "").strip()
        adding = edit_index == -1

        if field_type == "divider":
            field = {"type": "divider", "label": label}
            if adding:
                fields.append(field)
            else:
                fields[edit_index] = field
            return fields, None, _ok("Divider saved." if not adding else "Added divider.")

        if not label:
            return no_update, no_update, _err("Label is required.")

        new_id = _label_to_id(label)
        old_id = fields[edit_index].get("id", "") if not adding and edit_index < len(fields) else ""
        existing_ids = {f.get("id") for f in fields if f.get("id")} - ({old_id} if old_id else set())
        if new_id in existing_ids:
            return no_update, no_update, _err(f"A field with id '{new_id}' already exists.")

        wtype = widget_type or _DEFAULT_WIDGET_TYPE.get(field_type, field_type)
        field: dict = {
            "type": field_type,
            "widget_type": wtype,
            "id": new_id,
            "label": label,
            "required": bool(required),
        }

        if field_type in ("choice", "multi_choice"):
            options = [o.strip() for o in (options_text or "").split(",") if o.strip()]
            if len(options) < 2:
                return no_update, no_update, _err("At least 2 options required.")
            field["options"] = options
        elif field_type == "span_annotation":
            field["entity_types"] = [e.strip() for e in (options_text or "").split(",") if e.strip()]
        elif field_type == "hierarchical_label":
            import yaml
            ref = (hl_ref or "").strip()
            if not ref:
                return no_update, no_update, _err("Hierarchy name is required.")
            if not (hl_yaml or "").strip():
                return no_update, no_update, _err("Hierarchy YAML is required.")
            try:
                yaml.safe_load(hl_yaml)
            except Exception as exc:
                return no_update, no_update, _err(f"Invalid YAML: {exc}")
            field["hl_ref"] = ref
            field["hl_yaml"] = hl_yaml.strip()
        elif field_type in ("numeric", "range_slider"):
            for k, v in [("min_value", min_val), ("max_value", max_val), ("step", step)]:
                if v is not None:
                    field[k] = v
        elif field_type == "text":
            if (placeholder or "").strip():
                field["placeholder"] = placeholder.strip()

        if adding:
            fields.append(field)
            return fields, None, _ok(f"Added '{label}'.")
        else:
            fields[edit_index] = field
            return fields, None, _ok(f"Updated '{label}'.")

    # ---------- Move up/down ----------

    @app.callback(
        Output("schema-builder-fields", "data", allow_duplicate=True),
        Output("schema-builder-edit-index", "data", allow_duplicate=True),
        Input({"type": "schema-field-up", "index": ALL}, "n_clicks"),
        Input({"type": "schema-field-down", "index": ALL}, "n_clicks"),
        State("schema-builder-fields", "data"),
        State("schema-builder-edit-index", "data"),
        prevent_initial_call=True,
    )
    def move_field(_up, _down, fields, edit_index):
        if not ctx.triggered or not ctx.triggered[0].get("value"):
            return no_update, no_update
        triggered = ctx.triggered_id
        index = triggered["index"]
        going_up = triggered["type"] == "schema-field-up"
        new_pos = index - 1 if going_up else index + 1
        fields = list(fields or [])
        if new_pos < 0 or new_pos >= len(fields):
            return no_update, no_update
        fields[index], fields[new_pos] = fields[new_pos], fields[index]
        # Track the edited field's new position
        new_edit = edit_index
        if edit_index == index:
            new_edit = new_pos
        elif edit_index == new_pos:
            new_edit = index
        return fields, new_edit

    # ---------- Delete ----------

    @app.callback(
        Output("schema-builder-fields", "data", allow_duplicate=True),
        Output("schema-builder-edit-index", "data", allow_duplicate=True),
        Input({"type": "schema-field-delete", "index": ALL}, "n_clicks"),
        State("schema-builder-fields", "data"),
        State("schema-builder-edit-index", "data"),
        prevent_initial_call=True,
    )
    def delete_field(_clicks, fields, edit_index):
        if not ctx.triggered or not ctx.triggered[0].get("value"):
            return no_update, no_update
        index = ctx.triggered_id["index"]
        fields = list(fields or [])
        if 0 <= index < len(fields):
            fields.pop(index)
        new_edit = edit_index
        if edit_index == index:
            new_edit = None
        elif edit_index is not None and edit_index > index:
            new_edit = edit_index - 1
        return fields, new_edit

    # ---------- Field list render ----------

    @app.callback(
        Output("schema-builder-field-list", "children"),
        Input("schema-builder-fields", "data"),
        Input("schema-builder-edit-index", "data"),
    )
    def render_field_list(fields, edit_index):
        if not fields:
            return dmc.Text("No fields added yet.", size="sm", c="dimmed", ta="center", py="xs")
        n = len(fields)
        return [_field_row(f, i, n, i == edit_index) for i, f in enumerate(fields)]

    # ---------- Schema generation ----------

    @app.callback(
        Output("schema-builder-store", "data"),
        Output("schema-builder-apply-btn", "disabled"),
        Output("schema-builder-download-btn", "disabled"),
        Input("schema-builder-fields", "data"),
        Input("schema-builder-title", "value"),
    )
    def generate_schema(fields, title):
        if not fields or not any(f["type"] != "divider" for f in fields):
            return None, True, True
        return _fields_to_schema(fields, title or ""), False, False

    @app.callback(
        Output("schema-builder-download", "data"),
        Input("schema-builder-download-btn", "n_clicks"),
        State("schema-builder-store", "data"),
        State("schema-builder-title", "value"),
        prevent_initial_call=True,
    )
    def download_schema(_, schema_data, title):
        if not schema_data:
            return no_update
        import json
        filename = re.sub(r"[^a-z0-9]+", "_", (title or "schema").strip().lower()).strip("_") or "schema"
        return dcc.send_string(json.dumps(schema_data, indent=2), filename=f"{filename}.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _label_to_id(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_") or "field"


def _fields_to_schema(fields: list, title: str) -> dict:
    import yaml

    data_schema = []
    hierarchies: dict = {}

    for field in fields:
        if field["type"] == "divider":
            data_schema.append({"widget": {"type": "divider", "label": field["label"]}})
            continue
        ftype = field["type"]
        entry: dict = {"id": field["id"], "type": ftype}
        if ftype in ("choice", "multi_choice"):
            entry["options"] = field["options"]
        wtype = field.get("widget_type") or _DEFAULT_WIDGET_TYPE.get(ftype, ftype)
        widget: dict = {"type": wtype, "label": field["label"]}
        if field.get("required"):
            widget["required"] = True
        if ftype == "text" and field.get("placeholder"):
            widget["placeholder"] = field["placeholder"]
        if ftype in ("numeric", "range_slider"):
            for k in ("min_value", "max_value", "step"):
                if field.get(k) is not None:
                    widget[k] = field[k]
        if ftype == "span_annotation":
            entity_types = field.get("entity_types", [])
            if entity_types:
                widget["entity_types"] = entity_types
        if ftype == "hierarchical_label":
            ref = field.get("hl_ref", "")
            widget["hierarchy_ref"] = ref
            if ref and field.get("hl_yaml"):
                try:
                    hierarchies[ref] = yaml.safe_load(field["hl_yaml"])
                except Exception:
                    pass
        entry["widget"] = widget
        data_schema.append(entry)

    schema: dict = {
        "spec_version": "1.0",
        "title": title or "Annotation Schema",
        "data_schema": data_schema,
    }
    if hierarchies:
        schema["hierarchies"] = hierarchies
    return schema


def _field_row(field: dict, index: int, n: int, is_editing: bool) -> dmc.Paper:
    ftype = field["type"]
    wtype = field.get("widget_type", "")

    badges = [dmc.Badge(ftype, color=_TYPE_COLORS.get(ftype, "gray"), size="xs")]
    if wtype:
        badges.append(dmc.Badge(wtype.replace("_", " "), color="gray", variant="outline", size="xs"))

    preview = None
    if ftype in ("choice", "multi_choice"):
        opts = field.get("options", [])
        preview = ", ".join(opts[:4]) + ("…" if len(opts) > 4 else "")
    elif ftype == "span_annotation":
        et = field.get("entity_types", [])
        preview = (", ".join(et[:4]) + ("…" if len(et) > 4 else "")) if et else "unlabeled"
    elif ftype == "hierarchical_label":
        preview = f"→ {field['hl_ref']}" if field.get("hl_ref") else None

    left = dmc.Group(
        [
            dmc.Group(
                [
                    dmc.ActionIcon(
                        DashIconify(icon="tabler:arrow-up", width=12),
                        id={"type": "schema-field-up", "index": index},
                        n_clicks=0,
                        variant="subtle",
                        size="xs",
                        disabled=index == 0,
                    ),
                    dmc.ActionIcon(
                        DashIconify(icon="tabler:arrow-down", width=12),
                        id={"type": "schema-field-down", "index": index},
                        n_clicks=0,
                        variant="subtle",
                        size="xs",
                        disabled=index == n - 1,
                    ),
                ],
                gap=2,
            ),
            dmc.Text(field["label"] or "(divider)", size="sm", fw=500),
            *badges,
            *([dmc.Text(preview, size="xs", c="dimmed")] if preview else []),
        ],
        gap="xs",
        wrap="nowrap",
    )

    right = dmc.Group(
        [
            dmc.ActionIcon(
                DashIconify(icon="tabler:pencil", width=14),
                id={"type": "schema-field-edit", "index": index},
                n_clicks=0,
                color="blue",
                variant="filled" if is_editing else "subtle",
                size="sm",
            ),
            dmc.ActionIcon(
                DashIconify(icon="tabler:trash", width=14),
                id={"type": "schema-field-delete", "index": index},
                n_clicks=0,
                color="red",
                variant="subtle",
                size="sm",
            ),
        ],
        gap="xs",
    )

    paper_style = {"borderColor": "var(--mantine-color-blue-6)"} if is_editing else {}

    return dmc.Paper(
        dmc.Group(
            [left, right],
            justify="space-between",
            wrap="nowrap",
        ),
        p="xs",
        withBorder=True,
        radius="sm",
        mb="xs",
        style=paper_style,
    )


def _err(msg: str):
    return dmc.Text(msg, size="xs", c="red")


def _ok(msg: str):
    return dmc.Text(msg, size="xs", c="blue")
