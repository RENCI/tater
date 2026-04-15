"""Repeater widget showcase — list, tabs, and accordion styles for the same schema."""
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

from tater.widgets import (
    SegmentedControlWidget,
    CheckboxWidget,
    SwitchWidget,
    ListableWidget,
    TabsWidget,
    AccordionWidget,
)
from tater.widgets.hierarchical_label import HierarchicalLabelSelectWidget


class Pet(BaseModel):
    kind: Optional[Literal["cat", "dog", "fish"]] = None
    neutered: Optional[bool] = None
    indoor: Optional[bool] = None
    breed: Optional[List[str]] = None


class Schema(BaseModel):
    pets_list: List[Pet] = Field(default_factory=list)
    pets_tabs: List[Pet] = Field(default_factory=list)
    pets_accordion: List[Pet] = Field(default_factory=list)


title = "tater - repeater"
description = "Repeatable list widgets — list, tabs, and accordion styles."

instructions = """Demonstrates the three repeater widget styles for the same item schema:

- **List** — items as a vertical stack of cards
- **Tabs** — items as switchable tabs
- **Accordion** — items as collapsible sections
"""

_item_widgets = lambda: [
    SegmentedControlWidget(schema_field="kind", label="Pet Type"),
    CheckboxWidget(schema_field="neutered", label="Neutered / spayed"),
    SwitchWidget(schema_field="indoor", label="Indoor"),
    HierarchicalLabelSelectWidget(
        schema_field="breed",
        label="Breed",
        hierarchy="apps/examples/data/pet_ontology.yaml",
    ),
]

widgets = [
    ListableWidget(
        schema_field="pets_list",
        label="Pets (List)",
        description="Items shown as a vertical stack of cards.",
        item_label="Pet",
        item_widgets=_item_widgets(),
    ),
    TabsWidget(
        schema_field="pets_tabs",
        label="Pets (Tabs)",
        description="Items shown as switchable tabs.",
        item_label="Pet",
        item_widgets=_item_widgets(),
    ),
    AccordionWidget(
        schema_field="pets_accordion",
        label="Pets (Accordion)",
        description="Items shown as collapsible sections.",
        item_label="Pet",
        item_widgets=_item_widgets(),
    ),
]
