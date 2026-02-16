"""Annotation panel component for entering annotations."""
from dash import html, dcc
import dash_bootstrap_components as dbc
from typing import List, Dict, Any, Optional

from data.validator import AnnotationType
from utils.constants import (
    TYPE_SINGLE_CHOICE, TYPE_MULTI_CHOICE,
    TYPE_SPAN_ANNOTATION, TYPE_FREE_TEXT
)


def create_annotation_panel() -> dbc.Card:
    """
    Create the right panel annotation component.
    
    Returns:
        A Dash Bootstrap Card containing annotation controls
    """
    return dbc.Card([
        dbc.CardHeader([
            html.H5("Annotations", className="mb-0")
        ]),
        dbc.CardBody([
            html.Div(id="annotation-controls-container"),
            html.Hr(),
            dbc.Checkbox(
                id="flag-for-review",
                label="Flag for Review",
                value=False,
                className="mb-3"
            ),
            html.Div(id="save-status", className="mb-3 text-muted small"),
            dbc.Button(
                "Save Annotations",
                id="manual-save-button",
                color="primary",
                className="w-100"
            )
        ], style={"padding": "15px"})
    ], className="h-100")


def create_annotation_controls(
    schema: List[AnnotationType],
    current_values: Optional[Dict[str, Any]] = None
) -> List:
    """
    Dynamically generate annotation controls based on schema.
    
    Args:
        schema: List of AnnotationType objects
        current_values: Dictionary of current annotation values
    
    Returns:
        List of Dash components
    """
    if current_values is None:
        current_values = {}
    
    controls = []
    
    for ann_type in schema:
        controls.append(html.Hr())
        controls.append(html.H6(
            ann_type.label,
            className="mb-2"
        ))
        
        if ann_type.description:
            controls.append(html.Small(
                ann_type.description,
                className="text-muted d-block mb-2"
            ))
        
        # Get current value
        current_value = current_values.get(ann_type.id)
        
        # Create appropriate control based on type
        if ann_type.type == TYPE_SINGLE_CHOICE:
            controls.append(
                create_single_choice_control(
                    ann_type.id,
                    ann_type.options,
                    current_value,
                    ann_type.required
                )
            )
        
        elif ann_type.type == TYPE_MULTI_CHOICE:
            controls.append(
                create_multi_choice_control(
                    ann_type.id,
                    ann_type.options,
                    current_value,
                    ann_type.required
                )
            )
        
        elif ann_type.type == TYPE_SPAN_ANNOTATION:
            controls.append(
                create_span_annotation_control(
                    ann_type.id,
                    ann_type.entity_types,
                    ann_type.required
                )
            )
        
        elif ann_type.type == TYPE_FREE_TEXT:
            controls.append(
                create_free_text_control(
                    ann_type.id,
                    current_value,
                    ann_type.required
                )
            )
    
    return controls


def create_single_choice_control(
    control_id: str,
    options: List[str],
    current_value: Optional[str] = None,
    required: bool = False
) -> html.Div:
    """Create a single choice (radio button) control."""
    label = "Required *" if required else ""
    
    return html.Div([
        dbc.RadioItems(
            id={"type": "annotation-input", "id": control_id},
            options=[{"label": opt, "value": opt} for opt in options],
            value=current_value,
            className="mb-2"
        ),
        dbc.Button(
            "Clear",
            id={"type": "clear-single", "id": control_id},
            color="secondary",
            size="sm",
            outline=True
        ) if not required else html.Div(),
        html.Small(label, className="text-danger") if required else html.Div()
    ], className="mb-3")


def create_multi_choice_control(
    control_id: str,
    options: List[str],
    current_value: Optional[List[str]] = None,
    required: bool = False
) -> html.Div:
    """Create a multi choice (checkbox) control."""
    if current_value is None:
        current_value = []
    
    label = "Required *" if required else ""
    
    return html.Div([
        dbc.Checklist(
            id={"type": "annotation-input", "id": control_id},
            options=[{"label": opt, "value": opt} for opt in options],
            value=current_value,
            className="mb-2"
        ),
        html.Small(label, className="text-danger") if required else html.Div()
    ], className="mb-3")


def create_span_annotation_control(
    control_id: str,
    entity_types: List[str],
    required: bool = False
) -> html.Div:
    """Create a span annotation control."""
    label = "Required *" if required else ""
    
    return html.Div([
        html.P("Select text in the document, then choose entity type:", className="small text-muted mb-2"),
        dbc.Select(
            id={"type": "entity-type-selector", "id": control_id},
            options=[{"label": et, "value": et} for et in entity_types],
            placeholder="Select entity type...",
            className="mb-2"
        ),
        dbc.Button(
            "Add Selected Text",
            id={"type": "add-span", "id": control_id},
            color="success",
            size="sm",
            className="w-100"
        ),
        html.Small(label, className="text-danger") if required else html.Div(),
        # Hidden store for span annotations
        dcc.Store(
            id={"type": "annotation-input", "id": control_id},
            data=[]
        )
    ], className="mb-3")


def create_free_text_control(
    control_id: str,
    current_value: Optional[str] = None,
    required: bool = False
) -> html.Div:
    """Create a free text control."""
    label = "Required *" if required else ""
    
    return html.Div([
        dbc.Textarea(
            id={"type": "annotation-input", "id": control_id},
            value=current_value or "",
            placeholder="Enter notes here...",
            rows=4,
            className="mb-2"
        ),
        html.Small(label, className="text-danger") if required else html.Div()
    ], className="mb-3")
