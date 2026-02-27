"""Base widget class for Tater."""
from abc import ABC, abstractmethod
from typing import Any, Optional


class TaterWidget(ABC):
    """Abstract base class for all Tater widgets."""

    def __init__(
        self,
        schema_field: str,
        label: str = "",
        description: Optional[str] = None,
        required: bool = False,
    ):
        """
        Initialize a widget.

        Args:
            schema_field: Field name in the Pydantic schema (e.g., "sentiment" or "owner")
            label: Human-readable label for the widget
            description: Optional help text
            required: Whether this field is required
        """
        # Two-phase initialization for nested paths
        self._local_path = schema_field
        self._full_path: Optional[str] = None
        
        self.label = label
        self.description = description
        self.required = required

    @property
    def field_path(self) -> str:
        """
        Get the full field path.
        
        Returns the finalized full path if available, otherwise the local path.
        For nested widgets, the full path is computed during finalization.
        """
        if self._full_path is not None:
            return self._full_path
        return self._local_path
    
    def _finalize_paths(self, parent_path: str = "") -> None:
        """
        Finalize field paths after widget tree construction.
        
        This is called by TaterApp after all widgets are created to compute
        full paths for nested widgets. Container widgets override this to
        recursively finalize their children.
        
        Args:
            parent_path: The parent widget's full path (empty for top-level widgets)
        """
        if parent_path:
            self._full_path = f"{parent_path}.{self._local_path}"
        else:
            self._full_path = self._local_path

    def register_callbacks(self, app: Any) -> None:
        """Register any widget-specific callbacks with the Dash app."""
        return None

    @property
    def component_id(self) -> str:
        """Return unique component ID for Dash (dots replaced with hyphens)."""
        return f"annotation-{self.field_path.replace('.', '-')}"
    
    def component_id_dict(self, pattern_type: str = "widget") -> dict:
        """Return dictionary-based component ID for pattern-matching callbacks."""
        return {
            "type": pattern_type,
            "field": self.field_path,
        }

    @property
    def renders_own_label(self) -> bool:
        """Whether this widget renders its own label in component()."""
        return False

    @abstractmethod
    def component(self) -> Any:
        """
        Return the Dash component (dmc.SegmentedControl, etc).

        Returns:
            A Dash Mantine component
        """
        raise NotImplementedError

    @abstractmethod
    def to_python_type(self) -> type:
        """Return the Python type this widget produces."""
        raise NotImplementedError
