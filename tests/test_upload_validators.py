"""Unit tests for upload validation helpers in tater/ui/upload_layout.py.

Tests cover the two already-module-level helpers (_decode_json_upload,
_validate_schema_json) plus _validate_documents_data, which was extracted
from the validate_documents closure specifically for testability.
"""
from __future__ import annotations

import base64
import json

import pytest

from tater.ui.upload_layout import (
    _decode_json_upload,
    _validate_documents_data,
    _validate_schema_json,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _encode(obj) -> str:
    """Encode a Python object as a dcc.Upload content string."""
    payload = json.dumps(obj).encode("utf-8")
    return "data:application/json;base64," + base64.b64encode(payload).decode("ascii")


def _encode_raw(text: str) -> str:
    """Encode arbitrary text as a dcc.Upload content string."""
    return "data:text/plain;base64," + base64.b64encode(text.encode("utf-8")).decode("ascii")


# ---------------------------------------------------------------------------
# _decode_json_upload
# ---------------------------------------------------------------------------

class TestDecodeJsonUpload:
    def test_valid_dict(self):
        data = {"key": "value"}
        result, error = _decode_json_upload(_encode(data), "test.json")
        assert result == data
        assert error is None

    def test_valid_list(self):
        data = [{"id": "doc1", "text": "hello"}]
        result, error = _decode_json_upload(_encode(data), "docs.json")
        assert result == data
        assert error is None

    def test_invalid_json(self):
        contents = "data:application/json;base64," + base64.b64encode(b"{not valid json}").decode()
        result, error = _decode_json_upload(contents, "bad.json")
        assert result is None
        assert error is not None
        assert "bad.json" in error

    def test_non_utf8_bytes(self):
        bad_bytes = b"\xff\xfe"
        contents = "data:application/json;base64," + base64.b64encode(bad_bytes).decode()
        result, error = _decode_json_upload(contents, "bad.json")
        assert result is None
        assert error is not None

    def test_missing_comma_separator(self):
        # No comma → split fails
        result, error = _decode_json_upload("nodataurl", "bad.json")
        assert result is None
        assert error is not None

    def test_nested_object(self):
        data = {"a": {"b": [1, 2, 3]}}
        result, error = _decode_json_upload(_encode(data), "nested.json")
        assert result == data
        assert error is None


# ---------------------------------------------------------------------------
# _validate_schema_json
# ---------------------------------------------------------------------------

class TestValidateSchemaJson:
    def _minimal_schema(self, fields=None):
        return {
            "data_schema": fields or [{"id": "label", "type": "radio"}]
        }

    def test_valid_minimal_schema(self):
        ok, msg = _validate_schema_json(self._minimal_schema())
        assert ok is True
        assert msg == ""

    def test_not_a_dict(self):
        ok, msg = _validate_schema_json([{"id": "label", "type": "radio"}])
        assert ok is False
        assert "object" in msg.lower()

    def test_missing_data_schema_key(self):
        ok, msg = _validate_schema_json({"other_key": []})
        assert ok is False
        assert "data_schema" in msg

    def test_empty_data_schema(self):
        ok, msg = _validate_schema_json({"data_schema": []})
        assert ok is False
        assert "non-empty" in msg.lower()

    def test_data_schema_not_a_list(self):
        ok, msg = _validate_schema_json({"data_schema": "not a list"})
        assert ok is False

    def test_field_missing_id_and_type(self):
        ok, msg = _validate_schema_json({"data_schema": [{"widget": {"type": "text"}}]})
        assert ok is False
        assert "missing" in msg.lower()

    def test_field_missing_type_only(self):
        ok, msg = _validate_schema_json({"data_schema": [{"id": "label"}]})
        assert ok is False
        assert "missing" in msg.lower()

    def test_divider_by_type_key_is_allowed(self):
        schema = {"data_schema": [{"type": "divider"}]}
        ok, msg = _validate_schema_json(schema)
        assert ok is True

    def test_divider_by_widget_type_is_allowed(self):
        schema = {"data_schema": [{"widget": {"type": "divider"}}]}
        ok, msg = _validate_schema_json(schema)
        assert ok is True

    def test_field_not_a_dict(self):
        ok, msg = _validate_schema_json({"data_schema": ["not a dict"]})
        assert ok is False

    def test_multiple_valid_fields(self):
        schema = self._minimal_schema([
            {"id": "label", "type": "radio"},
            {"id": "notes", "type": "text"},
            {"type": "divider"},
        ])
        ok, _ = _validate_schema_json(schema)
        assert ok is True

    def test_schema_with_hierarchies_key(self):
        schema = self._minimal_schema()
        schema["hierarchies"] = {"pets": "pets.yaml"}
        ok, _ = _validate_schema_json(schema)
        assert ok is True


# ---------------------------------------------------------------------------
# _validate_documents_data
# ---------------------------------------------------------------------------

class TestValidateDocumentsData:
    def _docs(self, n=2):
        return [{"id": f"doc{i}", "text": f"text {i}"} for i in range(n)]

    def test_valid_documents(self):
        docs = self._docs()
        result, error = _validate_documents_data(docs, "docs.json")
        assert result == docs
        assert error is None

    def test_not_a_list(self):
        result, error = _validate_documents_data({"id": "doc1"}, "docs.json")
        assert result is None
        assert "array" in error.lower()

    def test_empty_list(self):
        result, error = _validate_documents_data([], "docs.json")
        assert result is None
        assert "non-empty" in error.lower()

    def test_item_not_a_dict(self):
        result, error = _validate_documents_data(["not a dict"], "docs.json")
        assert result is None
        assert "not objects" in error.lower()

    def test_file_path_docs_rejected(self):
        docs = [{"id": "doc1", "file_path": "/data/doc.txt"}]
        result, error = _validate_documents_data(docs, "docs.json")
        assert result is None
        assert "file_path" in error
        assert "hosted mode" in error.lower()

    def test_missing_text_field_rejected(self):
        docs = [{"id": "doc1"}]
        result, error = _validate_documents_data(docs, "docs.json")
        assert result is None
        assert "text" in error

    def test_mixed_valid_and_missing_text(self):
        docs = [{"id": "doc1", "text": "hello"}, {"id": "doc2"}]
        result, error = _validate_documents_data(docs, "docs.json")
        assert result is None
        assert "text" in error

    def test_error_reports_bad_indices(self):
        docs = [{"id": "doc0", "text": "ok"}, {"id": "doc1"}, {"id": "doc2"}]
        result, error = _validate_documents_data(docs, "docs.json")
        assert "1" in error

    def test_file_path_check_precedes_missing_text_check(self):
        # A doc with file_path but no text should fail on file_path, not text
        docs = [{"id": "doc1", "file_path": "/data/doc.txt"}]
        _, error = _validate_documents_data(docs, "docs.json")
        assert "file_path" in error

    def test_single_valid_document(self):
        docs = [{"id": "doc1", "text": "hello"}]
        result, error = _validate_documents_data(docs, "docs.json")
        assert result == docs
        assert error is None

    def test_extra_fields_are_allowed(self):
        docs = [{"id": "doc1", "text": "hello", "name": "Doc One", "info": {"x": 1}}]
        result, error = _validate_documents_data(docs, "docs.json")
        assert result == docs
        assert error is None
