"""Hierarchical label annotation using a pet/animal ontology."""
from typing import Optional
from pydantic import BaseModel

from tater.widgets import HierarchicalLabelFullWidget, HierarchicalLabelCompactWidget
from tater.widgets.hierarchical_label import load_hierarchy_from_yaml


class Schema(BaseModel):
    primary_breed: Optional[str] = None
    secondary_breed: Optional[str] = None


title = "tater - hierarchical"
description = "Ontology-driven annotation using compact and full hierarchical label widgets."

ontology = load_hierarchy_from_yaml("apps/examples/data/pet_ontology.yaml")

widgets = [
    HierarchicalLabelCompactWidget(
        schema_field="primary_breed",
        label="Primary Breed",
        description="Navigate the ontology to select a breed or type.",
        hierarchy=ontology,
        searchable=True,
    ),
    HierarchicalLabelFullWidget(
        schema_field="secondary_breed",
        label="Secondary Breed (Mixed)",
        description="Select a secondary breed if the pet is a mix.",
        hierarchy=ontology,
        searchable=True,
    ),
]
