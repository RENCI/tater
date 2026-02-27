"""ChipGroup widget for multi-choice annotations."""
from typing import Optional, List
import dash_mantine_components as dmc

from .base import TaterWidget


class ChipGroupWidget(TaterWidget):
    """Widget for selecting multiple options displayed as inline chip buttons."""

    def __init__(
        self,
        schema_field: str,
        label: str,
        options: list[str],
        description: Optional[str] = None,
        required: bool = False,
        default: Optional[List[str]] = None,
    ):
        super().__init__(
            schema_field=schema_field,
            label=label,
            description=description,
            required=required,
        )
        self.options = options
        self.default = default or []

    def component(self) -> dmc.ChipGroup:
        """Return Dash Mantine ChipGroup component."""
        return dmc.ChipGroup(
            dmc.Group(
                [dmc.Chip(opt, value=opt) for opt in self.options],
                wrap="wrap",
            ),
            id=self.component_id,
            value=self.default,
            multiple=True,
        )

    def to_python_type(self) -> type:
        """Return list since this widget produces a list of strings."""
        return list
