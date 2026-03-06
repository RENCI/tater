"""TabsWidget example — same schema as list.py but rendered as tabs."""
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

from tater.widgets import (
    TabsWidget,
    SegmentedControlWidget,
    CheckboxWidget,
    SwitchWidget,
)
from tater.widgets.hierarchical_label import HierarchicalLabelCompactWidget


class Pet(BaseModel):
    kind: Optional[Literal["cat", "dog", "fish"]] = None
    neutered: Optional[bool] = None
    indoor: Optional[bool] = None
    breed: Optional[str] = None


class Schema(BaseModel):
    pets: List[Pet] = Field(default_factory=list)


title = "tater - tabs"
description = "Repeatable item list using TabsWidget — each pet is a tab."

instructions = """## Steps

1. Click **Add Pet** to create a new tab
2. Fill in each pet's type, neutered status, indoor/outdoor, and breed
3. Switch between pets by clicking their tab
4. Delete a pet by clicking the × on its tab
"""

widgets = [
    TabsWidget(
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
