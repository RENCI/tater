"""Checkbox widget for boolean annotations."""
from dataclasses import dataclass
import dash_mantine_components as dmc

from .base import BooleanWidget


@dataclass(eq=False)
class CheckboxWidget(BooleanWidget):
    """Widget for boolean yes/no annotations."""

    default: bool = False

    def component(self) -> dmc.InputWrapper:
        return self._input_wrapper(dmc.Checkbox(id=self.schema_id, checked=self.default))

    @property
    def value_prop(self) -> str:
        return "checked"

    def to_python_type(self) -> type:
        return bool
