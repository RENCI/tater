"""Conditional widget visibility example.

Demonstrates the ``.conditional_on(field, value)`` API for showing/hiding
widgets based on both boolean fields and choice/option fields, inside a
repeatable AccordionWidget with GroupWidgets as item sections.
"""
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

from tater.widgets import (
    CheckboxWidget, SwitchWidget, ChipWidget, SelectWidget, RadioGroupWidget,
    TextInputWidget, TextAreaWidget, AccordionWidget,
)
from tater.widgets.group import GroupWidget


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


class PetItem(BaseModel):
    booleans: BooleanFields = Field(default_factory=BooleanFields)
    choices: ChoiceFields = Field(default_factory=ChoiceFields)
    additional_notes: Optional[str] = None


class Schema(BaseModel):
    pets: List[PetItem] = Field(default_factory=list)


title = "tater - conditional"
description = "Widgets that appear based on boolean toggles or the selected option."

instructions = """Try toggling or selecting inside each accordion item:

**Boolean conditions** (Status group)
- **Indoor?** – Reveals an indoor location field
- **Has health issue?** – Reveals a health description
- **Is stray?** – Reveals rescue organisation and notes

**Choice conditions** (Type & Breed group)
- **Pet Type** – Reveals dog, cat, or fish-specific fields
"""

widgets = [
    AccordionWidget(
        schema_field="pets",
        label="Conditional in Repeater",
        description="Boolean and choice conditionals inside grouped sections of a repeatable accordion.",
        item_label="Pet",
        item_widgets=[
            GroupWidget(
                schema_field="booleans",
                label="Status",
                description="Boolean toggle conditionals",
                children=[
                    SwitchWidget("is_indoor", label="Indoor?",
                                 description="Is this an indoor setting?"),
                    TextInputWidget("indoor_location", label="Indoor Location",
                                    placeholder="e.g. living room, kitchen",
                                    ).conditional_on("is_indoor", True),

                    CheckboxWidget("has_health_issue", label="Has health issue?"),
                    TextAreaWidget("health_description", label="Health Description",
                                   placeholder="Describe the health issue...",
                                   ).conditional_on("has_health_issue", True),

                    ChipWidget("is_stray", label="Is stray?"),
                    TextInputWidget("rescue_org", label="Rescue Organisation",
                                    placeholder="Organisation name",
                                    ).conditional_on("is_stray", True),
                    TextAreaWidget("rescue_notes", label="Rescue Notes",
                                   placeholder="Additional notes about rescue...",
                                   ).conditional_on("is_stray", True),
                ],
            ),
            GroupWidget(
                schema_field="choices",
                label="Type & Breed",
                description="Choice-based conditionals",
                children=[
                    SelectWidget("pet_type", label="Pet Type",
                                 description="Select the pet type to see relevant fields",
                                 required=True),
                    TextInputWidget("dog_breed", label="Dog Breed",
                                    placeholder="e.g. Golden Retriever",
                                    ).conditional_on("pet_type", "dog"),
                    RadioGroupWidget("dog_temperament", label="Dog Temperament",
                                     vertical=False,
                                     ).conditional_on("pet_type", "dog"),
                    TextInputWidget("cat_color", label="Cat Color",
                                    placeholder="e.g. Orange tabby",
                                    ).conditional_on("pet_type", "cat"),
                    SelectWidget("fish_tank_size", label="Tank Size",
                                 description="What size tank is the fish in?",
                                 ).conditional_on("pet_type", "fish"),
                ],
            ),
            TextAreaWidget("additional_notes", label="Additional Notes",
                           placeholder="Any other notes about the pet..."),
        ],
    ),
]
