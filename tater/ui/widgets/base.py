"""Base widget interface for Tater UI."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class TaterWidget(ABC):
    """Base class for Tater annotation widgets."""

    schema_id: str
    label: str
    description: Optional[str] = None
    value_prop: str = "value"

    @property
    def component_id(self) -> str:
        return f"annotation-{self.schema_id}"

    @abstractmethod
    def component(self):
        """Return the Dash component for this widget."""
        raise NotImplementedError
