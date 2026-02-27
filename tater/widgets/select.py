"""Select widget for single-choice annotations."""
from typing import Optional
import dash_mantine_components as dmc

from .base import ControlWidget


class SelectWidget(ControlWidget):
    """Widget for selecting a single option from a dropdown."""

    def __init__(
        self,
        schema_field: str,
        label: str,
        options: list[str],
        description: Optional[str] = None,
        default: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            schema_field=schema_field,
            label=label,
            description=description,
            **kwargs,
        )
        self.options = options
        self.default = default

    def component(self) -> dmc.Select:
        """Return Dash Mantine Select component."""
        return dmc.Select(
            id=self.component_id,
            data=[{"label": opt, "value": opt} for opt in self.options],
            value=self.default,
            clearable=True,
            searchable=True,
        )

    def to_python_type(self) -> type:
        return str
