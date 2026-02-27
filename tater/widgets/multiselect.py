"""MultiSelect widget for multi-choice annotations."""
from typing import Optional, List
import dash_mantine_components as dmc

from .base import ControlWidget

class MultiSelectWidget(ControlWidget):
    """Widget for selecting multiple options from a list."""

    def __init__(
        self,
        schema_field: str,
        label: str,
        options: list[str],
        description: Optional[str] = None,
        default: Optional[List[str]] = None,
        **kwargs,
    ):
        """
        Initialize MultiSelect widget.

        Args:
            schema_field: Field name in the Pydantic schema
            label: Human-readable label
            options: List of option strings
            description: Optional help text
            default: Default selected values (list)
        """
        super().__init__(
            schema_field=schema_field,
            label=label,
            description=description,
            **kwargs,
        )
        self.options = options
        self.default = default or []

    def component(self) -> dmc.MultiSelect:
        """Return Dash Mantine MultiSelect component."""
        data = [{"label": opt, "value": opt} for opt in self.options]
        return dmc.MultiSelect(
            id=self.component_id,
            data=data,
            value=self.default,
            clearable=True,
            searchable=True,
        )

    def to_python_type(self) -> type:
        """Return list since this widget produces a list of strings."""
        return list
