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
    {"value": "boolean", "label": "Boolean (checkbox)"},
    {"value": "text", "label": "Text"},
    {"value": "numeric", "label": "Numeric"},
    {"value": "divider", "label": "Divider (section separator)"},
]

_TYPE_COLORS = {
    "choice": "blue",
    "multi_choice": "cyan",
    "boolean": "green",
    "text": "violet",
    "numeric": "orange",
    "divider": "gray",
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
            dmc.Checkbox(
                id="schema-builder-field-required",
                label="Required",
                checked=False,
            ),
            # Options section — shown for choice / multi_choice
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
            # Numeric section — shown for numeric
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
            # Text section — shown for text
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
                        "Cancel",
                        id="schema-builder-cancel-btn",
                        variant="subtle",
                        color="gray",
                    ),
                ],
                justify="flex-end",
                mt="md",
            ),
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
        Input("schema-builder-field-type", "value"),
    )
    def show_type_options(field_type):
        return (
            _SHOW if field_type in ("choice", "multi_choice") else _HIDE,
            _SHOW if field_type == "numeric" else _HIDE,
            _SHOW if field_type == "text" else _HIDE,
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
    def add_field(_, field_type, label, required, options_text, min_val, max_val, step, placeholder, fields):
        label = (label or "").strip()
        if not label:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, _err("Label is required.")

        options = []
        if field_type in ("choice", "multi_choice"):
            options = [o.strip() for o in (options_text or "").split(",") if o.strip()]
            if len(options) < 2:
                return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, _err("At least 2 options required.")

        fields = list(fields or [])

        if field_type == "divider":
            field = {"type": "divider", "label": label}
        else:
            field_id = _label_to_id(label)
            if field_id in {f["id"] for f in fields if f["type"] != "divider"}:
                return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, _err(f"A field with id '{field_id}' already exists.")
            field = {"type": field_type, "id": field_id, "label": label, "required": bool(required)}
            if field_type in ("choice", "multi_choice"):
                field["options"] = options
            if field_type == "text" and (placeholder or "").strip():
                field["placeholder"] = placeholder.strip()
            if field_type == "numeric":
                for key, val in [("min_value", min_val), ("max_value", max_val), ("step", step)]:
                    if val is not None:
                        field[key] = val

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
        Input("schema-builder-fields", "data"),
        Input("schema-builder-title", "value"),
    )
    def generate_schema(fields, title):
        if not fields or not any(f["type"] != "divider" for f in fields):
            return None, True
        return _fields_to_schema(fields, title or ""), False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _label_to_id(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_") or "field"


_DEFAULT_WIDGET_TYPE = {
    "choice": "segmented_control",
    "multi_choice": "multi_select",
    "boolean": "checkbox",
    "text": "text_input",
    "numeric": "number_input",
}


def _fields_to_schema(fields: list, title: str) -> dict:
    data_schema = []
    for field in fields:
        if field["type"] == "divider":
            data_schema.append({"widget": {"type": "divider", "label": field["label"]}})
            continue
        entry = {"id": field["id"], "type": field["type"]}
        if field["type"] in ("choice", "multi_choice"):
            entry["options"] = field["options"]
        widget = {"type": _DEFAULT_WIDGET_TYPE[field["type"]], "label": field["label"]}
        if field.get("required"):
            widget["required"] = True
        if field["type"] == "text" and field.get("placeholder"):
            widget["placeholder"] = field["placeholder"]
        if field["type"] == "numeric":
            for k in ("min_value", "max_value", "step"):
                if field.get(k) is not None:
                    widget[k] = field[k]
        entry["widget"] = widget
        data_schema.append(entry)
    return {
        "spec_version": "1.0",
        "title": title or "Annotation Schema",
        "data_schema": data_schema,
    }


def _field_row(field: dict, index: int) -> dmc.Paper:
    field_type = field["type"]
    parts = [dmc.Badge(field_type, color=_TYPE_COLORS.get(field_type, "gray"), size="xs")]
    if field_type in ("choice", "multi_choice"):
        opts = field.get("options", [])
        preview = ", ".join(opts[:4]) + ("…" if len(opts) > 4 else "")
        parts.append(dmc.Text(preview, size="xs", c="dimmed"))
    return dmc.Paper(
        dmc.Group(
            [
                dmc.Group([dmc.Text(field["label"], size="sm", fw=500), dmc.Group(parts, gap="xs")], gap="xs"),
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
