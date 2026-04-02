"""Shared utilities used across all callback modules."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from dash import html, no_update
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from tater.ui import value_helpers
from tater.widgets.base import ContainerWidget, ControlWidget
from tater.widgets.group import GroupWidget
from tater.widgets.repeater import RepeaterWidget

if TYPE_CHECKING:
    from tater.ui.tater_app import TaterApp
    from tater.widgets.base import TaterWidget


# ---------------------------------------------------------------------------
# Store helpers
# ---------------------------------------------------------------------------

def _default_meta() -> dict:
    return {"flagged": False, "notes": "", "annotation_seconds": 0.0, "visited": False, "status": "not_started"}


def _get_ann(annotations_data: dict | None, doc_id: str | None):
    """Return the annotation dict for *doc_id*, or None."""
    if not annotations_data or not doc_id:
        return None
    return annotations_data.get(doc_id)


def _get_meta(metadata_data: dict | None, doc_id: str | None) -> dict:
    """Return the metadata dict for *doc_id* (with defaults filled in)."""
    base = _default_meta()
    if not metadata_data or not doc_id:
        return base
    stored = metadata_data.get(doc_id)
    if stored is None:
        return base
    return {**base, **stored}


def _has_value(value) -> bool:
    """Return True if a field value is considered filled (non-empty, non-None)."""
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, list) and len(value) == 0:
        return False
    return True


# ---------------------------------------------------------------------------
# Widget-tree collectors
# ---------------------------------------------------------------------------

def _collect_value_capture_widgets(widgets: list[TaterWidget]) -> list[TaterWidget]:
    """Recursively collect all ControlWidget instances (non-containers).

    Used to build the auto-advance field set and to find required widgets
    for status checking. Skips RepeaterWidget children (their items are
    handled dynamically via unified ALL callbacks).
    """
    captured = []
    for widget in widgets:
        if isinstance(widget, RepeaterWidget):
            continue
        elif isinstance(widget, GroupWidget):
            if hasattr(widget, "children") and widget.children:
                captured.extend(_collect_value_capture_widgets(widget.children))
        elif isinstance(widget, ControlWidget):
            captured.append(widget)
    return captured


def _collect_all_control_templates(widgets: list[TaterWidget]) -> list[TaterWidget]:
    """Recursively collect all ControlWidget templates, including inside repeaters.

    Used to build empty_value lookups for load callbacks.
    """
    captured = []
    for widget in widgets:
        if isinstance(widget, RepeaterWidget):
            captured.extend(_collect_all_control_templates(widget.item_widgets))
        elif isinstance(widget, GroupWidget):
            if hasattr(widget, "children") and widget.children:
                captured.extend(_collect_all_control_templates(widget.children))
        elif isinstance(widget, ControlWidget):
            captured.append(widget)
    return captured


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def update_status_for_doc(tater_app: TaterApp, doc_id: str, annotations_data: dict | None, metadata_data: dict) -> None:
    """Compute and store the annotation status for a document.

    Mutates ``metadata_data[doc_id]["status"]`` in-place.
    """
    if not doc_id or metadata_data is None:
        return
    meta = metadata_data.setdefault(doc_id, _default_meta())

    if not meta.get("visited", False):
        meta["status"] = "not_started"
        return

    # Booleans always have a value (True/False), so they cannot meaningfully gate completion.
    required_widgets = tater_app._required_widgets
    if not required_widgets:
        meta["status"] = "complete"
        return

    ann = _get_ann(annotations_data, doc_id)
    if ann is None:
        meta["status"] = "in_progress"
        return

    for widget in required_widgets:
        value = value_helpers.get_model_value(ann, widget.field_path)
        if not _has_value(value):
            meta["status"] = "in_progress"
            return

    meta["status"] = "complete"


# ---------------------------------------------------------------------------
# Navigation + menu
# ---------------------------------------------------------------------------

def _build_menu_items(tater_app: TaterApp, metadata_data: dict | None, flagged_only: bool = False) -> list:
    """Build document menu items with status badges and flag indicators."""
    status_labels = {"not_started": "Not Started", "in_progress": "In Progress", "complete": "Complete"}
    status_colors = {"not_started": "gray", "in_progress": "blue", "complete": "teal"}
    items = []
    for i, doc in enumerate(tater_app.documents):
        meta = _get_meta(metadata_data, doc.id)
        flagged = meta.get("flagged", False)
        if flagged_only and not flagged:
            continue
        status = meta.get("status", "not_started")
        right_children = []
        if flagged:
            right_children.append(DashIconify(icon="tabler:flag-filled", color="red", width=14))
        right_children.append(
            dmc.Badge(
                status_labels.get(status, status),
                color=status_colors.get(status, "gray"),
                variant="light",
                size="xs",
            )
        )
        items.append(
            dmc.MenuItem(
                dmc.Group(
                    [
                        dmc.Text(f"{i + 1}. {doc.display_name()}", size="sm"),
                        dmc.Group(right_children, gap="xs"),
                    ],
                    gap="xs",
                    wrap="nowrap",
                    justify="space-between",
                ),
                id={"type": "document-menu-item", "index": i},
            )
        )
    if not items:
        items.append(dmc.Text("No flagged documents", size="sm", c="dimmed", p="xs"))
    return items


def _perform_navigation(
    tater_app: TaterApp,
    current_doc_id: str,
    new_index: int,
    timing_data: dict,
    annotations_data: dict | None,
    metadata_data: dict | None,
) -> tuple:
    """Shared navigation logic: accumulate timing, update status, return new doc_id, timing, metadata."""
    now = time.time()
    metadata_data = dict(metadata_data or {})
    if current_doc_id:
        meta = dict(_get_meta(metadata_data, current_doc_id))
        start = timing_data.get("doc_start_time") if timing_data else None
        if start:
            meta["annotation_seconds"] = meta.get("annotation_seconds", 0.0) + (now - start)
        metadata_data[current_doc_id] = meta
        update_status_for_doc(tater_app, current_doc_id, annotations_data, metadata_data)

    doc_id = tater_app.documents[new_index].id if new_index < len(tater_app.documents) else ""
    if timing_data is None:
        timing_data = {}
    timing_data["last_save_time"] = now
    timing_data["doc_start_time"] = now
    timing_data["paused"] = False
    if "session_start_time" not in timing_data or timing_data["session_start_time"] is None:
        timing_data["session_start_time"] = now
    new_meta = _get_meta(metadata_data, doc_id)
    timing_data["annotation_seconds_at_load"] = new_meta.get("annotation_seconds", 0.0)

    return doc_id, timing_data, metadata_data
