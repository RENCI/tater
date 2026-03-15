"""Integration tests for TaterApp annotation save/load round-trip.

These tests exercise the persistence layer (TaterApp._save_annotations_to_file /
_load_annotations_from_file) directly without starting a browser or registering
Dash callbacks.
"""
import json
from typing import Optional, List, Literal

import pytest
from pydantic import BaseModel, Field

from tater.ui.tater_app import TaterApp
from tater import SpanAnnotation


# ---------------------------------------------------------------------------
# Minimal schemas used across tests
# ---------------------------------------------------------------------------

class FlatSchema(BaseModel):
    overall: Optional[str] = None
    score: Optional[int] = None
    flags: List[Literal["urgent", "review"]] = Field(default_factory=list)


class Pet(BaseModel):
    kind: Optional[Literal["cat", "dog"]] = None
    indoor: Optional[bool] = None


class NestedSchema(BaseModel):
    label: Optional[str] = None
    pets: List[Pet] = Field(default_factory=list)


class SpanSchema(BaseModel):
    spans: List[SpanAnnotation] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def docs_file(tmp_path):
    """Two-document JSON file with inline text."""
    docs = [
        {"id": "doc1", "text": "First document."},
        {"id": "doc2", "text": "Second document."},
    ]
    p = tmp_path / "docs.json"
    p.write_text(json.dumps(docs))
    return str(p)


@pytest.fixture
def single_doc_file(tmp_path):
    docs = [{"id": "doc1", "text": "Only document."}]
    p = tmp_path / "docs.json"
    p.write_text(json.dumps(docs))
    return str(p)


def make_app(schema_model, annotations_path):
    """Create a minimal TaterApp with no widgets registered."""
    return TaterApp(schema_model=schema_model, annotations_path=str(annotations_path))


# ---------------------------------------------------------------------------
# Basic round-trip
# ---------------------------------------------------------------------------

class TestFlatFieldRoundTrip:
    def test_str_field_persists(self, tmp_path, docs_file):
        ann_path = tmp_path / "ann.json"
        app = make_app(FlatSchema, ann_path)
        app.load_documents(docs_file)

        app.annotations["doc1"].overall = "abnormal"
        app._save_annotations_to_file()

        app2 = make_app(FlatSchema, ann_path)
        app2.load_documents(docs_file)
        assert app2.annotations["doc1"].overall == "abnormal"

    def test_int_field_persists(self, tmp_path, docs_file):
        ann_path = tmp_path / "ann.json"
        app = make_app(FlatSchema, ann_path)
        app.load_documents(docs_file)

        app.annotations["doc1"].score = 99
        app._save_annotations_to_file()

        app2 = make_app(FlatSchema, ann_path)
        app2.load_documents(docs_file)
        assert app2.annotations["doc1"].score == 99

    def test_list_field_persists(self, tmp_path, docs_file):
        ann_path = tmp_path / "ann.json"
        app = make_app(FlatSchema, ann_path)
        app.load_documents(docs_file)

        app.annotations["doc1"].flags = ["urgent", "review"]
        app._save_annotations_to_file()

        app2 = make_app(FlatSchema, ann_path)
        app2.load_documents(docs_file)
        assert app2.annotations["doc1"].flags == ["urgent", "review"]

    def test_none_field_stays_none(self, tmp_path, docs_file):
        ann_path = tmp_path / "ann.json"
        app = make_app(FlatSchema, ann_path)
        app.load_documents(docs_file)
        app._save_annotations_to_file()

        app2 = make_app(FlatSchema, ann_path)
        app2.load_documents(docs_file)
        assert app2.annotations["doc1"].overall is None
        assert app2.annotations["doc1"].score is None

    def test_multiple_docs_independent(self, tmp_path, docs_file):
        ann_path = tmp_path / "ann.json"
        app = make_app(FlatSchema, ann_path)
        app.load_documents(docs_file)

        app.annotations["doc1"].overall = "normal"
        app.annotations["doc2"].overall = "abnormal"
        app._save_annotations_to_file()

        app2 = make_app(FlatSchema, ann_path)
        app2.load_documents(docs_file)
        assert app2.annotations["doc1"].overall == "normal"
        assert app2.annotations["doc2"].overall == "abnormal"

    def test_overwrite_updates_value(self, tmp_path, docs_file):
        ann_path = tmp_path / "ann.json"
        app = make_app(FlatSchema, ann_path)
        app.load_documents(docs_file)

        app.annotations["doc1"].overall = "normal"
        app._save_annotations_to_file()

        app.annotations["doc1"].overall = "abnormal"
        app._save_annotations_to_file()

        app2 = make_app(FlatSchema, ann_path)
        app2.load_documents(docs_file)
        assert app2.annotations["doc1"].overall == "abnormal"


# ---------------------------------------------------------------------------
# Nested model round-trip
# ---------------------------------------------------------------------------

class TestNestedRoundTrip:
    def test_list_of_submodels_persists(self, tmp_path, single_doc_file):
        ann_path = tmp_path / "ann.json"
        app = make_app(NestedSchema, ann_path)
        app.load_documents(single_doc_file)

        app.annotations["doc1"].label = "positive"
        app.annotations["doc1"].pets = [Pet(kind="cat", indoor=True), Pet(kind="dog")]
        app._save_annotations_to_file()

        app2 = make_app(NestedSchema, ann_path)
        app2.load_documents(single_doc_file)
        ann = app2.annotations["doc1"]
        assert ann.label == "positive"
        assert len(ann.pets) == 2
        assert ann.pets[0].kind == "cat"
        assert ann.pets[0].indoor is True
        assert ann.pets[1].kind == "dog"

    def test_empty_list_persists(self, tmp_path, single_doc_file):
        ann_path = tmp_path / "ann.json"
        app = make_app(NestedSchema, ann_path)
        app.load_documents(single_doc_file)
        app._save_annotations_to_file()

        app2 = make_app(NestedSchema, ann_path)
        app2.load_documents(single_doc_file)
        assert app2.annotations["doc1"].pets == []

    def test_span_annotation_list_persists(self, tmp_path, single_doc_file):
        ann_path = tmp_path / "ann.json"
        app = make_app(SpanSchema, ann_path)
        app.load_documents(single_doc_file)

        app.annotations["doc1"].spans = [
            SpanAnnotation(start=0, end=5, text="hello", tag="Support"),
            SpanAnnotation(start=10, end=15, text="world", tag="Against"),
        ]
        app._save_annotations_to_file()

        app2 = make_app(SpanSchema, ann_path)
        app2.load_documents(single_doc_file)
        spans = app2.annotations["doc1"].spans
        assert len(spans) == 2
        assert spans[0].tag == "Support"
        assert spans[0].start == 0
        assert spans[1].tag == "Against"
        assert spans[1].text == "world"


# ---------------------------------------------------------------------------
# Metadata round-trip
# ---------------------------------------------------------------------------

class TestMetadataRoundTrip:
    def test_flagged_persists(self, tmp_path, single_doc_file):
        ann_path = tmp_path / "ann.json"
        app = make_app(FlatSchema, ann_path)
        app.load_documents(single_doc_file)

        app.metadata["doc1"].flagged = True
        app._save_annotations_to_file()

        app2 = make_app(FlatSchema, ann_path)
        app2.load_documents(single_doc_file)
        assert app2.metadata["doc1"].flagged is True

    def test_notes_persist(self, tmp_path, single_doc_file):
        ann_path = tmp_path / "ann.json"
        app = make_app(FlatSchema, ann_path)
        app.load_documents(single_doc_file)

        app.metadata["doc1"].notes = "needs second opinion"
        app._save_annotations_to_file()

        app2 = make_app(FlatSchema, ann_path)
        app2.load_documents(single_doc_file)
        assert app2.metadata["doc1"].notes == "needs second opinion"

    def test_annotation_seconds_persist(self, tmp_path, single_doc_file):
        ann_path = tmp_path / "ann.json"
        app = make_app(FlatSchema, ann_path)
        app.load_documents(single_doc_file)

        app.metadata["doc1"].annotation_seconds = 123.4
        app._save_annotations_to_file()

        app2 = make_app(FlatSchema, ann_path)
        app2.load_documents(single_doc_file)
        assert app2.metadata["doc1"].annotation_seconds == pytest.approx(123.4)

    def test_status_persists(self, tmp_path, single_doc_file):
        ann_path = tmp_path / "ann.json"
        app = make_app(FlatSchema, ann_path)
        app.load_documents(single_doc_file)

        app.metadata["doc1"].status = "complete"
        app._save_annotations_to_file()

        app2 = make_app(FlatSchema, ann_path)
        app2.load_documents(single_doc_file)
        assert app2.metadata["doc1"].status == "complete"

    def test_default_metadata_for_new_doc(self, tmp_path, single_doc_file):
        ann_path = tmp_path / "nonexistent.json"
        app = make_app(FlatSchema, ann_path)
        app.load_documents(single_doc_file)

        meta = app.metadata["doc1"]
        assert meta.flagged is False
        assert meta.notes == ""
        assert meta.annotation_seconds == 0.0
        assert meta.status == "not_started"


# ---------------------------------------------------------------------------
# Schema mismatch handling
# ---------------------------------------------------------------------------

class TestSchemaMismatch:
    def test_extra_fields_in_file_tracked_in_warnings(self, tmp_path, single_doc_file):
        ann_path = tmp_path / "ann.json"
        ann_path.write_text(json.dumps({
            "doc1": {
                "annotations": {"overall": "normal", "ghost_field": "unexpected"},
                "metadata": {},
            }
        }))
        app = make_app(FlatSchema, ann_path)
        app.load_documents(single_doc_file)

        assert "extra" in app._schema_warnings
        assert "ghost_field" in app._schema_warnings["extra"]

    def test_extra_fields_do_not_crash_load(self, tmp_path, single_doc_file):
        ann_path = tmp_path / "ann.json"
        ann_path.write_text(json.dumps({
            "doc1": {
                "annotations": {"overall": "normal", "ghost_field": "unexpected"},
                "metadata": {},
            }
        }))
        app = make_app(FlatSchema, ann_path)
        app.load_documents(single_doc_file)
        # Known fields should still load correctly
        assert app.annotations["doc1"].overall == "normal"

    def test_missing_fields_get_defaults(self, tmp_path, single_doc_file):
        # File has only one of three schema fields — the others are "missing".
        # ann_data must be non-empty to enter the warning-tracking branch.
        ann_path = tmp_path / "ann.json"
        ann_path.write_text(json.dumps({
            "doc1": {
                "annotations": {"overall": "normal"},
                "metadata": {},
            }
        }))
        app = make_app(FlatSchema, ann_path)
        app.load_documents(single_doc_file)

        assert app.annotations["doc1"].overall == "normal"
        assert app.annotations["doc1"].score is None  # missing → default
        assert "missing" in app._schema_warnings

    def test_no_warnings_for_matching_schema(self, tmp_path, single_doc_file):
        ann_path = tmp_path / "ann.json"
        app = make_app(FlatSchema, ann_path)
        app.load_documents(single_doc_file)
        app.annotations["doc1"].overall = "normal"
        app._save_annotations_to_file()

        app2 = make_app(FlatSchema, ann_path)
        app2.load_documents(single_doc_file)
        assert "extra" not in app2._schema_warnings
        assert "missing" not in app2._schema_warnings


# ---------------------------------------------------------------------------
# File format
# ---------------------------------------------------------------------------

class TestSaveFileFormat:
    def test_saved_file_is_valid_json(self, tmp_path, single_doc_file):
        ann_path = tmp_path / "ann.json"
        app = make_app(FlatSchema, ann_path)
        app.load_documents(single_doc_file)
        app.annotations["doc1"].overall = "normal"
        app._save_annotations_to_file()

        raw = json.loads(ann_path.read_text())
        assert "doc1" in raw
        assert "annotations" in raw["doc1"]
        assert "metadata" in raw["doc1"]

    def test_saved_annotations_have_no_empty_key(self, tmp_path, single_doc_file):
        """DividerWidget has schema_field="" — ensure no empty string key in saved data."""
        ann_path = tmp_path / "ann.json"
        app = make_app(FlatSchema, ann_path)
        app.load_documents(single_doc_file)
        app._save_annotations_to_file()

        raw = json.loads(ann_path.read_text())
        assert "" not in raw["doc1"]["annotations"]

    def test_no_existing_file_gives_fresh_annotations(self, tmp_path, single_doc_file):
        ann_path = tmp_path / "nonexistent.json"
        app = make_app(FlatSchema, ann_path)
        app.load_documents(single_doc_file)
        assert app.annotations["doc1"] == FlatSchema()

    def test_annotations_path_auto_derived_from_docs_path(self, tmp_path):
        docs = [{"id": "doc1", "text": "hi"}]
        docs_path = tmp_path / "my_docs.json"
        docs_path.write_text(json.dumps(docs))

        app = TaterApp(schema_model=FlatSchema)
        app.load_documents(str(docs_path))
        assert app.annotations_path == str(tmp_path / "my_docs_annotations.json")
