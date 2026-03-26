"""RepeaterWidget, ListableWidget, TabsWidget, and AccordionWidget.

RepeaterWidget is the abstract base for widgets that manage a repeatable list
of sub-form items (a ``List[ItemModel]`` schema field).  Subclasses implement
``_render_items()`` to control how items are presented:

- ``ListableWidget``   — vertical stack of bordered cards (default)
- ``TabsWidget``       — items as switchable tabs
- ``AccordionWidget``  — items as collapsible accordion sections

All repeater components use pipe-encoded field-path dict IDs:

    {"type": "repeater-add",    "field": "findings|0|annotations"}
    {"type": "repeater-delete", "field": "findings|0|annotations", "index": i}
    {"type": "repeater-store",  "field": "findings|0|annotations"}
    {"type": "repeater-items",  "field": "findings|0|annotations"}
    {"type": "repeater-change", "field": "findings|0|annotations"}

A single MATCH callback in ``callbacks.setup_repeater_callbacks`` handles every
repeater instance at every nesting depth without per-widget registration.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional, Any

from dash import dcc, html
import dash_mantine_components as dmc
from dash_iconify import DashIconify

import typing
from pydantic import BaseModel
from .base import ContainerWidget, TaterWidget, ControlWidget, _resolve_field_info, _unwrap_optional

# Component-type strings for nested (repeater-inside-repeater) IDs.
_NESTED_ADD_TYPE    = "nested-repeater-add"
_NESTED_DELETE_TYPE = "nested-repeater-delete"
_NESTED_STORE_TYPE  = "nested-repeater-store"
_NESTED_ITEMS_TYPE  = "nested-repeater-items"


def _load_defaults_from_annotation(widget: Any, tater_app: Any, doc_id: str, annotations_data: dict | None = None) -> None:
    """Recursively set annotation values as widget defaults for ControlWidget descendants.

    Called before rendering a GroupWidget inside a repeater so components are
    initialised with the stored value instead of schema defaults, avoiding a
    visible flash of incorrect values before the load_values/load_checked
    callbacks fire.
    """
    from tater.widgets.group import GroupWidget
    from tater.ui import value_helpers
    if isinstance(widget, GroupWidget):
        for child in widget.children:
            _load_defaults_from_annotation(child, tater_app, doc_id, annotations_data)
    elif isinstance(widget, ControlWidget):
        ann = (annotations_data or {}).get(doc_id) if doc_id else None
        if ann is None and tater_app and doc_id and doc_id in tater_app.annotations:
            ann = tater_app.annotations[doc_id]
        if ann is not None:
            value = value_helpers.get_model_value(ann, widget.field_path)
            if value is not None:
                widget.default = value


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class RepeaterWidget(ContainerWidget):
    """Abstract base for widgets that manage a repeatable list of sub-form items.

    Subclasses must implement ``_render_items()``.
    """

    item_widgets: list[TaterWidget] = field(kw_only=True, default_factory=list)
    item_label: str = field(kw_only=True, default="Item")

    def _empty_store_data(self) -> dict[str, Any]:
        return {"indices": [], "next_index": 0}

    # ------------------------------------------------------------------
    # Item widget rendering (shared)
    # ------------------------------------------------------------------

    def _render_item_widgets(
        self, index: int, tater_app: Optional[Any] = None, doc_id: Optional[str] = None,
        annotations_data: dict | None = None,
    ) -> list[Any]:
        """Render widgets for a single list item with pattern-matching IDs."""
        from tater.widgets.hierarchical_label import HierarchicalLabelWidget
        from tater.widgets.span import SpanAnnotationWidget
        from tater.widgets.group import GroupWidget
        from tater.ui import value_helpers
        rendered = []
        pipe_ld = self.field_path.replace(".", "|")
        for template in self.item_widgets:
            widget = copy.deepcopy(template)
            widget._finalize_paths(parent_path=f"{self.field_path}.{index}")

            # GroupWidget: set context before render_field so child schema_ids
            # use MATCH-compatible ld/path/tf keys.
            if isinstance(template, GroupWidget):
                widget._set_repeater_context(pipe_ld, str(index))
                _load_defaults_from_annotation(widget, tater_app, doc_id, annotations_data)
                rendered.append(widget.render_field(mt="sm"))
                continue

            # For nested RepeaterWidgets use _component_with_context so initial
            # items are pre-populated from the annotation rather than empty.
            if isinstance(template, RepeaterWidget):
                comp = widget._component_with_context(tater_app, doc_id, annotations_data)
            else:
                # Set repeater context BEFORE component() so the rendered
                # component gets MATCH-compatible schema_id (ld/path/tf) rather
                # than the standalone full-path encoding.  This is required for
                # conditional-visibility MATCH callbacks to find the component,
                # and ensures the component renders with correct annotation
                # values on doc navigation (prevents React controlled→uncontrolled
                # warnings when the same component ID is reused across docs).
                if isinstance(template, ControlWidget):
                    widget._set_repeater_context(pipe_ld, str(index))
                    ann = (annotations_data or {}).get(doc_id) if doc_id else None
                    if ann is None and tater_app and doc_id:
                        ann = tater_app.annotations.get(doc_id)
                    if ann is not None:
                        v = value_helpers.get_model_value(ann, widget.field_path)
                        if v is not None:
                            widget.default = v
                comp = widget.component()

            stack = dmc.Stack([comp], gap="xs", mt="sm")
            if widget._condition is not None:
                rendered.append(html.Div(stack, id=widget.conditional_wrapper_id))
            else:
                rendered.append(stack)
        return rendered

    # ------------------------------------------------------------------
    # Abstract — subclasses implement
    # ------------------------------------------------------------------

    def _render_items(
        self,
        indices: list[int],
        tater_app: Optional[Any] = None,
        doc_id: Optional[str] = None,
        active_value: Optional[str] = None,
    ) -> list[Any]:
        """Return the children list for the items container."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Shared component layout
    # ------------------------------------------------------------------

    def component(self) -> dmc.Stack:
        """Return the Dash component.  Shared by all subclasses."""
        return self._component_with_context()

    def _component_with_context(
        self, tater_app: Optional[Any] = None, doc_id: Optional[str] = None,
        annotations_data: dict | None = None,
    ) -> dmc.Stack:
        """Like component() but pre-populates items from the annotation when available.

        Called directly (with context) when rendering a nested repeater inside
        another repeater's ``_render_item_widgets``, so existing items are shown
        immediately without waiting for a subsequent callback round-trip.
        """
        from tater.ui import value_helpers
        pipe_field = self.field_path.replace(".", "|")
        indices: list[int] = []
        if doc_id:
            ann = (annotations_data or {}).get(doc_id)
            if ann is None and tater_app:
                ann = tater_app.annotations.get(doc_id)
            if ann is not None:
                lst = value_helpers.get_model_value(ann, self.field_path)
                if isinstance(lst, list):
                    indices = list(range(len(lst)))
        store_data = {"indices": indices, "next_index": len(indices)}
        return dmc.Stack([
            dmc.Group([
                dmc.Text(self.label, fw=500, size="sm"),
                dmc.Button(
                    f"Add {self.item_label}",
                    id={"type": "repeater-add", "field": pipe_field},
                    variant="outline",
                    size="xs",
                    leftSection=DashIconify(icon="tabler:plus", width=14),
                ),
            ], justify="space-between"),
            dmc.Text(self.description or "", size="xs", c="dimmed") if self.description else None,
            dmc.Stack(
                self._render_items(indices, tater_app, doc_id, annotations_data=annotations_data),
                id={"type": "repeater-items", "field": pipe_field},
                gap="md",
            ),
            dcc.Store(id={"type": "repeater-store", "field": pipe_field}, data=store_data),
            dcc.Store(id={"type": "repeater-change", "field": pipe_field}, data=0),
        ], gap="sm", mt="md")

    # ------------------------------------------------------------------
    # Callback registration (shared)
    # ------------------------------------------------------------------

    def register_callbacks(self, app: Any) -> None:
        """Register per-widget callbacks for child widgets.

        The list structure (add/delete/load) is handled by the unified MATCH
        callback in ``callbacks.setup_repeater_callbacks``; only register
        callbacks that cannot be expressed generically via MATCH.
        """
        tater_app = getattr(app, "_tater_app", None)
        if not tater_app:
            return

        from tater.widgets.group import GroupWidget

        repeater_ld = self.field_path.replace(".", "|")
        for item_widget_template in self.item_widgets:
            if isinstance(item_widget_template, RepeaterWidget):
                ld = f"{self.field_path}-{item_widget_template.schema_field}"
                item_widget_template.register_list_callbacks(
                    app, ld, [self.field_path, item_widget_template.schema_field]
                )
            elif isinstance(item_widget_template, GroupWidget):
                item_widget_template._register_repeater_conditional_callbacks(
                    app, repeater_ld
                )
            elif isinstance(item_widget_template, ControlWidget):
                if item_widget_template._condition is not None:
                    item_widget_template._register_repeater_conditional_callbacks(
                        app, repeater_ld, self.item_widgets
                    )

    # ------------------------------------------------------------------
    # Nested (repeater-inside-repeater) support (shared)
    # ------------------------------------------------------------------

    def component_in_list(
        self,
        ld: str,
        li: int,
        outer_list_field: str,
        item_field: str,
        tater_app: Optional[Any] = None,
        doc_id: Optional[str] = None,
        annotations_data: dict | None = None,
    ) -> Any:
        """Render this widget when nested inside an outer repeater.

        Uses dict IDs keyed by ``ld`` / ``li`` so a single pre-registered
        MATCH callback can serve all outer rows without runtime re-registration.
        Nested items are always rendered as cards regardless of the subclass.
        """
        from tater.ui import value_helpers
        indices: list[int] = []
        if doc_id:
            ann = (annotations_data or {}).get(doc_id)
            if ann is None and tater_app and doc_id in tater_app.annotations:
                ann = tater_app.annotations[doc_id]
            if ann is not None:
                full_path = f"{outer_list_field}.{li}.{item_field}"
                inner_list = value_helpers.get_model_value(ann, full_path)
                if isinstance(inner_list, list):
                    indices = list(range(len(inner_list)))

        store_data = {"indices": indices, "next_index": len(indices)}
        initial_items = self._render_nested_items(
            indices, ld, li, outer_list_field, item_field, tater_app, doc_id, annotations_data
        )

        return dmc.Stack([
            dmc.Group([
                dmc.Text(self.label, fw=500, size="sm"),
                dmc.Button(
                    f"Add {self.item_label}",
                    id={"type": _NESTED_ADD_TYPE, "ld": ld, "li": li},
                    variant="outline",
                    size="xs",
                    leftSection=DashIconify(icon="tabler:plus", width=14),
                ),
            ], justify="space-between"),
            dmc.Text(self.description, size="xs", c="dimmed") if self.description else None,
            dmc.Stack(
                initial_items,
                id={"type": _NESTED_ITEMS_TYPE, "ld": ld, "li": li},
                gap="md",
            ),
            dcc.Store(
                id={"type": _NESTED_STORE_TYPE, "ld": ld, "li": li},
                data=store_data,
            ),
            dcc.Store(
                id={"type": "nested-repeater-ann-relay", "ld": ld, "li": li},
                data=None,
            ),
        ], gap="sm", mt="md")

    def _render_nested_item_widgets(
        self,
        ld: str,
        outer_li: int,
        inner_index: int,
        outer_list_field: str,
        item_field: str,
        tater_app: Optional[Any] = None,
        doc_id: Optional[str] = None,
        annotations_data: dict | None = None,
    ) -> list[Any]:
        """Render widget components for one inner-list row with nested dict IDs."""
        from tater.widgets.hierarchical_label import HierarchicalLabelWidget
        from tater.widgets.group import GroupWidget
        from tater.ui import value_helpers
        rendered = []
        for template in self.item_widgets:
            if isinstance(template, HierarchicalLabelWidget):
                widget = copy.deepcopy(template)
                widget._finalize_paths(
                    parent_path=f"{outer_list_field}.{outer_li}.{item_field}.{inner_index}"
                )
                if doc_id:
                    ann = (annotations_data or {}).get(doc_id)
                    if ann is None and tater_app and doc_id in tater_app.annotations:
                        ann = tater_app.annotations[doc_id]
                    if ann is not None:
                        value = value_helpers.get_model_value(ann, widget.field_path)
                        if value is not None:
                            widget.default = value
                nested_ld = f"{outer_list_field}-{item_field}-{template.schema_field}"
                rendered.append(dmc.Stack([widget.component()], gap="xs", mt="sm"))
                continue
            nested_ld = f"{outer_list_field}|{item_field}"
            nested_path = f"{outer_li}.{inner_index}"
            parent_path = f"{outer_list_field}.{outer_li}.{item_field}.{inner_index}"

            if isinstance(template, GroupWidget):
                widget = copy.deepcopy(template)
                widget._finalize_paths(parent_path=parent_path)
                widget._set_repeater_context(nested_ld, nested_path)
                _load_defaults_from_annotation(widget, tater_app, doc_id, annotations_data)
                rendered.append(widget.render_field(mt="sm"))
                continue

            if not isinstance(template, ControlWidget):
                continue
            widget = copy.deepcopy(template)
            widget._finalize_paths(parent_path=parent_path)
            if doc_id:
                ann = (annotations_data or {}).get(doc_id)
                if ann is None and tater_app and doc_id in tater_app.annotations:
                    ann = tater_app.annotations[doc_id]
                if ann is not None:
                    value = value_helpers.get_model_value(ann, widget.field_path)
                    if value is not None:
                        widget.default = value

            # Set repeater context for MATCH-based callbacks (2-level nesting).
            widget._set_repeater_context(nested_ld, nested_path)

            comp = widget.component()

            stack = dmc.Stack([comp], gap="xs", mt="sm")
            if widget._condition is not None:
                rendered.append(html.Div(stack, id=widget.conditional_wrapper_id))
            else:
                rendered.append(stack)
        return rendered

    def _render_nested_items(
        self,
        indices: list[int],
        ld: str,
        outer_li: int,
        outer_list_field: str,
        item_field: str,
        tater_app: Optional[Any] = None,
        doc_id: Optional[str] = None,
        annotations_data: dict | None = None,
    ) -> list[Any]:
        """Render inner list cards for the given indices."""
        items = []
        for inner_index in indices:
            inner_widgets = self._render_nested_item_widgets(
                ld, outer_li, inner_index, outer_list_field, item_field, tater_app, doc_id, annotations_data
            )
            items.append(
                dmc.Card([
                    dmc.Group([
                        dmc.Text(f"{self.item_label} {inner_index + 1}", size="xs", c="dimmed"),
                        dmc.ActionIcon(
                            DashIconify(icon="tabler:x", width=14),
                            id={
                                "type": _NESTED_DELETE_TYPE,
                                "ld": ld,
                                "li": outer_li,
                                "inner_li": inner_index,
                            },
                            variant="subtle",
                            color="gray",
                            size="sm",
                        ),
                    ], justify="space-between"),
                    dmc.Stack(inner_widgets, gap="sm"),
                ], withBorder=True, p="md")
            )
        return items

    def register_list_callbacks(
        self,
        app: Any,
        ld: str,
        field_segments: list[str],
    ) -> None:
        """Register conditional visibility callbacks for item widgets nested inside this repeater.

        The add/delete/load callback (``_update_nested_items``) is now handled
        generically by ``setup_nested_repeater_callbacks`` in ``callbacks.py``.
        This method only registers conditional callbacks for nested item widgets
        that have ``_condition`` set.
        """
        tater_app = getattr(app, "_tater_app", None)
        if not tater_app:
            return

        from tater.widgets.group import GroupWidget
        item_widget_templates = self.item_widgets
        nested_ld = "|".join(field_segments)

        for iw_template in item_widget_templates:
            child_segments = field_segments + [iw_template.schema_field]
            child_ld = "-".join(child_segments)
            if isinstance(iw_template, RepeaterWidget):
                iw_template.register_list_callbacks(app, child_ld, child_segments)
            elif isinstance(iw_template, GroupWidget):
                iw_template._register_repeater_conditional_callbacks(app, nested_ld)
            elif isinstance(iw_template, ControlWidget):
                if iw_template._condition is not None:
                    iw_template._register_repeater_conditional_callbacks(
                        app, nested_ld, item_widget_templates
                    )

    # ------------------------------------------------------------------
    # Schema binding (shared)
    # ------------------------------------------------------------------

    def bind_schema(self, model: type) -> None:
        """Resolve the list item model type and bind each item widget template."""
        field_info = _resolve_field_info(model, self.field_path)
        if field_info is None:
            return
        inner = _unwrap_optional(field_info.annotation)
        if typing.get_origin(inner) is not list:
            raise TypeError(
                f"Field '{self.field_path}' has type {inner!r}, but {type(self).__name__} requires a list field."
            )
        item_type = typing.get_args(inner)[0]
        # Fill in widgets for any item model fields not explicitly covered,
        # using the same auto-generation logic as top-level widgets_from_model.
        # Lazy import avoids the circular dependency (model_loader imports repeater).
        if isinstance(item_type, type) and issubclass(item_type, BaseModel):
            from tater.loaders.model_loader import widgets_from_model
            self.item_widgets = widgets_from_model(item_type, overrides=self.item_widgets)
        for item_widget in self.item_widgets:
            # Pre-finalize so GroupWidget children get item-relative field_path
            # values (e.g. "booleans.is_indoor") before bind_schema traverses them.
            item_widget._finalize_paths()
            item_widget.bind_schema(item_type)

    def to_python_type(self) -> type:
        return list


# ---------------------------------------------------------------------------
# Concrete: ListableWidget
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class ListableWidget(RepeaterWidget):
    """Repeatable list rendered as a vertical stack of bordered cards."""

    def _render_items(
        self,
        indices: list[int],
        tater_app: Optional[Any] = None,
        doc_id: Optional[str] = None,
        active_value: Optional[str] = None,
        annotations_data: dict | None = None,
    ) -> list[Any]:
        pipe_field = self.field_path.replace(".", "|")
        items = []
        for index in indices:
            items.append(
                dmc.Card([
                    dmc.Group([
                        dmc.Text(f"{self.item_label} {index + 1}", size="xs", c="dimmed"),
                        dmc.ActionIcon(
                            DashIconify(icon="tabler:x", width=14),
                            id={"type": "repeater-delete", "field": pipe_field, "index": index},
                            variant="subtle",
                            color="gray",
                            size="sm",
                        ),
                    ], justify="space-between"),
                    dmc.Stack(self._render_item_widgets(index, tater_app, doc_id, annotations_data), gap="sm"),
                ], withBorder=True, p="md")
            )
        return items


# ---------------------------------------------------------------------------
# Concrete: TabsWidget
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class TabsWidget(RepeaterWidget):
    """Repeatable list rendered as switchable tabs."""

    def _render_items(
        self,
        indices: list[int],
        tater_app: Optional[Any] = None,
        doc_id: Optional[str] = None,
        active_value: Optional[str] = None,
        annotations_data: dict | None = None,
    ) -> list[Any]:
        if not indices:
            return []

        if active_value is None:
            active_value = str(indices[0])

        pipe_field = self.field_path.replace(".", "|")
        tabs = []
        panels = []
        for index in indices:
            tab_value = str(index)
            tabs.append(
                dmc.TabsTab(
                    dmc.Group([
                        dmc.Text(f"{self.item_label} {index + 1}", size="sm"),
                        html.Span(
                            DashIconify(icon="tabler:x", width=14),
                            id={"type": "repeater-delete", "field": pipe_field, "index": index},
                            n_clicks=0,
                            className="tater-delete-x",
                        ),
                    ], gap="xs"),
                    value=tab_value,
                )
            )
            panels.append(
                dmc.TabsPanel(
                    dmc.Stack(
                        self._render_item_widgets(index, tater_app, doc_id, annotations_data),
                        gap="sm",
                    ),
                    value=tab_value,
                    pt="md",
                )
            )

        return [dmc.Tabs([dmc.TabsList(tabs), *panels], value=active_value)]


# ---------------------------------------------------------------------------
# Concrete: AccordionWidget
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class AccordionWidget(RepeaterWidget):
    """Repeatable list rendered as collapsible accordion sections."""

    def _render_items(
        self,
        indices: list[int],
        tater_app: Optional[Any] = None,
        doc_id: Optional[str] = None,
        active_value: Optional[str] = None,
        annotations_data: dict | None = None,
    ) -> list[Any]:
        if not indices:
            return []

        if active_value is None:
            active_value = str(indices[0])

        pipe_field = self.field_path.replace(".", "|")
        items = []
        for index in indices:
            item_value = str(index)
            items.append(
                dmc.AccordionItem(
                    [
                        dmc.AccordionControl(
                            dmc.Group([
                                dmc.Text(f"{self.item_label} {index + 1}", size="sm"),
                                html.Span(
                                    DashIconify(icon="tabler:x", width=14),
                                    id={"type": "repeater-delete", "field": pipe_field, "index": index},
                                    n_clicks=0,
                                    className="tater-delete-x",
                                ),
                            ], justify="space-between", style={"flex": 1}),
                        ),
                        dmc.AccordionPanel(
                            dmc.Stack(
                                self._render_item_widgets(index, tater_app, doc_id, annotations_data),
                                gap="sm",
                            ),
                        ),
                    ],
                    value=item_value,
                )
            )

        return [dmc.Accordion(items, value=active_value, variant="separated", chevronPosition="left")]
