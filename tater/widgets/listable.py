"""Backward-compatible re-export — ListableWidget now lives in repeater.py."""
from tater.widgets.repeater import RepeaterWidget, ListableWidget, TabsWidget

__all__ = ["RepeaterWidget", "ListableWidget", "TabsWidget"]
