"""Repeatable nested model example using ListableWidget."""
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

from tater.widgets import SegmentedControlWidget, ListableWidget


class Pet(BaseModel):
    kind: Optional[Literal["cat", "dog", "fish"]] = None


class Schema(BaseModel):
    pets: List[Pet] = Field(default_factory=list)


title = "tater - list"
description = "Repeatable item list using ListableWidget — add or remove pet entries."

widgets = [
    ListableWidget(
        schema_field="pets",
        label="Pets",
        item_widgets=[
            SegmentedControlWidget(
                schema_field="kind",
                label="Pet Type",
            ),
        ],
        add_label="Add Pet",
        delete_label="Delete Pet",
        initial_count=1,
    ),
]
