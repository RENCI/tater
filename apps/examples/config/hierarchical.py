"""Hierarchical label annotation using a breast pathology ontology."""
from typing import Optional
from pydantic import BaseModel

from tater.widgets import HierarchicalLabelFullWidget, HierarchicalLabelCompactWidget
from tater.widgets.hierarchical_label import load_hierarchy_from_yaml


class Schema(BaseModel):
    diagnosis: Optional[str] = None
    secondary_diagnosis: Optional[str] = None


title = "tater - hierarchical"
description = "Ontology-driven annotation using compact and full hierarchical label widgets."

ontology = load_hierarchy_from_yaml("data/breast_fdx_ontology.yaml")

widgets = [
    HierarchicalLabelCompactWidget(
        schema_field="diagnosis",
        label="Diagnosis",
        description="Navigate the ontology to select a diagnosis.",
        hierarchy=ontology,
        searchable=True,
    ),
    HierarchicalLabelFullWidget(
        schema_field="secondary_diagnosis",
        label="Secondary Diagnosis",
        description="Navigate the ontology to select a secondary diagnosis.",
        hierarchy=ontology,
        searchable=True,
    ),
]
