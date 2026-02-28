"""Switch widget for boolean annotations."""
from typing import Optional
import dash_mantine_components as dmc

from .base import BooleanWidget


class SwitchWidget(BooleanWidget):
    """Widget for boolean yes/no annotations displayed as a toggle switch."""

    def __init__(
        self,
        schema_field: str,
        label: str = "",
        description: Optional[str] = None,
        default: bool = False,
    ):
        super().__init__(schema_field=schema_field, label=label, description=description)
        self.default = default

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
