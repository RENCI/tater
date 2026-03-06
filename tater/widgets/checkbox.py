"""Checkbox widget for boolean annotations."""
from dataclasses import dataclass
import dash_mantine_components as dmc

from .base import BooleanWidget


@dataclass(eq=False)
class CheckboxWidget(BooleanWidget):
    """Widget for boolean yes/no annotations."""

    default: bool = False

    def component(self) -> dmc.Checkbox:
        return dmc.Checkbox(id=self.component_id, label=self.label, checked=self.default)

    @property
    def renders_own_label(self) -> bool:
        return True

    @property
    def value_prop(self) -> str:
        return "checked"

    def to_python_type(self) -> type:
        return bool
