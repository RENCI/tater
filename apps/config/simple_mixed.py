"""Simple annotation using default widget generation with one override.

Only ``sentiment`` is specified explicitly; the runner detects the partial
list and auto-generates the remaining fields (``is_relevant``) via
``widgets_from_model``.
"""
from typing import Optional, Literal
from pydantic import BaseModel

from tater.widgets import RadioGroupWidget


class Schema(BaseModel):
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    is_relevant: bool = False


title = "tater - simple (mixed)"
description = "Explicitly specifies one widget; the remaining fields are auto-generated."

widgets = [
    RadioGroupWidget(
        schema_field="sentiment",
        label="Sentiment",
        description="Overall sentiment of the document",
        required=True,
        vertical=True,
    ),
]
