"""Single level of nesting example.

Demonstrates using GroupWidget to organise nested Pydantic models.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field

from tater.widgets import SegmentedControlWidget, RadioGroupWidget, GroupWidget


class OwnerInfo(BaseModel):
    owner_mood: Optional[Literal["happy", "anxious", "calm"]] = None
    pet_type: Optional[Literal["cat", "dog", "fish"]] = None


class Schema(BaseModel):
    document_mood: Optional[Literal["positive", "negative", "neutral"]] = None
    owner: OwnerInfo = Field(default_factory=OwnerInfo)


title = "tater - nested"
description = "Single level of nesting via GroupWidget for owner information."

widgets = [
    SegmentedControlWidget(
        schema_field="document_mood",
        label="Document Mood",
        description="Overall tone of the entire document",
    ),
    GroupWidget(
        schema_field="owner",
        label="Owner Information",
        description="Information about the pet owner",
        children=[
            SegmentedControlWidget(
                schema_field="owner_mood",
                label="Owner Mood",
            ),
            RadioGroupWidget(
                schema_field="pet_type",
                label="Owner's Pet Type",
                vertical=True,
            ),
        ],
    ),
]
