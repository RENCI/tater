"""Browser integration tests using dash.testing (dash_duo fixture).

Covers low-complexity interactions: navigation, document content display,
flag checkbox, and notes textarea — all using simple string component IDs.

Run with:
    pytest tests/test_browser.py --headless
"""
import json
import time
from pathlib import Path
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


def read_saved(tater) -> dict:
    """Read the on-disk annotations file and return the parsed dict.

    Flag/notes are persisted to disk via auto_save (server-side callback).
    tater.metadata is not updated during a browser session — the source of
    truth is the file written by _save_stores_to_file.
    """
    return json.loads(Path(tater.annotations_path).read_text())


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


@pytest.fixture
def tater_required(tmp_path, docs_file):
    """TaterApp with one required RadioGroup — status transitions are observable."""
    ann_path = tmp_path / "ann_req.json"
    app = TaterApp(
        title="Test App Required",
        schema_model=SimpleSchema,
        annotations_path=str(ann_path),
    )
    app.load_documents(docs_file)
    app.set_annotation_widgets([
        RadioGroupWidget(schema_field="label", label="Label", required=True),
    ])
    return app


@pytest.fixture
def tater_auto_advance(tmp_path, docs_file):
    """TaterApp with an auto_advance RadioGroup."""
    ann_path = tmp_path / "ann_aa.json"
    app = TaterApp(
        title="Test App Auto Advance",
        schema_model=SimpleSchema,
        annotations_path=str(ann_path),
    )
    app.load_documents(docs_file)
    app.set_annotation_widgets([
        RadioGroupWidget(schema_field="label", label="Label", auto_advance=True),
    ])
    return app


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

class TestNavigation:
    def test_first_document_shown_on_load(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")

    def test_document_content_displayed(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")
        content = dash_duo.find_element("#document-content")
        assert "First document text" in content.text

    def test_prev_button_disabled_on_first_doc(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")
        btn = dash_duo.find_element("#btn-prev")
        assert btn.get_attribute("disabled") is not None or \
               btn.get_attribute("data-disabled") is not None

    def test_next_advances_document(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")
        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "2 / 3")

    def test_next_content_updates(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")
        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_element("#document-content")
        content = dash_duo.find_element("#document-content")
        assert "Second document text" in content.text

    def test_prev_returns_to_first_document(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")
        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "2 / 3")
        js_click(dash_duo, "#btn-prev")
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")

    def test_next_button_disabled_on_last_doc(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")
        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "2 / 3")
        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "3 / 3")
        btn = dash_duo.find_element("#btn-next")
        assert btn.get_attribute("disabled") is not None or \
               btn.get_attribute("data-disabled") is not None

    def test_multi_step_navigation(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")
        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "2 / 3")
        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "3 / 3")
        js_click(dash_duo, "#btn-prev")
        dash_duo.wait_for_text_to_equal("#document-title", "2 / 3")


# ---------------------------------------------------------------------------
# Flag and notes
# ---------------------------------------------------------------------------

class TestFlagAndNotes:
    def test_flag_updates_metadata(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")

        js_click(dash_duo, "#flag-document")
        time.sleep(0.6)  # wait for auto_save to write

        saved = read_saved(tater)
        assert saved["doc1"]["metadata"]["flagged"] is True

    def test_unflag_updates_metadata(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")

        js_click(dash_duo, "#flag-document")
        time.sleep(0.3)
        js_click(dash_duo, "#flag-document")
        time.sleep(0.6)  # wait for auto_save to write

        saved = read_saved(tater)
        assert saved["doc1"]["metadata"]["flagged"] is False

    def test_flag_is_per_document(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")

        js_click(dash_duo, "#flag-document")
        time.sleep(0.3)

        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "2 / 3")
        time.sleep(0.6)  # wait for auto_save to write

        saved = read_saved(tater)
        assert saved["doc1"]["metadata"]["flagged"] is True
        assert saved.get("doc2", {}).get("metadata", {}).get("flagged", False) is False

    def test_notes_update_metadata(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")

        dash_duo.find_element("#document-notes").send_keys("needs review")
        time.sleep(0.6)  # wait for auto_save to write

        saved = read_saved(tater)
        assert saved["doc1"]["metadata"]["notes"] == "needs review"

    def test_notes_are_per_document(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")

        dash_duo.find_element("#document-notes").send_keys("doc1 note")
        time.sleep(0.3)

        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "2 / 3")
        time.sleep(0.6)  # wait for auto_save to write

        saved = read_saved(tater)
        assert saved["doc1"]["metadata"]["notes"] == "doc1 note"
        assert saved.get("doc2", {}).get("metadata", {}).get("notes", "") == ""

    def test_notes_field_clears_on_doc_change(self, dash_duo, tater):
        dash_duo.start_server(tater.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")

        dash_duo.find_element("#document-notes").send_keys("something")
        time.sleep(0.2)

        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "2 / 3")

        notes = dash_duo.find_element("#document-notes")
        val = notes.get_attribute("value") or notes.text
        assert val == ""


# ---------------------------------------------------------------------------
# Annotation persistence
# ---------------------------------------------------------------------------

class TestAnnotationPersistence:
    def test_annotation_survives_navigation(self, dash_duo, tater_required):
        """Select a value, navigate away and back — loadValues restores it."""
        dash_duo.start_server(tater_required.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")

        # Select "positive"
        dash_duo.driver.execute_script(
            "arguments[0].click();",
            dash_duo.find_element("input[type='radio'][value='positive']"),
        )

        # Navigate to doc 2 then back to doc 1
        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "2 / 3")
        js_click(dash_duo, "#btn-prev")
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")

        # loadValues restores the annotation clientside — wait for the checked input
        dash_duo.wait_for_element("input[type='radio'][value='positive']:checked")

    def test_status_badge_goes_complete_on_required_field_fill(self, dash_duo, tater_required):
        """Status badge reaches Complete once all required fields are filled."""
        dash_duo.start_server(tater_required.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")
        # Wait for on_doc_change (server callback) to settle — it writes visited=True to
        # metadata-store, which update_status_from_annotations depends on via State.
        # Without this, the status callback may read stale metadata and compute "not_started".
        time.sleep(0.5)

        dash_duo.driver.execute_script(
            "arguments[0].click();",
            dash_duo.find_element("input[type='radio'][value='positive']"),
        )
        dash_duo.wait_for_text_to_equal("#status-badge", "COMPLETE")

    def test_annotation_persists_to_file(self, dash_duo, tater_required):
        """Annotation written by captureValue reaches disk via auto_save."""
        dash_duo.start_server(tater_required.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")

        dash_duo.driver.execute_script(
            "arguments[0].click();",
            dash_duo.find_element("input[type='radio'][value='negative']"),
        )
        time.sleep(0.8)  # wait for auto_save

        saved = read_saved(tater_required)
        assert saved["doc1"]["annotations"]["label"] == "negative"

    def test_different_docs_have_independent_annotations(self, dash_duo, tater_required):
        """Annotations for each document are stored independently."""
        dash_duo.start_server(tater_required.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")

        dash_duo.driver.execute_script(
            "arguments[0].click();",
            dash_duo.find_element("input[type='radio'][value='positive']"),
        )

        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "2 / 3")

        dash_duo.driver.execute_script(
            "arguments[0].click();",
            dash_duo.find_element("input[type='radio'][value='negative']"),
        )
        time.sleep(0.8)  # wait for auto_save

        saved = read_saved(tater_required)
        assert saved["doc1"]["annotations"]["label"] == "positive"
        assert saved["doc2"]["annotations"]["label"] == "negative"


# ---------------------------------------------------------------------------
# Auto-advance
# ---------------------------------------------------------------------------

class TestAutoAdvance:
    def test_selecting_value_advances_to_next_doc(self, dash_duo, tater_auto_advance):
        """Selecting a value on an auto_advance widget advances to the next document."""
        dash_duo.start_server(tater_auto_advance.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")

        dash_duo.driver.execute_script(
            "arguments[0].click();",
            dash_duo.find_element("input[type='radio'][value='positive']"),
        )
        dash_duo.wait_for_text_to_equal("#document-title", "2 / 3")

    def test_auto_advance_does_not_advance_past_last_doc(self, dash_duo, tater_auto_advance):
        """Selecting a value on the last document does not navigate further."""
        dash_duo.start_server(tater_auto_advance.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")

        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "2 / 3")
        js_click(dash_duo, "#btn-next")
        dash_duo.wait_for_text_to_equal("#document-title", "3 / 3")

        dash_duo.driver.execute_script(
            "arguments[0].click();",
            dash_duo.find_element("input[type='radio'][value='positive']"),
        )
        time.sleep(0.5)
        assert dash_duo.find_element("#document-title").text == "3 / 3"


# ---------------------------------------------------------------------------
# Save and restore
# ---------------------------------------------------------------------------

class TestSaveRestore:
    def test_annotations_restored_on_reload(self, dash_duo, tater_required, docs_file, tmp_path):
        """Annotations written during a session are loaded by a new TaterApp instance."""
        dash_duo.start_server(tater_required.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")

        dash_duo.driver.execute_script(
            "arguments[0].click();",
            dash_duo.find_element("input[type='radio'][value='uncertain']"),
        )
        time.sleep(0.8)  # wait for auto_save

        # Verify the file was written before creating the new app
        saved = read_saved(tater_required)
        assert saved["doc1"]["annotations"]["label"] == "uncertain"

        # New TaterApp loading from the same annotations file
        from tater.ui.tater_app import TaterApp
        from tater.widgets import RadioGroupWidget

        app2 = TaterApp(
            title="Reload Test",
            schema_model=SimpleSchema,
            annotations_path=tater_required.annotations_path,
        )
        app2.load_documents(docs_file)
        app2.set_annotation_widgets([
            RadioGroupWidget(schema_field="label", label="Label", required=True),
        ])

        assert "doc1" in app2.annotations
        assert app2.annotations["doc1"].label == "uncertain"

    def test_no_restore_skips_loading(self, dash_duo, tater_required, docs_file, tmp_path):
        """--no-restore (restore_annotations=False) means prior annotations are ignored."""
        dash_duo.start_server(tater_required.app)
        dash_duo.wait_for_text_to_equal("#document-title", "1 / 3")

        dash_duo.driver.execute_script(
            "arguments[0].click();",
            dash_duo.find_element("input[type='radio'][value='positive']"),
        )
        time.sleep(0.8)

        from tater.ui.tater_app import TaterApp
        from tater.widgets import RadioGroupWidget

        app2 = TaterApp(
            title="No Restore Test",
            schema_model=SimpleSchema,
            annotations_path=tater_required.annotations_path,
            restore_annotations=False,
        )
        app2.load_documents(docs_file)
        app2.set_annotation_widgets([
            RadioGroupWidget(schema_field="label", label="Label", required=True),
        ])

        # No annotations loaded — doc1 should be absent or have no label
        ann = app2.annotations.get("doc1")
        assert ann is None or ann.label is None
