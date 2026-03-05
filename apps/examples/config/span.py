"""Span annotation example for tagging pet-related entities."""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from tater import SpanAnnotation, SpanAnnotationWidget, EntityType
from tater.widgets import SegmentedControlWidget


class Schema(BaseModel):
    entities: List[SpanAnnotation] = Field(default_factory=list)
    quality: Optional[Literal["high", "medium", "low"]] = None


title = "tater - span annotation"
description = "Tag named entities in pet-related text using the span annotation widget."

instructions = "Highlight relevant text spans in the document, then click an entity type to label the span."

widgets = [
    SpanAnnotationWidget(
        schema_field="entities",
        label="Pet Entities",
        description="Highlight text then click an entity type to label it.",
        entity_types=[
            EntityType("Pet"),
            EntityType("Breed"),
            EntityType("Behavior"),
            EntityType("Activity"),
        ],
    ),
    SegmentedControlWidget(
        schema_field="quality",
        label="Record Quality",
        required=True,
    ),
]
