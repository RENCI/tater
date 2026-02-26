"""SegmentedControl widget for single-choice annotations."""
from typing import Optional
import dash_mantine_components as dmc

from .base import TaterWidget


class SegmentedControlWidget(TaterWidget):
    """Widget for selecting from a list of mutually exclusive options."""

    def __init__(
        self,
        schema_field: str,
        label: str,
        options: list[str],
        description: Optional[str] = None,
        required: bool = False,
        default: Optional[str] = None,
    ):
        """
        Initialize SegmentedControl widget.

        Args:
            schema_field: Field name in the Pydantic schema
            label: Human-readable label
            options: List of option strings
            description: Optional help text
            required: Whether field is required
            default: Default selected value
        """
        super().__init__(
            schema_field=schema_field,
            label=label,
            description=description,
            required=required,
        )
        self.options = options
        self.default = default

    def component(self) -> dmc.SegmentedControl:
        """Return Dash Mantine SegmentedControl component."""
        data = [{"label": opt, "value": opt} for opt in self.options]

        return dmc.SegmentedControl(
            id=self.component_id,
            data=data,
            value=self.default,
            fullWidth=True,
        )

    def to_python_type(self) -> type:
        """Return str since this widget produces string values."""
        return str
