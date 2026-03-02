"""Widget showcase example demonstrating all available widget types."""
from typing import Optional, Literal, List
from pydantic import BaseModel

from tater import TaterApp, parse_args
from tater.widgets import (
    SegmentedControlWidget, RadioGroupWidget, CheckboxWidget, TextInputWidget,
    MultiSelectWidget, NumberInputWidget, ChipGroupWidget, SliderWidget,
    SwitchWidget, SelectWidget, TextAreaWidget, RangeSliderWidget,
)


class MultipleAnnotation(BaseModel):
    """Annotation schema showcasing all widget types."""
    # Single value selects
    pet_type: Optional[Literal["cat", "dog", "fish"]] = None
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    location: Optional[Literal["home", "park", "vet", "shelter", "other"]] = None
    # Boolean
    is_cute: bool = False
    is_indoor: bool = False
    # Multi value selects
    favorite_colors: Optional[List[Literal["red", "green", "blue", "yellow", "purple"]]] = None
    traits: Optional[List[Literal["friendly", "playful", "lazy", "energetic", "shy"]]] = None
    # Numeric
    pet_age: Optional[float] = None
    confidence: Optional[float] = None
    age_range: list[float] = [0.0, 30.0]
    # Text
    reviewer_note: Optional[str] = None
    detailed_notes: Optional[str] = None


def main() -> None:
    args = parse_args()

    widgets = [
        # Single value selects
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
        # Boolean
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
        # Multi value selects
        MultiSelectWidget(
            schema_field="favorite_colors",
            label="Favorite Colors",
            description="Select one or more favorite colors",
            required=True,
        ),
        ChipGroupWidget(
            schema_field="traits",
            label="Traits",
            description="Select all traits that apply",
            required=True,
        ),
        # Numeric
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
        # Range
        RangeSliderWidget(
            schema_field="age_range",
            label="Age Range",
            description="Estimated age range of the pet",
            min_value=0,
            max_value=30,
            step=1,
        ),
        # Text
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

    app = TaterApp(
        title="tater - multiple",
        theme="light",
        annotations_path=args.annotations,
        schema_model=MultipleAnnotation,
    )

    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets)
    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
