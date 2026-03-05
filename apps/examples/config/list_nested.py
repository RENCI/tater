"""List of nested models example using ListableWidget with multiple item fields."""
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

from tater.widgets import (
    ListableWidget,
    SegmentedControlWidget,
    RadioGroupWidget,
    TextInputWidget,
    TextAreaWidget,
)


class VetVisit(BaseModel):
    date: Optional[str] = None
    reason: Optional[Literal["checkup", "vaccination", "illness", "injury"]] = None
    notes: Optional[str] = None


class Schema(BaseModel):
    vet_visits: List[VetVisit] = Field(default_factory=list)


title = "tater - list (nested)"
description = "List of structured items, each with multiple fields."

widgets = [
    ListableWidget(
        schema_field="vet_visits",
        label="Vet Visits",
        description="Add each veterinary visit with date, reason, and notes.",
        item_label="Visit",
        item_widgets=[
            TextInputWidget(
                schema_field="date",
                label="Visit Date",
                placeholder="e.g. 2024-01-15",
            ),
            RadioGroupWidget(
                schema_field="reason",
                label="Visit Reason",
                vertical=False,
            ),
            TextAreaWidget(
                schema_field="notes",
                label="Visit Notes",
                placeholder="Additional details about the visit...",
            ),
        ],
    ),
]
