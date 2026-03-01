"""ChipGroup widget for multi-choice annotations."""
from typing import Optional
import dash_mantine_components as dmc

from .base import MultiChoiceWidget


class ChipGroupWidget(MultiChoiceWidget):
    """Widget for selecting multiple options displayed as inline chip buttons."""

    def __init__(
        self,
        schema_field: str,
        label: str = "",
        description: Optional[str] = None,
        required: bool = False,
        default: Optional[list[str]] = None,
        vertical: bool = False,
    ):
        super().__init__(
            schema_field=schema_field,
            label=label,
            description=description,
            required=required,
            default=default,
        )
        self.vertical = vertical

    def component(self) -> dmc.ChipGroup:
        chips = [dmc.Chip(opt, value=opt) for opt in self.options]
        container = dmc.Stack(chips, gap="xs") if self.vertical else dmc.Group(chips, wrap="wrap")
        return dmc.ChipGroup(
            container,
            id=self.component_id,
            value=self.default,
            multiple=True,
        )

    def to_python_type(self) -> type:
        return list
