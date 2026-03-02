"""Select widget for single-choice annotations."""
from dataclasses import dataclass
import dash_mantine_components as dmc

from .base import ChoiceWidget


@dataclass(eq=False)
class SelectWidget(ChoiceWidget):
    """Widget for selecting a single option from a dropdown."""

    def component(self) -> dmc.Select:
        return dmc.Select(
            id=self.component_id,
            data=[{"label": opt, "value": opt} for opt in self.options],
            value=self.default,
            clearable=True,
            searchable=True,
        )

    def to_python_type(self) -> type:
        return str
