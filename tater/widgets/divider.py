"""DividerWidget — a labeled section break with no schema field."""
from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional

import dash_mantine_components as dmc

from .base import ContainerWidget


@dataclass(eq=False)
class DividerWidget(ContainerWidget):
    """A labeled horizontal divider for visually separating widget sections.

    Has no schema field — does not contribute to the annotation model.

    In a manual widget list, place it between other widgets to create named sections.
    When using ``widgets_from_model``, set ``before`` to the field name (or dot-path)
    it should precede and include it in the ``overrides`` list::

        DividerWidget(label="Clinical Findings", before="diagnosis")
        DividerWidget(label="Demographics", before="pet.age")
    """

    field_type: ClassVar[str] = "divider"

    schema_field: str = ""
    before: Optional[str] = field(kw_only=True, default=None)

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
