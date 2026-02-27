"""Simple flat schema example - no nesting.

Tater app with just flat fields.
"""
from typing import Optional, Literal
from pydantic import BaseModel

from tater import TaterApp, parse_args
from tater.widgets import SegmentedControlWidget, RadioGroupWidget, CheckboxWidget, TextInputWidget, MultiSelectWidget, NumberInputWidget


# Define types
PetType = Literal["cat", "dog", "fish"]
SentimentType = Literal["positive", "negative", "neutral"]


class SimpleAnnotation(BaseModel):
    """Simple flat annotation schema - no nested models."""
    pet_type: Optional[PetType] = None
    sentiment: Optional[SentimentType] = None
    is_cute: bool = False
    reviewer_note: Optional[str] = None
    favorite_colors: Optional[list[str]] = None
    pet_age: Optional[float] = None


def main() -> None:
    args = parse_args()
    
    widgets = [
        RadioGroupWidget(
            schema_field="pet_type",
            label="Pet Type",
            description="What type of pet is mentioned?",
            options=["cat", "dog", "fish"],
            orientation="vertical",
        ),
        SegmentedControlWidget(
            schema_field="sentiment",
            label="Sentiment",
            description="Overall sentiment of the document",
            options=["positive", "negative", "neutral"],
        ),
        CheckboxWidget(
            schema_field="is_cute",
            label="Is cute?",
            description="Check if this pet is cute",
            default=False,
        ),
        TextInputWidget(
            schema_field="reviewer_note",
            label="Reviewer note",
            description="Optional short note about this document",
            placeholder="Enter a short note",
        ),
        MultiSelectWidget(
            schema_field="favorite_colors",
            label="Favorite Colors",
            description="Select one or more favorite colors",
            options=["red", "green", "blue", "yellow", "purple"],
        ),
        NumberInputWidget(
            schema_field="pet_age",
            label="Pet Age",
            description="How old is the pet?",
            min_=0,
            max_=50,
            step=0.1,
        ),
    ]

    app = TaterApp(
        title="tater - simple",
        theme="light",
        annotations_path=args.annotations,
        schema_model=SimpleAnnotation
    )
    
    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets)
    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
