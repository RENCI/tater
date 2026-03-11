"""Tests for widget bind_schema — option derivation and type validation."""
import pytest
from tater.widgets import (
    SegmentedControlWidget, RadioGroupWidget, SelectWidget,
    MultiSelectWidget, CheckboxGroupWidget, CheckboxWidget, SwitchWidget, ChipWidget,
    TextInputWidget, TextAreaWidget, ListableWidget,
)
from tests.conftest import Schema, Pet


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
