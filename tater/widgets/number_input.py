"""NumberInput widget for numeric annotations."""
from typing import Optional
import dash_mantine_components as dmc

from .base import NumericWidget


class NumberInputWidget(NumericWidget):
    """Widget for entering a numeric value."""

    def __init__(
        self,
        schema_field: str,
        label: str = "",
        description: Optional[str] = None,
        required: bool = False,
        default: Optional[float] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        step: Optional[float] = None,
    ):
        super().__init__(schema_field=schema_field, label=label, description=description, required=required)
        self.default = default
        self.min_value = min_value
        self.max_value = max_value
        self.step = step

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
