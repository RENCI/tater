"""De-identification verification - Tater version.

Translates verify_deid.py to Tater format.
Annotators confirm each document is fully de-identified and note any remaining PHI.
"""
from typing import Optional
from pydantic import BaseModel

from tater.widgets import CheckboxWidget, TextAreaWidget


class Schema(BaseModel):
    verified_deidentified: bool = False
    remaining_phi: Optional[str] = None


title = "tater - verify de-identification"
description = "Confirm each document is fully de-identified and flag any remaining PHI."

widgets = [
    CheckboxWidget(
        schema_field="verified_deidentified",
        label="This document contains no PHI",
        description="Check only if you have read the entire document and found no identifying information.",
        required=True,
        auto_advance=True,
    ),
    TextAreaWidget(
        schema_field="remaining_phi",
        label="Remaining PHI",
        description="If PHI was found, describe what was found and where (e.g. 'Patient name in header line 1').",
        placeholder="Describe any PHI found...",
    ),
]

instructions = """## De-identification Verification Instructions

Read the **entire document** and confirm it contains no Protected Health Information (PHI).

### PHI categories to check

- **Names**: patient, physician, family member
- **Dates**: birthdate, admission/discharge dates, any date that could identify a patient
- **Geographic identifiers**: street address, city/zip smaller than state level
- **Phone / fax numbers**
- **Email addresses**
- **Medical record numbers, account numbers, device IDs**
- **URLs or IP addresses**
- **Ages over 89**

### Workflow

1. Read the full document carefully.
2. If **no PHI found**: check the box — this advances to the next document automatically.
3. If **PHI found**: leave the box unchecked, describe what you found in the text field, then use Next to proceed.
"""
