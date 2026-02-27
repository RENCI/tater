"""Widget showcase example demonstrating all available widget types."""
from typing import Optional, Literal
from pydantic import BaseModel

from tater import TaterApp, parse_args
from tater.widgets import SegmentedControlWidget, RadioGroupWidget, CheckboxWidget, TextInputWidget, MultiSelectWidget, NumberInputWidget, ChipGroupWidget, SliderWidget, SwitchWidget, SelectWidget


# Define types
PetType = Literal["cat", "dog", "fish"]
SentimentType = Literal["positive", "negative", "neutral"]


class MultipleAnnotation(BaseModel):
    """Annotation schema showcasing all widget types."""
    # Single value selects
    pet_type: Optional[PetType] = None
    sentiment: Optional[SentimentType] = None
    location: Optional[str] = None
    # Boolean
    is_cute: bool = False
    is_indoor: bool = False
    # Multi value selects
    favorite_colors: Optional[list[str]] = None
    traits: Optional[list[str]] = None
    # Numeric
    pet_age: Optional[float] = None
    confidence: Optional[float] = None
    # Text
    reviewer_note: Optional[str] = None


def main() -> None:
    args = parse_args()
    
    widgets = [
        # Single value selects
        RadioGroupWidget(
            schema_field="pet_type",
            label="Pet Type",
            description="What type of pet is mentioned?",
            options=["cat", "dog", "fish"],
            required=True,
        ),
        SegmentedControlWidget(
            schema_field="sentiment",
            label="Sentiment",
            description="Overall sentiment of the document",
            options=["positive", "negative", "neutral"],
            required=True,
        ),
        SelectWidget(
            schema_field="location",
            label="Location",
            description="Where is the pet located?",
            options=["home", "park", "vet", "shelter", "other"],
            required=True,
        ),
        # Boolean
        CheckboxWidget(
            schema_field="is_cute",
            label="Is cute?",
            description="Check if this pet is cute",
            default=False,
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
            options=["red", "green", "blue", "yellow", "purple"],
            required=True,
        ),
        ChipGroupWidget(
            schema_field="traits",
            label="Traits",
            description="Select all traits that apply",
            options=["friendly", "playful", "lazy", "energetic", "shy"],
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
        # Text
        TextInputWidget(
            schema_field="reviewer_note",
            label="Reviewer note",
            description="Optional short note about this document",
            placeholder="Enter a short note",
            required=True,
        ),
    ]

    app = TaterApp(
        title="tater - multiple",
        theme="light",
        annotations_path=args.annotations,
        schema_model=MultipleAnnotation
    )
    
    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets)
    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
