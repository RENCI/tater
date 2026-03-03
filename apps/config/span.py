"""Span annotation example for tagging medical entities."""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from tater import SpanAnnotation, SpanAnnotationWidget, EntityType
from tater.widgets import SegmentedControlWidget


class Schema(BaseModel):
    entities: List[SpanAnnotation] = Field(default_factory=list)
    quality: Optional[Literal["high", "medium", "low"]] = None


title = "tater - span annotation"

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
