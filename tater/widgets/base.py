"""Base widget classes for Tater."""
import typing
from abc import ABC, abstractmethod
from typing import Any, Optional
import dash_mantine_components as dmc


# ---------------------------------------------------------------------------
# Schema introspection helpers
# ---------------------------------------------------------------------------

def _unwrap_optional(annotation: Any) -> Any:
    """Return the inner type if annotation is Optional[X], else annotation itself."""
    origin = typing.get_origin(annotation)
    if origin is typing.Union:
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


def _resolve_field_info(model: type, field_path: str) -> Any:
    """Resolve a Pydantic FieldInfo by traversing a dotted field_path.

    Numeric path segments (list indices) are skipped so that paths like
    ``pets.0.kind`` resolve the same as ``kind`` against the item model.
    """
    parts = [p for p in field_path.split(".") if not p.isdigit()]
    current_model = model
    field_info = None
    for part in parts:
        if not hasattr(current_model, "model_fields"):
            return None
        field_info = current_model.model_fields.get(part)
        if field_info is None:
            return None
        inner = _unwrap_optional(field_info.annotation)
        if typing.get_origin(inner) is list:
            inner = typing.get_args(inner)[0]
        current_model = inner
    return field_info


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class TaterWidget(ABC):
    """Abstract base class for all Tater widgets."""

    def __init__(
        self,
        schema_field: str,
        label: str = "",
        description: Optional[str] = None,
    ):
        self._local_path = schema_field
        self._full_path: Optional[str] = None
        self.label = label
        self.description = description

    @property
    def field_path(self) -> str:
        if self._full_path is not None:
            return self._full_path
        return self._local_path

    def _finalize_paths(self, parent_path: str = "") -> None:
        self._full_path = f"{parent_path}.{self._local_path}" if parent_path else self._local_path

    def bind_schema(self, model: type) -> None:
        """Validate against the schema model and derive any missing config. No-op by default."""
        pass

    def register_callbacks(self, app: Any) -> None:
        return None

    @property
    def component_id(self) -> str:
        return f"annotation-{self.field_path.replace('.', '-')}"

    def component_id_dict(self, pattern_type: str = "widget") -> dict:
        return {"type": pattern_type, "field": self.field_path}

    def render_field(self, mt: str = "md") -> Any:
        required = getattr(self, "required", False)
        if self.renders_own_label:
            if required:
                return dmc.Group(
                    [dmc.Text("*", size="sm", c="red"), self.component()],
                    gap=4,
                    align="self-start",
                    mt=mt,
                )
            return self.component()
        else:
            label_row = dmc.Group(
                [
                    *([dmc.Text("*", size="sm", c="red")] if required else []),
                    dmc.Text(self.label, fw=500, size="sm"),
                ],
                gap=4,
            )
            items = [label_row]
            if self.description:
                items.append(dmc.Text(self.description, size="xs", c="dimmed"))
            items.append(self.component())
            return dmc.Stack(items, gap="xs", mt=mt)

    @property
    @abstractmethod
    def renders_own_label(self) -> bool:
        pass

    @abstractmethod
    def component(self) -> Any:
        pass

    @abstractmethod
    def to_python_type(self) -> type:
        pass


# ---------------------------------------------------------------------------
# Leaf (value-capturing) base
# ---------------------------------------------------------------------------

class ControlWidget(TaterWidget):
    """Base class for leaf (value-capturing) widgets."""

    @property
    def renders_own_label(self) -> bool:
        return False

    @property
    def value_prop(self) -> str:
        return "value"

    @property
    def empty_value(self) -> Any:
        return None

    def __init__(self, schema_field: str, label: str = "", description: Optional[str] = None,
                 required: bool = False):
        super().__init__(schema_field=schema_field, label=label, description=description)
        self.required = required


# ---------------------------------------------------------------------------
# Typed intermediate classes
# ---------------------------------------------------------------------------

class ChoiceWidget(ControlWidget):
    """Base for single-value choice widgets.

    Schema field must be ``Literal[...]`` or ``Optional[Literal[...]]``.
    Options are derived automatically from the schema via ``bind_schema``.
    """

    def __init__(self, schema_field: str, label: str = "", description: Optional[str] = None,
                 required: bool = False, default: Optional[str] = None, **kwargs):
        super().__init__(schema_field=schema_field, label=label, description=description, required=required)
        self.options: list[str] = []
        self.default = default

    def bind_schema(self, model: type) -> None:
        field_info = _resolve_field_info(model, self.field_path)
        if field_info is None:
            raise ValueError(
                f"{type(self).__name__}: field '{self.field_path}' not found in {model.__name__}"
            )
        inner = _unwrap_optional(field_info.annotation)
        if typing.get_origin(inner) is not typing.Literal:
            raise TypeError(
                f"{type(self).__name__}: field '{self.field_path}' must be Literal[...] or "
                f"Optional[Literal[...]], got {field_info.annotation!r}"
            )
        self.options = [str(a) for a in typing.get_args(inner)]


class MultiChoiceWidget(ControlWidget):
    """Base for multi-value choice widgets.

    Schema field must be ``List[Literal[...]]`` or ``Optional[List[Literal[...]]]``.
    Options are derived automatically from the schema via ``bind_schema``.
    """

    def __init__(self, schema_field: str, label: str = "", description: Optional[str] = None,
                 required: bool = False, default: Optional[list[str]] = None, **kwargs):
        super().__init__(schema_field=schema_field, label=label, description=description, required=required)
        self.options: list[str] = []
        self.default: list[str] = default or []

    def bind_schema(self, model: type) -> None:
        field_info = _resolve_field_info(model, self.field_path)
        if field_info is None:
            raise ValueError(
                f"{type(self).__name__}: field '{self.field_path}' not found in {model.__name__}"
            )
        inner = _unwrap_optional(field_info.annotation)
        if typing.get_origin(inner) is not list:
            raise TypeError(
                f"{type(self).__name__}: field '{self.field_path}' must be "
                f"List[Literal[...]] or Optional[List[Literal[...]]], got {field_info.annotation!r}"
            )
        item_type = typing.get_args(inner)[0]
        if typing.get_origin(item_type) is not typing.Literal:
            raise TypeError(
                f"{type(self).__name__}: list item type for '{self.field_path}' must be "
                f"Literal[...], got {item_type!r}"
            )
        self.options = [str(a) for a in typing.get_args(item_type)]


class BooleanWidget(ControlWidget):
    """Base for boolean widgets. Schema field must be ``bool`` or ``Optional[bool]``."""

    def bind_schema(self, model: type) -> None:
        field_info = _resolve_field_info(model, self.field_path)
        if field_info is None:
            raise ValueError(
                f"{type(self).__name__}: field '{self.field_path}' not found in {model.__name__}"
            )
        inner = _unwrap_optional(field_info.annotation)
        if inner is not bool:
            raise TypeError(
                f"{type(self).__name__}: field '{self.field_path}' must be bool or Optional[bool], "
                f"got {field_info.annotation!r}"
            )


class NumericWidget(ControlWidget):
    """Base for numeric widgets. Schema field must be ``int``, ``float``, or ``Optional`` thereof."""

    def bind_schema(self, model: type) -> None:
        field_info = _resolve_field_info(model, self.field_path)
        if field_info is None:
            raise ValueError(
                f"{type(self).__name__}: field '{self.field_path}' not found in {model.__name__}"
            )
        inner = _unwrap_optional(field_info.annotation)
        if inner not in (int, float):
            raise TypeError(
                f"{type(self).__name__}: field '{self.field_path}' must be int/float or "
                f"Optional[int/float], got {field_info.annotation!r}"
            )


class TextWidget(ControlWidget):
    """Base for free-text widgets. Schema field must be ``str`` or ``Optional[str]``."""

    def bind_schema(self, model: type) -> None:
        field_info = _resolve_field_info(model, self.field_path)
        if field_info is None:
            raise ValueError(
                f"{type(self).__name__}: field '{self.field_path}' not found in {model.__name__}"
            )
        inner = _unwrap_optional(field_info.annotation)
        if inner is not str:
            raise TypeError(
                f"{type(self).__name__}: field '{self.field_path}' must be str or Optional[str], "
                f"got {field_info.annotation!r}"
            )


# ---------------------------------------------------------------------------
# Container (structural) base
# ---------------------------------------------------------------------------

class ContainerWidget(TaterWidget):
    """Base class for container (structural) widgets that hold child widgets."""

    @property
    def renders_own_label(self) -> bool:
        return True
