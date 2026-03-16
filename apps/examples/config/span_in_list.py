"""Span annotation inside a ListableWidget — each finding has labelled evidence spans."""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from tater import SpanAnnotation, SpanAnnotationWidget, EntityType
from tater.widgets import ListableWidget, SegmentedControlWidget


class Finding(BaseModel):
    label: Optional[Literal["positive", "negative", "uncertain"]] = None
    evidence: List[SpanAnnotation] = Field(default_factory=list)


class Schema(BaseModel):
    findings: List[Finding] = Field(default_factory=list)
    overall: Optional[Literal["normal", "abnormal"]] = None


title = "tater - spans in list"
description = "Span annotation inside a repeatable list — each finding tracks its own evidence spans."

instructions = """## Steps

1. Click **Add Finding** to create a new finding card
2. Select the finding label (positive / negative / uncertain)
3. Highlight text in the document, then click an evidence entity type to tag it for that finding
4. Repeat for each finding
5. Set the overall assessment at the bottom
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
            SpanAnnotationWidget(
                schema_field="evidence",
                label="Evidence Spans",
                description="Highlight text then click an entity type to tag evidence for this finding.",
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
