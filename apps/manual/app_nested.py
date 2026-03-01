"""Single level of nesting example.

Demonstrates using GroupWidget to organize nested Pydantic models.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field

from tater import TaterApp, parse_args
from tater.widgets import SegmentedControlWidget, RadioGroupWidget, GroupWidget


class OwnerInfo(BaseModel):
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    pet_type: Optional[Literal["cat", "dog", "fish"]] = None


class NestedAnnotation(BaseModel):
    document_sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    owner: OwnerInfo = Field(default_factory=OwnerInfo)


def main() -> None:
    args = parse_args()

    widgets = [
        SegmentedControlWidget(
            schema_field="document_sentiment",
            label="Document Sentiment",
            description="Overall sentiment of the entire document",
        ),
        GroupWidget(
            schema_field="owner",
            label="Owner Information",
            description="Information about the pet owner",
            children=[
                SegmentedControlWidget(
                    schema_field="sentiment",
                    label="Owner Sentiment",
                ),
                RadioGroupWidget(
                    schema_field="pet_type",
                    label="Owner's Pet Type",
                    vertical=True,
                ),
            ],
        ),
    ]

    app = TaterApp(
        title="tater - nested",
        theme="light",
        annotations_path=args.annotations,
        schema_model=NestedAnnotation,
    )

    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets)
    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
