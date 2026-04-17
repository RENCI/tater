"""Popup span annotation example — entity buttons appear on text selection."""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from tater import SpanAnnotation, SpanPopupWidget, EntityType
from tater.widgets import SegmentedControlWidget


class Schema(BaseModel):
    entities: List[SpanAnnotation] = Field(default_factory=list)
    quality: Optional[Literal["high", "medium", "low"]] = None


title = "tater - popup span annotation"
description = "Select text in the document to tag entities with a floating popup."

instructions = """1. Highlight text in the document
2. A popup appears near the selection — click an entity type to label it:
   - `Pet` - animal name or subject
   - `Breed` - species or breed
   - `Behavior` - actions or states
   - `Activity` - what the pet is doing
3. Click the counter strip on the right to switch which widget is active
   when multiple span fields are present
"""

widgets = [
    SpanPopupWidget(
        schema_field="entities",
        label="Pet Entities",
        description="Highlight text to tag — popup appears near the selection.",
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
