"""IHC test results annotation - Tater version.

Translates STAND's ihc_stand.py to Tater format.
Annotates immunohistochemical (IHC) test results including stain,
qualitative result, and optional span highlighting.

Supports three test types with type-specific fields shown via conditional visibility:
- General IHC: basic stain and result
- Breast biomarker IHC: includes intensity and % cell staining
- Ki67 IHC: includes % positive cells
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

from tater import SpanAnnotation
from tater.widgets import (
    TextInputWidget, SelectWidget, CheckboxWidget, SpanAnnotationWidget,
    AccordionWidget, EntityType
)


class IHCTest(BaseModel):
    """Single IHC test result with type-specific fields."""
    test_type: Literal["general", "breast_biomarker", "ki67"] = "general"
    stain: Optional[str] = None
    qualitative_result: Optional[Literal["Negative", "Positive", "Other"]] = None
    # Breast biomarker specific
    stain_intensity: Optional[Literal["Weak", "Moderate", "Strong"]] = None
    percentage_of_cell_staining: Optional[str] = None
    # Ki67 specific
    percentage_of_positive_cells: Optional[str] = None
    # Common metadata
    block_run_on: Optional[str] = None
    test_results_not_reported: bool = False
    results_not_from_this_tissue: bool = False
    relevant_spans: List[SpanAnnotation] = Field(default_factory=list)


class Schema(BaseModel):
    """Top-level schema for IHC test annotation."""
    tests: List[IHCTest] = Field(default_factory=lambda: [IHCTest()])


title = "tater - IHC test results"
description = "Annotate immunohistochemical (IHC) test results with stain, result, block location, and spans."

widgets = [
    AccordionWidget(
        schema_field="tests",
        label="IHC Test Results",
        description="Add and annotate each IHC test mentioned in the report",
        item_label="Test",
        item_widgets=[
            # Test type selector
            SelectWidget(
                schema_field="test_type",
                label="Test Type",
                description="Select the type of IHC test performed",
            ),
            
            # Stain name (required for general and breast biomarker; optional for Ki67)
            TextInputWidget(
                schema_field="stain",
                label="Stain",
                placeholder="e.g. HER2, ER, PR, Ki67, CD20, etc.",
                description="Name of the antibody stain used (optional for Ki67)",
            ),
            
            # Qualitative result (all types)
            SelectWidget(
                schema_field="qualitative_result",
                label="Result",
                description="Qualitative assessment of the stain",
            ),
            
            # Breast biomarker specific fields
            SelectWidget(
                schema_field="stain_intensity",
                label="Stain Intensity",
                description="Only for breast biomarker tests",
            ).conditional_on("test_type", "breast_biomarker"),
            
            TextInputWidget(
                schema_field="percentage_of_cell_staining",
                label="Percentage of cells staining",
                placeholder="e.g. 10%, <5%, >90%, etc.",
                description="Only for breast biomarker tests",
            ).conditional_on("test_type", "breast_biomarker"),
            
            # Ki67 specific field
            TextInputWidget(
                schema_field="percentage_of_positive_cells",
                label="Percentage of positive cells",
                placeholder="e.g. 10%, 15%, 20%, etc.",
                description="Only for Ki67 tests",
            ).conditional_on("test_type", "ki67"),
            
            # Common metadata fields
            TextInputWidget(
                schema_field="block_run_on",
                label="Which block was the test run on",
                placeholder="e.g. B3, C4, D1 or B3.2 for slides",
                description="Naming convention: <PART LETTER><BLOCK NUM> (e.g. B3 = part B, block 3). For slides: B3.2",
            ),
            
            CheckboxWidget(
                schema_field="test_results_not_reported",
                label="The test results are not reported here",
            ),
            
            CheckboxWidget(
                schema_field="results_not_from_this_tissue",
                label="The test results reported here were NOT run on this tissue",
            ),
            
            # Span highlighting
            SpanAnnotationWidget(
                schema_field="relevant_spans",
                label="Highlight relevant text",
                description="Select text sections relevant to this IHC test",
                entity_types=[EntityType("Relevant")],
            ),
        ],
    ),
]

instructions = """
**Annotation Instructions for IHC Test Results**

IHC (Immunohistochemical) testing uses antibodies to detect specific antigens in tissue samples.

**For each IHC test:**

1. **Select test type**:
   - General IHC: Any stain with basic positive/negative/other result
   - Breast biomarker IHC: HER2, ER, PR, etc. with intensity and percentage
   - Ki67 IHC: Proliferation marker with percentage of positive cells

2. **Fill in test details**:
   - Stain name (e.g., HER2, ER, PR, Ki67, etc.)
   - Qualitative result (Negative/Positive/Other)
   - For breast biomarkers: intensity (Weak/Moderate/Strong) and % of cells staining
   - For Ki67: percentage of positive cells

3. **Block identification**:
   - Identify which block/slide the test was run on
   - Use naming convention: <PART LETTER><BLOCK NUM> (e.g., B3 = part B, block 3)
   - For slides, append: B3.2

4. **Highlight relevant text**:
   - Optionally highlight text sections relevant to this test
   - Helps trace annotation back to source material

5. **Handle exceptions**:
   - If results not reported in this document → check "Results not reported"
   - If results from different tissue → check "Results from different tissue"
"""
