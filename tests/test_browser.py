"""Browser integration tests using dash.testing (dash_duo fixture).

Covers low-complexity interactions: navigation, document content display,
flag checkbox, and notes textarea — all using simple string component IDs.

Run with:
    pytest tests/test_browser.py --headless
"""
import json
import time
from typing import Optional, Literal

import pytest
from pydantic import BaseModel

from tater.ui.tater_app import TaterApp
from tater.widgets import RadioGroupWidget


def js_click(dash_duo, selector):
    """Click via JavaScript to avoid ElementClickInterceptedException from the sticky footer."""
    el = dash_duo.find_element(selector)
    dash_duo.driver.execute_script("arguments[0].click();", el)
    return el


# ---------------------------------------------------------------------------
# Minimal schema and fixtures
# ---------------------------------------------------------------------------

class SimpleSchema(BaseModel):
    label: Optional[Literal["positive", "negative", "uncertain"]] = None


@pytest.fixture
def docs_file(tmp_path):
    docs = [
        {"id": "doc1", "text": "First document text.", "name": "Doc One"},
        {"id": "doc2", "text": "Second document text.", "name": "Doc Two"},
        {"id": "doc3", "text": "Third document text.", "name": "Doc Three"},
    ]
    p = tmp_path / "docs.json"
    p.write_text(json.dumps(docs))
    return str(p)


@pytest.fixture
def tater(tmp_path, docs_file):
    """A fully wired TaterApp with one RadioGroup widget."""
    ann_path = tmp_path / "ann.json"
    app = TaterApp(
        title="Test App",
        schema_model=SimpleSchema,
        annotations_path=str(ann_path),
    )
    app.load_documents(docs_file)
    app.set_annotation_widgets([
        RadioGroupWidget(schema_field="label", label="Label"),
    ])
    return app


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

class TestNavigation:
    def test_first_document_shown_on_load(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "Document 1 of 3")

    def test_document_content_displayed(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_element("#document-content")
        content = dash_duo.find_element("#document-content")
        assert "First document text" in content.text

    def test_prev_button_disabled_on_first_doc(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "Document 1 of 3")
        btn = dash_duo.find_element("#btn-prev")
        assert btn.get_attribute("disabled") is not None or \
               btn.get_attribute("data-disabled") is not None

    def test_next_advances_document(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "Document 1 of 3")
        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "Document 2 of 3")

    def test_next_content_updates(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "Document 1 of 3")
        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_element("#document-content")
        content = dash_duo.find_element("#document-content")
        assert "Second document text" in content.text

    def test_prev_returns_to_first_document(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "Document 2 of 3")
        js_click(dash_duo, "#btn-prev")
        dash_duo.wait_for_text_to_equal("#document-title", "Document 1 of 3")

    def test_next_button_disabled_on_last_doc(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "Document 2 of 3")
        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "Document 3 of 3")
        btn = dash_duo.find_element("#btn-next")
        assert btn.get_attribute("disabled") is not None or \
               btn.get_attribute("data-disabled") is not None

    def test_multi_step_navigation(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "Document 2 of 3")
        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "Document 3 of 3")
        js_click(dash_duo, "#btn-prev")
        dash_duo.wait_for_text_to_equal("#document-title", "Document 2 of 3")


# ---------------------------------------------------------------------------
# Flag and notes
# ---------------------------------------------------------------------------

class TestFlagAndNotes:
    def test_flag_updates_metadata(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "Document 1 of 3")

        js_click(dash_duo, "#flag-document")
        time.sleep(0.4)

        assert tater.metadata["doc1"].flagged is True

    def test_unflag_updates_metadata(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "Document 1 of 3")

        js_click(dash_duo, "#flag-document")
        time.sleep(0.3)
        js_click(dash_duo, "#flag-document")
        time.sleep(0.3)

        assert tater.metadata["doc1"].flagged is False

    def test_flag_is_per_document(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "Document 1 of 3")

        js_click(dash_duo, "#flag-document")
        time.sleep(0.3)

        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "Document 2 of 3")

        assert tater.metadata["doc1"].flagged is True
        assert tater.metadata["doc2"].flagged is False

    def test_notes_update_metadata(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "Document 1 of 3")

        notes = dash_duo.find_element("#document-notes")
        notes.send_keys("needs review")
        time.sleep(0.4)

        assert tater.metadata["doc1"].notes == "needs review"

    def test_notes_are_per_document(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "Document 1 of 3")

        dash_duo.find_element("#document-notes").send_keys("doc1 note")
        time.sleep(0.3)

        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "Document 2 of 3")

        assert tater.metadata["doc1"].notes == "doc1 note"
        assert tater.metadata["doc2"].notes == ""

    def test_notes_field_clears_on_doc_change(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "Document 1 of 3")

        dash_duo.find_element("#document-notes").send_keys("something")
        time.sleep(0.2)

        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "Document 2 of 3")

        notes = dash_duo.find_element("#document-notes")
        val = notes.get_attribute("value") or notes.text
        assert val == ""
