"""Base widget classes for Tater."""
import typing
from dataclasses import dataclass, field
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

@dataclass(eq=False)
class TaterWidget:
    """Abstract base class for all Tater widgets."""

    schema_field: str
    label: str = ""
    description: Optional[str] = None

    _full_path: Optional[str] = field(init=False, default=None, repr=False)
    _condition: Optional[tuple] = field(init=False, default=None, repr=False)

    def conditional_on(self, controlling_field: str, value: Any) -> "TaterWidget":
        """Set conditional visibility. Returns self for chaining.

        Args:
            controlling_field: The schema_field of the controlling widget (boolean or option).
            value: Show this widget when the controlling field equals this value.
                   For booleans: True or False. For options: string value (e.g., "dog").

        Example::

            TextInputWidget("indoor_location", label="Location").conditional_on("is_indoor", True)
            TextInputWidget("breed_notes", label="Breed").conditional_on("pet_type", "dog")

        Note: Controlling widget must be declared before this widget in the widget list.
        """
        self._condition = (controlling_field, value)
        return self

    @property
    def field_path(self) -> str:
        return self._full_path if self._full_path is not None else self.schema_field

    def _finalize_paths(self, parent_path: str = "") -> None:
        self._full_path = f"{parent_path}.{self.schema_field}" if parent_path else self.schema_field

    def bind_schema(self, model: type) -> None:
        """Validate against the schema model and derive any missing config. No-op by default."""
        pass

    def register_callbacks(self, app: Any) -> None:
        return None

    @property
    def component_id(self) -> str:
        return f"annotation-{self.field_path.replace('.', '-')}"

    @property
    def conditional_wrapper_id(self) -> str:
        return f"visibility-wrapper-{self.field_path.replace('.', '-')}"

    def component_id_dict(self, pattern_type: str = "widget") -> dict:
        return {"type": pattern_type, "field": self.field_path}

    def render_field(self, mt: str = "md") -> Any:
        content = self._build_field_content(mt)
        if self._condition is not None:
            from dash import html
            return html.Div(content, id=self.conditional_wrapper_id)
        return content

    def _build_field_content(self, mt: str = "md") -> Any:
        required = getattr(self, "required", False)
        if self.renders_own_label:
            comp = self.component()
            if required:
                row = dmc.Group([dmc.Text("*", size="sm", c="red"), comp], gap=4, align="self-start")
                items = [row]
            else:
                items = [comp]
            # ContainerWidget subclasses render their own description inside component();
            # only leaf (ControlWidget) widgets need it appended here.
            if self.description and not isinstance(self, ContainerWidget):
                items.append(dmc.Text(self.description, size="xs", c="dimmed"))
            return dmc.Stack(items, gap="xs", mt=mt)
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

    def _register_conditional_callbacks(self, app: Any) -> None:
        """Register clientside + server callbacks for conditional visibility.

        The clientside callback immediately toggles display style (no round-trip).
        The server callback clears the widget value when it becomes hidden, so
        stale values are not saved. Supports boolean and option-based conditions.
        """
        if self._condition is None:
            return
        from dash import Output, Input, no_update

        controlling_field, target_value = self._condition
        controlling_id = f"annotation-{controlling_field.replace('.', '-')}"

        # Determine which property the controlling widget uses.
        # For simplicity: assume it's "checked" for BooleanWidget, "value" for all others.
        # This will be refined via the app's widget registry if needed.
        controlling_prop = self._get_controlling_property(app, controlling_field)

        # Serialize target_value for JavaScript comparison.
        # For booleans: use true/false; for strings: use quoted "value".
        if isinstance(target_value, bool):
            target_js = "true" if target_value else "false"
        else:
            target_js = f'"{target_value}"'

        # Clientside: toggle display instantly without a server round-trip.
        app.clientside_callback(
            f"function(v) {{ return v === {target_js} ? {{}} : {{'display': 'none'}}; }}",
            Output(self.conditional_wrapper_id, "style"),
            Input(controlling_id, controlling_prop),
            prevent_initial_call=False,
        )

        # Server: clear value when widget is hidden so stale data is not saved.
        _empty = self.empty_value
        _value_prop = self.value_prop
        _target = target_value

        @app.callback(
            Output(self.component_id, _value_prop, allow_duplicate=True),
            Input(controlling_id, controlling_prop),
            prevent_initial_call=True,
        )
        def _clear_when_hidden(v):
            if v != _target:
                return _empty
            return no_update

    def _get_controlling_property(self, app: Any, controlling_field: str) -> str:
        """Determine which property (checked/value) the controlling widget uses.

        Returns "checked" for BooleanWidget, "value" for all others.
        """
        # Try to look up the controlling widget from the app's registry.
        # If not found, default to "value" (which works for most option widgets).
        if hasattr(app, "_tater_app") and hasattr(app._tater_app, "_all_widgets"):
            for widget in app._tater_app._all_widgets:
                if widget.field_path == controlling_field:
                    # BooleanWidget has value_prop="checked"
                    return getattr(widget, "value_prop", "value")
        # Default: assume option/choice widget uses "value"
        return "value"

    # Subclasses must override these three methods.
    # Without ABC enforcement, forgetting to do so will cause a runtime error
    # when the method is called rather than at instantiation time.

    @property
    def renders_own_label(self) -> bool:
        pass

    def component(self) -> Any:
        pass

    def to_python_type(self) -> type:
        pass


# ---------------------------------------------------------------------------
# Leaf (value-capturing) base
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class ControlWidget(TaterWidget):
    """Base class for leaf (value-capturing) widgets."""

    required: bool = False
    auto_advance: bool = False

    @property
    def renders_own_label(self) -> bool:
        return False

    @property
    def value_prop(self) -> str:
        return "value"

    @property
    def empty_value(self) -> Any:
        return None


# ---------------------------------------------------------------------------
# Typed intermediate classes
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class ChoiceWidget(ControlWidget):
    """Base for single-value choice widgets.

    Schema field must be ``Literal[...]`` or ``Optional[Literal[...]]``.
    Options are derived automatically from the schema via ``bind_schema``.
    """

    default: Optional[str] = None
    options: list[str] = field(init=False, default_factory=list, repr=False)

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


@dataclass(eq=False)
class MultiChoiceWidget(ControlWidget):
    """Base for multi-value choice widgets.

    Schema field must be ``List[Literal[...]]`` or ``Optional[List[Literal[...]]]``.
    Options are derived automatically from the schema via ``bind_schema``.
    """

    default: Optional[list[str]] = None
    options: list[str] = field(init=False, default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.default is None:
            self.default = []

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


@dataclass(eq=False)
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


@dataclass(eq=False)
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


@dataclass(eq=False)
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

@dataclass(eq=False)
class ContainerWidget(TaterWidget):
    """Base class for container (structural) widgets that hold child widgets."""

    @property
    def renders_own_label(self) -> bool:
        return True
