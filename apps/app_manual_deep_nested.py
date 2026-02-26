"""Deep nesting example - two levels of GroupWidget.

Demonstrates arbitrary nesting depth with Pydantic models.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field

from tater import TaterApp, parse_args
from tater.widgets import SegmentedControlWidget, RadioGroupWidget, GroupWidget


# Define types
PetType = Literal["cat", "dog", "fish"]
SentimentType = Literal["positive", "negative", "neutral"]


class Location(BaseModel):
    """Deeply nested model - third level."""
    sentiment: Optional[SentimentType] = None


class Address(BaseModel):
    """Nested model - second level."""
    location: Location = Field(default_factory=Location)
    pet_type: Optional[PetType] = None


class DeepAnnotation(BaseModel):
    """Annotation schema with two levels of nesting."""
    document_sentiment: Optional[SentimentType] = None
    address: Address = Field(default_factory=Address)


def main() -> None:
    args = parse_args()
    
    # Define widgets with two levels of GroupWidget nesting
    widgets = [
        SegmentedControlWidget(
            schema_field="document_sentiment",
            label="Document Sentiment",
            description="Top-level field",
            options=["positive", "negative", "neutral"],
        ),
        GroupWidget(
            schema_field="address",
            label="Address",
            description="First level of nesting",
            children=[
                RadioGroupWidget(
                    schema_field="pet_type",  # Will become "address.pet_type"
                    label="Pet Type at Address",
                    options=["cat", "dog", "fish"],
                    orientation="vertical",
                ),
                GroupWidget(
                    schema_field="location",  # Will become "address.location"
                    label="Location Details",
                    description="Second level of nesting",
                    children=[
                        SegmentedControlWidget(
                            schema_field="sentiment",  # Will become "address.location.sentiment"
                            label="Location Sentiment",
                            description="Three levels deep!",
                            options=["positive", "negative", "neutral"],
                        ),
                    ]
                ),
            ]
        ),
    ]

    app = TaterApp(
        title="Deep Nested Annotation",
        theme="light",
        annotations_path=args.annotations
    )
    
    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets)
    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
