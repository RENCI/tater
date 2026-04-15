"""Accordion → list → span + hierarchy (pet-focused).

Each top-level observation is an accordion section.  Within each observation,
the annotator builds a list of mentions — each mention has:
  - evidence spans highlighted in the document
  - a breed/species category selected from the pet ontology hierarchy

Schema depth: observations (Accordion) → mentions (Listable) → spans (Span) + breed (HL)
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from tater import SpanAnnotation, SpanAnnotationWidget, EntityType
from tater.widgets import (
    AccordionWidget,
    ListableWidget,
    SegmentedControlWidget,
    HierarchicalLabelCompactWidget,
)
from tater.widgets.hierarchical_label import load_hierarchy_from_yaml


ontology = load_hierarchy_from_yaml("apps/examples/data/pet_ontology.yaml")


class Mention(BaseModel):
    breed: Optional[List[str]] = None
    confidence: Optional[Literal["definite", "likely", "uncertain"]] = None
    spans: List[SpanAnnotation] = Field(default_factory=list)


class Observation(BaseModel):
    observation_type: Optional[Literal["breed mention", "behavior", "health condition", "owner note"]] = None
    mentions: List[Mention] = Field(default_factory=list)


class Schema(BaseModel):
    observations: List[Observation] = Field(default_factory=list)
    overall_assessment: Optional[Literal["routine", "follow-up needed", "urgent"]] = None


title = "tater - doubly nested span and hierarchy widgets"
description = "Pet record observations in accordion sections; each observation has a list of breed mentions with span evidence and hierarchical breed labels."

instructions = """## Annotation workflow

1. Click **Add Observation** to create a new accordion section
2. Select the **Observation Type** (breed mention, behavior, health condition, owner note)
3. Inside the observation, click **Add Mention** for each time a breed or animal is referenced
4. For each mention:
   - Highlight the text in the document and click **Span** to tag it
   - Use the **Breed / Species** hierarchy to identify the animal
   - Set your **Confidence** in the identification
5. Collapse completed observations with the accordion controls
6. Set the **Overall Assessment** at the bottom
"""

widgets = [
    AccordionWidget(
        schema_field="observations",
        label="Observations",
        description="Annotate each observation in the pet record.",
        item_label="Observation",
        item_widgets=[
            SegmentedControlWidget(
                schema_field="observation_type",
                label="Observation Type",
            ),
            ListableWidget(
                schema_field="mentions",
                label="Breed Mentions",
                description="Each time a breed or species is referenced in this observation.",
                item_label="Mention",
                item_widgets=[
                    SpanAnnotationWidget(
                        schema_field="spans",
                        label="Span",
                        description="Highlight the text that names or describes the breed.",
                        entity_types=[
                            EntityType("Breed", color="#74c0fc"),
                            EntityType("Species", color="#a9e34b"),
                        ],
                    ),
                    HierarchicalLabelCompactWidget(
                        schema_field="breed",
                        label="Breed / Species",
                        description="Navigate the pet ontology to select the breed or species.",
                        hierarchy=ontology,
                        searchable=True,
                    ),
                    SegmentedControlWidget(
                        schema_field="confidence",
                        label="Confidence",
                    ),
                ],
            ),
        ],
    ),
    SegmentedControlWidget(
        schema_field="overall_assessment",
        label="Overall Assessment",
        required=True,
    ),
]
