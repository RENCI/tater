"""RadioGroup widget for single-choice annotations."""
from typing import Optional
import dash_mantine_components as dmc
from dash import html

from ...models.schema import DataField
from ...models.ui_config import WidgetConfig
from .base import TaterWidget


class RadioGroupWidget(TaterWidget):
    """Radio group widget implementation."""

    def __init__(
        self,
        schema_id: str,
        label: Optional[str] = None,
        description: Optional[str] = None,
        options: Optional[list[str]] = None,
        orientation: str = "vertical",
        required: bool = False,
        default: Optional[str] = None
    ) -> None:
        label = label or schema_id.replace("_", " ").title()
        super().__init__(schema_id=schema_id, label=label, description=description)
        self.options = options or []
        self.orientation = orientation
        self.required = required
        self.default = default

    @classmethod
    def from_field(
        cls,
        field: DataField,
        widget_config: Optional[WidgetConfig] = None,
        value: Optional[str] = None
    ) -> "RadioGroupWidget":
        label = widget_config.label if widget_config and widget_config.label else field.id.replace("_", " ").title()
        description = widget_config.description if widget_config and widget_config.description else field.description
        orientation = widget_config.orientation if widget_config and widget_config.orientation else "vertical"
        options = field.options or []
        default = value if value is not None else field.default

        return cls(
            schema_id=field.id,
            label=label,
            description=description,
            options=options,
            orientation=orientation,
            required=field.required,
            default=default
        )

    def component(self) -> dmc.Stack:
        # Add required indicator if field is required
        if self.required:
            label_component = dmc.Group([
                html.Span(self.label, style={"fontWeight": 500, "fontSize": "14px"}),
                dmc.Badge("Required", color="red", size="xs", variant="dot")
            ], gap="xs", mb="xs")

            radio_group = dmc.RadioGroup(
                id=self.component_id,
                description=self.description,
                value=self.default,
                children=dmc.Stack(
                    [dmc.Radio(label=opt, value=opt) for opt in self.options],
                    gap="xs"
                ) if self.orientation == "vertical" else dmc.Group(
                    [dmc.Radio(label=opt, value=opt) for opt in self.options],
                    gap="md"
                ),
                size="sm",
                mb="md"
            )

            return dmc.Stack([label_component, radio_group], gap=0)

        # Non-required field - use standard label
        radio_group = dmc.RadioGroup(
            id=self.component_id,
            label=self.label,
            description=self.description,
            value=self.default,
            children=dmc.Stack(
                [dmc.Radio(label=opt, value=opt) for opt in self.options],
                gap="xs"
            ) if self.orientation == "vertical" else dmc.Group(
                [dmc.Radio(label=opt, value=opt) for opt in self.options],
                gap="md"
            ),
            size="sm",
            mb="md"
        )

        return radio_group


def create_radio_group(
    field: DataField,
    widget_config: Optional[WidgetConfig] = None,
    value: Optional[str] = None
) -> dmc.Stack:
    """Create a radio group widget for single-choice selection."""
    return RadioGroupWidget.from_field(field, widget_config, value).component()
