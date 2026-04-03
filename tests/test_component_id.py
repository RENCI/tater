"""Tests for widget schema_id and conditional_wrapper_id derivation."""
from tater.widgets import SegmentedControlWidget, CheckboxWidget, TextInputWidget


class TestSchemaId:
    def test_standalone_flat_field(self):
        w = SegmentedControlWidget(schema_field="kind", label="Kind")
        sid = w.schema_id
        assert sid["type"] == "tater-control"
        assert sid["ld"] == ""
        assert sid["path"] == ""
        assert sid["tf"] == "kind"

    def test_standalone_nested_field(self):
        w = SegmentedControlWidget(schema_field="kind", label="Kind")
        w._finalize_paths(parent_path="pets.0")
        sid = w.schema_id
        assert sid["type"] == "tater-control"
        assert sid["ld"] == ""
        assert sid["path"] == ""
        # Standalone: tf encodes full pipe path
        assert sid["tf"] == "pets|0|kind"

    def test_boolean_widget_uses_bool_type(self):
        w = CheckboxWidget(schema_field="neutered", label="Neutered")
        sid = w.schema_id
        assert sid["type"] == "tater-bool-control"

    def test_repeater_context(self):
        w = SegmentedControlWidget(schema_field="kind", label="Kind")
        w._finalize_paths(parent_path="pets.0")
        w._set_repeater_context("pets", "0")
        sid = w.schema_id
        assert sid["type"] == "tater-control"
        assert sid["ld"] == "pets"
        assert sid["path"] == "0"
        assert sid["tf"] == "kind"

    def test_different_widget_types_same_field(self):
        w1 = SegmentedControlWidget(schema_field="kind", label="Kind")
        w2 = TextInputWidget(schema_field="kind", label="Kind")
        assert w1.schema_id["tf"] == w2.schema_id["tf"] == "kind"


class TestConditionalWrapperId:
    def test_is_dict(self):
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
