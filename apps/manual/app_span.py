"""Span annotation example using clinical notes.

Demonstrates SpanAnnotationWidget for tagging medical entities.
Run with: python apps/app_manual_span.py --documents data/documents.json
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from tater import TaterApp, SpanAnnotation, SpanAnnotationWidget, EntityType, parse_args
from tater.widgets import SegmentedControlWidget


class ClinicalAnnotation(BaseModel):
    entities: List[SpanAnnotation] = Field(default_factory=list)
    quality: Optional[Literal["high", "medium", "low"]] = None


def main() -> None:
    args = parse_args()

    widgets = [
        SpanAnnotationWidget(
            schema_field="entities",
            label="Clinical Entities",
            description="Highlight text then click an entity type to label it.",
            entity_types=[
                EntityType("Medication"),
                EntityType("Diagnosis"),
                EntityType("Symptom"),
                EntityType("Procedure"),
            ],
        ),
        SegmentedControlWidget(
            schema_field="quality",
            label="Note Quality",
            required=True,
        ),
    ]

    app = TaterApp(
        title="tater - clinical span annotation",
        theme="light",
        annotations_path=args.annotations,
        schema_model=ClinicalAnnotation,
    )

    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets)
    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
