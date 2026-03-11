"""Textarea widget for multi-line text annotations."""
from dataclasses import dataclass
from typing import Optional
import dash_mantine_components as dmc

from .base import TextWidget


@dataclass(eq=False)
class TextAreaWidget(TextWidget):
    """Widget for entering multi-line text."""

    default: Optional[str] = None
    placeholder: Optional[str] = None

    @property
    def empty_value(self) -> str:
        return ""

    def component(self) -> dmc.Textarea:
        return dmc.Textarea(
            id=self.schema_id,
            value=self.default if self.default is not None else self.empty_value,
            placeholder=self.placeholder,
        )

    def to_python_type(self) -> type:
        return str
