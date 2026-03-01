"""Text input widget for free-form string annotations."""
from typing import Optional
import dash_mantine_components as dmc

from .base import TextWidget


class TextInputWidget(TextWidget):
    """Widget for entering a single line of text."""

    def __init__(
        self,
        schema_field: str,
        label: str = "",
        description: Optional[str] = None,
        required: bool = False,
        default: Optional[str] = None,
        placeholder: Optional[str] = None,
    ):
        super().__init__(schema_field=schema_field, label=label, description=description, required=required)
        self.default = default
        self.placeholder = placeholder

    @property
    def empty_value(self) -> str:
        return ""

    def component(self) -> dmc.TextInput:
        return dmc.TextInput(
            id=self.component_id,
            value=self.default if self.default is not None else self.empty_value,
            placeholder=self.placeholder,
        )

    def to_python_type(self) -> type:
        return str
