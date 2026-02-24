"""UI configuration models."""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class WidgetConfig(BaseModel):
    """Configuration for a single UI widget."""
    
    schema_id: str = Field(..., description="ID of the schema field this widget represents")
    widget: Literal["radio_group", "segmented_control", "checkbox_group", "select", "textarea", "checkbox"] = Field(
        ..., description="Type of widget to render"
    )
    label: Optional[str] = Field(None, description="Display label for the widget")
    description: Optional[str] = Field(None, description="Help text or description")
    orientation: Optional[Literal["horizontal", "vertical"]] = Field(
        None, description="Layout orientation for choice widgets"
    )


class UIConfig(BaseModel):
    """Complete UI configuration."""
    
    ui: list[WidgetConfig] = Field(default_factory=list, description="List of widget configurations")
    
    def get_widget_config(self, field_id: str) -> Optional[WidgetConfig]:
        """Get widget configuration for a specific field."""
        for widget in self.ui:
            if widget.schema_id == field_id:
                return widget
        return None
