"""GroupWidget for containing nested model fields."""
from typing import Optional
import dash_mantine_components as dmc

from .base import TaterWidget


class GroupWidget(TaterWidget):
    """Container widget for nested Pydantic model fields."""

    def __init__(
        self,
        label: str,
        children: list[TaterWidget],
        field_path: Optional[str] = None,
        description: Optional[str] = None,
        required: bool = False,
        schema_id: Optional[str] = None,
    ):
        """
        Initialize GroupWidget.

        Args:
            label: Human-readable label for the group
            children: List of child widgets
            field_path: Path to the nested model field (e.g., "address")
            description: Optional help text
            required: Whether this group is required
            schema_id: Alias for field_path
        """
        super().__init__(
            field_path=field_path,
            label=label,
            description=description,
            required=required,
            schema_id=schema_id,
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

    def to_python_type(self) -> type:
        """Return dict since this represents a nested model."""
        return dict
