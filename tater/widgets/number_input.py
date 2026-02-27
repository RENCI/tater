"""NumberInput widget for numeric annotations."""
from typing import Optional
import dash_mantine_components as dmc

from .base import ControlWidget

class NumberInputWidget(ControlWidget):
    """Widget for entering a numeric value."""

    def __init__(
        self,
        schema_field: str,
        label: str,
        description: Optional[str] = None,
        default: Optional[float] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        step: Optional[float] = None,
        **kwargs,
    ):
        """
        Initialize NumberInput widget.

        Args:
            schema_field: Field name in the Pydantic schema
            label: Human-readable label
            description: Optional help text
            default: Default value
            min_: Minimum value
            max_: Maximum value
            step: Step size
        """
        super().__init__(
            schema_field=schema_field,
            label=label,
            description=description,
            **kwargs,
        )
        self.default = default
        self.min_value = min_value
        self.max_value = max_value
        self.step = step

    def component(self) -> dmc.NumberInput:
        """Return Dash Mantine NumberInput component."""
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
        """Return float since this widget produces numeric values."""
        return float
