"""Base widget classes for Tater."""
from abc import ABC, abstractmethod
from typing import Any, Optional


class TaterWidget(ABC):
    """Abstract base class for all Tater widgets."""

    def __init__(
        self,
        schema_field: str,
        label: str = "",
        description: Optional[str] = None,
    ):
        """
        Initialize a widget.

        Args:
            schema_field: Field name in the Pydantic schema (e.g., "sentiment" or "owner")
            label: Human-readable label for the widget
            description: Optional help text
        """
        # Two-phase initialization for nested paths
        self._local_path = schema_field
        self._full_path: Optional[str] = None

        self.label = label
        self.description = description

    @property
    def field_path(self) -> str:
        """Return the finalized full path, or local path if not yet finalized."""
        if self._full_path is not None:
            return self._full_path
        return self._local_path

    def _finalize_paths(self, parent_path: str = "") -> None:
        """Finalize field path after widget tree construction."""
        self._full_path = f"{parent_path}.{self._local_path}" if parent_path else self._local_path

    def register_callbacks(self, app: Any) -> None:
        """Register any widget-specific callbacks with the Dash app."""
        return None

    @property
    def component_id(self) -> str:
        """Return unique component ID for Dash (dots replaced with hyphens)."""
        return f"annotation-{self.field_path.replace('.', '-')}"

    def component_id_dict(self, pattern_type: str = "widget") -> dict:
        """Return dictionary-based component ID for pattern-matching callbacks."""
        return {"type": pattern_type, "field": self.field_path}

    @property
    @abstractmethod
    def renders_own_label(self) -> bool:
        """Whether this widget renders its own label in component()."""

    @abstractmethod
    def component(self) -> Any:
        """Return the Dash component for this widget."""

    @abstractmethod
    def to_python_type(self) -> type:
        """Return the Python type this widget produces."""


class ControlWidget(TaterWidget):
    """Base class for leaf (value-capturing) widgets."""

    @property
    def renders_own_label(self) -> bool:
        return False

    @property
    def value_prop(self) -> str:
        """Dash prop name used to read/write this widget's value."""
        return "value"

    @property
    def empty_value(self) -> Any:
        """Fallback value when no annotation value exists."""
        return None

    def __init__(self, schema_field: str, label: str = "", description: Optional[str] = None,
                 required: bool = False):
        super().__init__(schema_field=schema_field, label=label, description=description)
        self.required = required


class ContainerWidget(TaterWidget):
    """Base class for container (structural) widgets that hold child widgets."""

    @property
    def renders_own_label(self) -> bool:
        return True
