"""MultiSelect widget for multi-choice annotations."""
from dataclasses import dataclass
import dash_mantine_components as dmc

from .base import MultiChoiceWidget


@dataclass(eq=False)
class MultiSelectWidget(MultiChoiceWidget):
    """Widget for selecting multiple options from a list."""

    def component(self) -> dmc.MultiSelect:
        data = [{"label": opt, "value": opt} for opt in self.options]
        return dmc.MultiSelect(
            id=self.schema_id,
            data=data,
            value=self.default,
            clearable=True,
            searchable=True,
        )

    def to_python_type(self) -> type:
        return list
