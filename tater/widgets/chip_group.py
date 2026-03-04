"""ChipGroup widget for multi-choice annotations."""
from dataclasses import dataclass
import dash_mantine_components as dmc

from .base import MultiChoiceWidget


@dataclass(eq=False)
class ChipGroupWidget(MultiChoiceWidget):
    """Widget for selecting multiple options displayed as inline chip buttons."""

    vertical: bool = False

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
