"""Widget gallery demonstrating all available widget types, grouped by category."""
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

from tater.widgets import (
    SegmentedControlWidget, RadioGroupWidget, CheckboxWidget, TextInputWidget,
    MultiSelectWidget, CheckboxGroupWidget, NumberInputWidget, SliderWidget, RangeSliderWidget,
    SwitchWidget, SelectWidget, TextAreaWidget, ChipWidget, GroupWidget,
)


class SingleChoiceFields(BaseModel):
    pet_type: Optional[Literal["cat", "dog", "fish"]] = None
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    location: Optional[Literal["home", "park", "vet", "shelter", "other"]] = None


class BooleanFields(BaseModel):
    is_cute: bool = False
    is_indoor: bool = False
    is_vaccinated: bool = False


class MultiChoiceFields(BaseModel):
    favorite_colors: Optional[List[Literal["red", "green", "blue", "yellow", "purple"]]] = None
    traits: Optional[List[Literal["friendly", "shy", "energetic", "calm", "playful"]]] = None


class NumericFields(BaseModel):
    pet_age: Optional[float] = None
    confidence: Optional[float] = None
    age_range: Optional[list[float]] = None


class TextFields(BaseModel):
    reviewer_note: Optional[str] = None
    detailed_notes: Optional[str] = None


class Schema(BaseModel):
    boolean: BooleanFields = Field(default_factory=BooleanFields)
    single_choice: SingleChoiceFields = Field(default_factory=SingleChoiceFields)
    multi_choice: MultiChoiceFields = Field(default_factory=MultiChoiceFields)
    numeric: NumericFields = Field(default_factory=NumericFields)
    text: TextFields = Field(default_factory=TextFields)


title = "tater - gallery"
description = "Showcases all available widget types grouped by category."

instructions = "This is a widget gallery. Each group demonstrates a different category of widget."

widgets = [
    GroupWidget(
        schema_field="boolean",
        label="Boolean",
        description="True/false toggles.",
        children=[
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
            ChipWidget(
                schema_field="is_vaccinated",
                label="Vaccinated",
                description="Is this pet vaccinated?",
            ),
        ],
    ),
    GroupWidget(
        schema_field="single_choice",
        label="Single Choice",
        description="Pick one value from a set of options.",
        children=[
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
        ],
    ),
    GroupWidget(
        schema_field="multi_choice",
        label="Multi Choice",
        description="Select one or more values from a set of options.",
        children=[
            MultiSelectWidget(
                schema_field="favorite_colors",
                label="Favorite Colors",
                description="Select one or more favorite colors",
                required=True,
            ),
            CheckboxGroupWidget(
                schema_field="traits",
                label="Traits",
                description="Select all traits that apply",
            ),
        ],
    ),
    GroupWidget(
        schema_field="numeric",
        label="Numeric",
        description="Enter or select a number.",
        children=[
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
        ],
    ),
    GroupWidget(
        schema_field="text",
        label="Text",
        description="Free-text entry.",
        children=[
            TextInputWidget(
                schema_field="reviewer_note",
                label="Reviewer Note",
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
        ],
    ),
]
