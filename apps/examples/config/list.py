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

instructions = """Click 'Add' to add pets, or delete individual entries by clicking the delete icon.
Fill in each pet's type.
"""

widgets = [
    ListableWidget(
        schema_field="pets",
        label="Pets",
        description="Track one or more pets for this record.",
        item_label="Pet",
        item_widgets=[
            SegmentedControlWidget(
                schema_field="kind",
                label="Pet Type",
            ),
        ],
    ),
]
