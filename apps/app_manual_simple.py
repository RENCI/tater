"""Simple flat schema example - no nesting.

Tater app with just flat fields.
"""
from typing import Optional, Literal
from pydantic import BaseModel

from tater import TaterApp, parse_args
from tater.widgets import SegmentedControlWidget, RadioGroupWidget


# Define types
PetType = Literal["cat", "dog", "fish"]
SentimentType = Literal["positive", "negative", "neutral"]


class SimpleAnnotation(BaseModel):
    """Simple flat annotation schema - no nested models."""
    pet_type: Optional[PetType] = None
    sentiment: Optional[SentimentType] = None


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
        )
    ]

    app = TaterApp(
        title="Simple Annotation",
        theme="light",
        annotations_path=args.annotations
    )
    
    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets)
    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
