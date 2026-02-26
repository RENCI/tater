"""SegmentedControl widget for single-choice annotations."""
from typing import Optional
import dash_mantine_components as dmc

from .base import TaterWidget


class SegmentedControlWidget(TaterWidget):
    """Widget for selecting from a list of mutually exclusive options."""

    def __init__(
        self,
        label: str,
        options: list[str],
        field_path: Optional[str] = None,
        description: Optional[str] = None,
        required: bool = False,
        default: Optional[str] = None,
        schema_id: Optional[str] = None,
    ):
        """
        Initialize SegmentedControl widget.

        Args:
            label: Human-readable label
            options: List of option strings
            field_path: Dotted path to field (e.g., "sentiment")
            description: Optional help text
            required: Whether field is required
            default: Default selected value
            schema_id: Alias for field_path (for backwards compatibility)
        """
        super().__init__(
            field_path=field_path,
            label=label,
            description=description,
            required=required,
            schema_id=schema_id,
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
