"""Slider widget for numeric annotations."""
from dataclasses import dataclass
from typing import Optional
import dash_mantine_components as dmc

from .base import NumericWidget


@dataclass(eq=False)
class SliderWidget(NumericWidget):
    """Widget for selecting a numeric value via a slider."""

    default: Optional[float] = None
    min_value: float = 0
    max_value: float = 100
    step: Optional[float] = None

    @property
    def empty_value(self):
        return self.default if self.default is not None else self.min_value

    def component(self) -> dmc.Slider:
        return dmc.Slider(
            id=self.schema_id,
            value=self.default if self.default is not None else self.min_value,
            min=self.min_value,
            max=self.max_value,
            step=self.step,
        )

    def to_python_type(self) -> type:
        return float
