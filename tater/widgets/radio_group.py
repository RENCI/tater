"""Radio group widget for single-choice annotations."""
from typing import Optional
import dash_mantine_components as dmc

from .base import ControlWidget


class RadioGroupWidget(ControlWidget):
    """Widget for selecting from a list of mutually exclusive options."""

    def __init__(
        self,
        schema_field: str,
        label: str,
        options: list[str],
        description: Optional[str] = None,
        default: Optional[str] = None,
        vertical: bool = False,
    ):
        super().__init__(
            schema_field=schema_field,
            label=label,
            description=description,
        )
        self.options = options
        self.default = default
        self.vertical = vertical

    def component(self) -> dmc.RadioGroup:
        """Return Dash Mantine RadioGroup component."""
        radio_items = [dmc.Radio(label=opt, value=opt) for opt in self.options]
        container = dmc.Stack(radio_items, gap="xs") if self.vertical else dmc.Group(radio_items, wrap="wrap")
        return dmc.RadioGroup(
            id=self.component_id,
            children=container,
            value=self.default,
        )

    def to_python_type(self) -> type:
        """Return str since this widget produces string values."""
        return str
