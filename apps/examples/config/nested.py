"""Single level of nesting example.

Demonstrates using GroupWidget to organise nested Pydantic models.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field

from tater.widgets import SegmentedControlWidget, RadioGroupWidget, GroupWidget


class OwnerInfo(BaseModel):
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    pet_type: Optional[Literal["cat", "dog", "fish"]] = None


class Schema(BaseModel):
    document_sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    owner: OwnerInfo = Field(default_factory=OwnerInfo)


title = "tater - nested"
description = "Single level of nesting via GroupWidget for owner information."

widgets = [
    SegmentedControlWidget(
        schema_field="document_sentiment",
        label="Document Sentiment",
        description="Overall sentiment of the entire document",
    ),
    GroupWidget(
        schema_field="owner",
        label="Owner Information",
        description="Information about the pet owner",
        children=[
            SegmentedControlWidget(
                schema_field="sentiment",
                label="Owner Sentiment",
            ),
            RadioGroupWidget(
                schema_field="pet_type",
                label="Owner's Pet Type",
                vertical=True,
            ),
        ],
    ),
]
