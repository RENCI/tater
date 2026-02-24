"""SegmentedControl widget for single-choice annotations."""
from typing import Optional
import dash_mantine_components as dmc

from ...models.schema import DataField
from ...models.ui_config import WidgetConfig


def create_segmented_control(
    field: DataField,
    widget_config: Optional[WidgetConfig] = None,
    value: Optional[str] = None
) -> dmc.Stack:
    """Create a segmented control widget for single-choice selection.
    
    Args:
        field: DataField definition from schema
        widget_config: Optional UI configuration
        value: Current selected value
        
    Returns:
        Dash component containing the segmented control
    """
    label = widget_config.label if widget_config and widget_config.label else field.id.replace("_", " ").title()
    description = widget_config.description if widget_config and widget_config.description else field.description
    
    # Set default value if not provided
    if value is None and field.default is not None:
        value = field.default
    
    data = [{"label": opt, "value": opt} for opt in (field.options or [])]
    
    return dmc.Stack([
        dmc.Title(label, order=6),
        dmc.SegmentedControl(
            id=f"annotation-{field.id}",
            data=data,
            value=value,
            fullWidth=True
        ),
        dmc.Text(description, size="sm", c="dimmed") if description else None
    ], gap="xs")
