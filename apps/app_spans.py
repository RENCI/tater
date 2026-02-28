"""Span annotation example — label named entities in document text."""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from tater import TaterApp, SpanAnnotation, SpanAnnotationWidget, EntityType, parse_args
from tater.widgets import SegmentedControlWidget


class DocumentAnnotation(BaseModel):
    entities: List[SpanAnnotation] = Field(default_factory=list)
    relevance: Optional[Literal["high", "medium", "low"]] = None


def main() -> None:
    args = parse_args()

    widgets = [
        SpanAnnotationWidget(
            schema_field="entities",
            label="Named Entities",
            description="Highlight text then click an entity type to label it.",
            entity_types=[
                EntityType("Person",       "#a8d8a8"),
                EntityType("Organization", "#a8c8e8"),
                EntityType("Location",     "#f8d8a8"),
                EntityType("Date",         "#e8c8f8"),
            ],
        ),
        SegmentedControlWidget(
            schema_field="relevance",
            label="Relevance",
            required=True,
        ),
    ]

    app = TaterApp(
        title="tater - span annotation",
        theme="light",
        annotations_path=args.annotations,
        schema_model=DocumentAnnotation,
    )

    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets)
    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
