"""Example demonstrating DividerWidget for named section breaks."""
from typing import Optional, Literal
from pydantic import BaseModel

from tater.widgets import (
    DividerWidget,
    SegmentedControlWidget,
    RadioGroupWidget,
    CheckboxWidget,
    TextAreaWidget,
)


class Schema(BaseModel):
    pet_mood: Optional[Literal["happy", "anxious", "calm"]] = None
    energy_level: Optional[Literal["low", "medium", "high"]] = None
    needs_attention: bool = False
    notes: Optional[str] = None


title = "tater - divider"
description = "Demonstrates DividerWidget for section breaks."

widgets = [
    DividerWidget(label="Mood Assessment", description="Emotional and energy state of the pet"),
    SegmentedControlWidget("pet_mood", label="Pet Mood", required=True),
    RadioGroupWidget("energy_level", label="Energy Level", required=True),
    DividerWidget(label="Actions"),
    CheckboxWidget("needs_attention", label="Needs Attention?"),
    TextAreaWidget("notes", label="Notes", description="Any additional observations"),
]
