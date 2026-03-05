"""Granular breast cancer diagnosis annotation - Tater version.

Translates STAND's granular_breast_fdx_stand.py to Tater format.
Annotates individual diagnoses selected from a hierarchical diagnosis ontology,
with per-diagnosis flags for definitiveness.

Pattern: List of DiagnosisItem, each selecting from the hierarchy and marking
whether it's definitive or not-yet-definitive.
"""
from typing import Optional, List
from pydantic import BaseModel, Field

from tater.widgets import (
    CheckboxWidget, HierarchicalLabelCompactWidget,
    ListableWidget
)
from tater.widgets.hierarchical_label import load_hierarchy_from_yaml


class DiagnosisItem(BaseModel):
    """Single diagnosis code and its definitive status."""
    diagnosis_code: Optional[str] = None
    not_definitive: bool = False
    still_pending: bool = False


class Schema(BaseModel):
    """Top-level schema for granular diagnosis annotation."""
    diagnoses: List[DiagnosisItem] = Field(default_factory=list)


title = "tater - granular breast diagnosis annotation"
description = "Annotate individual breast cancer diagnoses with definitive status."

# Load the hierarchical diagnosis ontology
ontology = load_hierarchy_from_yaml("apps/pathology/granular_breast_fdx/breast_fdx_ontology.yaml")


widgets = [
    ListableWidget(
        schema_field="diagnoses",
        label="Breast Cancer Diagnoses",
        description="Add each diagnosis mentioned in the pathology report",
        item_label="Diagnosis",
        item_widgets=[
            HierarchicalLabelCompactWidget(
                schema_field="diagnosis_code",
                label="Diagnosis",
                description="Browse the hierarchical diagnosis ontology",
                hierarchy=ontology,
                searchable=True,
            ),
            
            CheckboxWidget(
                schema_field="not_definitive",
                label="Not yet definitive (requires additional testing)",
                description="Check if this diagnosis is incomplete or provisional",
            ),
            
            CheckboxWidget(
                schema_field="still_pending",
                label="Still pending results",
                description="Check if additional test results are still pending",
            ),
        ],
    ),
]

instructions = """
**Annotation Instructions for Granular Breast Diagnosis**

This tool helps annotate individual breast cancer diagnoses from a pathology report.

**For each diagnosis:**

1. **Select the diagnosis code**:
   - Browse the hierarchical diagnosis ontology using the chevron (›) buttons
   - Navigate through levels: Tumor Type → Histologic Grade → Molecular Subtype (if applicable)
   - Click a diagnosis to select it; the selected path appears above

2. **Mark definitiveness**:
   - Check "Not yet definitive" if this diagnosis is provisional or incomplete
   - Provisional diagnoses typically require additional testing (immunohistochemistry, molecular studies, etc.)
   - Final diagnoses should remain unchecked

3. **Note pending results**:
   - Check "Still pending results" if additional test results are expected
   - This helps track which diagnoses may be updated once results arrive

**Examples:**
- "Invasive ductal carcinoma, grade 2" (definitive, unchecked)
- "Likely lymphoma, pending flow cytometry results" (not definitive + pending)
- "Potential BRCA-related tumor, pending molecular testing" (not definitive + pending)
"""
