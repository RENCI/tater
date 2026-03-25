"""ChipRadio widget for single-choice annotations displayed as chip buttons."""
from dataclasses import dataclass
import dash_mantine_components as dmc

from .base import ChoiceWidget


@dataclass(eq=False)
class ChipRadioWidget(ChoiceWidget):
    """Widget for selecting one option from a set displayed as inline chip buttons."""

    vertical: bool = False

    def component(self) -> dmc.InputWrapper:
        chips = [dmc.Chip(opt, value=opt) for opt in self.options]
        container = dmc.Stack(chips, gap="xs") if self.vertical else dmc.Group(chips, wrap="wrap")
        return self._input_wrapper(dmc.ChipGroup(
            container,
            id=self.schema_id,
            value=self.default,
            deselectable=True,
        ))

    def to_python_type(self) -> type:
        return str
