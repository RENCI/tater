"""Switch widget for boolean annotations."""
from dataclasses import dataclass
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from .base import BooleanWidget


@dataclass(eq=False)
class SwitchWidget(BooleanWidget):
    """Widget for boolean yes/no annotations displayed as a toggle switch."""

    default: bool = False

    def component(self) -> dmc.Switch:
        if self.auto_advance:
            label = dmc.Group([
                dmc.Text(self.label, size="sm"),
                dmc.Tooltip(
                    DashIconify(icon="tabler:circle-open-arrow-right", width=13, color="var(--mantine-color-dimmed)"),
                    label="Auto-advances to next document",
                    position="right",
                    withArrow=True,
                ),
            ], gap=4)
        else:
            label = self.label
        return dmc.Switch(id=self.component_id, label=label, checked=self.default)

    @property
    def renders_own_label(self) -> bool:
        return True

    @property
    def value_prop(self) -> str:
        return "checked"

    def to_python_type(self) -> type:
        return bool
