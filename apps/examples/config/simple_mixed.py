"""Simple annotation using default widget generation with one override.

Only ``pet_mood`` is specified explicitly; the runner detects the partial
list and auto-generates the remaining fields (``needs_attention``) via
``widgets_from_model``.
"""
from typing import Optional, Literal
from pydantic import BaseModel

from tater.widgets import RadioGroupWidget


class Schema(BaseModel):
    pet_mood: Optional[Literal["happy", "anxious", "calm"]] = None
    needs_attention: bool = False


title = "tater - simple (mixed)"
description = "Explicitly specifies one widget; the remaining fields are auto-generated."

widgets = [
    RadioGroupWidget(
        schema_field="pet_mood",
        label="Pet Mood",
        description="Overall mood of the pet in this record",
        required=True,
        vertical=True,
    ),
]
