"""Breast pathology specimen annotation - Tater version.

Translates STAND's breast_part_fdx_stand.py to Tater format.
Annotates specimen parts including anatomical location, laterality, 
procedure, and diagnosis concepts using hierarchical labels.
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

from tater.widgets import (
    TextInputWidget, SelectWidget, CheckboxWidget,
    HierarchicalLabelSelectWidget, ListableWidget, AccordionWidget,
)
from tater.widgets.hierarchical_label import load_hierarchy_from_yaml


class DiagnosisConcept(BaseModel):
    """A single diagnosis concept with definitive flag."""
    label: Optional[List[str]] = None
    not_definitive: bool = False


class SpecimenPart(BaseModel):
    """A single specimen part with location, procedure, and diagnoses."""
    anatomical_location: Optional[str] = None
    breast_laterality: Optional[Literal["left", "right", "not_specified"]] = None
    procedure: Optional[str] = None
    explicit_label: Optional[str] = None
    
    diagnosis_concepts: List[DiagnosisConcept] = Field(default_factory=list)
    no_significant_abnormalty: bool = False
    not_a_diagnosis: bool = False


class Schema(BaseModel):
    """Top-level schema for specimen annotation."""
    specimens: List[SpecimenPart] = Field(default_factory=list)


title = "tater - breast pathology (specimen parts)"
description = "Annotate specimen parts with location, laterality, procedure, and diagnosis concepts."

# Load the ontology for hierarchical diagnosis selection
ontology = load_hierarchy_from_yaml("apps/examples/data/breast_fdx_ontology.yaml")

# Build the diagnosis concept widget (reusable for each list item)
diagnosis_concept_children = [
    HierarchicalLabelSelectWidget(
        schema_field="label",
        label="Diagnosis Concept",
        description="Navigate to select the most specific diagnosis concept",
        hierarchy=ontology,
    ),
    CheckboxWidget(
        schema_field="not_definitive",
        label="NOT definitive (e.g., 'suspicious for' or ambiguous language)",
    ),
]

# Build specimen part widget (reusable for each list item)
specimen_children = [
    TextInputWidget(
        schema_field="anatomical_location",
        label="Anatomical Location",
        placeholder="e.g. Breast, Lymph node, etc.",
    ),
    SelectWidget(
        schema_field="breast_laterality",
        label="Breast Laterality",
        description="If applicable",
    ),
    TextInputWidget(
        schema_field="procedure",
        label="Procedure/Sampling Method",
        placeholder="e.g. Fine needle aspirate, excisional biopsy, etc.",
    ),
    TextInputWidget(
        schema_field="explicit_label",
        label="Explicit Specimen Label",
        placeholder="e.g. A, B, C or other label used in report",
    ),
    ListableWidget(
        schema_field="diagnosis_concepts",
        label="Diagnosis Concepts",
        description="Add all positive diagnosis references (exclude negated concepts)",
        item_label="Concept",
        item_widgets=diagnosis_concept_children,
    ),
    CheckboxWidget(
        schema_field="no_significant_abnormalty",
        label="No significant pathologic abnormality",
        description="No diseases/abnormalities present (e.g., 'No evidence of tumor')",
    ),
    CheckboxWidget(
        schema_field="not_a_diagnosis",
        label="Not a diagnosis",
        description="Sentence doesn't mention diagnosis (e.g., 'See comment.' or 'Surgical hardware.')",
    ),
]

widgets = [
    AccordionWidget(
        schema_field="specimens",
        label="Specimen Parts",
        description="Annotate each specimen part discussed in the final diagnosis section. Order by appearance.",
        item_label="Specimen",
        item_widgets=specimen_children,
    ),
]

instructions = """
**Annotation Instructions for Breast Pathology Specimen Parts**

You will annotate specimen parts from a breast pathology report.

**For each specimen part:**

1. **Identify location & procedure**: 
   - Extract anatomical location (e.g., "Breast", "Lymph node")
   - Breast laterality if applicable (left/right/not specified)
   - Sampling procedure (e.g., "Fine needle aspirate", "Excisional biopsy")
   - Copy from text if possible with minimal editing

2. **Identify diagnosis concepts**:
   - Mark all **positive** references to diagnosis concepts (ignore negated ones)
   - Ignore negations like "No evidence of DCIS"
   - Select the **most specific** concept in the hierarchy
   - If language is uncertain (e.g., "suspicious for", "possibly A or B"), mark as "NOT definitive"

3. **Handle edge cases**:
   - If NO diagnosis concepts apply, mark:
     - "No significant pathologic abnormality" if tissue is healthy/normal
     - "Not a diagnosis" if sentence contains no diagnosis info (e.g., "See comment")

4. **Specimen ordering**:
   - Order specimens as they appear in the final diagnosis section  
   - Usually labeled A, B, C... but may be out of order
   - Capture explicit labels if used in report

**Note**: All concepts refer to breast disease (e.g., "epithelial tumors" = breast epithelial tumors),
except "Other malignancy" or "Other disease/abnormality".
"""
