"""Hierarchical multi-select with all four search filter mode combinations."""
from typing import List, Optional
from pydantic import BaseModel

from tater.widgets import HierarchicalLabelMultiWidget
from tater.widgets.hierarchical_label import load_hierarchy_from_yaml


class Schema(BaseModel):
    breeds_ancestors: Optional[List[List[str]]] = None
    breeds_siblings: Optional[List[List[str]]] = None
    breeds_children: Optional[List[List[str]]] = None
    breeds_context: Optional[List[List[str]]] = None


title = "tater - hierarchical multi search modes"
description = "Compares the four search filter modes for HierarchicalLabelMultiWidget."

instructions = """## Search filter modes

All four widgets share the same ontology. Try searching **"spaniel"** (a leaf term)
or **"sporting"** (a non-leaf group) to see how results differ.

| Widget | `search_show_siblings` | `search_show_children` | What you see |
|--------|----------------------|----------------------|--------------|
| **Ancestors only** | ✗ | ✗ | Matched terms + spine to root |
| **Siblings** | ✓ | ✗ | Matched terms + ancestors + peer nodes |
| **Children** | ✗ | ✓ | Matched terms + ancestors + direct children |
| **Context** | ✓ | ✓ | Matched terms + ancestors + siblings + children |
"""

ontology = load_hierarchy_from_yaml("apps/examples/data/pet_ontology.yaml")

allow_non_leaf = False

widgets = [
    HierarchicalLabelMultiWidget(
        schema_field="breeds_ancestors",
        label="Ancestors only",
        description="Matched terms + spine to root. Try searching 'spaniel' or 'sporting'.",
        hierarchy=ontology,
        searchable=True,
        allow_non_leaf=allow_non_leaf,
        search_show_siblings=False,
        search_show_children=False,
    ),
    HierarchicalLabelMultiWidget(
        schema_field="breeds_siblings",
        label="Siblings",
        description="Matched terms + ancestors + peer nodes at the same level.",
        hierarchy=ontology,
        searchable=True,
        allow_non_leaf=allow_non_leaf,
        search_show_siblings=True,
        search_show_children=False,
    ),
    HierarchicalLabelMultiWidget(
        schema_field="breeds_children",
        label="Children",
        description="Matched terms + ancestors + direct children of matched terms.",
        hierarchy=ontology,
        searchable=True,
        allow_non_leaf=allow_non_leaf,
        search_show_siblings=False,
        search_show_children=True,
    ),
    HierarchicalLabelMultiWidget(
        schema_field="breeds_context",
        label="Context (siblings + children)",
        description="Matched terms + ancestors + siblings + direct children.",
        hierarchy=ontology,
        searchable=True,
        allow_non_leaf=allow_non_leaf,
        search_show_siblings=True,
        search_show_children=True,
    ),
]
