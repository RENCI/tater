"""Simple annotation example with a single-choice and a boolean widget."""
from typing import Optional, Literal
from pydantic import BaseModel

from tater.widgets import SegmentedControlWidget, CheckboxWidget


class Schema(BaseModel):
    pet_mood: Optional[Literal["happy", "anxious", "calm"]] = None
    needs_attention: bool = False


title = "tater - simple"
description = "All widgets specified explicitly."

instructions = """Annotate the pet's current mood using the segmented control.
Check the 'Needs Attention' box if this pet requires immediate care.
"""

widgets = [
    SegmentedControlWidget(
        schema_field="pet_mood",
        label="Pet Mood",
        description="Overall mood of the pet in this record",
        required=True,
    ),
    CheckboxWidget(
        schema_field="needs_attention",
        label="Needs Attention?",
        description="Does this pet require immediate attention?",
    ),
]
