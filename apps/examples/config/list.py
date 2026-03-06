"""Repeatable nested model example using ListableWidget."""
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

from tater.widgets import (
    SegmentedControlWidget,
    CheckboxWidget,
    SwitchWidget,
    ListableWidget,
)
from tater.widgets.hierarchical_label import HierarchicalLabelCompactWidget


class Pet(BaseModel):
    kind: Optional[Literal["cat", "dog", "fish"]] = None
    neutered: Optional[bool] = None
    indoor: Optional[bool] = None
    breed: Optional[str] = None


class Schema(BaseModel):
    pets: List[Pet] = Field(default_factory=list)


title = "tater - list"
description = "Repeatable item list using ListableWidget — add or remove pet entries."

instructions = """## Steps

1. Click **Add Pet** to create a new pet entry
2. Fill in each pet's type, neutered status, indoor/outdoor, and breed
3. Delete entries by clicking the × icon
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
            CheckboxWidget(
                schema_field="neutered",
                label="Neutered / spayed",
            ),
            SwitchWidget(
                schema_field="indoor",
                label="Indoor",
            ),
            HierarchicalLabelCompactWidget(
                schema_field="breed",
                label="Breed",
                hierarchy="apps/examples/data/pet_ontology.yaml",
            ),
        ],
    ),
]
