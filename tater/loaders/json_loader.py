"""JSON schema loader for Tater.

Converts a tater JSON schema file into a Pydantic model and widget list.
Schema files are used with the ``tater --schema`` CLI flag:

    tater --schema apps/schema/simple.json --documents data/documents.json

Schema format::

    {
      "spec_version": "1.0",
      "title": "My Annotation App",
      "description": "Optional subtitle shown below the title.",
      "hierarchies": {
        "ontology": "data/my_ontology.yaml",
        "regions": {"Head": ["Brain", "Eye"], "Thorax": ["Lung", "Heart"]}
      },
      "data_schema": [
        {
          "id": "sentiment",
          "type": "choice",
          "options": ["positive", "negative", "neutral"],
          "required": true,
          "label": "Sentiment",
          "description": "Overall tone of the document",
          "widget": {"type": "radio_group", "orientation": "vertical"}
        },
        {
          "id": "diagnosis",
          "type": "hierarchical_label",
          "hierarchy_ref": "ontology",
          "label": "Diagnosis",
          "widget": {"searchable": true}
        },
        {
          "id": "address",
          "type": "group",
          "label": "Location",
          "fields": [
            {"id": "city",    "type": "text", "label": "City"},
            {"id": "country", "type": "text", "label": "Country"}
          ]
        },
        {
          "id": "pets",
          "type": "repeater",
          "label": "Pets",
          "item_fields": [
            {"id": "name", "type": "text",   "label": "Name"},
            {"id": "kind", "type": "choice", "label": "Kind",
             "options": ["cat", "dog"]}
          ]
        }
      ]
    }

The ``widget`` object is optional on leaf fields. Without it, a sensible
default widget is chosen for each field type.

Field types:
  ``boolean``           — true/false (default: CheckboxWidget)
  ``choice``            — single selection from ``options`` (default: SegmentedControlWidget)
  ``multi_choice``      — multiple selections from ``options`` (default: MultiSelectWidget)
  ``numeric``           — number (default: NumberInputWidget)
  ``range_slider``      — numeric range; requires ``min_value``/``max_value`` in ``widget``
  ``text``              — free text (default: TextInputWidget)
  ``span_annotation``   — text span labelling (SpanAnnotationWidget)
  ``hierarchical_label``— tree-based label (default: HierarchicalLabelTagsWidget)
  ``group``             — nested sub-model with ``fields``
  ``repeater``          — repeatable list of sub-items with ``item_fields``
                          (widget type override: ``tabs`` or ``accordion``)
  ``divider``           — labeled section break; no ``id`` required; supports ``label``,
                          ``description``

Widget override types (``"widget": {"type": "..."}``):
  ``radio_group``              — for ``choice`` fields
  ``select``                   — for ``choice`` fields
  ``chip_radio``               — for ``choice`` fields
  ``checkbox_group``           — for ``multi_choice`` fields
  ``text_area``                — for ``text`` fields
  ``switch``                   — for ``boolean`` fields
  ``chip_boolean``             — for ``boolean`` fields
  ``slider``                   — for ``numeric`` fields
  ``hierarchical_label_compact`` — for ``hierarchical_label`` fields
  ``hierarchical_label_full``    — for ``hierarchical_label`` fields
  ``hierarchical_label_tags``    — for ``hierarchical_label`` fields

Widget options (``"widget": {"option": value}``):
  ``auto_advance``  — ``true`` on ``choice`` or ``boolean`` fields to advance to the next
                      document on selection/toggle

For ``hierarchical_label`` fields, ``hierarchy_ref`` must match a key in the
top-level ``hierarchies`` dict. File paths in ``hierarchies`` are resolved
relative to the schema file's directory when using ``load_schema``.
"""
from __future__ import annotations

import json
import types as _builtin_types
import typing
from pathlib import Path
from typing import Any, Optional, Literal, Union

from pydantic import BaseModel, Field, create_model

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
from tater.widgets.span import SpanAnnotationWidget, EntityType
from tater.widgets.divider import DividerWidget
from tater.widgets.group import GroupWidget
from tater.widgets.repeater import ListableWidget, TabsWidget, AccordionWidget
from tater.widgets.hierarchical_label import (
    HierarchicalLabelCompactWidget,
    HierarchicalLabelFullWidget,
    HierarchicalLabelTagsWidget,
    build_tree,
    load_hierarchy_from_yaml,
    Node,
)
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

    # Literal["a", "b"] → SegmentedControlWidget
    if origin is Literal:
        return _build_widget(field_name, "choice", False, label, None, None, {}, {}, {})

    # list[X]
    if origin is list:
        item_type = args[0] if args else None
        if item_type is None:
            return None
        item_origin = typing.get_origin(item_type)

        # list[Literal[...]] → MultiSelectWidget
        if item_origin is Literal:
            return _build_widget(field_name, "multi_choice", False, label, None, None, {}, {}, {})

        # list[SpanAnnotation] → SpanAnnotationWidget
        if item_type is SpanAnnotation:
            return _build_widget(field_name, "span_annotation", False, label, None, None, {}, {}, {})

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
        return _build_widget(field_name, "boolean", False, label, None, None, {}, {}, {})

    if field_type is str:
        return _build_widget(field_name, "text", False, label, None, None, {}, {}, {})

    if field_type in (float, int):
        return _build_widget(field_name, "numeric", False, label, None, None, {}, {}, {})

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
                   indistinguishable from a plain text field) and
                   ``SpanAnnotationWidget`` (auto-generation produces a widget
                   with no entity types). Use overrides for any other field
                   where a non-default widget is desired.

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


def _load_hierarchies(data: dict, base_dir: Path) -> dict[str, Node]:
    """Build the named hierarchy map from the top-level ``hierarchies`` section."""
    hierarchy_map: dict[str, Node] = {}
    for name, source in data.get("hierarchies", {}).items():
        if isinstance(source, str):
            path = Path(source)
            if not path.is_absolute():
                path = base_dir / path
            hierarchy_map[name] = load_hierarchy_from_yaml(path)
        else:
            hierarchy_map[name] = build_tree(source)
    return hierarchy_map


def parse_schema(
    data: dict, base_dir: Path | None = None
) -> tuple[type[BaseModel], list[TaterWidget]]:
    """Parse a schema dict into a Pydantic model and widget list.

    Args:
        data: Parsed JSON dict with a ``data_schema`` list. Each field entry
              may include an optional ``widget`` object for UI configuration.
        base_dir: Directory used to resolve relative ``hierarchy_file`` paths.
                  Defaults to the current working directory.

    Returns:
        A ``(model_class, widgets)`` tuple ready to pass to
        ``TaterApp(schema_model=model)`` and ``set_annotation_widgets(widgets)``.
    """
    base_dir = base_dir or Path.cwd()
    hierarchy_map = _load_hierarchies(data, base_dir)

    model_fields: dict[str, Any] = {}
    widgets: list[TaterWidget] = []

    for spec in data.get("data_schema", []):
        if spec.get("type") == "divider":
            widgets.append(DividerWidget(
                label=spec.get("label", ""),
                description=spec.get("description"),
            ))
            continue
        fid = spec["id"]
        field_def, widget = _process_field(spec, fid, hierarchy_map)
        model_fields[fid] = field_def
        widgets.append(widget)

    return create_model("AnnotationModel", **model_fields), widgets


def _process_field(
    spec: dict, local_id: str, hierarchy_map: dict[str, Node]
) -> tuple[Any, TaterWidget]:
    """Recursively process one field spec into a (pydantic_field_def, widget) pair.

    Child widgets for ``group`` and ``repeater`` types use their local id only —
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
            child_def, child_widget = _process_field(child_spec, child_id, hierarchy_map)
            child_model_fields[child_id] = child_def
            child_widgets.append(child_widget)
        sub_model = create_model(_to_classname(local_id), **child_model_fields)
        return (Optional[sub_model], None), GroupWidget(
            local_id, label=label, description=description, children=child_widgets
        )

    if ftype == "repeater":
        item_model_fields: dict[str, Any] = {}
        item_widgets: list[TaterWidget] = []
        for child_spec in spec.get("item_fields", []):
            child_id = child_spec["id"]
            child_def, child_widget = _process_field(child_spec, child_id, hierarchy_map)
            item_model_fields[child_id] = child_def
            item_widgets.append(child_widget)
        item_model = create_model(_to_classname(local_id) + "Item", **item_model_fields)
        widget_spec: dict = spec.get("widget") or {}
        widget_type = widget_spec.get("type")
        item_label = widget_spec.get("item_label", "Item")
        repeater_cls = {"tabs": TabsWidget, "accordion": AccordionWidget}.get(widget_type, ListableWidget)
        return (list[item_model], Field(default_factory=list)), repeater_cls(
            local_id,
            label=label,
            description=description,
            item_widgets=item_widgets,
            item_label=item_label,
        )

    # --- Leaf field types ---
    options: list[str] = spec.get("options", [])
    required: bool = spec.get("required", False)
    default = spec.get("default")
    widget_spec = spec.get("widget") or {}
    widget_type: str | None = widget_spec.get("type")

    if ftype == "choice":
        lit = _make_literal(options)
        field_def = (Optional[lit], default)
    elif ftype == "multi_choice":
        lit = _make_literal(options)
        field_def = (list[lit], Field(default_factory=list))
    elif ftype == "text":
        field_def = (Optional[str], default)
    elif ftype == "boolean":
        field_def = (bool, default if default is not None else False)
    elif ftype == "numeric":
        field_def = (Optional[float], default)
    elif ftype == "range_slider":
        _min = float(widget_spec.get("min_value", 0))
        _max = float(widget_spec.get("max_value", 100))
        field_def = (list[float], Field(default_factory=lambda a=_min, b=_max: [a, b]))
    elif ftype == "span_annotation":
        field_def = (list[SpanAnnotation], Field(default_factory=list))
    elif ftype == "hierarchical_label":
        field_def = (Optional[str], None)
    else:
        raise ValueError(f"Unknown field type {ftype!r} for field {local_id!r}")

    widget = _build_widget(
        local_id, ftype, required, label, description, widget_type, widget_spec, spec,
        hierarchy_map,
    )
    if widget_spec.get("auto_advance") and ftype in ("choice", "boolean"):
        widget.auto_advance = True
    condition = spec.get("conditional_on")
    if condition is not None:
        widget.conditional_on(condition["field"], bool(condition["value"]))
    return field_def, widget


def _build_widget(
    fid: str,
    ftype: str,
    required: bool,
    label: str,
    description: str | None,
    widget_type: str | None,
    widget_spec: dict,
    spec: dict,
    hierarchy_map: dict[str, Node],
) -> TaterWidget:
    if ftype == "choice":
        if widget_type == "radio_group":
            return RadioGroupWidget(
                fid, label=label, description=description, required=required,
                vertical=widget_spec.get("orientation") == "vertical",
            )
        if widget_type == "select":
            return SelectWidget(fid, label=label, description=description, required=required)
        if widget_type == "chip_radio":
            return ChipRadioWidget(
                fid, label=label, description=description, required=required,
                vertical=widget_spec.get("orientation") == "vertical",
            )
        return SegmentedControlWidget(
            fid, label=label, description=description, required=required,
            vertical=widget_spec.get("orientation") == "vertical",
        )

    if ftype == "multi_choice":
        if widget_type == "checkbox_group":
            return CheckboxGroupWidget(
                fid, label=label, description=description, required=required,
                vertical=widget_spec.get("orientation") == "vertical",
            )
        return MultiSelectWidget(fid, label=label, description=description, required=required)

    if ftype == "text":
        if widget_type == "text_area":
            return TextAreaWidget(
                fid, label=label, description=description, required=required,
                placeholder=widget_spec.get("placeholder"),
            )
        return TextInputWidget(
            fid, label=label, description=description, required=required,
            placeholder=widget_spec.get("placeholder"),
        )

    if ftype == "boolean":
        if widget_type == "switch":
            return SwitchWidget(fid, label=label, description=description)
        if widget_type == "chip_boolean":
            return ChipWidget(fid, label=label, description=description)
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

    if ftype == "range_slider":
        return RangeSliderWidget(
            fid, label=label, description=description, required=required,
            min_value=widget_spec.get("min_value", 0),
            max_value=widget_spec.get("max_value", 100),
            step=widget_spec.get("step"),
            default=spec.get("default"),
        )

    if ftype == "span_annotation":
        entity_types = [EntityType(name=et) for et in spec.get("entity_types", [])]
        return SpanAnnotationWidget(fid, label=label, entity_types=entity_types, description=description)

    if ftype == "hierarchical_label":
        ref = spec.get("hierarchy_ref")
        hierarchy = hierarchy_map.get(ref) if ref else None
        searchable = widget_spec.get("searchable", True)
        if widget_type == "hierarchical_label_compact":
            return HierarchicalLabelCompactWidget(
                fid, label=label, description=description,
                hierarchy=hierarchy, searchable=searchable,
            )
        if widget_type == "hierarchical_label_full":
            return HierarchicalLabelFullWidget(
                fid, label=label, description=description,
                hierarchy=hierarchy, searchable=searchable,
            )
        if widget_type == "hierarchical_label_tags":
            return HierarchicalLabelTagsWidget(
                fid, label=label, description=description,
                hierarchy=hierarchy, searchable=searchable,
            )
        return HierarchicalLabelTagsWidget(
            fid, label=label, description=description,
            hierarchy=hierarchy, searchable=searchable,
        )

    raise ValueError(f"Unknown field type {ftype!r}")


def load_schema(path: str | Path) -> dict:
    """Load a schema JSON file and return a config dict.

    Args:
        path: Path to a tater JSON schema file. Relative paths in the
              ``hierarchies`` section are resolved from this file's directory.

    Returns:
        A dict with keys ``schema_model``, ``widgets``, ``title``,
        ``description``.
    """
    path = Path(path)
    with open(path) as f:
        data = json.load(f)
    schema_model, widgets = parse_schema(data, base_dir=path.parent)
    return {
        "schema_model": schema_model,
        "widgets": widgets,
        "title": data.get("title"),
        "description": data.get("description"),
        "instructions": data.get("instructions"),
    }
