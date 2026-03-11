"""CheckboxGroup widget for multi-choice annotations."""
from dataclasses import dataclass
import dash_mantine_components as dmc

from .base import MultiChoiceWidget


@dataclass(eq=False)
class CheckboxGroupWidget(MultiChoiceWidget):
    """Widget for selecting multiple options displayed as a group of checkboxes."""

    vertical: bool = False

    def component(self) -> dmc.CheckboxGroup:
        checkbox_items = [dmc.Checkbox(label=opt, value=opt) for opt in self.options]
        container = dmc.Stack(checkbox_items, gap="xs") if self.vertical else dmc.Group(checkbox_items, wrap="wrap")
        return dmc.CheckboxGroup(
            id=self.schema_id,
            children=container,
            value=self.default,
        )

    def to_python_type(self) -> type:
        return list
