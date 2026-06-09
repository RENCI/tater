"""GI pathology final diagnosis annotation - Tater version.

Translates gi_fdx/gi_fdx.py to Tater format.
Annotates the primary diagnosis category and any secondary categories
present in a GI pathology final diagnosis.
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

from tater.widgets import ChipRadioWidget, MultiSelectWidget


DiagnosisCategory = Literal[
    "No significant pathologic abnormality",
    "Inflammatory or other non-proliferative changes",
    "Proliferative non-neoplastic changes",
    "Dysplastic changes",
    "Neoplastic malignant changes",
    "Other",
]


class Schema(BaseModel):
    primary_label: Optional[DiagnosisCategory] = None
    other_labels: List[DiagnosisCategory] = Field(default_factory=list)


title = "tater - GI pathology final diagnosis"
description = "Annotate the primary and secondary diagnosis categories for a GI pathology report."

widgets = [
    ChipRadioWidget(
        schema_field="primary_label",
        label="Primary Diagnosis Category",
        description="Select the single best category for the overall diagnosis.",
        required=True,
    ),
    MultiSelectWidget(
        schema_field="other_labels",
        label="Secondary Diagnosis Categories",
        description="Select any additional categories also present in this diagnosis.",
    ),
]

instructions = """## Annotation Instructions for GI Pathology Final Diagnosis

Assign diagnosis categories based on the **final diagnosis** section of the report only.

### Categories

| Category | Examples |
|---|---|
| **No significant pathologic abnormality** | Normal mucosa, no histologic abnormality |
| **Inflammatory or other non-proliferative changes** | H. pylori gastritis, colitis, eosinophilic esophagitis, celiac disease |
| **Proliferative non-neoplastic changes** | Hyperplastic polyp, metaplasia, regenerative changes |
| **Dysplastic changes** | Low-grade dysplasia, high-grade dysplasia, adenoma |
| **Neoplastic malignant changes** | Adenocarcinoma, lymphoma, carcinoid/NET, GIST |
| **Other** | Diagnoses that do not fit the above categories |

### Rules

1. Select **one primary label** — the single most important finding.
2. Use **secondary labels** for additional distinct categories also present.
3. Base annotation on the **final diagnosis section only** — ignore clinical history and microscopic description.
4. If the specimen is entirely normal, select only "No significant pathologic abnormality".
"""
