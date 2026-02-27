"""Slider widget for numeric annotations."""
from typing import Optional
import dash_mantine_components as dmc

from .base import TaterWidget


class SliderWidget(TaterWidget):
    """Widget for selecting a numeric value via a slider."""

    def __init__(
        self,
        schema_field: str,
        label: str,
        description: Optional[str] = None,
        required: bool = False,
        default: Optional[float] = None,
        min_value: float = 0,
        max_value: float = 100,
        step: Optional[float] = None,
    ):
        super().__init__(
            schema_field=schema_field,
            label=label,
            description=description,
            required=required,
        )
        self.default = default
        self.min_value = min_value
        self.max_value = max_value
        self.step = step

    def component(self) -> dmc.Slider:
        """Return Dash Mantine Slider component."""
        return dmc.Slider(
            id=self.component_id,
            value=self.default if self.default is not None else self.min_value,
            min=self.min_value,
            max=self.max_value,
            step=self.step,
        )

    def to_python_type(self) -> type:
        return float
