"""Auto-generation with dot-path overrides, positioned dividers, and cross-group conditionals.

Exercises three recent widgets_from_model improvements:

  Fix 3 — dot-path overrides: replace specific nested child widgets without
           spelling out the entire group.  RadioGroupWidget and TextAreaWidget
           below are specified with dot-paths ("findings.status.severity") so
           they slot into the auto-generated ListableWidget's item widgets.

  Fix 2 — DividerWidget with before=: inject section breaks inside the
           auto-generated item layout by providing DividerWidgets in the
           overrides list with a 'before' dot-path target field.

  Fix 1 — cross-group conditionals: 'cross_group_note' at the Finding item
           level is conditional on 'status.is_confirmed', a field that lives
           inside the 'status' GroupWidget.  This cross-group reference is
           resolved correctly by the pre-built tf_defaults map.
"""
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

from tater.loaders.model_loader import widgets_from_model
from tater.widgets import RadioGroupWidget, TextAreaWidget, SelectWidget, DividerWidget


# --- Schema ------------------------------------------------------------------

class Status(BaseModel):
    severity: Optional[Literal["mild", "moderate", "severe"]] = None
    is_confirmed: bool = False
    confirmation_note: Optional[str] = None


class Details(BaseModel):
    location: Optional[Literal["central", "peripheral", "diffuse"]] = None
    size_cm: Optional[float] = None
    notes: Optional[str] = None


class Finding(BaseModel):
    status: Status = Field(default_factory=Status)
    details: Details = Field(default_factory=Details)
    # This widget is conditional on status.is_confirmed — a field in a sibling
    # GroupWidget.  Requires Fix 1 (cross-group tf_defaults lookup).
    cross_group_note: Optional[str] = None
    reviewer: Optional[str] = None


class Schema(BaseModel):
    report_type: Optional[Literal["preliminary", "final", "addendum"]] = None
    findings: List[Finding] = Field(default_factory=list)


# --- App metadata ------------------------------------------------------------

title = "tater - autogen"
description = "Auto-generated widgets with dot-path overrides, dividers, and cross-group conditionals."

instructions = """This example is built entirely with ``widgets_from_model`` — no manual widget list.

**Fix 3 — dot-path overrides**
- *Severity* uses a ``RadioGroupWidget`` (default would be ``SegmentedControlWidget``)
- *Notes* inside Details uses a ``TextAreaWidget`` (default would be ``TextInputWidget``)
- *Confirmation Note* inside Status uses a ``TextAreaWidget`` and is conditional on *Confirmed?*

**Fix 2 — dividers via** ``before=``
- "Status" and "Details" section headings appear inside each finding item without a manual widget list.

**Fix 1 — cross-group conditional**
- **Cross-group Note** appears at the finding item level but is conditional on *Confirmed?* which lives inside the *Status* group.  Toggle *Confirmed?* on/off to verify it shows and hides correctly.
"""

# --- Widgets (auto-generated with targeted overrides) ------------------------

widgets = widgets_from_model(Schema, overrides=[
    # Fix 3: top-level override — use Select instead of SegmentedControl for report_type
    SelectWidget("report_type", label="Report Type"),

    # Fix 3: dot-path overrides for nested children
    RadioGroupWidget("findings.status.severity", label="Severity", vertical=False),
    TextAreaWidget(
        "findings.status.confirmation_note",
        label="Confirmation Note",
        placeholder="Describe what confirmed this finding...",
    ).conditional_on("is_confirmed", True),
    TextAreaWidget(
        "findings.details.notes",
        label="Notes",
        placeholder="Free-text detail notes...",
    ),

    # Fix 1: cross-group conditional — conditional on status.is_confirmed
    # (status lives in a sibling GroupWidget; the cross-group reference requires
    # the pre-built tf_defaults map introduced in Fix 1)
    TextAreaWidget(
        "findings.cross_group_note",
        label="Cross-group Note",
        description="Only shown when 'Confirmed?' is checked (cross-group condition).",
        placeholder="Notes triggered by confirmation in a sibling group...",
    ).conditional_on("status.is_confirmed", True),

    # Fix 2: dividers injected before specific fields via dot-path before=
    DividerWidget(label="Status", before="findings.status"),
    DividerWidget(label="Details", before="findings.details"),
    DividerWidget(label="Review", before="findings.cross_group_note"),
])
