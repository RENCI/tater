"""Tests for _decode_field_path — reconstructs dot-path from schema_id components."""
import pytest
from tater.ui.callbacks import _decode_field_path


class TestDecodeFieldPath:
    # ------------------------------------------------------------------
    # Standalone widgets (ld == "")
    # ------------------------------------------------------------------

    def test_standalone_flat_field(self):
        # Simple top-level field: tf carries the field name directly.
        assert _decode_field_path("", "", "kind") == "kind"

    def test_standalone_pipe_encoded_path(self):
        # Standalone widget whose field_path was stored pipe-encoded.
        assert _decode_field_path("", "", "pets|0|kind") == "pets.0.kind"

    def test_standalone_deeply_nested(self):
        assert _decode_field_path("", "", "a|b|c|d") == "a.b.c.d"

    # ------------------------------------------------------------------
    # Single-level repeater (one list, one index)
    # ------------------------------------------------------------------

    def test_single_repeater_simple_tf(self):
        # pets[0].kind
        assert _decode_field_path("pets", "0", "kind") == "pets.0.kind"

    def test_single_repeater_second_item(self):
        # pets[3].breed
        assert _decode_field_path("pets", "3", "breed") == "pets.3.breed"

    def test_single_repeater_group_child(self):
        # GroupWidget child: tf is pipe-encoded within the item model.
        # pets[1].booleans.is_indoor
        assert _decode_field_path("pets", "1", "booleans|is_indoor") == "pets.1.booleans.is_indoor"

    # ------------------------------------------------------------------
    # Doubly-nested repeater (two lists, two indices)
    # ------------------------------------------------------------------

    def test_doubly_nested(self):
        # findings[0].evidence[2].tag
        assert _decode_field_path("findings|evidence", "0.2", "tag") == "findings.0.evidence.2.tag"

    def test_doubly_nested_first_items(self):
        assert _decode_field_path("findings|evidence", "0.0", "quote") == "findings.0.evidence.0.quote"

    def test_doubly_nested_group_child(self):
        # findings[1].evidence[0].meta.note
        assert _decode_field_path("findings|evidence", "1.0", "meta|note") == "findings.1.evidence.0.meta.note"

    # ------------------------------------------------------------------
    # Triply-nested repeater
    # ------------------------------------------------------------------

    def test_triply_nested(self):
        assert _decode_field_path("a|b|c", "0.1.2", "x") == "a.0.b.1.c.2.x"

    # ------------------------------------------------------------------
    # Round-trip symmetry with schema_id construction
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("ld, path, tf, expected", [
        ("",              "",    "score",           "score"),
        ("",              "",    "owner|address|city", "owner.address.city"),
        ("pets",          "0",   "kind",            "pets.0.kind"),
        ("pets",          "2",   "neutered",        "pets.2.neutered"),
        ("findings",      "0",   "label",           "findings.0.label"),
        ("findings|evidence", "0.1", "tag",         "findings.0.evidence.1.tag"),
    ])
    def test_parametrized(self, ld, path, tf, expected):
        assert _decode_field_path(ld, path, tf) == expected
