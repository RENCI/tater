"""JSON schema loader for Tater.

Converts a tater JSON schema file into a Pydantic model and widget list,
so users don't need to write Python to define their annotation schema.

Usage::

    from tater.schema import load_schema

    model, widgets = load_schema("data/simple_schema.json")
    app = TaterApp(title="My App", schema_model=model)
    app.load_documents(args.documents)
    app.set_annotation_widgets(widgets)
    app.run(...)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Literal

from pydantic import BaseModel, Field, create_model

from tater.widgets.base import TaterWidget
from tater.widgets.segmented_control import SegmentedControlWidget
from tater.widgets.radio_group import RadioGroupWidget
from tater.widgets.select import SelectWidget
from tater.widgets.chip_group import ChipGroupWidget
from tater.widgets.multiselect import MultiSelectWidget
from tater.widgets.text_input import TextInputWidget
from tater.widgets.checkbox import CheckboxWidget
from tater.widgets.switch import SwitchWidget
from tater.widgets.number_input import NumberInputWidget
from tater.widgets.slider import SliderWidget
from tater.widgets.span import SpanAnnotationWidget, EntityType
from tater.models.span import SpanAnnotation


def _humanize(field_id: str) -> str:
    """Convert snake_case or kebab-case id to Title Case label."""
    return field_id.replace("_", " ").replace("-", " ").title()


def _make_literal(options: list[str]) -> Any:
    """Dynamically create Literal[opt1, opt2, ...] from a list of strings."""
    return Literal[tuple(options)]


def parse_schema(data: dict) -> tuple[type[BaseModel], list[TaterWidget]]:
    """Parse a schema dict into a Pydantic model and widget list.

    Args:
        data: Parsed JSON dict with ``data_schema`` (required) and
              optional ``ui`` sections.

    Returns:
        A ``(model_class, widgets)`` tuple ready to pass to
        ``TaterApp(schema_model=model)`` and ``set_annotation_widgets(widgets)``.
    """
    field_specs: list[dict] = data.get("data_schema", [])
    ui_list: list[dict] = data.get("ui", [])
    ui_map: dict[str, dict] = {entry["schema_id"]: entry for entry in ui_list}

    model_fields: dict[str, Any] = {}
    widgets: list[TaterWidget] = []

    for spec in field_specs:
        fid: str = spec["id"]
        ftype: str = spec["type"]
        options: list[str] = spec.get("options", [])
        required: bool = spec.get("required", False)
        default = spec.get("default", None)
        schema_description: str | None = spec.get("description")

        ui = ui_map.get(fid, {})
        label: str = ui.get("label") or _humanize(fid)
        description: str | None = ui.get("description") or schema_description

        # Build Pydantic field annotation and default
        if ftype == "single_choice":
            lit = _make_literal(options)
            model_fields[fid] = (Optional[lit], default)

        elif ftype == "multi_choice":
            lit = _make_literal(options)
            model_fields[fid] = (list[lit], Field(default_factory=list))

        elif ftype == "free_text":
            model_fields[fid] = (Optional[str], default)

        elif ftype == "boolean":
            bool_default = default if default is not None else False
            model_fields[fid] = (bool, bool_default)

        elif ftype == "numeric":
            model_fields[fid] = (Optional[float], default)

        elif ftype == "span_annotation":
            model_fields[fid] = (list[SpanAnnotation], Field(default_factory=list))

        else:
            raise ValueError(f"Unknown field type {ftype!r} for field {fid!r}")

        # Build widget
        widget_name: str | None = ui.get("widget")
        widgets.append(
            _build_widget(fid, ftype, required, label, description, widget_name, ui, spec)
        )

    model = create_model("AnnotationModel", **model_fields)
    return model, widgets


def _build_widget(
    fid: str,
    ftype: str,
    required: bool,
    label: str,
    description: str | None,
    widget_name: str | None,
    ui: dict,
    spec: dict,
) -> TaterWidget:
    if ftype == "single_choice":
        if widget_name == "radio_group":
            return RadioGroupWidget(
                fid, label=label, description=description, required=required,
                vertical=ui.get("orientation") == "vertical",
            )
        if widget_name == "select":
            return SelectWidget(fid, label=label, description=description, required=required)
        if widget_name == "chip_group":
            return ChipGroupWidget(fid, label=label, description=description, required=required)
        # default
        return SegmentedControlWidget(fid, label=label, description=description, required=required)

    if ftype == "multi_choice":
        if widget_name == "chip_group":
            return ChipGroupWidget(fid, label=label, description=description, required=required)
        # default
        return MultiSelectWidget(fid, label=label, description=description, required=required)

    if ftype == "free_text":
        return TextInputWidget(
            fid, label=label, description=description, required=required,
            placeholder=ui.get("placeholder"),
        )

    if ftype == "boolean":
        if widget_name == "switch":
            return SwitchWidget(fid, label=label, description=description)
        return CheckboxWidget(fid, label=label, description=description)

    if ftype == "numeric":
        if widget_name == "slider":
            return SliderWidget(
                fid, label=label, description=description, required=required,
                min_value=ui.get("min_value", 0),
                max_value=ui.get("max_value", 100),
                step=ui.get("step"),
                default=spec.get("default"),
            )
        return NumberInputWidget(
            fid, label=label, description=description, required=required,
            min_value=ui.get("min_value"),
            max_value=ui.get("max_value"),
            step=ui.get("step"),
        )

    if ftype == "span_annotation":
        entity_types = [EntityType(name=et) for et in spec.get("entity_types", [])]
        return SpanAnnotationWidget(fid, label=label, entity_types=entity_types, description=description)

    raise ValueError(f"Unknown field type {ftype!r}")


def load_schema(path: str | Path) -> tuple[type[BaseModel], list[TaterWidget]]:
    """Load a schema JSON file and return ``(model_class, widgets)``.

    Args:
        path: Path to a tater JSON schema file.

    Returns:
        A ``(model_class, widgets)`` tuple.
    """
    with open(path) as f:
        data = json.load(f)
    return parse_schema(data)
