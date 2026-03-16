"""Hierarchical label annotation using a pet/animal ontology."""
from typing import Optional
from pydantic import BaseModel

from tater.widgets import HierarchicalLabelFullWidget, HierarchicalLabelCompactWidget, HierarchicalLabelTagsWidget
from tater.widgets.hierarchical_label import load_hierarchy_from_yaml


class Schema(BaseModel):
    tags_breed: Optional[str] = None
    primary_breed: Optional[str] = None
    secondary_breed: Optional[str] = None


title = "tater - hierarchical"
description = "Ontology-driven annotation using tags, compact, and full hierarchical label widgets."

instructions = """## Navigation

- Use **chevron buttons** (→) to explore the ontology
- Use **search** to find breeds by name
- Expand/collapse branches with the tree UI

**Tags Breed** uses tags view (path shown as dismissible pills).
**Primary Breed** uses compact view (shows only selected).
**Secondary Breed** uses full view (shows all siblings).
"""

ontology = load_hierarchy_from_yaml("apps/examples/data/pet_ontology.yaml")

widgets = [
    HierarchicalLabelTagsWidget(
        schema_field="tags_breed",
        label="Tags Breed",
        description="Navigate via pill tags — click a tag to go back, × to deselect.",
        hierarchy=ontology,
        searchable=True,
    ),
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
