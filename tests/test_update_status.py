"""Tests for update_status_for_doc and _has_value."""
import json
from typing import Optional, List, Literal

import pytest
from pydantic import BaseModel, Field

from tater.ui.tater_app import TaterApp
from tater.ui.callbacks import update_status_for_doc, _has_value
from tater.widgets import (
    RadioGroupWidget, TextInputWidget, CheckboxWidget, SelectWidget,
    GroupWidget,
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class Simple(BaseModel):
    label: Optional[Literal["pos", "neg"]] = None
    notes: Optional[str] = None


class BoolOnly(BaseModel):
    reviewed: Optional[bool] = None


class WithGroup(BaseModel):
    class Sub(BaseModel):
        value: Optional[Literal["a", "b"]] = None
    sub: Optional[Sub] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_app(schema_model, widgets, docs, tmp_path):
    ann_path = tmp_path / "ann.json"
    docs_path = tmp_path / "docs.json"
    docs_path.write_text(json.dumps([{"id": d, "text": d} for d in docs]))
    app = TaterApp(schema_model=schema_model, annotations_path=str(ann_path))
    app.load_documents(str(docs_path))
    app.set_annotation_widgets(widgets)
    return app


def make_stores(app):
    """Build annotations_data and metadata_data dicts from app server-side state."""
    annotations_data = {doc_id: ann.model_dump() for doc_id, ann in app.annotations.items()}
    metadata_data = {doc_id: meta.model_dump() for doc_id, meta in app.metadata.items()}
    return annotations_data, metadata_data


# ---------------------------------------------------------------------------
# _has_value
# ---------------------------------------------------------------------------

class TestHasValue:
    def test_none_is_empty(self):
        assert _has_value(None) is False

    def test_empty_string_is_empty(self):
        assert _has_value("") is False

    def test_whitespace_string_is_empty(self):
        assert _has_value("   ") is False

    def test_non_empty_string(self):
        assert _has_value("hello") is True

    def test_empty_list_is_empty(self):
        assert _has_value([]) is False

    def test_non_empty_list(self):
        assert _has_value(["a"]) is True

    def test_zero_is_truthy(self):
        assert _has_value(0) is True

    def test_false_is_truthy(self):
        assert _has_value(False) is True

    def test_integer(self):
        assert _has_value(42) is True


# ---------------------------------------------------------------------------
# update_status_for_doc
# ---------------------------------------------------------------------------

class TestUpdateStatusForDoc:
    def test_not_started_when_not_visited(self, tmp_path):
        app = make_app(Simple, [RadioGroupWidget("label", required=True)], ["d1"], tmp_path)
        # metadata.visited defaults to False
        annotations_data, metadata_data = make_stores(app)
        update_status_for_doc(app, "d1", annotations_data, metadata_data)
        assert metadata_data["d1"]["status"] == "not_started"

    def test_no_required_widgets_is_complete(self, tmp_path):
        app = make_app(Simple, [RadioGroupWidget("label")], ["d1"], tmp_path)
        annotations_data, metadata_data = make_stores(app)
        metadata_data["d1"]["visited"] = True
        update_status_for_doc(app, "d1", annotations_data, metadata_data)
        assert metadata_data["d1"]["status"] == "complete"

    def test_required_filled_is_complete(self, tmp_path):
        app = make_app(Simple, [RadioGroupWidget("label", required=True)], ["d1"], tmp_path)
        annotations_data, metadata_data = make_stores(app)
        metadata_data["d1"]["visited"] = True
        annotations_data["d1"]["label"] = "pos"
        update_status_for_doc(app, "d1", annotations_data, metadata_data)
        assert metadata_data["d1"]["status"] == "complete"

    def test_required_empty_is_in_progress(self, tmp_path):
        app = make_app(Simple, [RadioGroupWidget("label", required=True)], ["d1"], tmp_path)
        annotations_data, metadata_data = make_stores(app)
        metadata_data["d1"]["visited"] = True
        # label stays None
        update_status_for_doc(app, "d1", annotations_data, metadata_data)
        assert metadata_data["d1"]["status"] == "in_progress"

    def test_all_required_must_be_filled(self, tmp_path):
        widgets = [
            RadioGroupWidget("label", required=True),
            TextInputWidget("notes", required=True),
        ]
        app = make_app(Simple, widgets, ["d1"], tmp_path)
        annotations_data, metadata_data = make_stores(app)
        metadata_data["d1"]["visited"] = True
        annotations_data["d1"]["label"] = "pos"
        # notes still None
        update_status_for_doc(app, "d1", annotations_data, metadata_data)
        assert metadata_data["d1"]["status"] == "in_progress"

        annotations_data["d1"]["notes"] = "some text"
        update_status_for_doc(app, "d1", annotations_data, metadata_data)
        assert metadata_data["d1"]["status"] == "complete"

    def test_boolean_required_does_not_gate_completion(self, tmp_path):
        # required=True on a bool widget should not block complete status
        app = make_app(BoolOnly, [CheckboxWidget("reviewed", required=True)], ["d1"], tmp_path)
        annotations_data, metadata_data = make_stores(app)
        metadata_data["d1"]["visited"] = True
        # reviewed stays None (unchecked = False in practice, but type is bool)
        update_status_for_doc(app, "d1", annotations_data, metadata_data)
        assert metadata_data["d1"]["status"] == "complete"

    def test_no_doc_id_is_noop(self, tmp_path):
        app = make_app(Simple, [RadioGroupWidget("label", required=True)], ["d1"], tmp_path)
        annotations_data, metadata_data = make_stores(app)
        # Should not raise
        update_status_for_doc(app, "", annotations_data, metadata_data)
        update_status_for_doc(app, None, annotations_data, metadata_data)

    def test_status_updates_independently_per_doc(self, tmp_path):
        widgets = [RadioGroupWidget("label", required=True)]
        app = make_app(Simple, widgets, ["d1", "d2"], tmp_path)
        annotations_data, metadata_data = make_stores(app)
        metadata_data["d1"]["visited"] = True
        metadata_data["d2"]["visited"] = True
        annotations_data["d1"]["label"] = "pos"
        # d2 label stays None

        update_status_for_doc(app, "d1", annotations_data, metadata_data)
        update_status_for_doc(app, "d2", annotations_data, metadata_data)

        assert metadata_data["d1"]["status"] == "complete"
        assert metadata_data["d2"]["status"] == "in_progress"

    def test_required_in_group_widget(self, tmp_path):
        sub_widget = SelectWidget("value", required=True)
        group = GroupWidget("sub", label="Sub", children=[sub_widget])
        app = make_app(WithGroup, [group], ["d1"], tmp_path)
        annotations_data, metadata_data = make_stores(app)
        metadata_data["d1"]["visited"] = True

        update_status_for_doc(app, "d1", annotations_data, metadata_data)
        assert metadata_data["d1"]["status"] == "in_progress"

        annotations_data["d1"]["sub"] = {"value": "a"}
        update_status_for_doc(app, "d1", annotations_data, metadata_data)
        assert metadata_data["d1"]["status"] == "complete"
