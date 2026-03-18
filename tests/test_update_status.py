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
        update_status_for_doc(app, "d1")
        assert app.metadata["d1"].status == "not_started"

    def test_no_required_widgets_is_complete(self, tmp_path):
        app = make_app(Simple, [RadioGroupWidget("label")], ["d1"], tmp_path)
        app.metadata["d1"].visited = True
        update_status_for_doc(app, "d1")
        assert app.metadata["d1"].status == "complete"

    def test_required_filled_is_complete(self, tmp_path):
        app = make_app(Simple, [RadioGroupWidget("label", required=True)], ["d1"], tmp_path)
        app.metadata["d1"].visited = True
        app.annotations["d1"].label = "pos"
        update_status_for_doc(app, "d1")
        assert app.metadata["d1"].status == "complete"

    def test_required_empty_is_in_progress(self, tmp_path):
        app = make_app(Simple, [RadioGroupWidget("label", required=True)], ["d1"], tmp_path)
        app.metadata["d1"].visited = True
        # label stays None
        update_status_for_doc(app, "d1")
        assert app.metadata["d1"].status == "in_progress"

    def test_all_required_must_be_filled(self, tmp_path):
        widgets = [
            RadioGroupWidget("label", required=True),
            TextInputWidget("notes", required=True),
        ]
        app = make_app(Simple, widgets, ["d1"], tmp_path)
        app.metadata["d1"].visited = True
        app.annotations["d1"].label = "pos"
        # notes still None
        update_status_for_doc(app, "d1")
        assert app.metadata["d1"].status == "in_progress"

        app.annotations["d1"].notes = "some text"
        update_status_for_doc(app, "d1")
        assert app.metadata["d1"].status == "complete"

    def test_boolean_required_does_not_gate_completion(self, tmp_path):
        # required=True on a bool widget should not block complete status
        app = make_app(BoolOnly, [CheckboxWidget("reviewed", required=True)], ["d1"], tmp_path)
        app.metadata["d1"].visited = True
        # reviewed stays None (unchecked = False in practice, but type is bool)
        update_status_for_doc(app, "d1")
        assert app.metadata["d1"].status == "complete"

    def test_no_doc_id_is_noop(self, tmp_path):
        app = make_app(Simple, [RadioGroupWidget("label", required=True)], ["d1"], tmp_path)
        # Should not raise
        update_status_for_doc(app, "")
        update_status_for_doc(app, None)

    def test_status_updates_independently_per_doc(self, tmp_path):
        widgets = [RadioGroupWidget("label", required=True)]
        app = make_app(Simple, widgets, ["d1", "d2"], tmp_path)
        app.metadata["d1"].visited = True
        app.metadata["d2"].visited = True
        app.annotations["d1"].label = "pos"
        # d2 label stays None

        update_status_for_doc(app, "d1")
        update_status_for_doc(app, "d2")

        assert app.metadata["d1"].status == "complete"
        assert app.metadata["d2"].status == "in_progress"

    def test_required_in_group_widget(self, tmp_path):
        sub_widget = SelectWidget("value", required=True)
        group = GroupWidget("sub", label="Sub", children=[sub_widget])
        app = make_app(WithGroup, [group], ["d1"], tmp_path)
        app.metadata["d1"].visited = True

        update_status_for_doc(app, "d1")
        assert app.metadata["d1"].status == "in_progress"

        app.annotations["d1"].sub = WithGroup.Sub(value="a")
        update_status_for_doc(app, "d1")
        assert app.metadata["d1"].status == "complete"
