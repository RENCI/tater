"""NumberInput widget for numeric annotations."""
from typing import Optional
import dash_mantine_components as dmc

from .base import TaterWidget

class NumberInputWidget(TaterWidget):
    """Widget for entering a numeric value."""

    def __init__(
        self,
        schema_field: str,
        label: str,
        description: Optional[str] = None,
        required: bool = False,
        default: Optional[float] = None,
        min_: Optional[float] = None,
        max_: Optional[float] = None,
        step: Optional[float] = None,
    ):
        """
        Initialize NumberInput widget.

        Args:
            schema_field: Field name in the Pydantic schema
            label: Human-readable label
            description: Optional help text
            required: Whether field is required
            default: Default value
            min_: Minimum value
            max_: Maximum value
            step: Step size
        """
        super().__init__(
            schema_field=schema_field,
            label=label,
            description=description,
            required=required,
        )
        self.default = default
        self.min_ = min_
        self.max_ = max_
        self.step = step

    def component(self) -> dmc.NumberInput:
        """Return Dash Mantine NumberInput component."""
        return dmc.NumberInput(
            id=self.component_id,
            value=self.default,
            min=self.min_,
            max=self.max_,
            step=self.step,
            hideControls=False,
            style={"maxWidth": 200},
        )

    def to_python_type(self) -> type:
        """Return float since this widget produces numeric values."""
        return float
