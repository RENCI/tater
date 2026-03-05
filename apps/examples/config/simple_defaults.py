"""Simple annotation example using fully auto-generated widgets."""
from typing import Optional, Literal
from pydantic import BaseModel


class Schema(BaseModel):
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    is_relevant: bool = False


title = "tater - simple (defaults)"
description = "All widgets are auto-generated from the schema."
