"""Radio group widget for single-choice annotations."""
from typing import Optional
import dash_mantine_components as dmc

from .base import TaterWidget


class RadioGroupWidget(TaterWidget):
    """Widget for selecting from a list of mutually exclusive options (vertical layout)."""

    def __init__(
        self,
        schema_field: str,
        label: str,
        options: list[str],
        description: Optional[str] = None,
        required: bool = False,
        default: Optional[str] = None,
        orientation: str = "vertical",
    ):
        """
        Initialize RadioGroup widget.

        Args:
            schema_field: Field name in the Pydantic schema
            label: Human-readable label
            options: List of option strings
            description: Optional help text
            required: Whether field is required
            default: Default selected value
            orientation: Layout orientation ("vertical" or "horizontal")
        """
        super().__init__(
            schema_field=schema_field,
            label=label,
            description=description,
            required=required,
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
            children=dmc.Stack(radio_items, gap="xs"),
            value=self.default,
        )

    def to_python_type(self) -> type:
        """Return str since this widget produces string values."""
        return str
