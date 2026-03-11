"""Widget showcase demonstrating all available widget types."""
from typing import Optional, Literal, List
from pydantic import BaseModel

from tater.widgets import (
    SegmentedControlWidget, RadioGroupWidget, CheckboxWidget, TextInputWidget,
    MultiSelectWidget, NumberInputWidget, SliderWidget,
    SwitchWidget, SelectWidget, TextAreaWidget, RangeSliderWidget,
)


class Schema(BaseModel):
    pet_type: Optional[Literal["cat", "dog", "fish"]] = None
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    location: Optional[Literal["home", "park", "vet", "shelter", "other"]] = None
    is_cute: bool = False
    is_indoor: bool = False
    favorite_colors: Optional[List[Literal["red", "green", "blue", "yellow", "purple"]]] = None
    traits: Optional[List[Literal["friendly", "playful", "lazy", "energetic", "shy"]]] = None
    pet_age: Optional[float] = None
    confidence: Optional[float] = None
    age_range: Optional[list[float]] = None
    reviewer_note: Optional[str] = None
    detailed_notes: Optional[str] = None


title = "tater - multiple"
description = "Showcases all available widget types in a single annotation schema."

instructions = "This is a widget showcase. Fill in each field using the appropriate widget type: radio buttons, segmented controls, checkboxes, text inputs, sliders, and multi-select dropdowns."

widgets = [
    RadioGroupWidget(
        schema_field="pet_type",
        label="Pet Type",
        description="What type of pet is mentioned?",
        required=True,
    ),
    SegmentedControlWidget(
        schema_field="sentiment",
        label="Sentiment",
        description="Overall sentiment of the document",
        required=True,
    ),
    SelectWidget(
        schema_field="location",
        label="Location",
        description="Where is the pet located?",
        required=True,
    ),
    CheckboxWidget(
        schema_field="is_cute",
        label="Is cute?",
        description="Check if this pet is cute",
    ),
    SwitchWidget(
        schema_field="is_indoor",
        label="Indoor?",
        description="Is this an indoor setting?",
    ),
    MultiSelectWidget(
        schema_field="favorite_colors",
        label="Favorite Colors",
        description="Select one or more favorite colors",
        required=True,
    ),
    MultiSelectWidget(
        schema_field="traits",
        label="Traits",
        description="Select all traits that apply",
        required=True,
    ),
    NumberInputWidget(
        schema_field="pet_age",
        label="Pet Age",
        description="How old is the pet?",
        min_value=0,
        max_value=50,
        step=0.1,
        required=True,
    ),
    SliderWidget(
        schema_field="confidence",
        label="Confidence",
        description="How confident are you in this annotation?",
        min_value=0,
        max_value=100,
        step=1,
        default=50,
        required=True,
    ),
    RangeSliderWidget(
        schema_field="age_range",
        label="Age Range",
        description="Estimated age range of the pet",
        min_value=0,
        max_value=30,
        step=1,
    ),
    TextInputWidget(
        schema_field="reviewer_note",
        label="Reviewer note",
        description="Optional short note about this document",
        placeholder="Enter a short note",
        required=True,
    ),
    TextAreaWidget(
        schema_field="detailed_notes",
        label="Detailed Notes",
        description="Extended notes about this document",
        placeholder="Enter detailed notes...",
    ),
]
