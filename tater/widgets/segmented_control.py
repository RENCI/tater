"""SegmentedControl widget for single-choice annotations."""
from dataclasses import dataclass
import dash_mantine_components as dmc

from .base import ChoiceWidget


@dataclass(eq=False)
class SegmentedControlWidget(ChoiceWidget):
    """Widget for selecting from a list of mutually exclusive options."""

    vertical: bool = False

    def component(self) -> dmc.InputWrapper:
        data = [{"label": opt, "value": opt} for opt in self.options]
        return self._input_wrapper(dmc.SegmentedControl(
            id=self.schema_id,
            data=data,
            value=self.default,
            fullWidth=True,
            orientation="vertical" if self.vertical else "horizontal",
        ))

    def to_python_type(self) -> type:
        return str
