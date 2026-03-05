"""Simple annotation example using fully auto-generated widgets."""
from typing import Optional, Literal
from pydantic import BaseModel


class Schema(BaseModel):
    pet_mood: Optional[Literal["happy", "anxious", "calm"]] = None
    needs_attention: bool = False


title = "tater - simple (defaults)"
description = "All widgets are auto-generated from the schema."
