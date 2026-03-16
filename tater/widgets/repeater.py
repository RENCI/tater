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
from .base import ContainerWidget, TaterWidget, ControlWidget, _resolve_field_info, _unwrap_optional

# Component-type strings for nested (repeater-inside-repeater) IDs.
_NESTED_ADD_TYPE    = "nested-repeater-add"
_NESTED_DELETE_TYPE = "nested-repeater-delete"
_NESTED_STORE_TYPE  = "nested-repeater-store"
_NESTED_ITEMS_TYPE  = "nested-repeater-items"


def _load_defaults_from_annotation(widget: Any, tater_app: Any, doc_id: str) -> None:
    """Recursively set annotation values as widget defaults for ControlWidget descendants.

    Called before rendering a GroupWidget inside a repeater so components are
    initialised with the stored value instead of schema defaults, avoiding a
    visible flash of incorrect values before the load_values/load_checked
    callbacks fire.
    """
    from tater.widgets.group import GroupWidget
    if isinstance(widget, GroupWidget):
        for child in widget.children:
            _load_defaults_from_annotation(child, tater_app, doc_id)
    elif isinstance(widget, ControlWidget):
        if tater_app and doc_id and doc_id in tater_app.annotations:
            annotation = tater_app.annotations[doc_id]
            value = tater_app._get_model_value(annotation, widget.field_path)
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
        self, index: int, tater_app: Optional[Any] = None, doc_id: Optional[str] = None
    ) -> list[Any]:
        """Render widgets for a single list item with pattern-matching IDs."""
        from tater.widgets.hierarchical_label import HierarchicalLabelWidget
        from tater.widgets.span import SpanAnnotationWidget
        from tater.widgets.group import GroupWidget
        rendered = []
        for template in self.item_widgets:
            widget = copy.deepcopy(template)
            widget._finalize_paths(parent_path=f"{self.field_path}.{index}")

            # For nested RepeaterWidgets use _component_with_context so initial
            # items are pre-populated from the annotation rather than empty.
            if isinstance(template, RepeaterWidget):
                comp = widget._component_with_context(tater_app, doc_id)
            else:
                comp = widget.component()

            # GroupWidget: propagate repeater context to children so their
            # schema_ids use MATCH-compatible ld/path/tf keys, then render normally.
            if isinstance(template, GroupWidget):
                widget._set_repeater_context(self.field_path.replace(".", "|"), str(index))
                _load_defaults_from_annotation(widget, tater_app, doc_id)
                rendered.append(widget.render_field(mt="sm"))
                continue

            # Set repeater context on ControlWidget so schema_id uses MATCH-
            # compatible ld/path keys instead of the full pipe-encoded path.
            if isinstance(template, ControlWidget):
                widget._set_repeater_context(self.field_path.replace(".", "|"), str(index))

            items = []
            if not widget.renders_own_label:
                items.append(dmc.Text(widget.label, fw=500, size="sm"))
            items.append(comp)
            if widget.description and not widget.renders_own_label:
                items.append(dmc.Text(widget.description, size="xs", c="dimmed"))
            stack = dmc.Stack(items, gap="xs", mt="sm")
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
        self, tater_app: Optional[Any] = None, doc_id: Optional[str] = None
    ) -> dmc.Stack:
        """Like component() but pre-populates items from the annotation when available.

        Called directly (with context) when rendering a nested repeater inside
        another repeater's ``_render_item_widgets``, so existing items are shown
        immediately without waiting for a subsequent callback round-trip.
        """
        from tater.ui import value_helpers
        pipe_field = self.field_path.replace(".", "|")
        indices: list[int] = []
        if tater_app and doc_id:
            annotation = tater_app.annotations.get(doc_id)
            if annotation is not None:
                lst = value_helpers.get_model_value(annotation, self.field_path)
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
                self._render_items(indices, tater_app, doc_id),
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
    ) -> Any:
        """Render this widget when nested inside an outer repeater.

        Uses dict IDs keyed by ``ld`` / ``li`` so a single pre-registered
        MATCH callback can serve all outer rows without runtime re-registration.
        Nested items are always rendered as cards regardless of the subclass.
        """
        indices: list[int] = []
        if tater_app and doc_id and doc_id in tater_app.annotations:
            annotation = tater_app.annotations[doc_id]
            full_path = f"{outer_list_field}.{li}.{item_field}"
            inner_list = tater_app._get_model_value(annotation, full_path)
            if isinstance(inner_list, list):
                indices = list(range(len(inner_list)))

        store_data = {"indices": indices, "next_index": len(indices)}
        initial_items = self._render_nested_items(
            indices, ld, li, outer_list_field, item_field, tater_app, doc_id
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
    ) -> list[Any]:
        """Render widget components for one inner-list row with nested dict IDs."""
        from tater.widgets.hierarchical_label import HierarchicalLabelWidget
        from tater.widgets.group import GroupWidget
        rendered = []
        for template in self.item_widgets:
            if isinstance(template, HierarchicalLabelWidget):
                widget = copy.deepcopy(template)
                widget._finalize_paths(
                    parent_path=f"{outer_list_field}.{outer_li}.{item_field}.{inner_index}"
                )
                if tater_app and doc_id and doc_id in tater_app.annotations:
                    annotation = tater_app.annotations[doc_id]
                    value = tater_app._get_model_value(annotation, widget.field_path)
                    if value is not None:
                        widget.default = value
                nested_ld = f"{outer_list_field}-{item_field}-{template.schema_field}"
                items = []
                if widget.label:
                    items.append(dmc.Text(widget.label, fw=500, size="sm"))
                items.append(widget.component())
                if widget.description:
                    items.append(dmc.Text(widget.description, size="xs", c="dimmed"))
                rendered.append(dmc.Stack(items, gap="xs", mt="sm"))
                continue
            nested_ld = f"{outer_list_field}|{item_field}"
            nested_path = f"{outer_li}.{inner_index}"
            parent_path = f"{outer_list_field}.{outer_li}.{item_field}.{inner_index}"

            if isinstance(template, GroupWidget):
                widget = copy.deepcopy(template)
                widget._finalize_paths(parent_path=parent_path)
                widget._set_repeater_context(nested_ld, nested_path)
                _load_defaults_from_annotation(widget, tater_app, doc_id)
                rendered.append(widget.render_field(mt="sm"))
                continue

            if not isinstance(template, ControlWidget):
                continue
            widget = copy.deepcopy(template)
            widget._finalize_paths(parent_path=parent_path)
            if tater_app and doc_id and doc_id in tater_app.annotations:
                annotation = tater_app.annotations[doc_id]
                value = tater_app._get_model_value(annotation, widget.field_path)
                if value is not None:
                    widget.default = value

            # Set repeater context for MATCH-based callbacks (2-level nesting).
            widget._set_repeater_context(nested_ld, nested_path)

            comp = widget.component()

            items = []
            if not widget.renders_own_label:
                items.append(dmc.Text(widget.label, fw=500, size="sm"))
            items.append(comp)
            if widget.description:
                items.append(dmc.Text(widget.description, size="xs", c="dimmed"))
            stack = dmc.Stack(items, gap="xs", mt="sm")
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
    ) -> list[Any]:
        """Render inner list cards for the given indices."""
        items = []
        for inner_index in indices:
            inner_widgets = self._render_nested_item_widgets(
                ld, outer_li, inner_index, outer_list_field, item_field, tater_app, doc_id
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
        """Register MATCH-based callbacks for this widget when nested inside another repeater.

        ``field_segments`` is the ordered list of field names from the outermost list down
        to this repeater's own field, e.g. ``["findings", "annotations"]`` when this
        repeater lives at ``findings[i].annotations``.  Passing a longer list here is what
        enables arbitrary-depth nesting: each recursive call appends one more segment.
        """
        from dash import ALL, MATCH, Input, Output, State, ctx
        from dash.exceptions import PreventUpdate

        # The two names needed for the 2-level MATCH callback body.
        outer_list_field = field_segments[0]
        item_field = field_segments[-1]

        tater_app = getattr(app, "_tater_app", None)
        item_widget_templates = self.item_widgets

        @app.callback(
            [
                Output({"type": _NESTED_STORE_TYPE, "ld": ld, "li": MATCH}, "data"),
                Output({"type": _NESTED_ITEMS_TYPE, "ld": ld, "li": MATCH}, "children"),
            ],
            [
                Input({"type": _NESTED_ADD_TYPE, "ld": ld, "li": MATCH}, "n_clicks"),
                Input(
                    {"type": _NESTED_DELETE_TYPE, "ld": ld, "li": MATCH, "inner_li": ALL},
                    "n_clicks",
                ),
            ],
            [
                State({"type": _NESTED_STORE_TYPE, "ld": ld, "li": MATCH}, "data"),
                State("current-doc-id", "data"),
            ],
        )
        def _update_nested_items(add_clicks, delete_clicks, store_data, doc_id):
            outer_li = ctx.outputs_list[0]["id"]["li"]

            if not ctx.triggered or not ctx.triggered[0].get("value"):
                raise PreventUpdate

            if store_data is None:
                store_data = {"indices": [], "next_index": 0}

            indices = list(store_data.get("indices", []))

            if isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get("type") == _NESTED_ADD_TYPE:
                new_index = len(indices)
                indices = list(range(new_index + 1))
                if tater_app and doc_id and doc_id in tater_app.annotations:
                    annotation = tater_app.annotations[doc_id]
                    for iw in item_widget_templates:
                        if isinstance(iw, ContainerWidget):
                            continue
                        if not isinstance(iw, ControlWidget):
                            continue
                        try:
                            tater_app._set_model_value(
                                annotation,
                                f"{outer_list_field}.{outer_li}.{item_field}.{new_index}.{iw.schema_field}",
                                iw.empty_value,
                            )
                        except Exception:
                            pass
                    tater_app._save_annotations_to_file(doc_id=doc_id)

            elif isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get("type") == _NESTED_DELETE_TYPE:
                inner_li_del = ctx.triggered_id.get("inner_li")
                if inner_li_del in indices:
                    del_position = indices.index(inner_li_del)
                    if tater_app and doc_id and doc_id in tater_app.annotations:
                        annotation = tater_app.annotations[doc_id]
                        full_path = f"{outer_list_field}.{outer_li}.{item_field}"
                        inner_list = tater_app._get_model_value(annotation, full_path)
                        if isinstance(inner_list, list) and del_position < len(inner_list):
                            inner_list.pop(del_position)
                        tater_app._save_annotations_to_file(doc_id=doc_id)
                    indices = list(range(len(indices) - 1))

            new_data = {"indices": indices, "next_index": len(indices)}
            return new_data, self._render_nested_items(
                indices, ld, outer_li, outer_list_field, item_field, tater_app, doc_id
            )

        if tater_app:
            from tater.widgets.group import GroupWidget
            # ld for ControlWidget conditional callbacks: pipe-join the list fields.
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
                    dmc.Stack(self._render_item_widgets(index, tater_app, doc_id), gap="sm"),
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
                        self._render_item_widgets(index, tater_app, doc_id),
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
                                self._render_item_widgets(index, tater_app, doc_id),
                                gap="sm",
                            ),
                        ),
                    ],
                    value=item_value,
                )
            )

        return [dmc.Accordion(items, value=active_value, variant="separated", chevronPosition="left")]
