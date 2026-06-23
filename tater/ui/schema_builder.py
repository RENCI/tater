"""No-code schema builder — modal form for hosted mode upload page."""
from __future__ import annotations

import re

from dash import ALL, Dash, Input, Output, State, ctx, dcc, html, no_update
import dash_mantine_components as dmc
from dash_iconify import DashIconify


SCHEMA_BUILDER_STORES = [
    dcc.Store(id="schema-builder-fields", data=[]),
    dcc.Store(id="schema-builder-store", data=None),
]

_FIELD_TYPES = [
    {"value": "choice", "label": "Choice (single select)"},
    {"value": "multi_choice", "label": "Multi-choice"},
    {"value": "boolean", "label": "Boolean"},
    {"value": "text", "label": "Text"},
    {"value": "numeric", "label": "Numeric"},
    {"value": "range_slider", "label": "Range slider"},
    {"value": "span_annotation", "label": "Span annotation"},
    {"value": "divider", "label": "Divider"},
]

_WIDGET_OPTIONS: dict[str, list[dict]] = {
    "choice": [
        {"value": "segmented_control", "label": "Segmented control"},
        {"value": "radio_group", "label": "Radio group"},
        {"value": "select", "label": "Select dropdown"},
        {"value": "chip_radio", "label": "Chip"},
    ],
    "multi_choice": [
        {"value": "multi_select", "label": "Multi-select dropdown"},
        {"value": "checkbox_group", "label": "Checkbox group"},
    ],
    "boolean": [
        {"value": "checkbox", "label": "Checkbox"},
        {"value": "switch", "label": "Switch"},
        {"value": "chip_boolean", "label": "Chip"},
    ],
    "text": [
        {"value": "text_input", "label": "Text input"},
        {"value": "text_area", "label": "Text area"},
    ],
    "numeric": [
        {"value": "number_input", "label": "Number input"},
        {"value": "slider", "label": "Slider"},
    ],
    "range_slider": [],
    "span_annotation": [
        {"value": "span_annotation", "label": "Inline"},
        {"value": "span_popup", "label": "Popup"},
    ],
    "divider": [],
}

_DEFAULT_WIDGET_TYPE: dict[str, str] = {
    ft: opts[0]["value"] for ft, opts in _WIDGET_OPTIONS.items() if opts
}
_DEFAULT_WIDGET_TYPE["range_slider"] = "range_slider"

_TYPE_COLORS = {
    "choice": "blue",
    "multi_choice": "cyan",
    "boolean": "green",
    "text": "violet",
    "numeric": "orange",
    "range_slider": "yellow",
    "span_annotation": "red",
    "divider": "gray",
}

# Options textarea config per field type (for types that share the options section)
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
    form = dmc.Stack(
        [
            dmc.TextInput(
                id="schema-builder-title",
                label="Schema title",
                placeholder="e.g. Document Review",
                description="Displayed at the top of the annotation UI.",
            ),
            dmc.Divider(label="Add a field", labelPosition="left"),
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
            # Widget type selector — hidden for types with only one variant
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
            ),
            # Options/entity-types section — choice, multi_choice, span_annotation
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
            # Numeric section — numeric and range_slider
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
            # Text section — text only
            html.Div(
                dmc.TextInput(
                    id="schema-builder-placeholder",
                    label="Placeholder",
                    placeholder="Optional hint text",
                ),
                id="schema-builder-text-section",
                style=_HIDE,
            ),
            dmc.Button(
                "Add field",
                id="schema-builder-add-btn",
                leftSection=DashIconify(icon="tabler:plus", width=16),
            ),
            html.Div(id="schema-builder-add-feedback"),
            dmc.Divider(label="Fields", labelPosition="left"),
            html.Div(id="schema-builder-field-list"),
        ],
        gap="sm",
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
        children=[
            form,
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

    @app.callback(
        Output("schema-builder-options-section", "style"),
        Output("schema-builder-numeric-section", "style"),
        Output("schema-builder-text-section", "style"),
        Output("schema-builder-widget-type-section", "style"),
        Output("schema-builder-widget-type", "data"),
        Output("schema-builder-widget-type", "value"),
        Output("schema-builder-options", "label"),
        Output("schema-builder-options", "description"),
        Output("schema-builder-options", "placeholder"),
        Input("schema-builder-field-type", "value"),
    )
    def show_type_options(field_type):
        opts = _WIDGET_OPTIONS.get(field_type, [])
        cfg = _OPTIONS_CONFIG.get(field_type, _OPTIONS_CONFIG["choice"])
        return (
            _SHOW if field_type in ("choice", "multi_choice", "span_annotation") else _HIDE,
            _SHOW if field_type in ("numeric", "range_slider") else _HIDE,
            _SHOW if field_type == "text" else _HIDE,
            _SHOW if len(opts) > 1 else _HIDE,
            opts,
            opts[0]["value"] if opts else None,
            cfg["label"],
            cfg["description"],
            cfg["placeholder"],
        )

    @app.callback(
        Output("schema-builder-fields", "data", allow_duplicate=True),
        Output("schema-builder-field-label", "value"),
        Output("schema-builder-options", "value"),
        Output("schema-builder-min", "value"),
        Output("schema-builder-max", "value"),
        Output("schema-builder-step", "value"),
        Output("schema-builder-placeholder", "value"),
        Output("schema-builder-field-required", "checked"),
        Output("schema-builder-add-feedback", "children"),
        Input("schema-builder-add-btn", "n_clicks"),
        State("schema-builder-field-type", "value"),
        State("schema-builder-widget-type", "value"),
        State("schema-builder-field-label", "value"),
        State("schema-builder-field-required", "checked"),
        State("schema-builder-options", "value"),
        State("schema-builder-min", "value"),
        State("schema-builder-max", "value"),
        State("schema-builder-step", "value"),
        State("schema-builder-placeholder", "value"),
        State("schema-builder-fields", "data"),
        prevent_initial_call=True,
    )
    def add_field(_, field_type, widget_type, label, required, options_text, min_val, max_val, step, placeholder, fields):
        _nu = (no_update,) * 8

        label = (label or "").strip()
        fields = list(fields or [])

        if field_type == "divider":
            fields.append({"type": "divider", "label": label})
            return fields, "", "", None, None, None, "", False, _ok(f"Added divider.")

        if not label:
            return (*_nu, _err("Label is required."))

        field_id = _label_to_id(label)
        if field_id in {f.get("id") for f in fields if f.get("id")}:
            return (*_nu, _err(f"A field with id '{field_id}' already exists."))

        wtype = widget_type or _DEFAULT_WIDGET_TYPE.get(field_type, field_type)
        field: dict = {
            "type": field_type,
            "widget_type": wtype,
            "id": field_id,
            "label": label,
            "required": bool(required),
        }

        if field_type in ("choice", "multi_choice"):
            options = [o.strip() for o in (options_text or "").split(",") if o.strip()]
            if len(options) < 2:
                return (*_nu, _err("At least 2 options required."))
            field["options"] = options

        elif field_type == "span_annotation":
            entity_types = [e.strip() for e in (options_text or "").split(",") if e.strip()]
            field["entity_types"] = entity_types

        elif field_type in ("numeric", "range_slider"):
            for k, v in [("min_value", min_val), ("max_value", max_val), ("step", step)]:
                if v is not None:
                    field[k] = v

        elif field_type == "text":
            if (placeholder or "").strip():
                field["placeholder"] = placeholder.strip()

        fields.append(field)
        return fields, "", "", None, None, None, "", False, _ok(f"Added '{label}'.")

    @app.callback(
        Output("schema-builder-field-list", "children"),
        Input("schema-builder-fields", "data"),
    )
    def render_field_list(fields):
        if not fields:
            return dmc.Text("No fields added yet.", size="sm", c="dimmed")
        return [_field_row(f, i) for i, f in enumerate(fields)]

    @app.callback(
        Output("schema-builder-fields", "data", allow_duplicate=True),
        Input({"type": "schema-field-delete", "index": ALL}, "n_clicks"),
        State("schema-builder-fields", "data"),
        prevent_initial_call=True,
    )
    def delete_field(n_clicks_list, fields):
        if not ctx.triggered or not ctx.triggered[0].get("value"):
            return no_update
        index = ctx.triggered_id["index"]
        fields = list(fields or [])
        if 0 <= index < len(fields):
            fields.pop(index)
        return fields

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
    data_schema = []
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
        entry["widget"] = widget
        data_schema.append(entry)
    return {
        "spec_version": "1.0",
        "title": title or "Annotation Schema",
        "data_schema": data_schema,
    }


def _field_row(field: dict, index: int) -> dmc.Paper:
    ftype = field["type"]
    wtype = field.get("widget_type", "")
    default_wtype = _DEFAULT_WIDGET_TYPE.get(ftype, "")

    badges = [dmc.Badge(ftype, color=_TYPE_COLORS.get(ftype, "gray"), size="xs")]
    if wtype and wtype != default_wtype:
        badges.append(dmc.Badge(wtype.replace("_", " "), color="gray", variant="outline", size="xs"))

    preview = None
    if ftype in ("choice", "multi_choice"):
        opts = field.get("options", [])
        preview = ", ".join(opts[:4]) + ("…" if len(opts) > 4 else "")
    elif ftype == "span_annotation":
        et = field.get("entity_types", [])
        preview = ", ".join(et[:4]) + ("…" if len(et) > 4 else "") if et else "unlabeled"

    right = dmc.Group(badges + ([dmc.Text(preview, size="xs", c="dimmed")] if preview else []), gap="xs")

    return dmc.Paper(
        dmc.Group(
            [
                dmc.Group([dmc.Text(field["label"] or "(divider)", size="sm", fw=500), right], gap="xs"),
                dmc.ActionIcon(
                    DashIconify(icon="tabler:trash", width=14),
                    id={"type": "schema-field-delete", "index": index},
                    n_clicks=0,
                    color="red",
                    variant="subtle",
                    size="sm",
                ),
            ],
            justify="space-between",
            wrap="nowrap",
        ),
        p="xs",
        withBorder=True,
        radius="sm",
        mb="xs",
    )


def _err(msg: str):
    return dmc.Text(msg, size="xs", c="red")


def _ok(msg: str):
    return dmc.Text(msg, size="xs", c="blue")
