"""Base widget classes for Tater."""
import typing
from dataclasses import dataclass, field
from typing import Any, Optional
import dash_mantine_components as dmc
from dash_iconify import DashIconify


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

    def conditional_on(self, controlling_field: "str | list[str] | tuple[str, ...]", value: Any) -> "TaterWidget":
        """Set conditional visibility. Returns self for chaining.

        Args:
            controlling_field: The field of the controlling widget. Either a
                dot-joined path string (``"is_indoor"`` / ``"booleans.is_indoor"``)
                or a sequence of path segments (``["booleans", "is_indoor"]``).
                Use a sequence to avoid writing dot-joined group prefixes by hand.
            value: Show this widget when the controlling field equals this value.
                   For booleans: True or False. For options: string value (e.g., "dog").

        Examples::

            # flat schema
            TextInputWidget("location").conditional_on("is_indoor", True)

            # inside a GroupWidget — sequence avoids hard-coding the prefix
            TextInputWidget("location").conditional_on(["booleans", "is_indoor"], True)

        Note: Controlling widget must be declared before this widget in the widget list.
        """
        if isinstance(controlling_field, (list, tuple)):
            controlling_field = ".".join(controlling_field)
        self._condition = (controlling_field, value)
        print(f"[TATER:create] {type(self).__name__}({self.schema_field!r}).conditional_on({controlling_field!r}, {value!r})")
        return self

    @property
    def field_path(self) -> str:
        return self._full_path if self._full_path is not None else self.schema_field

    def _finalize_paths(self, parent_path: str = "") -> None:
        self._full_path = f"{parent_path}.{self.schema_field}" if parent_path else self.schema_field
        print(f"[TATER:create] _finalize_paths: {type(self).__name__}({self.schema_field!r}) → field_path={self._full_path!r}")

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
            auto_advance = getattr(self, "auto_advance", False)
            label_row = dmc.Group(
                [
                    *([dmc.Text("*", size="sm", c="red")] if required else []),
                    dmc.Text(self.label, fw=500, size="sm"),
                    *(
                        [dmc.Tooltip(
                            DashIconify(icon="tabler:circle-open-arrow-right", width=13, color="var(--mantine-color-dimmed)"),
                            label="Auto-advances to next document",
                            position="right",
                            withArrow=True,
                        )]
                        if auto_advance else []
                    ),
                ],
                gap=4,
            )
            items = [label_row]
            if self.description and not getattr(self, "_description_in_component", False):
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
        print(f"[TATER:register] _register_conditional_callbacks: {type(self).__name__}({self.field_path!r}) controlling={self._condition[0]!r} when={self._condition[1]!r}")
        from dash import Output, Input, no_update

        controlling_field, target_value = self._condition
        controlling_widget, controlling_prop = self._get_controlling_widget(app, controlling_field)

        # Use the controlling widget's own schema_id so the encoding is always
        # consistent with how the component was actually rendered.
        if controlling_widget is not None:
            controlling_schema_id = controlling_widget.schema_id
        else:
            controlling_type = "tater-control"
            controlling_schema_id = {"type": controlling_type, "field": controlling_field.replace(".", "|")}

        # Serialize target_value for JavaScript comparison.
        # For booleans: use true/false; for strings: use quoted "value".
        if isinstance(target_value, bool):
            target_js = "true" if target_value else "false"
        else:
            target_js = f'"{target_value}"'

        print(f"[TATER:register]   controlling_schema_id={controlling_schema_id!r} prop={controlling_prop!r}")
        print(f"[TATER:register]   wrapper_id={self.conditional_wrapper_id!r} self_schema_id={self.schema_id!r}")
        # Clientside: toggle display instantly without a server round-trip.
        app.clientside_callback(
            f"function(v) {{ return v === {target_js} ? {{}} : {{'display': 'none'}}; }}",
            Output(self.conditional_wrapper_id, "style"),
            Input(controlling_schema_id, controlling_prop),
            prevent_initial_call=False,
        )

        # Server: clear value when widget is hidden so stale data is not saved.
        _empty = self.empty_value
        _value_prop = self.value_prop
        _target = target_value
        _schema_id = self.schema_id

        @app.callback(
            Output(_schema_id, _value_prop, allow_duplicate=True),
            Input(controlling_schema_id, controlling_prop),
            prevent_initial_call=True,
        )
        def _clear_when_hidden(v):
            if v != _target:
                print(f"[TATER:fire] _clear_when_hidden: controlling={v!r} != target={_target!r} → clearing {_schema_id} {_value_prop}={_empty!r}")
                return _empty
            print(f"[TATER:fire] _clear_when_hidden: controlling={v!r} == target={_target!r} → no_update")
            return no_update

    def _get_controlling_widget(self, app: Any, controlling_field: str) -> tuple:
        """Look up the controlling widget and its value property.

        Returns ``(widget, prop)`` where ``prop`` is ``"checked"`` for
        BooleanWidgets and ``"value"`` for all others.  ``widget`` may be
        ``None`` if the registry is not yet available.
        """
        if hasattr(app, "_tater_app") and hasattr(app._tater_app, "_all_widgets"):
            for widget in app._tater_app._all_widgets:
                if widget.field_path == controlling_field:
                    return widget, getattr(widget, "value_prop", "value")
        return None, "value"

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

    @property
    def schema_id(self) -> dict:
        # Dots in dict ID field values break Dash 4's client-side dependency
        # parser (splitIdAndProp in dependencies.js splits prop_ids on "." to
        # separate the component ID from the property name, so a dot inside a
        # JSON string value causes JSON.parse to fail). Pipes are safe because
        # they cannot appear in Python identifiers. Callbacks decode "|" → "."
        # before using the field as a dot-notation path.
        return {"type": "tater-control", "field": self.field_path.replace(".", "|")}


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

    @property
    def empty_value(self) -> bool:
        return False

    @property
    def schema_id(self) -> dict:
        # See ControlWidget.schema_id for why dots are encoded as pipes.
        return {"type": "tater-bool-control", "field": self.field_path.replace(".", "|")}

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
