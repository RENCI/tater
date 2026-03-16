"""Tests for widget component_id derivation."""
from tater.widgets import SegmentedControlWidget, CheckboxWidget, TextInputWidget


class TestComponentId:
    def test_flat_field(self):
        w = SegmentedControlWidget(schema_field="kind", label="Kind")
        assert w.component_id == "annotation-kind"

    def test_nested_field_dot_replaced(self):
        w = SegmentedControlWidget(schema_field="pet.kind", label="Kind")
        assert w.component_id == "annotation-pet-kind"

    def test_finalize_paths_prepends_parent(self):
        w = SegmentedControlWidget(schema_field="kind", label="Kind")
        w._finalize_paths(parent_path="pets.0")
        assert w.field_path == "pets.0.kind"
        assert w.component_id == "annotation-pets-0-kind"

    def test_conditional_wrapper_id_is_dict(self):
        w = CheckboxWidget(schema_field="neutered", label="Neutered")
        w._finalize_paths(parent_path="pets.0")
        cid = w.conditional_wrapper_id
        assert isinstance(cid, dict)
        assert cid["type"] == "tater-cond-wrapper"
        # Standalone widget (no repeater context): ld and path are empty sentinels.
        assert cid["ld"] == ""
        assert cid["path"] == ""
        # tf encodes the full field path (pipe-separated) for standalone widgets.
        assert cid["tf"] == "pets|0|neutered"

    def test_different_widget_types_same_field(self):
        w1 = SegmentedControlWidget(schema_field="kind", label="Kind")
        w2 = TextInputWidget(schema_field="kind", label="Kind")
        assert w1.component_id == w2.component_id == "annotation-kind"
