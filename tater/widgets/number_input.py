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

    @property
    def empty_value(self):
        return ""

    def component(self) -> dmc.NumberInput:
        return dmc.NumberInput(
            id=self.schema_id,
            value=self.default if self.default is not None else "",
            min=self.min_value,
            max=self.max_value,
            step=self.step,
            hideControls=False,
            style={"maxWidth": 200},
            label=self._label_with_tooltip(),
            description=self.description,
            withAsterisk=self.required,
        )

    def to_python_type(self) -> type:
        return float
