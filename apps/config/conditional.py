"""Conditional widget visibility example.

Demonstrates the ``.conditional_on(field, value)`` API for showing/hiding
widgets based on the value of a boolean field.
"""
from typing import Optional
from pydantic import BaseModel

from tater.widgets import CheckboxWidget, SwitchWidget, TextInputWidget, TextAreaWidget


class Schema(BaseModel):
    is_indoor: bool = False
    indoor_location: Optional[str] = None

    has_health_issue: bool = False
    health_description: Optional[str] = None

    is_stray: bool = False
    rescue_org: Optional[str] = None
    rescue_notes: Optional[str] = None


title = "tater - conditional"

widgets = [
    SwitchWidget(
        schema_field="is_indoor",
        label="Indoor?",
        description="Is this an indoor setting?",
    ),
    TextInputWidget(
        schema_field="indoor_location",
        label="Indoor Location",
        placeholder="e.g. living room, kitchen",
    ).conditional_on("is_indoor", True),

    CheckboxWidget(
        schema_field="has_health_issue",
        label="Has health issue?",
    ),
    TextAreaWidget(
        schema_field="health_description",
        label="Health Description",
        placeholder="Describe the health issue...",
    ).conditional_on("has_health_issue", True),

    SwitchWidget(
        schema_field="is_stray",
        label="Is stray?",
    ),
    TextInputWidget(
        schema_field="rescue_org",
        label="Rescue Organisation",
        placeholder="Organisation name",
    ).conditional_on("is_stray", True),
    TextAreaWidget(
        schema_field="rescue_notes",
        label="Rescue Notes",
        placeholder="Additional notes about rescue...",
    ).conditional_on("is_stray", True),
]
