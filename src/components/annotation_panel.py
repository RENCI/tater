"""Annotation panel component for entering annotations."""
from dash import html, dcc
import dash_mantine_components as dmc
from typing import List, Dict, Any, Optional

from data.validator import AnnotationType
from utils.constants import (
    TYPE_SINGLE_CHOICE, TYPE_MULTI_CHOICE,
    TYPE_SPAN_ANNOTATION, TYPE_FREE_TEXT,
    ENTITY_COLORS
)


def create_annotation_panel() -> dmc.Paper:
    """
    Create the right panel annotation component.
    
    Returns:
        A Dash Mantine Paper containing annotation controls
    """
    return dmc.Paper([
        dmc.Stack([
            dmc.Title("Annotations", order=5),
            html.Div(id="annotation-controls-container"),
            dmc.Divider(),
            dmc.Checkbox(
                id="flag-for-review",
                label="Flag for Review",
                checked=False
            ),
            html.Div(id="save-status", style={"color": "#868e96", "fontSize": "0.875rem"}),
            dmc.Button(
                "Save Annotations",
                id="manual-save-button",
                fullWidth=True
            )
        ], gap="md")
    ], p="md", shadow="sm", radius="md", style={"height": "100%"})


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
        controls.append(dmc.Divider())
        controls.append(dmc.Title(
            ann_type.label,
            order=6
        ))
        
        if ann_type.description:
            controls.append(dmc.Text(
                ann_type.description,
                size="sm",
                c="dimmed"
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
        dmc.RadioGroup(
            id={"type": "annotation-input", "id": control_id},
            children=dmc.Stack([dmc.Radio(opt, value=opt) for opt in options], gap="xs"),
            value=current_value
        ),
        dmc.Button(
            "Clear",
            id={"type": "clear-single", "id": control_id},
            variant="subtle",
            size="xs"
        ) if not required else html.Div(),
        dmc.Text(label, size="sm", c="red") if required else html.Div()
    ], style={"marginBottom": "1rem"})


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
        dmc.CheckboxGroup(
            id={"type": "annotation-input", "id": control_id},
            children=dmc.Stack([dmc.Checkbox(opt, value=opt) for opt in options], gap="xs"),
            value=current_value
        ),
        dmc.Text(label, size="sm", c="red") if required else html.Div()
    ], style={"marginBottom": "1rem"})


def create_span_annotation_control(
    control_id: str,
    entity_types: List[str],
    required: bool = False
) -> html.Div:
    """Create a span annotation control."""
    label = "Required *" if required else ""
    
    # Create individual buttons for each entity type with color indicators
    entity_buttons = []
    for et in entity_types:
        color = ENTITY_COLORS.get(et, "#E0E0E0")
        entity_buttons.append(
            dmc.Button(
                [
                    html.Span(
                        "",
                        style={
                            "display": "inline-block",
                            "width": "12px",
                            "height": "12px",
                            "backgroundColor": color,
                            "borderRadius": "2px",
                            "marginRight": "6px",
                            "border": "1px solid rgba(0,0,0,0.2)"
                        }
                    ),
                    et
                ],
                id={"type": "add-span", "id": control_id, "entity": et},
                variant="light",
                size="xs",
                fullWidth=True,
                style={"border": f"2px solid {color}", "justifyContent": "flex-start", "marginBottom": "4px"}
            )
        )
    
    return html.Div([
        dmc.Text(
            "Highlight text in the document, then select entity type:",
            size="sm",
            c="dimmed"
        ),
        dmc.Text("Select entity type:", size="sm", c="dimmed", mt="sm"),
        dmc.Stack(entity_buttons, gap="xs"),
        html.Div(
            id={"type": "span-status", "id": control_id},
            style={"fontSize": "0.875rem"}
        ),
        dmc.Text(label, size="sm", c="red") if required else html.Div(),
        # Hidden store for span annotations
        dcc.Store(
            id={"type": "annotation-input", "id": control_id},
            data=[]
        )
    ], style={"marginBottom": "1rem"})


def create_free_text_control(
    control_id: str,
    current_value: Optional[str] = None,
    required: bool = False
) -> html.Div:
    """Create a free text control."""
    label = "Required *" if required else ""
    
    return html.Div([
        dmc.Textarea(
            id={"type": "annotation-input", "id": control_id},
            value=current_value or "",
            placeholder="Enter notes here...",
            minRows=4
        ),
        dmc.Text(label, size="sm", c="red") if required else html.Div()
    ], style={"marginBottom": "1rem"})
