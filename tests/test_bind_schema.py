"""Tests for widget bind_schema — option derivation and type validation."""
import pytest
from tater.widgets import (
    SegmentedControlWidget, RadioGroupWidget, SelectWidget, ChipRadioWidget,
    MultiSelectWidget, CheckboxGroupWidget, CheckboxWidget, SwitchWidget, ChipWidget,
    TextInputWidget, TextAreaWidget, ListableWidget,
    NumberInputWidget, SliderWidget, RangeSliderWidget,
    GroupWidget, DividerWidget, TabsWidget, AccordionWidget,
    HierarchicalLabelSelectWidget, HierarchicalLabelMultiWidget,
    SpanAnnotationWidget, EntityType,
)
from tests.conftest import Schema, Pet, Measurements


# ---------------------------------------------------------------------------
# ChoiceWidget: derives options from Literal field
# ---------------------------------------------------------------------------

class TestChoiceWidgetBindSchema:
    def test_segmented_control_derives_options(self):
        w = SegmentedControlWidget(schema_field="kind", label="Kind")
        w._finalize_paths(parent_path="pets.0")
        w.bind_schema(Schema)
        assert w.options == ["cat", "dog", "fish"]

    def test_radio_group_derives_options(self):
        w = RadioGroupWidget(schema_field="label", label="Label")
        w._finalize_paths(parent_path="findings.0")
        w.bind_schema(Schema)
        assert w.options == ["positive", "negative", "uncertain"]

    def test_select_derives_options(self):
        w = SelectWidget(schema_field="kind", label="Kind")
        w._finalize_paths(parent_path="pets.0")
        w.bind_schema(Schema)
        assert w.options == ["cat", "dog", "fish"]

    def test_chip_radio_derives_options(self):
        w = ChipRadioWidget(schema_field="kind", label="Kind")
        w._finalize_paths(parent_path="pets.0")
        w.bind_schema(Schema)
        assert w.options == ["cat", "dog", "fish"]

    def test_raises_for_non_literal_field(self):
        w = SegmentedControlWidget(schema_field="breed", label="Breed")
        w._finalize_paths(parent_path="pets.0")
        with pytest.raises(TypeError):
            w.bind_schema(Schema)

    def test_raises_for_missing_field(self):
        w = SegmentedControlWidget(schema_field="nonexistent", label="X")
        with pytest.raises(ValueError):
            w.bind_schema(Schema)


# ---------------------------------------------------------------------------
# MultiChoiceWidget
# ---------------------------------------------------------------------------

class TestMultiChoiceWidgetBindSchema:
    def test_multi_select_derives_options(self):
        w = MultiSelectWidget(schema_field="flags", label="Flags")
        w.bind_schema(Schema)
        assert w.options == ["urgent", "review"]

    def test_checkbox_group_derives_options(self):
        w = CheckboxGroupWidget(schema_field="flags", label="Flags")
        w.bind_schema(Schema)
        assert w.options == ["urgent", "review"]

    def test_raises_for_non_list_field(self):
        w = MultiSelectWidget(schema_field="overall", label="Overall")
        with pytest.raises(TypeError):
            w.bind_schema(Schema)


# ---------------------------------------------------------------------------
# BooleanWidget
# ---------------------------------------------------------------------------

class TestBooleanWidgetBindSchema:
    def test_checkbox_binds_bool_field(self):
        w = CheckboxWidget(schema_field="neutered", label="Neutered")
        w._finalize_paths(parent_path="pets.0")
        w.bind_schema(Schema)  # should not raise

    def test_switch_binds_bool_field(self):
        w = SwitchWidget(schema_field="indoor", label="Indoor")
        w._finalize_paths(parent_path="pets.0")
        w.bind_schema(Schema)

    def test_raises_for_non_bool_field(self):
        w = CheckboxWidget(schema_field="kind", label="Kind")
        w._finalize_paths(parent_path="pets.0")
        with pytest.raises(TypeError):
            w.bind_schema(Schema)

    def test_chip_binds_bool_field(self):
        w = ChipWidget(schema_field="indoor", label="Indoor")
        w._finalize_paths(parent_path="pets.0")
        w.bind_schema(Schema)  # should not raise

    def test_empty_value_is_false(self):
        w = CheckboxWidget(schema_field="neutered", label="Neutered")
        assert w.empty_value is False


# ---------------------------------------------------------------------------
# TextWidget
# ---------------------------------------------------------------------------

class TestTextWidgetBindSchema:
    def test_text_input_binds_str_field(self):
        w = TextInputWidget(schema_field="breed", label="Breed")
        w._finalize_paths(parent_path="pets.0")
        w.bind_schema(Schema)

    def test_raises_for_non_str_field(self):
        w = TextInputWidget(schema_field="score", label="Score")
        with pytest.raises(TypeError):
            w.bind_schema(Schema)


# ---------------------------------------------------------------------------
# ListableWidget
# ---------------------------------------------------------------------------

class TestListableWidgetBindSchema:
    def test_binds_list_field(self):
        w = ListableWidget(
            schema_field="pets",
            label="Pets",
            item_label="Pet",
            item_widgets=[SegmentedControlWidget(schema_field="kind", label="Kind")],
        )
        w.bind_schema(Schema)  # should not raise

    def test_raises_for_non_list_field(self):
        w = ListableWidget(
            schema_field="overall",
            label="Overall",
            item_label="Item",
            item_widgets=[],
        )
        with pytest.raises((TypeError, ValueError)):
            w.bind_schema(Schema)


# ---------------------------------------------------------------------------
# NumericWidget (NumberInputWidget, SliderWidget)
# ---------------------------------------------------------------------------

class TestNumericWidgetBindSchema:
    def test_number_input_binds_int(self):
        w = NumberInputWidget(schema_field="score", label="Score")
        w.bind_schema(Schema)  # score is Optional[int]

    def test_slider_binds_float(self):
        w = SliderWidget(schema_field="weight", label="Weight")
        w._finalize_paths(parent_path="measurements")
        w.bind_schema(Schema)

    def test_raises_for_str_field(self):
        w = NumberInputWidget(schema_field="overall", label="Overall")
        with pytest.raises(TypeError):
            w.bind_schema(Schema)

    def test_raises_for_list_field(self):
        w = NumberInputWidget(schema_field="flags", label="Flags")
        with pytest.raises(TypeError):
            w.bind_schema(Schema)


# ---------------------------------------------------------------------------
# RangeSliderWidget
# ---------------------------------------------------------------------------

class TestRangeSliderWidgetBindSchema:
    def test_binds_list_float(self):
        w = RangeSliderWidget(schema_field="range_float", label="Range")
        w._finalize_paths(parent_path="measurements")
        w.bind_schema(Schema)

    def test_binds_list_int(self):
        w = RangeSliderWidget(schema_field="range_int", label="Range")
        w._finalize_paths(parent_path="measurements")
        w.bind_schema(Schema)

    def test_raises_for_non_list_field(self):
        w = RangeSliderWidget(schema_field="score", label="Score")
        with pytest.raises(TypeError):
            w.bind_schema(Schema)

    def test_raises_for_list_of_wrong_type(self):
        w = RangeSliderWidget(schema_field="range_str", label="Range")
        w._finalize_paths(parent_path="measurements")
        with pytest.raises(TypeError):
            w.bind_schema(Schema)

    def test_empty_value_uses_default(self):
        w = RangeSliderWidget(schema_field="range_float", min_value=10, max_value=90, label="R")
        assert w.empty_value == [10, 90]

    def test_empty_value_custom_default(self):
        w = RangeSliderWidget(
            schema_field="range_float", min_value=0, max_value=100,
            default=[20, 80], label="R",
        )
        assert w.empty_value == [20, 80]


# ---------------------------------------------------------------------------
# GroupWidget
# ---------------------------------------------------------------------------

class TestGroupWidgetBindSchema:
    def test_delegates_to_children(self):
        child = SegmentedControlWidget(schema_field="kind", label="Kind")
        w = GroupWidget(
            schema_field="pets.0",
            label="Pet",
            children=[child],
        )
        w._finalize_paths()
        w.bind_schema(Schema)
        assert child.options == ["cat", "dog", "fish"]

    def test_no_raise_with_no_children(self):
        w = GroupWidget(schema_field="owner", label="Owner", children=[])
        w.bind_schema(Schema)

    def test_raises_when_child_raises(self):
        bad_child = SegmentedControlWidget(schema_field="nonexistent", label="X")
        w = GroupWidget(schema_field="pets.0", label="Pet", children=[bad_child])
        w._finalize_paths()
        with pytest.raises((TypeError, ValueError)):
            w.bind_schema(Schema)


# ---------------------------------------------------------------------------
# DividerWidget
# ---------------------------------------------------------------------------

class TestDividerWidgetBindSchema:
    def test_no_op_does_not_raise(self):
        w = DividerWidget(label="Section")
        w.bind_schema(Schema)

    def test_schema_field_is_empty_string(self):
        w = DividerWidget(label="Section")
        assert w.schema_field == ""

    def test_multiple_dividers_same_model(self):
        w1 = DividerWidget(label="Section A")
        w2 = DividerWidget(label="Section B")
        w1.bind_schema(Schema)
        w2.bind_schema(Schema)


# ---------------------------------------------------------------------------
# TabsWidget / AccordionWidget
# ---------------------------------------------------------------------------

class TestTabsAndAccordionBindSchema:
    def test_tabs_binds_list_field(self):
        w = TabsWidget(
            schema_field="pets",
            label="Pets",
            item_label="Pet",
            item_widgets=[SegmentedControlWidget(schema_field="kind", label="Kind")],
        )
        w.bind_schema(Schema)

    def test_accordion_binds_list_field(self):
        w = AccordionWidget(
            schema_field="pets",
            label="Pets",
            item_label="Pet",
            item_widgets=[SegmentedControlWidget(schema_field="kind", label="Kind")],
        )
        w.bind_schema(Schema)

    def test_tabs_raises_for_non_list_field(self):
        w = TabsWidget(
            schema_field="overall",
            label="Overall",
            item_label="Item",
            item_widgets=[],
        )
        with pytest.raises((TypeError, ValueError)):
            w.bind_schema(Schema)


# ---------------------------------------------------------------------------
# HierarchicalLabel variants
# ---------------------------------------------------------------------------

class TestHierarchicalLabelBindSchema:
    _hierarchy = {"Animals": {"Mammals": None, "Birds": None}}

    def test_select_binds_list_str_field(self):
        w = HierarchicalLabelSelectWidget(
            schema_field="hl_path", label="HL", hierarchy=self._hierarchy
        )
        w.bind_schema(Schema)

    def test_multi_binds_list_list_str_field(self):
        from tests.conftest import Schema as S
        import inspect
        # hl_multi_path field would be Optional[List[List[str]]] — use a custom model
        from pydantic import BaseModel
        from typing import Optional, List

        class M(BaseModel):
            tags: Optional[List[List[str]]] = None

        w = HierarchicalLabelMultiWidget(
            schema_field="tags", label="HL Multi", hierarchy=self._hierarchy
        )
        w.bind_schema(M)

    def test_select_raises_for_non_list_str_field(self):
        w = HierarchicalLabelSelectWidget(
            schema_field="score", label="HL", hierarchy=self._hierarchy
        )
        with pytest.raises(TypeError):
            w.bind_schema(Schema)

    def test_select_raises_for_plain_str_field(self):
        # str is not accepted — must be List[str]
        w = HierarchicalLabelSelectWidget(
            schema_field="overall", label="HL", hierarchy=self._hierarchy
        )
        with pytest.raises(TypeError):
            w.bind_schema(Schema)

    def test_select_raises_for_missing_field(self):
        w = HierarchicalLabelSelectWidget(
            schema_field="nonexistent", label="HL", hierarchy=self._hierarchy
        )
        with pytest.raises(ValueError):
            w.bind_schema(Schema)


# ---------------------------------------------------------------------------
# SpanAnnotationWidget
# ---------------------------------------------------------------------------

class TestSpanAnnotationWidgetBindSchema:
    def test_no_op_does_not_raise(self):
        w = SpanAnnotationWidget(
            schema_field="findings",
            label="Spans",
            entity_types=[EntityType("Support"), EntityType("Against")],
        )
        w.bind_schema(Schema)

    def test_palette_colors_assigned(self):
        w = SpanAnnotationWidget(
            schema_field="findings",
            label="Spans",
            entity_types=[EntityType("A"), EntityType("B", color="#ff0000")],
            palette="tableau10",
        )
        # A gets a palette color; B keeps its explicit color
        assert w.entity_types[0].color is not None
        assert w.entity_types[1].color == "#ff0000"
