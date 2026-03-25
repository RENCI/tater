"""Radio group widget for single-choice annotations."""
from dataclasses import dataclass
import dash_mantine_components as dmc

from .base import ChoiceWidget


@dataclass(eq=False)
class RadioGroupWidget(ChoiceWidget):
    """Widget for selecting from a list of mutually exclusive options."""

    vertical: bool = False

    def component(self) -> dmc.RadioGroup:
        radio_items = [dmc.Radio(label=opt, value=opt) for opt in self.options]
        mt = 4 if self.description else None
        container = dmc.Stack(radio_items, gap="xs", mt=mt) if self.vertical else dmc.Group(radio_items, wrap="wrap", mt=mt)
        return dmc.RadioGroup(
            id=self.schema_id,
            children=container,
            value=self.default,
            deselectable=True,
            label=self._label_with_tooltip(),
            description=self.description,
            withAsterisk=self.required,
        )

    def to_python_type(self) -> type:
        return str
