"""Switch widget for boolean annotations."""
from dataclasses import dataclass
import dash_mantine_components as dmc

from .base import BooleanWidget


@dataclass(eq=False)
class SwitchWidget(BooleanWidget):
    """Widget for boolean yes/no annotations displayed as a toggle switch."""

    default: bool = False

    def component(self) -> dmc.Stack:
        parts = [dmc.Switch(id=self.component_id, label=self.label, checked=self.default)]
        if self.description:
            parts.append(dmc.Text(self.description, size="xs", c="dimmed"))
        return dmc.Stack(parts, gap="xs", mt="md")

    @property
    def renders_own_label(self) -> bool:
        return True

    @property
    def value_prop(self) -> str:
        return "checked"

    def to_python_type(self) -> type:
        return bool
