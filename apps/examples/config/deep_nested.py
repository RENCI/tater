"""Deep nesting example — two levels of GroupWidget."""
from typing import Optional, Literal
from pydantic import BaseModel, Field

from tater.widgets import SegmentedControlWidget, RadioGroupWidget, GroupWidget


class Location(BaseModel):
    location_mood: Optional[Literal["cheerful", "stressful", "peaceful"]] = None


class Address(BaseModel):
    location: Location = Field(default_factory=Location)
    pet_type: Optional[Literal["cat", "dog", "fish"]] = None


class Schema(BaseModel):
    document_mood: Optional[Literal["positive", "negative", "neutral"]] = None
    address: Address = Field(default_factory=Address)


title = "tater - deep nested"
description = "Two levels of GroupWidget nesting demonstrating deep schema paths."

widgets = [
    SegmentedControlWidget(
        schema_field="document_mood",
        label="Document Mood",
        description="Top-level field",
    ),
    GroupWidget(
        schema_field="address",
        label="Address",
        description="First level of nesting",
        children=[
            RadioGroupWidget(
                schema_field="pet_type",
                label="Pet Type at Address",
                vertical=True,
            ),
            GroupWidget(
                schema_field="location",
                label="Location Details",
                description="Second level of nesting",
                children=[
                    SegmentedControlWidget(
                        schema_field="location_mood",
                        label="Location Atmosphere",
                        description="Three levels deep!",
                    ),
                ],
            ),
        ],
    ),
]
