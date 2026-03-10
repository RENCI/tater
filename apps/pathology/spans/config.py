"""Generic pathology span annotation - Tater version.

Translates spans.py to Tater format.
Highlights clinically relevant spans in pathology reports using configurable entity types.
"""
from typing import List
from pydantic import BaseModel, Field

from tater import SpanAnnotation, SpanAnnotationWidget, EntityType


class Schema(BaseModel):
    spans: List[SpanAnnotation] = Field(default_factory=list)


title = "tater - pathology span annotation"
description = "Highlight clinically relevant spans in pathology reports."

widgets = [
    SpanAnnotationWidget(
        schema_field="spans",
        label="Annotated Spans",
        description="Highlight text then click an entity type to tag it.",
        entity_types=[
            EntityType("Diagnosis"),
            EntityType("Anatomy"),
            EntityType("Procedure"),
            EntityType("Finding"),
            EntityType("Qualifier"),
        ],
    ),
]

instructions = """## Annotation Instructions

Highlight a span of text in the document, then click the appropriate entity type button to tag it.

| Entity Type | Examples |
|---|---|
| **Diagnosis** | "Invasive ductal carcinoma", "DCIS", "adenocarcinoma" |
| **Anatomy** | "left breast", "axillary lymph node", "upper outer quadrant" |
| **Procedure** | "core needle biopsy", "excisional biopsy", "mastectomy" |
| **Finding** | "positive margins", "lymphovascular invasion", "grade 2" |
| **Qualifier** | "moderately differentiated", "high-grade", "bilateral" |

### Tips
- Tag only spans in the **final diagnosis** section unless instructed otherwise.
- Keep spans tight — do not include surrounding punctuation or whitespace.
- Overlapping spans are not permitted.
- Click an existing highlight in the document to delete it.
"""
