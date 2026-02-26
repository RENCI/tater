"""Base widget class for Tater."""
from abc import ABC, abstractmethod
from typing import Any, Optional


class TaterWidget(ABC):
    """Abstract base class for all Tater widgets."""

    def __init__(
        self,
        field_path: Optional[str] = None,
        label: str = "",
        description: Optional[str] = None,
        required: bool = False,
        schema_id: Optional[str] = None,
    ):
        """
        Initialize a widget.

        Args:
            field_path: Dotted path to field (e.g., "sentiment" or "address.street")
            label: Human-readable label for the widget
            description: Optional help text
            required: Whether this field is required
            schema_id: Alias for field_path (for backwards compatibility)
        """
        # Support both field_path and schema_id
        local_path = schema_id if schema_id is not None else field_path
        if local_path is None:
            raise ValueError("Either field_path or schema_id must be provided")
        
        # Two-phase initialization for nested paths
        self._local_path = local_path
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

    @property
    def component_id(self) -> str:
        """Return unique component ID for Dash."""
        return f"annotation-{self.field_path}"

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
