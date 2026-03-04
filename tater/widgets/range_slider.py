"""RangeSlider widget for selecting a numeric range."""
import typing
from dataclasses import dataclass
from typing import Optional
import dash_mantine_components as dmc

from .base import ControlWidget, _unwrap_optional, _resolve_field_info


@dataclass(eq=False)
class RangeSliderWidget(ControlWidget):
    """Widget for selecting a min/max numeric range via a slider.

    The schema field must be ``Optional[list[float]]`` or ``Optional[list[int]]``
    with a default of ``None``. The value is stored as a two-element list ``[min, max]``.
    """

    min_value: float = 0
    max_value: float = 100
    step: Optional[float] = None
    default: Optional[list[float]] = None

    def __post_init__(self) -> None:
        if self.default is None:
            self.default = [self.min_value, self.max_value]

    def bind_schema(self, model: type) -> None:
        field_info = _resolve_field_info(model, self.field_path)
        if field_info is None:
            raise ValueError(
                f"{type(self).__name__}: field '{self.field_path}' not found in {model.__name__}"
            )
        inner = _unwrap_optional(field_info.annotation)
        origin = typing.get_origin(inner)
        if origin is not list:
            raise TypeError(
                f"{type(self).__name__}: field '{self.field_path}' must be list[float] or "
                f"list[int] (or Optional thereof), got {field_info.annotation!r}"
            )
        item_type = typing.get_args(inner)[0] if typing.get_args(inner) else None
        if item_type not in (int, float):
            raise TypeError(
                f"{type(self).__name__}: list item type for '{self.field_path}' must be "
                f"float or int, got {item_type!r}"
            )

    @property
    def empty_value(self) -> None:
        return None

    def component(self) -> dmc.RangeSlider:
        return dmc.RangeSlider(
            id=self.component_id,
            value=self.default,
            min=self.min_value,
            max=self.max_value,
            step=self.step,
        )

    def to_python_type(self) -> type:
        return list
