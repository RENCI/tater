"""Checkbox widget for boolean annotations."""
from typing import Optional

import dash_mantine_components as dmc

from .base import ControlWidget


class CheckboxWidget(ControlWidget):
    """Widget for boolean yes/no annotations."""

    def __init__(
        self,
        schema_field: str,
        label: str,
        description: Optional[str] = None,
        default: bool = False,
        **kwargs,
    ):
        """
        Initialize Checkbox widget.

        Args:
            schema_field: Field name in the Pydantic schema
            label: Human-readable label
            description: Optional help text
            default: Default checked state
        """
        super().__init__(
            schema_field=schema_field,
            label=label,
            description=description,
            **kwargs,
        )
        self.default = default

    def component(self) -> dmc.Stack:
        """Return Dash Mantine Checkbox component."""
        parts = [
            dmc.Checkbox(
                id=self.component_id,
                label=self.label,
                checked=self.default,
            )
        ]

        if self.description:
            parts.append(dmc.Text(self.description, size="xs", c="dimmed"))

        return dmc.Stack(parts, gap="xs", mt="md")

    @property
    def renders_own_label(self) -> bool:
        """Checkbox renders its own label in component()."""
        return True

    @property
    def value_prop(self) -> str:
        """Checkbox values are read/written via `checked`."""
        return "checked"

    def to_python_type(self) -> type:
        """Return bool since this widget produces boolean values."""
        return bool
