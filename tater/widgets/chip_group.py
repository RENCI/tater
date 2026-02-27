"""ChipGroup widget for multi-choice annotations."""
from typing import Optional, List
import dash_mantine_components as dmc

from .base import ControlWidget


class ChipGroupWidget(ControlWidget):
    """Widget for selecting multiple options displayed as inline chip buttons."""

    def __init__(
        self,
        schema_field: str,
        label: str,
        options: list[str],
        description: Optional[str] = None,
        default: Optional[List[str]] = None,
        vertical: bool = False,
        **kwargs,
    ):
        super().__init__(
            schema_field=schema_field,
            label=label,
            description=description,
            **kwargs,
        )
        self.options = options
        self.default = default or []
        self.vertical = vertical

    def component(self) -> dmc.ChipGroup:
        """Return Dash Mantine ChipGroup component."""
        chips = [dmc.Chip(opt, value=opt) for opt in self.options]
        container = dmc.Stack(chips, gap="xs") if self.vertical else dmc.Group(chips, wrap="wrap")
        return dmc.ChipGroup(
            container,
            id=self.component_id,
            value=self.default,
            multiple=True,
        )

    def to_python_type(self) -> type:
        """Return list since this widget produces a list of strings."""
        return list
