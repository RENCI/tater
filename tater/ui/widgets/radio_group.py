"""RadioGroup widget for single-choice annotations."""
from typing import Optional
import dash_mantine_components as dmc
from dash import html

from ...models.schema import DataField
from ...models.ui_config import WidgetConfig


def create_radio_group(
    field: DataField,
    widget_config: Optional[WidgetConfig] = None,
    value: Optional[str] = None
) -> dmc.Stack:
    """Create a radio group widget for single-choice selection.
    
    Args:
        field: DataField definition from schema
        widget_config: Optional UI configuration
        value: Current selected value
        
    Returns:
        Dash component containing the radio group
    """
    # Use widget config if provided, otherwise use field defaults
    label = widget_config.label if widget_config and widget_config.label else field.id.replace("_", " ").title()
    description = widget_config.description if widget_config and widget_config.description else field.description
    orientation = widget_config.orientation if widget_config and widget_config.orientation else "vertical"
    
    # Build radio group options
    options = field.options or []
    
    # Set default value if not provided
    if value is None and field.default is not None:
        value = field.default
    
    # Add required indicator if field is required
    if field.required:
        label_component = dmc.Group([
            html.Span(label, style={"fontWeight": 500, "fontSize": "14px"}),
            dmc.Badge("Required", color="red", size="xs", variant="dot")
        ], gap="xs", mb="xs")
        
        radio_group = dmc.RadioGroup(
            id=f"annotation-{field.id}",
            description=description,
            value=value,
            children=dmc.Stack(
                [dmc.Radio(label=opt, value=opt) for opt in options],
                gap="xs"
            ) if orientation == "vertical" else dmc.Group(
                [dmc.Radio(label=opt, value=opt) for opt in options],
                gap="md"
            ),
            size="sm",
            mb="md"
        )
        
        return dmc.Stack([label_component, radio_group], gap=0)
    
    # Non-required field - use standard label
    radio_group = dmc.RadioGroup(
        id=f"annotation-{field.id}",
        label=label,
        description=description,
        value=value,
        children=dmc.Stack(
            [dmc.Radio(label=opt, value=opt) for opt in options],
            gap="xs"
        ) if orientation == "vertical" else dmc.Group(
            [dmc.Radio(label=opt, value=opt) for opt in options],
            gap="md"
        ),
        size="sm",
        mb="md"
    )
    
    return radio_group
