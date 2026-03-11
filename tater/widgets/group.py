"""GroupWidget for containing nested model fields."""
from dataclasses import dataclass, field
import dash_mantine_components as dmc

from .base import ContainerWidget, TaterWidget


@dataclass(eq=False)
class GroupWidget(ContainerWidget):
    """Container widget for nested Pydantic model fields."""

    children: list[TaterWidget] = field(kw_only=True, default_factory=list)

    def _finalize_paths(self, parent_path: str = "") -> None:
        super()._finalize_paths(parent_path)
        for child in self.children:
            child._finalize_paths(self.field_path)

    def component(self) -> dmc.Card:
        child_components = [child.render_field(mt="sm") for child in self.children]
        return dmc.Card([
            dmc.Title(self.label, order=5, mb="sm"),
            dmc.Text(self.description or "", size="xs", c="dimmed", mb="sm") if self.description else None,
            dmc.Stack(child_components, gap="sm"),
        ], withBorder=True, p="md", mt="md")

    def bind_schema(self, model: type) -> None:
        for child in self.children:
            child.bind_schema(model)

    def register_callbacks(self, app) -> None:
        for child in self.children:
            child.register_callbacks(app)
            child._register_conditional_callbacks(app)

    def to_python_type(self) -> type:
        return dict
