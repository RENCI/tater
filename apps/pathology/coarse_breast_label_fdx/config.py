"""Coarse breast pathology label annotation - Tater version.

Translates coarse_breast_label_fdx.py to Tater format.
Assigns a single high-level diagnosis category to each breast pathology report.
"""
from typing import Optional, Literal
from pydantic import BaseModel

from tater.widgets import SegmentedControlWidget, CheckboxWidget


class Schema(BaseModel):
    label: Optional[Literal[
        "Invasive",
        "In-situ",
        "Atypical",
        "Benign",
        "Ambiguous",
        "Metastasis",
        "Other",
    ]] = None
    not_breast: bool = False


title = "tater - coarse breast pathology label"
description = "Assign a single high-level diagnosis category to each breast pathology report."

widgets = [
    SegmentedControlWidget(
        schema_field="label",
        label="Diagnosis Category",
        required=True,
        auto_advance=True,
    ),
    CheckboxWidget(
        schema_field="not_breast",
        label="Not breast tissue",
        description="Check if the specimen is not breast tissue (e.g. lymph node only, skin, other organ).",
    ),
]

instructions = """## Annotation Instructions

Assign **one** label based on the primary finding in the final diagnosis.

| Label | When to use |
|---|---|
| **Invasive** | Invasive carcinoma of any type (ductal, lobular, NST, etc.) |
| **In-situ** | DCIS or LCIS only, no invasive component |
| **Atypical** | ADH, ALH, flat epithelial atypia — no in-situ or invasive |
| **Benign** | Benign findings only (fibroadenoma, fibrocystic changes, normal) |
| **Ambiguous** | Diagnosis is unclear or indeterminate |
| **Metastasis** | Metastasis to breast from another primary site |
| **Other** | Lymphoma, sarcoma, phyllodes, implant, non-breast tissue, see comment |

Check **Not breast tissue** if the specimen does not contain breast parenchyma at all.

Selecting a label automatically advances to the next document.
"""
