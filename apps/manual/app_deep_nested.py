"""Deep nesting example - two levels of GroupWidget.

Demonstrates arbitrary nesting depth with Pydantic models.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field

from tater import TaterApp, parse_args
from tater.widgets import SegmentedControlWidget, RadioGroupWidget, GroupWidget


class Location(BaseModel):
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None


class Address(BaseModel):
    location: Location = Field(default_factory=Location)
    pet_type: Optional[Literal["cat", "dog", "fish"]] = None


class DeepAnnotation(BaseModel):
    document_sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    address: Address = Field(default_factory=Address)


def main() -> None:
    args = parse_args()

    widgets = [
        SegmentedControlWidget(
            schema_field="document_sentiment",
            label="Document Sentiment",
            description="Top-level field",
        ),
        GroupWidget(
            schema_field="address",
            label="Address",
            description="First level of nesting",
            children=[
                RadioGroupWidget(
                    schema_field="pet_type",
                    label="Pet Type at Address",
                    vertical=True,
                ),
                GroupWidget(
                    schema_field="location",
                    label="Location Details",
                    description="Second level of nesting",
                    children=[
                        SegmentedControlWidget(
                            schema_field="sentiment",
                            label="Location Sentiment",
                            description="Three levels deep!",
                        ),
                    ],
                ),
            ],
        ),
    ]

    app = TaterApp(
        title="tater - deep nested",
        theme="light",
        annotations_path=args.annotations,
        schema_model=DeepAnnotation,
    )

    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets)
    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
