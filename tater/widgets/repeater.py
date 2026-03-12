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
        """Render widgets for a single list item."""
        print(f"[TATER:render] {type(self).__name__}._render_item_widgets: field={self.field_path!r} index={index} doc={doc_id!r}")

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

            items = []
            if not widget.renders_own_label:
                items.append(dmc.Text(widget.label, fw=500, size="sm"))
            items.append(comp)
            if widget.description:
                items.append(dmc.Text(widget.description, size="xs", c="dimmed"))
            rendered.append(dmc.Stack(items, gap="xs", mt="sm"))
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
        print(f"[TATER:create] {type(self).__name__}.bind_schema: field={self.field_path!r} item_type={item_type.__name__} templates={[w.schema_field for w in self.item_widgets]}")
        for item_widget in self.item_widgets:
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
