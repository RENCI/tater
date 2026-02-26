"""Radio group widget for single-choice annotations."""
from typing import Optional
import dash_mantine_components as dmc

from .base import TaterWidget


class RadioGroupWidget(TaterWidget):
    """Widget for selecting from a list of mutually exclusive options (vertical layout)."""

    def __init__(
        self,
        label: str,
        options: list[str],
        field_path: Optional[str] = None,
        description: Optional[str] = None,
        required: bool = False,
        default: Optional[str] = None,
        orientation: str = "vertical",
        schema_id: Optional[str] = None,
    ):
        """
        Initialize RadioGroup widget.

        Args:
            label: Human-readable label
            options: List of option strings
            field_path: Dotted path to field (e.g., "category")
            description: Optional help text
            required: Whether field is required
            default: Default selected value
            orientation: Layout orientation ("vertical" or "horizontal")
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
        self.orientation = orientation

    def component(self) -> dmc.RadioGroup:
        """Return Dash Mantine RadioGroup component."""
        radio_items = [
            dmc.Radio(label=opt, value=opt)
            for opt in self.options
        ]

        return dmc.RadioGroup(
            id=self.component_id,
            children=radio_items,
            value=self.default,
        )

    def to_python_type(self) -> type:
        """Return str since this widget produces string values."""
        return str
