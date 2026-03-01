"""JSON schema loader for Tater.

Converts a tater JSON schema file into a Pydantic model and widget list,
so users don't need to write Python to define their annotation schema.

Usage::

    from tater.loaders import load_schema

    model, widgets = load_schema("data/simple_schema.json")
    app = TaterApp(title="My App", schema_model=model)
    app.load_documents(args.documents)
    app.set_annotation_widgets(widgets)
    app.run(...)

Schema format::

    {
      "spec_version": "1.0",
      "data_schema": [
        {
          "id": "sentiment",
          "type": "single_choice",
          "options": ["positive", "negative", "neutral"],
          "required": true,
          "label": "Sentiment",
          "description": "Overall tone of the document",
          "widget": {"type": "radio_group", "orientation": "vertical"}
        },
        {
          "id": "address",
          "type": "group",
          "label": "Location",
          "fields": [
            {"id": "city",    "type": "free_text", "label": "City"},
            {"id": "country", "type": "free_text", "label": "Country"}
          ]
        },
        {
          "id": "pets",
          "type": "list",
          "label": "Pets",
          "item_fields": [
            {"id": "name", "type": "free_text",     "label": "Name"},
            {"id": "kind", "type": "single_choice", "label": "Kind",
             "options": ["cat", "dog"]}
          ]
        }
      ]
    }

The ``widget`` object is optional on leaf fields. Without it, a sensible
default widget is chosen for each field type.
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
from tater.widgets.group import GroupWidget
from tater.widgets.listable import ListableWidget
from tater.models.span import SpanAnnotation


def _humanize(field_id: str) -> str:
    """Convert snake_case or kebab-case id to Title Case label."""
    return field_id.replace("_", " ").replace("-", " ").title()


def _make_literal(options: list[str]) -> Any:
    """Dynamically create Literal[opt1, opt2, ...] from a list of strings."""
    return Literal[tuple(options)]


def _to_classname(field_id: str) -> str:
    """Convert snake_case or kebab-case id to PascalCase for model class naming."""
    return "".join(part.title() for part in field_id.replace("-", "_").split("_"))


def parse_schema(data: dict) -> tuple[type[BaseModel], list[TaterWidget]]:
    """Parse a schema dict into a Pydantic model and widget list.

    Args:
        data: Parsed JSON dict with a ``data_schema`` list. Each field entry
              may include an optional ``widget`` object for UI configuration.

    Returns:
        A ``(model_class, widgets)`` tuple ready to pass to
        ``TaterApp(schema_model=model)`` and ``set_annotation_widgets(widgets)``.
    """
    model_fields: dict[str, Any] = {}
    widgets: list[TaterWidget] = []

    for spec in data.get("data_schema", []):
        fid = spec["id"]
        field_def, widget = _process_field(spec, fid)
        model_fields[fid] = field_def
        widgets.append(widget)

    return create_model("AnnotationModel", **model_fields), widgets


def _process_field(spec: dict, local_id: str) -> tuple[Any, TaterWidget]:
    """Recursively process one field spec into a (pydantic_field_def, widget) pair.

    Child widgets for ``group`` and ``list`` types use their local id only —
    ``GroupWidget._finalize_paths`` and ``ListableWidget._render_item_widgets``
    propagate the full path automatically.
    """
    ftype: str = spec["type"]
    label: str = spec.get("label") or _humanize(local_id)
    description: str | None = spec.get("description")

    if ftype == "group":
        child_model_fields: dict[str, Any] = {}
        child_widgets: list[TaterWidget] = []
        for child_spec in spec.get("fields", []):
            child_id = child_spec["id"]
            child_def, child_widget = _process_field(child_spec, child_id)
            child_model_fields[child_id] = child_def
            child_widgets.append(child_widget)
        sub_model = create_model(_to_classname(local_id), **child_model_fields)
        return (Optional[sub_model], None), GroupWidget(
            local_id, label=label, description=description, children=child_widgets
        )

    if ftype == "list":
        item_model_fields: dict[str, Any] = {}
        item_widgets: list[TaterWidget] = []
        for child_spec in spec.get("item_fields", []):
            child_id = child_spec["id"]
            child_def, child_widget = _process_field(child_spec, child_id)
            item_model_fields[child_id] = child_def
            item_widgets.append(child_widget)
        item_model = create_model(_to_classname(local_id) + "Item", **item_model_fields)
        widget_spec: dict = spec.get("widget") or {}
        return (list[item_model], Field(default_factory=list)), ListableWidget(
            local_id,
            label=label,
            description=description,
            item_widgets=item_widgets,
            add_label=widget_spec.get("add_label", "Add"),
            delete_label=widget_spec.get("delete_label", "Delete"),
            initial_count=widget_spec.get("initial_count", 1),
        )

    # --- Leaf field types ---
    options: list[str] = spec.get("options", [])
    required: bool = spec.get("required", False)
    default = spec.get("default")
    widget_spec = spec.get("widget") or {}
    widget_type: str | None = widget_spec.get("type")

    if ftype == "single_choice":
        lit = _make_literal(options)
        field_def = (Optional[lit], default)
    elif ftype == "multi_choice":
        lit = _make_literal(options)
        field_def = (list[lit], Field(default_factory=list))
    elif ftype == "free_text":
        field_def = (Optional[str], default)
    elif ftype == "boolean":
        field_def = (bool, default if default is not None else False)
    elif ftype == "numeric":
        field_def = (Optional[float], default)
    elif ftype == "span_annotation":
        field_def = (list[SpanAnnotation], Field(default_factory=list))
    else:
        raise ValueError(f"Unknown field type {ftype!r} for field {local_id!r}")

    return field_def, _build_widget(
        local_id, ftype, required, label, description, widget_type, widget_spec, spec
    )


def _build_widget(
    fid: str,
    ftype: str,
    required: bool,
    label: str,
    description: str | None,
    widget_type: str | None,
    widget_spec: dict,
    spec: dict,
) -> TaterWidget:
    if ftype == "single_choice":
        if widget_type == "radio_group":
            return RadioGroupWidget(
                fid, label=label, description=description, required=required,
                vertical=widget_spec.get("orientation") == "vertical",
            )
        if widget_type == "select":
            return SelectWidget(fid, label=label, description=description, required=required)
        if widget_type == "chip_group":
            return ChipGroupWidget(fid, label=label, description=description, required=required)
        return SegmentedControlWidget(fid, label=label, description=description, required=required)

    if ftype == "multi_choice":
        if widget_type == "chip_group":
            return ChipGroupWidget(fid, label=label, description=description, required=required)
        return MultiSelectWidget(fid, label=label, description=description, required=required)

    if ftype == "free_text":
        return TextInputWidget(
            fid, label=label, description=description, required=required,
            placeholder=widget_spec.get("placeholder"),
        )

    if ftype == "boolean":
        if widget_type == "switch":
            return SwitchWidget(fid, label=label, description=description)
        return CheckboxWidget(fid, label=label, description=description)

    if ftype == "numeric":
        if widget_type == "slider":
            return SliderWidget(
                fid, label=label, description=description, required=required,
                min_value=widget_spec.get("min_value", 0),
                max_value=widget_spec.get("max_value", 100),
                step=widget_spec.get("step"),
                default=spec.get("default"),
            )
        return NumberInputWidget(
            fid, label=label, description=description, required=required,
            min_value=widget_spec.get("min_value"),
            max_value=widget_spec.get("max_value"),
            step=widget_spec.get("step"),
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
