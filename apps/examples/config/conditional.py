"""Conditional widget visibility example.

Demonstrates the ``.conditional_on(field, value)`` API for showing/hiding
widgets based on both boolean fields and choice/option fields.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field

from tater.widgets import (
    CheckboxWidget, SwitchWidget, ChipWidget, SelectWidget, RadioGroupWidget,
    TextInputWidget, TextAreaWidget, GroupWidget,
)


class BooleanFields(BaseModel):
    is_indoor: bool = False
    indoor_location: Optional[str] = None
    has_health_issue: bool = False
    health_description: Optional[str] = None
    is_stray: bool = False
    rescue_org: Optional[str] = None
    rescue_notes: Optional[str] = None


class ChoiceFields(BaseModel):
    pet_type: Optional[Literal["cat", "dog", "fish"]] = None
    dog_breed: Optional[str] = None
    dog_temperament: Optional[Literal["calm", "playful", "aggressive"]] = None
    cat_color: Optional[str] = None
    fish_tank_size: Optional[Literal["small", "medium", "large"]] = None
    additional_notes: Optional[str] = None


class Schema(BaseModel):
    booleans: BooleanFields = Field(default_factory=BooleanFields)
    choices: ChoiceFields = Field(default_factory=ChoiceFields)


title = "tater - conditional"
description = "Widgets that appear based on boolean toggles or the selected option."

instructions = """Try toggling or selecting:

**Boolean conditions**
- **Indoor?** – Reveals an indoor location field
- **Has health issue?** – Reveals a health description
- **Is stray?** – Reveals rescue organisation and notes

**Choice conditions**
- **Pet Type** – Reveals dog, cat, or fish-specific fields
"""

widgets = [
    GroupWidget(
        schema_field="booleans",
        label="Boolean Conditions",
        children=[
            SwitchWidget("is_indoor", label="Indoor?",
                         description="Is this an indoor setting?"),
            TextInputWidget("indoor_location", label="Indoor Location",
                            placeholder="e.g. living room, kitchen",
                            ).conditional_on(["booleans", "is_indoor"], True),

            CheckboxWidget("has_health_issue", label="Has health issue?"),
            TextAreaWidget("health_description", label="Health Description",
                           placeholder="Describe the health issue...",
                           ).conditional_on(["booleans", "has_health_issue"], True),

            ChipWidget("is_stray", label="Is stray?"),
            TextInputWidget("rescue_org", label="Rescue Organisation",
                            placeholder="Organisation name",
                            ).conditional_on(["booleans", "is_stray"], True),
            TextAreaWidget("rescue_notes", label="Rescue Notes",
                           placeholder="Additional notes about rescue...",
                           ).conditional_on(["booleans", "is_stray"], True),
        ],
    ),
    GroupWidget(
        schema_field="choices",
        label="Choice Conditions",
        children=[
            SelectWidget("pet_type", label="Pet Type",
                         description="Select the pet type to see relevant fields",
                         required=True),
            TextInputWidget("dog_breed", label="Dog Breed",
                            placeholder="e.g. Golden Retriever",
                            ).conditional_on(["choices", "pet_type"], "dog"),
            RadioGroupWidget("dog_temperament", label="Dog Temperament",
                             vertical=False,
                             ).conditional_on(["choices", "pet_type"], "dog"),
            TextInputWidget("cat_color", label="Cat Color",
                            placeholder="e.g. Orange tabby",
                            ).conditional_on(["choices", "pet_type"], "cat"),
            SelectWidget("fish_tank_size", label="Tank Size",
                         description="What size tank is the fish in?",
                         ).conditional_on(["choices", "pet_type"], "fish"),
            TextAreaWidget("additional_notes", label="Additional Notes",
                           placeholder="Any other notes about the pet..."),
        ],
    ),
]
