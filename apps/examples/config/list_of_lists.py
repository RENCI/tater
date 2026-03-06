"""List-of-lists example — demonstrates nested ListableWidget (currently partial support).

Each "finding" in a clinical note has a type, a severity, and a list of supporting evidence
snippets. The outer ListableWidget (findings) works fully. The inner ListableWidget (evidence)
renders its items correctly on load but its Add/Delete buttons are inert because
register_callbacks is only called on top-level widgets — nested container widgets are skipped.

This config exists to drive implementation of nested list callback registration.
"""
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

from tater.widgets import (
    ListableWidget,
    SegmentedControlWidget,
    RadioGroupWidget,
    TextInputWidget,
    TextAreaWidget,
)


class Evidence(BaseModel):
    quote: Optional[str] = None
    location: Optional[Literal["title", "abstract", "methods", "results", "discussion"]] = None


class Finding(BaseModel):
    category: Optional[Literal["diagnosis", "treatment", "outcome", "risk_factor"]] = None
    severity: Optional[Literal["mild", "moderate", "severe"]] = None
    evidence: List[Evidence] = Field(default_factory=list)


class Schema(BaseModel):
    findings: List[Finding] = Field(default_factory=list)


title = "tater - list of lists"
description = "Each finding contains a nested list of supporting evidence items."

instructions = """## Instructions

1. Click **Add Finding** to create a new finding entry
2. Select the finding **category** and **severity**
3. Within each finding, click **Add Evidence** to attach supporting quotes
4. For each evidence item, paste the quote and select where in the document it appears

> **Note:** The inner evidence list renders correctly on load but Add/Delete buttons
> are not yet wired up (nested ListableWidget callbacks not implemented).
"""

widgets = [
    ListableWidget(
        schema_field="findings",
        label="Findings",
        description="Annotate each clinical finding and its supporting evidence.",
        item_label="Finding",
        item_widgets=[
            SegmentedControlWidget(
                schema_field="category",
                label="Category",
            ),
            RadioGroupWidget(
                schema_field="severity",
                label="Severity",
                vertical=False,
            ),
            ListableWidget(
                schema_field="evidence",
                label="Supporting Evidence",
                description="Add quotes from the document that support this finding.",
                item_label="Evidence",
                item_widgets=[
                    TextAreaWidget(
                        schema_field="quote",
                        label="Quote",
                        placeholder="Paste the relevant passage...",
                    ),
                    SegmentedControlWidget(
                        schema_field="location",
                        label="Location",
                    ),
                ],
            ),
        ],
    ),
]
