"""List-of-lists example — nested ListableWidget.

Each "finding" in a clinical note has a category, a severity, and a list of supporting evidence
snippets.  The outer ListableWidget (findings) and the inner ListableWidget (evidence) are both
fully wired: Add / Delete and value capture work at both levels.
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

instructions = """## Steps

1. Click **Add Finding** to create a new finding entry
2. Select the finding **Category** and **Severity**
3. Within each finding, click **Add Evidence** to attach supporting quotes
4. For each evidence item, paste the quote and select where in the document it appears
5. Delete entries at either level by clicking the × icon
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
