"""Tests for model_loader.widgets_from_model and _widget_from_field_type."""
from typing import Literal, Optional, List
import pytest
from pydantic import BaseModel, Field

from tater import SpanAnnotation
from tater.loaders.model_loader import widgets_from_model, WIDGET_CLASS, DEFAULT_WIDGET
from tater.widgets.segmented_control import SegmentedControlWidget
from tater.widgets.multiselect import MultiSelectWidget
from tater.widgets.text_input import TextInputWidget
from tater.widgets.checkbox import CheckboxWidget
from tater.widgets.number_input import NumberInputWidget
from tater.widgets.span import SpanAnnotationWidget
from tater.widgets.group import GroupWidget
from tater.widgets.repeater import ListableWidget


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class FlatModel(BaseModel):
    mood: Optional[Literal["happy", "sad"]] = None
    tags: List[Literal["a", "b"]] = Field(default_factory=list)
    name: Optional[str] = None
    active: bool = False
    score: Optional[float] = None
    entities: List[SpanAnnotation] = Field(default_factory=list)


class PetItem(BaseModel):
    kind: Optional[Literal["cat", "dog"]] = None
    indoor: bool = False


class NestedModel(BaseModel):
    pet: Optional[PetItem] = None
    pets: List[PetItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# DEFAULT_WIDGET map coverage
# ---------------------------------------------------------------------------

class TestDefaultWidgetMap:
    def test_all_field_type_keys_present(self):
        expected_keys = {
            "choice", "multi_choice", "text", "boolean",
            "numeric", "range_slider", "span_annotation", "hierarchical_label",
        }
        assert expected_keys <= set(DEFAULT_WIDGET.keys())

    def test_choice_maps_to_segmented_control(self):
        assert DEFAULT_WIDGET["choice"] is SegmentedControlWidget

    def test_multi_choice_maps_to_multi_select(self):
        assert DEFAULT_WIDGET["multi_choice"] is MultiSelectWidget

    def test_text_maps_to_text_input(self):
        assert DEFAULT_WIDGET["text"] is TextInputWidget

    def test_boolean_maps_to_checkbox(self):
        assert DEFAULT_WIDGET["boolean"] is CheckboxWidget

    def test_numeric_maps_to_number_input(self):
        assert DEFAULT_WIDGET["numeric"] is NumberInputWidget

    def test_span_annotation_maps_to_span_widget(self):
        assert DEFAULT_WIDGET["span_annotation"] is SpanAnnotationWidget


# ---------------------------------------------------------------------------
# WIDGET_CLASS map
# ---------------------------------------------------------------------------

class TestWidgetClassMap:
    def test_all_default_types_present(self):
        for key in DEFAULT_WIDGET:
            if key not in ("range_slider", "hierarchical_label"):
                assert key in WIDGET_CLASS or any(
                    v is DEFAULT_WIDGET[key] for v in WIDGET_CLASS.values()
                )

    def test_listable_present(self):
        assert "listable" in WIDGET_CLASS

    def test_divider_present(self):
        assert "divider" in WIDGET_CLASS

    def test_tabs_present(self):
        assert "tabs" in WIDGET_CLASS

    def test_accordion_present(self):
        assert "accordion" in WIDGET_CLASS


# ---------------------------------------------------------------------------
# widgets_from_model — flat model auto-gen
# ---------------------------------------------------------------------------

class TestWidgetsFromModelFlat:
    def test_generates_one_widget_per_field(self):
        widgets = widgets_from_model(FlatModel)
        assert len(widgets) == len(FlatModel.model_fields)

    def test_choice_field_produces_segmented_control(self):
        widgets = widgets_from_model(FlatModel)
        mood_widget = next(w for w in widgets if w.schema_field == "mood")
        assert isinstance(mood_widget, SegmentedControlWidget)

    def test_multi_choice_field_produces_multi_select(self):
        widgets = widgets_from_model(FlatModel)
        tags_widget = next(w for w in widgets if w.schema_field == "tags")
        assert isinstance(tags_widget, MultiSelectWidget)

    def test_text_field_produces_text_input(self):
        widgets = widgets_from_model(FlatModel)
        name_widget = next(w for w in widgets if w.schema_field == "name")
        assert isinstance(name_widget, TextInputWidget)

    def test_boolean_field_produces_checkbox(self):
        widgets = widgets_from_model(FlatModel)
        active_widget = next(w for w in widgets if w.schema_field == "active")
        assert isinstance(active_widget, CheckboxWidget)

    def test_numeric_field_produces_number_input(self):
        widgets = widgets_from_model(FlatModel)
        score_widget = next(w for w in widgets if w.schema_field == "score")
        assert isinstance(score_widget, NumberInputWidget)

    def test_span_annotation_field_produces_span_widget(self):
        widgets = widgets_from_model(FlatModel)
        entities_widget = next(w for w in widgets if w.schema_field == "entities")
        assert isinstance(entities_widget, SpanAnnotationWidget)

    def test_label_humanized_from_field_name(self):
        widgets = widgets_from_model(FlatModel)
        mood_widget = next(w for w in widgets if w.schema_field == "mood")
        assert mood_widget.label == "Mood"


# ---------------------------------------------------------------------------
# widgets_from_model — nested model (group + repeater)
# ---------------------------------------------------------------------------

class TestWidgetsFromModelNested:
    def test_sub_model_produces_group_widget(self):
        widgets = widgets_from_model(NestedModel)
        pet_widget = next(w for w in widgets if w.schema_field == "pet")
        assert isinstance(pet_widget, GroupWidget)

    def test_list_of_sub_model_produces_listable(self):
        widgets = widgets_from_model(NestedModel)
        pets_widget = next(w for w in widgets if w.schema_field == "pets")
        assert isinstance(pets_widget, ListableWidget)

    def test_group_has_child_widgets(self):
        widgets = widgets_from_model(NestedModel)
        pet_widget = next(w for w in widgets if w.schema_field == "pet")
        assert isinstance(pet_widget, GroupWidget)
        assert len(pet_widget.children) == len(PetItem.model_fields)

    def test_listable_has_item_widgets(self):
        widgets = widgets_from_model(NestedModel)
        pets_widget = next(w for w in widgets if w.schema_field == "pets")
        assert isinstance(pets_widget, ListableWidget)
        assert len(pets_widget.item_widgets) == len(PetItem.model_fields)


# ---------------------------------------------------------------------------
# widgets_from_model — overrides
# ---------------------------------------------------------------------------

class TestWidgetsFromModelOverrides:
    def test_override_replaces_auto_gen(self):
        from tater.widgets.radio_group import RadioGroupWidget
        override = RadioGroupWidget("mood", label="Custom Mood")
        widgets = widgets_from_model(FlatModel, overrides=[override])
        mood_widget = next(w for w in widgets if w.schema_field == "mood")
        assert isinstance(mood_widget, RadioGroupWidget)

    def test_non_overridden_fields_still_auto_gen(self):
        from tater.widgets.radio_group import RadioGroupWidget
        override = RadioGroupWidget("mood", label="Custom Mood")
        widgets = widgets_from_model(FlatModel, overrides=[override])
        name_widget = next(w for w in widgets if w.schema_field == "name")
        assert isinstance(name_widget, TextInputWidget)

    def test_field_order_follows_model(self):
        widgets = widgets_from_model(FlatModel)
        fields = list(FlatModel.model_fields.keys())
        widget_fields = [w.schema_field for w in widgets]
        assert widget_fields == fields

    def test_partial_overrides_preserves_order(self):
        from tater.widgets.radio_group import RadioGroupWidget
        override = RadioGroupWidget("mood", label="Custom")
        widgets = widgets_from_model(FlatModel, overrides=[override])
        fields = list(FlatModel.model_fields.keys())
        widget_fields = [w.schema_field for w in widgets]
        assert widget_fields == fields
