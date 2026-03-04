"""NumberInput widget for numeric annotations."""
from dataclasses import dataclass
from typing import Optional
import dash_mantine_components as dmc

from .base import NumericWidget


@dataclass(eq=False)
class NumberInputWidget(NumericWidget):
    """Widget for entering a numeric value."""

    default: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None

    def component(self) -> dmc.NumberInput:
        return dmc.NumberInput(
            id=self.component_id,
            value=self.default,
            min=self.min_value,
            max=self.max_value,
            step=self.step,
            hideControls=False,
            style={"maxWidth": 200},
        )

    def to_python_type(self) -> type:
        return float
