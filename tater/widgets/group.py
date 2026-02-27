"""GroupWidget for containing nested model fields."""
from typing import Optional
import dash_mantine_components as dmc

from .base import ContainerWidget, TaterWidget


class GroupWidget(ContainerWidget):
    """Container widget for nested Pydantic model fields."""

    def __init__(
        self,
        schema_field: str,
        label: str,
        children: list[TaterWidget],
        description: Optional[str] = None,
    ):
        """
        Initialize GroupWidget.

        Args:
            schema_field: Field name in the Pydantic schema
            label: Human-readable label for the group
            children: List of child widgets
            description: Optional help text
        """
        super().__init__(
            schema_field=schema_field,
            label=label,
            description=description,
        )
        self.children = children

    def _finalize_paths(self, parent_path: str = "") -> None:
        """
        Finalize paths for this group and all children.
        
        Children's local paths are prepended with this group's full path.
        
        Args:
            parent_path: The parent widget's full path
        """
        # Finalize this widget's path
        super()._finalize_paths(parent_path)
        
        # Recursively finalize all children with this widget's full path as their parent
        for child in self.children:
            child._finalize_paths(self.field_path)

    def component(self) -> dmc.Card:
        """
        Return Dash component with children rendered inside a card.
        
        Returns:
            A Dash Mantine Card containing all child widgets
        """
        child_components = []
        for child in self.children:
            child_stack = dmc.Stack([
                dmc.Text(child.label, fw=500, size="sm"),
                child.component(),
                dmc.Text(child.description or "", size="xs", c="dimmed") if child.description else None,
            ], gap="xs", mt="sm")
            child_components.append(child_stack)
        
        return dmc.Card([
            dmc.Title(self.label, order=5, mb="sm"),
            dmc.Text(self.description or "", size="xs", c="dimmed", mb="sm") if self.description else None,
            dmc.Stack(child_components, gap="sm"),
        ], withBorder=True, p="md", mt="md")

    def register_callbacks(self, app) -> None:
        """Register callbacks for any child widgets that need them."""
        for child in self.children:
            child.register_callbacks(app)

    def to_python_type(self) -> type:
        """Return dict since this represents a nested model."""
        return dict
