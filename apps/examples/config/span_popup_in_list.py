"""Popup span annotation inside a ListableWidget — each finding has labelled evidence spans."""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from tater import SpanAnnotation, SpanPopupWidget, EntityType
from tater.widgets import ListableWidget, SegmentedControlWidget


class Finding(BaseModel):
    label: Optional[Literal["positive", "negative", "uncertain"]] = None
    evidence: List[SpanAnnotation] = Field(default_factory=list)


class Schema(BaseModel):
    findings: List[Finding] = Field(default_factory=list)
    overall: Optional[Literal["normal", "abnormal"]] = None


title = "tater - popup spans in list"
description = "Popup span annotation inside a repeatable list — select text to tag evidence per finding."

instructions = """## Steps

1. Click **Add Finding** to create a new finding card
2. Select the finding label (positive / negative / uncertain)
3. Click a finding's evidence strip to make it the active widget
4. Highlight text in the document — a popup appears near the selection
5. Click an entity type in the popup to tag that span
6. Repeat for each finding
7. Set the overall assessment at the bottom

The active finding's evidence strip is fully highlighted; inactive ones are faded.
"""

widgets = [
    ListableWidget(
        schema_field="findings",
        label="Findings",
        item_label="Finding",
        item_widgets=[
            SegmentedControlWidget(
                schema_field="label",
                label="Label",
            ),
            SpanPopupWidget(
                schema_field="evidence",
                label="Evidence Spans",
                description="Click to activate, then highlight text to tag evidence for this finding.",
                entity_types=[
                    EntityType("Support"),
                    EntityType("Against"),
                    EntityType("Context"),
                ],
            ),
        ],
    ),
    SegmentedControlWidget(
        schema_field="overall",
        label="Overall Assessment",
        required=True,
    ),
]
