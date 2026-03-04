"""Simple annotation example with a single-choice and a boolean widget."""
from typing import Optional, Literal
from pydantic import BaseModel

from tater.widgets import SegmentedControlWidget, CheckboxWidget


class Schema(BaseModel):
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    is_relevant: bool = False


title = "tater - simple"
description = "All widgets specified explicitly."

widgets = [
    SegmentedControlWidget(
        schema_field="sentiment",
        label="Sentiment",
        description="Overall sentiment of the document",
        required=True,
    ),
    CheckboxWidget(
        schema_field="is_relevant",
        label="Relevant?",
        description="Is this document relevant?",
    ),
]
