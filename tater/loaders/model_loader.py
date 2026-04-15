"""Widget class registry and model-driven widget auto-generation."""
from __future__ import annotations

import types as _builtin_types
import typing
from typing import Any, Literal, Union

from pydantic import BaseModel

from tater.widgets.base import TaterWidget
from tater.widgets.segmented_control import SegmentedControlWidget
from tater.widgets.radio_group import RadioGroupWidget
from tater.widgets.select import SelectWidget
from tater.widgets.multiselect import MultiSelectWidget
from tater.widgets.checkbox_group import CheckboxGroupWidget
from tater.widgets.chip_radio import ChipRadioWidget
from tater.widgets.text_input import TextInputWidget
from tater.widgets.checkbox import CheckboxWidget
from tater.widgets.switch import SwitchWidget
from tater.widgets.chip import ChipWidget
from tater.widgets.number_input import NumberInputWidget
from tater.widgets.slider import SliderWidget
from tater.widgets.textarea import TextAreaWidget
from tater.widgets.range_slider import RangeSliderWidget
from tater.widgets.span import SpanAnnotationWidget
from tater.widgets.divider import DividerWidget
from tater.widgets.group import GroupWidget
from tater.widgets.repeater import ListableWidget, TabsWidget, AccordionWidget
from tater.widgets.hierarchical_label import (
    HierarchicalLabelCompactWidget,
    HierarchicalLabelFullWidget,
    HierarchicalLabelTagsWidget,
    HierarchicalLabelMultiWidget,
)
from tater.models.span import SpanAnnotation


def _humanize(field_id: str) -> str:
    """Convert snake_case or kebab-case id to Title Case label."""
    return field_id.replace("_", " ").replace("-", " ").title()


# Maps widget type strings to widget classes.
# Used by json_loader._build_widget_from_spec to look up classes by name.
WIDGET_CLASS: dict[str, type[TaterWidget]] = {
    # boolean
    "checkbox":                   CheckboxWidget,
    "switch":                     SwitchWidget,
    "chip_boolean":               ChipWidget,

    # choice
    "segmented_control":          SegmentedControlWidget,
    "radio_group":                RadioGroupWidget,
    "select":                     SelectWidget,
    "chip_radio":                 ChipRadioWidget,

    # multi-choice
    "multi_select":               MultiSelectWidget,
    "checkbox_group":             CheckboxGroupWidget,

    # numeric
    "number_input":               NumberInputWidget,
    "slider":                     SliderWidget,
    "range_slider":               RangeSliderWidget,

    # text
    "text_input":                 TextInputWidget,
    "text_area":                  TextAreaWidget,

    # span annotation
    "span_annotation":            SpanAnnotationWidget,

    # hierarchical label
    "hierarchical_label_tags":    HierarchicalLabelTagsWidget,
    "hierarchical_label_compact": HierarchicalLabelCompactWidget,
    "hierarchical_label_full":    HierarchicalLabelFullWidget,
    "hierarchical_label_multi":   HierarchicalLabelMultiWidget,

    # group widget doesn't have a type string since it's not directly specifiable in JSON

    # repeaters
    "listable":                   ListableWidget,
    "tabs":                       TabsWidget,
    "accordion":                  AccordionWidget,

    # structural
    "divider":                    DividerWidget,
}


# Maps field type strings to default widget classes.
# Used by _widget_from_field_type for auto-generation; change an entry here
# to change the default widget for that field type across the whole app.
DEFAULT_WIDGET: dict[str, type[TaterWidget]] = {
    "choice":             SegmentedControlWidget,
    "multi_choice":       MultiSelectWidget,
    "text":               TextInputWidget,
    "boolean":            CheckboxWidget,
    "numeric":            NumberInputWidget,
    "range_slider":       RangeSliderWidget,
    "span_annotation":    SpanAnnotationWidget,
    "hierarchical_label": HierarchicalLabelTagsWidget,
}


def _widget_from_field_type(field_name: str, field_type: Any) -> TaterWidget | None:
    """Build a default widget from a Pydantic field's type hint.

    Returns ``None`` for unrecognized types.
    """
    label = _humanize(field_name)
    origin = typing.get_origin(field_type)
    args = typing.get_args(field_type)

    # Unwrap Optional[X] / Union[X, None] / X | None (Python 3.10+)
    is_union = origin is Union or (
        hasattr(_builtin_types, "UnionType")
        and isinstance(field_type, _builtin_types.UnionType)
    )
    if is_union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _widget_from_field_type(field_name, non_none[0])
        return None

    # Literal["a", "b"] → choice default
    if origin is Literal:
        return DEFAULT_WIDGET["choice"](field_name, label=label)

    # list[X]
    if origin is list:
        item_type = args[0] if args else None
        if item_type is None:
            return None
        item_origin = typing.get_origin(item_type)

        # list[Literal[...]] → multi_choice default
        if item_origin is Literal:
            return DEFAULT_WIDGET["multi_choice"](field_name, label=label)

        # list[SpanAnnotation] → span_annotation default (no entity types — requires override)
        if item_type is SpanAnnotation:
            return DEFAULT_WIDGET["span_annotation"](field_name, label=label, entity_types=[])

        # list[SubModel] → ListableWidget
        if isinstance(item_type, type) and issubclass(item_type, BaseModel):
            item_widgets = [
                w for w in (
                    _widget_from_field_type(n, fi.annotation)
                    for n, fi in item_type.model_fields.items()
                ) if w is not None
            ]
            return ListableWidget(field_name, label=label, item_widgets=item_widgets)

        return None

    # bool must come before int (bool is a subclass of int)
    if field_type is bool:
        return DEFAULT_WIDGET["boolean"](field_name, label=label)

    if field_type is str:
        return DEFAULT_WIDGET["text"](field_name, label=label)

    if field_type in (float, int):
        return DEFAULT_WIDGET["numeric"](field_name, label=label)

    # SubModel → GroupWidget
    if isinstance(field_type, type) and issubclass(field_type, BaseModel):
        child_widgets = [
            w for w in (
                _widget_from_field_type(n, fi.annotation)
                for n, fi in field_type.model_fields.items()
            ) if w is not None
        ]
        return GroupWidget(field_name, label=label, children=child_widgets)

    return None


def widgets_from_model(
    model: type[BaseModel],
    overrides: list[TaterWidget] | None = None,
) -> list[TaterWidget]:
    """Generate default widgets from a Pydantic model's field type hints.

    Uses the same widget defaults as the JSON schema loader. Unrecognized
    field types are silently skipped.

    Args:
        model: A Pydantic ``BaseModel`` subclass.
        overrides: Widgets to use in place of the generated defaults. Matched
                   by field name. Two widget types **must** always be supplied
                   via overrides and cannot be usefully auto-generated:
                   ``HierarchicalLabel*`` widgets (``Optional[str]`` is
                   indistinguishable from a plain text field without a
                   hierarchy) and ``SpanAnnotationWidget`` (auto-generation
                   produces a widget with no entity types). Use overrides for
                   any other field where a non-default widget is desired.

    Returns:
        A list of ``TaterWidget`` instances ready to pass to
        ``set_annotation_widgets``, in model field order.
    """
    override_map = {w.schema_field: w for w in (overrides or [])}
    result = []
    for name, fi in model.model_fields.items():
        if name in override_map:
            result.append(override_map[name])
        else:
            w = _widget_from_field_type(name, fi.annotation)
            if w is not None:
                result.append(w)
    return result
