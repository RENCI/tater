"""List of nested models example using ListableWidget with multiple item fields."""
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

from tater.widgets import (
    ListableWidget,
    SegmentedControlWidget,
    RadioGroupWidget,
    TextInputWidget,
)


class Medication(BaseModel):
    name: Optional[str] = None
    route: Optional[Literal["oral", "iv", "topical", "inhaled"]] = None
    frequency: Optional[Literal["once daily", "twice daily", "as needed"]] = None


class Schema(BaseModel):
    medications: List[Medication] = Field(default_factory=list)


title = "tater - list (nested)"
description = "List of structured items, each with multiple fields."

widgets = [
    ListableWidget(
        schema_field="medications",
        label="Medications",
        description="Add each medication entry with name, route, and frequency.",
        item_label="Medication",
        item_widgets=[
            TextInputWidget(
                schema_field="name",
                label="Medication Name",
                placeholder="e.g. Ibuprofen",
            ),
            RadioGroupWidget(
                schema_field="route",
                label="Route",
                vertical=False,
            ),
            SegmentedControlWidget(
                schema_field="frequency",
                label="Frequency",
            ),
        ],
    ),
]
