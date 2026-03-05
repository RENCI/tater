"""Conditional widgets based on choice/option field values.

Demonstrates the ``.conditional_on(field, value)`` API for showing/hiding
widgets based on the value of an option field (not just booleans).
"""
from typing import Optional, Literal
from pydantic import BaseModel

from tater.widgets import (
    SelectWidget, TextInputWidget, TextAreaWidget, CheckboxWidget, RadioGroupWidget
)


class Schema(BaseModel):
    pet_type: Optional[Literal["cat", "dog", "fish"]] = None
    dog_breed: Optional[str] = None
    dog_temperament: Optional[Literal["calm", "playful", "aggressive"]] = None
    cat_color: Optional[str] = None
    fish_tank_size: Optional[Literal["small", "medium", "large"]] = None
    additional_notes: Optional[str] = None


title = "tater - conditional (choice-based)"
description = "Widgets that appear based on the selected pet type."

widgets = [
    SelectWidget(
        schema_field="pet_type",
        label="Pet Type",
        description="Select the pet type to see relevant fields",
        required=True,
    ),
    # Dog-specific fields
    TextInputWidget(
        schema_field="dog_breed",
        label="Dog Breed",
        placeholder="e.g. Golden Retriever",
    ).conditional_on("pet_type", "dog"),
    
    RadioGroupWidget(
        schema_field="dog_temperament",
        label="Dog Temperament",
        vertical=False,
    ).conditional_on("pet_type", "dog"),

    # Cat-specific field
    TextInputWidget(
        schema_field="cat_color",
        label="Cat Color",
        placeholder="e.g. Orange tabby",
    ).conditional_on("pet_type", "cat"),

    # Fish-specific field
    SelectWidget(
        schema_field="fish_tank_size",
        label="Tank Size",
        description="What size tank is the fish in?",
    ).conditional_on("pet_type", "fish"),

    # Always visible
    TextAreaWidget(
        schema_field="additional_notes",
        label="Additional Notes",
        placeholder="Any other notes about the pet...",
    ),
]
