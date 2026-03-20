"""Tests for get_model_value / set_model_value and get_dict_value / set_dict_value."""
import pytest
from tater.ui.value_helpers import (
    get_model_value,
    set_model_value,
    get_dict_value,
    set_dict_value,
    create_list_item,
)
from tater import SpanAnnotation
from tests.conftest import Schema, Pet, Finding, Owner, Address


# ---------------------------------------------------------------------------
# get_model_value
# ---------------------------------------------------------------------------

class TestGetModelValue:
    def test_flat_field(self):
        s = Schema(overall="normal")
        assert get_model_value(s, "overall") == "normal"

    def test_flat_field_none(self):
        s = Schema()
        assert get_model_value(s, "overall") is None

    def test_nested_submodel(self):
        s = Schema(owner=Owner(address=Address(city="Boston")))
        assert get_model_value(s, "owner.address.city") == "Boston"

    def test_list_index_in_range(self):
        s = Schema(pets=[Pet(kind="cat"), Pet(kind="dog")])
        assert get_model_value(s, "pets.0.kind") == "cat"
        assert get_model_value(s, "pets.1.kind") == "dog"

    def test_list_index_out_of_range(self):
        s = Schema(pets=[Pet(kind="cat")])
        assert get_model_value(s, "pets.5.kind") is None

    def test_path_through_none(self):
        s = Schema()  # owner is None
        assert get_model_value(s, "owner.address.city") is None

    def test_dict_input(self):
        d = {"a": {"b": {"c": 42}}}
        assert get_model_value(d, "a.b.c") == 42

    def test_dict_missing_key(self):
        d = {"a": 1}
        assert get_model_value(d, "a.b") is None

    def test_span_annotation_in_list(self):
        span = SpanAnnotation(start=0, end=5, text="hello", tag="Support")
        s = Schema(findings=[Finding(evidence=[span])])
        result = get_model_value(s, "findings.0.evidence.0")
        assert result.tag == "Support"


# ---------------------------------------------------------------------------
# set_model_value
# ---------------------------------------------------------------------------

class TestSetModelValue:
    def test_flat_field(self):
        s = Schema()
        set_model_value(s, "overall", "abnormal")
        assert s.overall == "abnormal"

    def test_nested_submodel_auto_creates(self):
        s = Schema()
        set_model_value(s, "owner.address.city", "Cambridge")
        assert s.owner.address.city == "Cambridge"

    def test_list_extend_and_set(self):
        s = Schema()
        set_model_value(s, "pets.0.kind", "fish")
        assert len(s.pets) == 1
        assert s.pets[0].kind == "fish"

    def test_list_set_beyond_length(self):
        s = Schema()
        set_model_value(s, "pets.2.kind", "dog")
        assert len(s.pets) == 3
        assert s.pets[2].kind == "dog"
        # Intermediate items should be Pet instances (not None)
        assert isinstance(s.pets[0], Pet)
        assert isinstance(s.pets[1], Pet)

    def test_doubly_nested_list(self):
        s = Schema()
        span = SpanAnnotation(start=10, end=15, text="world", tag="Against")
        set_model_value(s, "findings.0.evidence.0", span)
        assert s.findings[0].evidence[0].tag == "Against"

    def test_dict_input(self):
        d = {}
        set_model_value(d, "pets.0.kind", "cat")
        assert d["pets"][0]["kind"] == "cat"

    def test_overwrite_existing_value(self):
        s = Schema(overall="normal")
        set_model_value(s, "overall", "abnormal")
        assert s.overall == "abnormal"

    def test_round_trip(self):
        s = Schema()
        set_model_value(s, "score", 42)
        assert get_model_value(s, "score") == 42


# ---------------------------------------------------------------------------
# create_list_item
# ---------------------------------------------------------------------------

class TestCreateListItem:
    def test_returns_pet_for_pets_field(self):
        s = Schema()
        # Build a nav stack that points at the pets list
        nav_stack = [(s, "pets")]
        result = create_list_item(nav_stack)
        assert isinstance(result, Pet)

    def test_returns_dict_for_evidence_field(self):
        # SpanAnnotation has required fields so can't be auto-instantiated; falls back to {}
        s = Schema()
        finding = Finding()
        nav_stack = [(s, "findings"), (finding, "evidence")]
        result = create_list_item(nav_stack)
        assert result == {}

    def test_returns_dict_for_empty_stack(self):
        result = create_list_item([])
        assert result == {}


# ---------------------------------------------------------------------------
# get_dict_value / set_dict_value (dict variants)
# ---------------------------------------------------------------------------

class TestDictHelpers:
    def test_get_nested(self):
        d = {"pets": [{"kind": "cat"}]}
        assert get_dict_value(d, "pets.0.kind") == "cat"

    def test_get_missing(self):
        assert get_dict_value({}, "a.b") is None

    def test_set_creates_intermediate_dicts(self):
        d = {}
        set_dict_value(d, "a.b.c", "hello")
        assert d["a"]["b"]["c"] == "hello"

    def test_set_creates_list_for_numeric_key(self):
        d = {}
        set_dict_value(d, "items.0.name", "first")
        assert d["items"][0]["name"] == "first"

    def test_round_trip(self):
        d = {}
        set_dict_value(d, "x.y", 99)
        assert get_dict_value(d, "x.y") == 99
