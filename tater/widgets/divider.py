"""DividerWidget — a labeled section break with no schema field."""
from dataclasses import dataclass
from typing import Any

import dash_mantine_components as dmc

from .base import ContainerWidget


@dataclass(eq=False)
class DividerWidget(ContainerWidget):
    """A labeled horizontal divider for visually separating widget sections.

    Has no schema field — does not contribute to the annotation model.
    Place it in the widget list between other widgets to create named sections.

    Usage::

        DividerWidget(label="Clinical Findings")
        DividerWidget(label="Demographics", description="Patient background info")
    """

    schema_field: str = ""

    @property
    def renders_own_label(self) -> bool:
        return True

    def component(self) -> Any:
        items = [dmc.Divider(label=self.label or None, labelPosition="center")]
        if self.description:
            items.append(dmc.Text(self.description, size="xs", c="dimmed"))
        return dmc.Stack(items, gap="xs") if len(items) > 1 else items[0]

    def bind_schema(self, model: type) -> None:
        pass

    def register_callbacks(self, app: Any) -> None:
        pass

    def to_python_type(self) -> type:
        return type(None)
