"""Single level of nesting example.

Demonstrates using GroupWidget to organize nested Pydantic models.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field

from tater import TaterApp, parse_args
from tater.widgets import SegmentedControlWidget, RadioGroupWidget, GroupWidget


# Define types
PetType = Literal["cat", "dog", "fish"]
SentimentType = Literal["positive", "negative", "neutral"]


class OwnerInfo(BaseModel):
    """Nested model for owner information."""
    sentiment: Optional[SentimentType] = None
    pet_type: Optional[PetType] = None


class NestedAnnotation(BaseModel):
    """Annotation schema with one level of nesting."""
    document_sentiment: Optional[SentimentType] = None
    owner: OwnerInfo = Field(default_factory=OwnerInfo)


def main() -> None:
    args = parse_args()
    
    # Define widgets with one GroupWidget for nested model
    widgets = [
        SegmentedControlWidget(
            schema_id="document_sentiment",
            label="Document Sentiment",
            description="Overall sentiment of the entire document",
            options=["positive", "negative", "neutral"],
        ),
        GroupWidget(
            schema_id="owner",
            label="Owner Information",
            description="Information about the pet owner",
            children=[
                SegmentedControlWidget(
                    schema_id="sentiment",  # Will become "owner.sentiment"
                    label="Owner Sentiment",
                    options=["positive", "negative", "neutral"],
                ),
                RadioGroupWidget(
                    schema_id="pet_type",  # Will become "owner.pet_type"
                    label="Owner's Pet Type",
                    options=["cat", "dog", "fish"],
                    orientation="vertical",
                )
            ]
        ),
    ]

    app = TaterApp(
        title="Nested Annotation",
        theme="light",
        annotations_path=args.annotations
    )
    
    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets)
    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
