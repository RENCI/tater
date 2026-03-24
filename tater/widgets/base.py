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
# Shared callback helper
# ---------------------------------------------------------------------------

def _build_conditional_callbacks(
    app: Any,
    target_value: Any,
    *,
    wrapper_id: Any,
    controlling_id: Any,
    controlling_prop: str,
    self_id: Any,
    value_prop: str,
    empty_value: Any,
) -> None:
    """Register the clientside visibility toggle and server-side value-clear callbacks.

    Used by both ``_register_conditional_callbacks`` (standalone widgets, plain
    dict IDs) and ``_register_repeater_conditional_callbacks`` (repeater items,
    MATCH dict IDs).  The caller is responsible for building the correct ID dicts.
    """
    from dash import Output, Input, no_update

    if isinstance(target_value, bool):
        target_js = "true" if target_value else "false"
    else:
        target_js = f'"{target_value}"'

    app.clientside_callback(
        f"function(v) {{ return v === {target_js} ? {{}} : {{'display': 'none'}}; }}",
        Output(wrapper_id, "style"),
        Input(controlling_id, controlling_prop),
        prevent_initial_call=False,
    )

    _empty = empty_value
    _target = target_value

    @app.callback(
        Output(self_id, value_prop, allow_duplicate=True),
        Input(controlling_id, controlling_prop),
        prevent_initial_call=True,
    )
    def _clear_when_hidden(v):
        if v != _target:
            return _empty
        return no_update


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
    def conditional_wrapper_id(self) -> dict:
        ld = getattr(self, "_repeater_ld", "")
        path = getattr(self, "_repeater_path", "")
        # ControlWidgets supply _item_relative_tf which handles group-child paths.
        _irtf = getattr(self, "_item_relative_tf", None)
        if _irtf is not None:
            tf = _irtf
        else:
            tf = self.schema_field if ld else self.field_path.replace(".", "|")
        return {"type": "tater-cond-wrapper", "ld": ld, "path": path, "tf": tf}

    def _set_repeater_context(self, ld: str, path: str) -> None:
        """Propagate repeater list-field path and row index to this widget.

        Called by RepeaterWidget before rendering an item so that MATCH-based
        component IDs can be generated with the correct ``ld`` and ``path``.
        Default is a no-op; ControlWidget and GroupWidget override it.
        """
        pass

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

        This method handles standalone (non-repeater) widgets only.  For widgets
        inside a RepeaterWidget call ``_register_repeater_conditional_callbacks``
        from the repeater's ``register_callbacks``.
        """
        if self._condition is None:
            return
        from dash import Output, Input, no_update

        controlling_field, target_value = self._condition
        controlling_widget, controlling_prop = self._get_controlling_widget(app, controlling_field)

        # Use the controlling widget's own schema_id (new 3-key format).
        if controlling_widget is not None:
            controlling_schema_id = controlling_widget.schema_id
        else:
            # Fallback: assume non-boolean standalone widget.
            controlling_schema_id = {
                "type": "tater-control",
                "ld": "",
                "path": "",
                "tf": controlling_field.replace(".", "|"),
            }

        _build_conditional_callbacks(
            app, target_value,
            wrapper_id=self.conditional_wrapper_id,
            controlling_id=controlling_schema_id,
            controlling_prop=controlling_prop,
            self_id=self.schema_id,
            value_prop=self.value_prop,
            empty_value=self.empty_value,
        )

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

    # Set by RepeaterWidget before rendering an item to enable MATCH-based
    # pattern callbacks.  ``_repeater_ld`` is the pipe-joined list-field path
    # (e.g. ``"pets"`` or ``"findings|annotations"``); ``_repeater_path`` is the
    # dot-joined index chain (e.g. ``"0"`` or ``"0.2"``).  Both default to ``""``
    # for standalone (non-repeater) widgets.
    _repeater_ld: str = field(init=False, default="", repr=False)
    _repeater_path: str = field(init=False, default="", repr=False)

    def _set_repeater_context(self, ld: str, path: str) -> None:
        self._repeater_ld = ld
        self._repeater_path = path

    @property
    def _item_relative_tf(self) -> str:
        """Pipe-encoded item-relative path for the ``tf`` key in schema_id / conditional_wrapper_id.

        For standalone widgets (``_repeater_ld == ""``), returns the full
        pipe-encoded ``field_path`` (globally unique; no MATCH needed).

        For template widgets (``_repeater_path`` not yet set) and for rendered
        row widgets, returns the path relative to the repeater item root, so
        the value is the same across all rows and matches what was registered.

        A GroupWidget child of a repeater will have a path like
        ``"booleans|is_indoor"`` rather than the bare ``"is_indoor"`` of a
        direct repeater child; this ensures uniqueness within an item and
        correct MATCH pairing between controlling and controlled widgets.
        """
        if not self._repeater_ld or not self._repeater_path:
            # standalone or template (pre-render): field_path is already the right scope
            return self.field_path.replace(".", "|")
        # Rendered row: strip the "list_field.index." prefix from field_path.
        list_fields = self._repeater_ld.split("|")
        indices = self._repeater_path.split(".")
        prefix_parts: list[str] = []
        for seg, idx in zip(list_fields, indices):
            prefix_parts.extend([seg, idx])
        prefix = ".".join(prefix_parts) + "."
        if self.field_path.startswith(prefix):
            return self.field_path[len(prefix):].replace(".", "|")
        return self.schema_field.replace(".", "|")

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
        # ``tf`` (template field) is the item-relative pipe-encoded path.
        # For direct repeater children: same as schema_field.
        # For group children inside a repeater: group-prefixed (e.g. "booleans|is_indoor").
        # For standalone widgets: full pipe-encoded field_path (no MATCH needed).
        # Dots in dict ID values break Dash 4's client-side dependency parser;
        # pipes are used instead (callbacks decode "|" → ".").
        return {"type": "tater-control", "ld": self._repeater_ld, "path": self._repeater_path, "tf": self._item_relative_tf}

    def _register_repeater_conditional_callbacks(
        self, app: Any, ld: str, sibling_widgets: list
    ) -> None:
        """Register MATCH-based conditional callbacks for this widget inside a repeater.

        ``ld`` is the pipe-joined outer list-field path (e.g. ``"pets"``).
        ``sibling_widgets`` is the repeater's ``item_widgets`` list (templates),
        used to look up the controlling widget's type and schema_field.
        """
        if self._condition is None:
            return
        from dash import MATCH

        controlling_field, target_value = self._condition

        # Find the controlling widget among siblings by schema_field.
        # Use only the last dot-segment so "booleans.is_indoor" → "is_indoor"
        # still matches a sibling with schema_field "is_indoor".
        controlling_schema_field = controlling_field.split(".")[-1]
        controlling_widget = next(
            (w for w in sibling_widgets if w.schema_field == controlling_schema_field),
            None,
        )
        if controlling_widget is None:
            return  # cannot register without knowing the controlling widget's type

        is_bool = isinstance(controlling_widget, BooleanWidget)
        controlling_type = "tater-bool-control" if is_bool else "tater-control"
        controlling_prop = "checked" if is_bool else "value"

        # Use _item_relative_tf so group children encode their group prefix
        # (e.g. "booleans|is_indoor") matching what the rendered components emit.
        self_tf = self._item_relative_tf
        controlling_tf = controlling_widget._item_relative_tf
        self_type = self.schema_id["type"]

        wrapper_match_id = {"type": "tater-cond-wrapper", "ld": ld, "path": MATCH, "tf": self_tf}
        controlling_match_id = {"type": controlling_type, "ld": ld, "path": MATCH, "tf": controlling_tf}
        self_match_id = {"type": self_type, "ld": ld, "path": MATCH, "tf": self_tf}

        _build_conditional_callbacks(
            app, target_value,
            wrapper_id=wrapper_match_id,
            controlling_id=controlling_match_id,
            controlling_prop=controlling_prop,
            self_id=self_match_id,
            value_prop=self.value_prop,
            empty_value=self.empty_value,
        )


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
        # See ControlWidget.schema_id / _item_relative_tf for the encoding rationale.
        return {"type": "tater-bool-control", "ld": self._repeater_ld, "path": self._repeater_path, "tf": self._item_relative_tf}

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
    """Base for numeric widgets. Schema field must be ``int``, ``float``, or ``Optional[int|float]``."""

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
