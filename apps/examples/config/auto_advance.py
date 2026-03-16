"""Auto-advance example — choice and boolean widgets that navigate on selection.

Selecting a choice or toggling a boolean with ``auto_advance=True`` automatically
moves to the next document as soon as a value is captured, so annotators never
have to reach for the navigation buttons on high-throughput labelling tasks.

Two auto-advance patterns are shown:
  - ``SegmentedControlWidget`` (choice): advances when the user picks any option
  - ``SwitchWidget`` (boolean): advances when the toggle is turned on *or* off
"""
from typing import Optional, Literal
from pydantic import BaseModel

from tater.widgets import (
    SegmentedControlWidget,
    SwitchWidget,
    TextAreaWidget,
)


class Schema(BaseModel):
    relevance: Optional[Literal["relevant", "not relevant", "unsure"]] = None
    needs_review: bool = False
    notes: Optional[str] = None


title = "tater - auto-advance"
description = "Choice and boolean widgets that automatically advance to the next document on selection."

instructions = """## Auto-advance annotation

This example demonstrates two auto-advance patterns:

**Choice auto-advance** (`SegmentedControlWidget`)
- Selecting any option immediately moves to the next document
- Useful for high-throughput single-label tasks

**Boolean auto-advance** (`SwitchWidget`)
- Toggling the switch (on *or* off) immediately moves to the next document
- Useful for quick yes/no screening passes

The **Notes** field does not auto-advance — free-text fields rarely benefit from it.

> **Tip:** If you need to correct a label on a previous document, use the document
> selector in the sidebar rather than navigating back through auto-advanced docs.
"""

widgets = [
    SegmentedControlWidget(
        schema_field="relevance",
        label="Relevance",
        description="Is this document relevant to the study? Selecting an option advances to the next document.",
        required=True,
        auto_advance=True,
    ),
    SwitchWidget(
        schema_field="needs_review",
        label="Needs Review",
        description="Flag this document for a second-pass review. Toggling advances to the next document.",
        auto_advance=True,
    ),
    TextAreaWidget(
        schema_field="notes",
        label="Notes",
        description="Optional free-text notes. Does not trigger auto-advance.",
        placeholder="Any additional observations...",
    ),
]
