"""Text input widget for free-form string annotations."""
from dataclasses import dataclass
from typing import Optional
import dash_mantine_components as dmc

from .base import TextWidget


@dataclass(eq=False)
class TextInputWidget(TextWidget):
    """Widget for entering a single line of text."""

    default: Optional[str] = None
    placeholder: Optional[str] = None

    @property
    def empty_value(self) -> str:
        return ""

    def component(self) -> dmc.TextInput:
        return dmc.TextInput(
            id=self.schema_id,
            value=self.default if self.default is not None else self.empty_value,
            placeholder=self.placeholder,
        )

    def to_python_type(self) -> type:
        return str
