"""SegmentedControl widget for single-choice annotations."""
from typing import Optional
import dash_mantine_components as dmc

from ...models.schema import DataField
from ...models.ui_config import WidgetConfig
from .base import TaterWidget


class SegmentedControlWidget(TaterWidget):
    """Segmented control widget implementation."""

    def __init__(
        self,
        schema_id: str,
        label: Optional[str] = None,
        description: Optional[str] = None,
        options: Optional[list[str]] = None,
        required: bool = False,
        default: Optional[str] = None
    ) -> None:
        label = label or schema_id.replace("_", " ").title()
        super().__init__(schema_id=schema_id, label=label, description=description)
        self.options = options or []
        self.required = required
        self.default = default

    @classmethod
    def from_field(
        cls,
        field: DataField,
        widget_config: Optional[WidgetConfig] = None,
        value: Optional[str] = None
    ) -> "SegmentedControlWidget":
        label = widget_config.label if widget_config and widget_config.label else field.id.replace("_", " ").title()
        description = widget_config.description if widget_config and widget_config.description else field.description
        options = field.options or []
        default = value if value is not None else field.default

        return cls(
            schema_id=field.id,
            label=label,
            description=description,
            options=options,
            required=field.required,
            default=default
        )

    def to_field(self) -> DataField:
        """Convert this widget back to a schema field."""
        return DataField(
            id=self.schema_id,
            type="single_choice",
            options=self.options,
            required=self.required,
            default=self.default,
            description=self.description
        )

    def component(self) -> dmc.Stack:
        data = [{"label": opt, "value": opt} for opt in self.options]

        if self.required:
            label_component = dmc.Group([
                dmc.Text("*", c="red", fw=700, size="sm"),
                dmc.Title(self.label, order=6)
            ], gap="xs")
        else:
            label_component = dmc.Title(self.label, order=6)

        return dmc.Stack([
            label_component,
            dmc.Text(self.description, size="sm", c="dimmed") if self.description else None,
            dmc.SegmentedControl(
                id=self.component_id,
                data=data,
                value=self.default,
                fullWidth=True
            )
        ], gap="xs")


def create_segmented_control(
    field: DataField,
    widget_config: Optional[WidgetConfig] = None,
    value: Optional[str] = None
) -> dmc.Stack:
    """Create a segmented control widget for single-choice selection."""
    return SegmentedControlWidget.from_field(field, widget_config, value).component()
