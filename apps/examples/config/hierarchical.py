"""Hierarchical label annotation using a pet/animal ontology."""
from typing import List, Optional
from pydantic import BaseModel

from tater.widgets import HierarchicalLabelSelectWidget, HierarchicalLabelMultiWidget, DividerWidget
from tater.widgets.hierarchical_label import load_hierarchy_from_yaml


class Schema(BaseModel):
    breed: Optional[List[str]] = None
    breeds_multi: Optional[List[List[str]]] = None
    breed_any: Optional[List[str]] = None
    breeds_multi_any: Optional[List[List[str]]] = None


title = "tater - hierarchical"
description = "Ontology-driven annotation using single-select and multi-select hierarchical label widgets."

instructions = """## Usage

- Type to search the ontology by name
- Select a breed from the filtered dropdown
- Use the multi-select widget to choose multiple breeds
- The "any level" variants allow selecting intermediate nodes (e.g. a species group)
"""

ontology = load_hierarchy_from_yaml("apps/examples/data/pet_ontology.yaml")

widgets = [
    DividerWidget(label="Leaf nodes only"),
    HierarchicalLabelSelectWidget(
        schema_field="breed",
        label="Breed",
        description="Select a single breed or type.",
        hierarchy=ontology,
    ),
    HierarchicalLabelMultiWidget(
        schema_field="breeds_multi",
        label="Breeds (Multi)",
        description="Select one or more breeds.",
        hierarchy=ontology,
    ),
    DividerWidget(label="Any level"),
    HierarchicalLabelSelectWidget(
        schema_field="breed_any",
        label="Breed",
        description="Select a breed or any intermediate category.",
        hierarchy=ontology,
        allow_non_leaf=True,
    ),
    HierarchicalLabelMultiWidget(
        schema_field="breeds_multi_any",
        label="Breeds (Multi)",
        description="Select one or more breeds or intermediate categories.",
        hierarchy=ontology,
        allow_non_leaf=True,
    ),
]
