"""RepeaterWidget, ListableWidget, TabsWidget, and AccordionWidget.

RepeaterWidget is the abstract base for widgets that manage a repeatable list
of sub-form items (a ``List[ItemModel]`` schema field).  Subclasses implement
``_render_items()`` to control how items are presented:

- ``ListableWidget``   — vertical stack of bordered cards (default)
- ``TabsWidget``       — items as switchable tabs
- ``AccordionWidget``  — items as collapsible accordion sections
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Optional, Any

from dash import dcc, html, Input, Output, State, ctx, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc
from dash_iconify import DashIconify

import typing
from .base import ContainerWidget, TaterWidget, ControlWidget, _resolve_field_info, _unwrap_optional

# Dict-ID type strings used for nested (repeater-inside-repeater) components.
_NESTED_ADD_TYPE = "listable-add-list"
_NESTED_DELETE_TYPE = "listable-delete-list"
_NESTED_STORE_TYPE = "listable-store-list"
_NESTED_ITEMS_TYPE = "listable-items-list"


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

    # ------------------------------------------------------------------
    # Component IDs
    # ------------------------------------------------------------------

    def _store_id(self) -> str:
        return f"{self.component_id}-list-store"

    def _items_id(self) -> str:
        return f"{self.component_id}-items"

    def _add_id(self) -> str:
        return f"{self.component_id}-add"

    def _delete_type(self) -> str:
        return f"{self.component_id}-delete"

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
        print(f"[TATER:render] {type(self).__name__}._render_item_widgets: field={self.field_path!r} index={index} doc={doc_id!r}")
        rendered = []
        for template in self.item_widgets:
            widget = copy.deepcopy(template)
            widget._finalize_paths(parent_path=f"{self.field_path}.{index}")

            if tater_app and doc_id and doc_id in tater_app.annotations:
                annotation = tater_app.annotations[doc_id]
                value = tater_app._get_model_value(annotation, widget.field_path)
                if value is not None:
                    widget.default = value

            # Nested RepeaterWidget (ListableWidget, TabsWidget, …)
            if isinstance(template, RepeaterWidget):
                ld = f"{self.field_path}-{template.schema_field}"
                rendered.append(widget.component_in_list(
                    ld, index, self.field_path, template.schema_field, tater_app, doc_id
                ))
                continue

            # HierarchicalLabel uses MATCH-based dict IDs
            if isinstance(template, HierarchicalLabelWidget):
                ld = f"{self.field_path}-{template.schema_field}"
                items = []
                if not widget.renders_own_label:
                    items.append(dmc.Text(widget.label, fw=500, size="sm"))
                items.append(widget.component_in_repeater(ld, str(index)))
                if widget.description:
                    items.append(dmc.Text(widget.description, size="xs", c="dimmed"))
                rendered.append(dmc.Stack(items, gap="xs", mt="sm"))
                continue

            items = []
            if not widget.renders_own_label:
                items.append(dmc.Text(widget.label, fw=500, size="sm"))
            items.append(widget.component())
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
        """Return the children list for the items container.

        ``active_value`` is a hint for tab-style subclasses indicating which
        item should be active after an add/delete operation; card-style
        subclasses may ignore it.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Shared component layout
    # ------------------------------------------------------------------

    def component(self) -> dmc.Stack:
        """Return the Dash component.  Shared by all subclasses."""
        store_data = self._empty_store_data()
        return dmc.Stack([
            dmc.Group([
                dmc.Text(self.label, fw=500, size="sm"),
                dmc.Button(
                    f"Add {self.item_label}",
                    id=self._add_id(),
                    variant="outline",
                    size="xs",
                    leftSection=DashIconify(icon="tabler:plus", width=14),
                ),
            ], justify="space-between"),
            dmc.Text(self.description or "", size="xs", c="dimmed") if self.description else None,
            dmc.Stack(
                self._render_items(store_data["indices"], None, None),
                id=self._items_id(),
                gap="md",
            ),
            dcc.Store(id=self._store_id(), data=store_data),
        ], gap="sm", mt="md")

    # ------------------------------------------------------------------
    # Callback registration (shared)
    # ------------------------------------------------------------------

    def register_callbacks(self, app: Any) -> None:
        """Register callbacks to manage list structure and capture item values."""
        from dash import ALL, Input, Output, State, ctx
        from dash.exceptions import PreventUpdate
        from pydantic import BaseModel

        tater_app = getattr(app, "_tater_app", None)
        print(f"[TATER:register] {type(self).__name__}.register_callbacks: field={self.field_path!r} store={self._store_id()!r}")

        add_id = self._add_id()
        items_id = self._items_id()
        store_id = self._store_id()
        delete_type = self._delete_type()
        field_path = self.field_path
        item_widget_templates = self.item_widgets

        def _sync_annotation_add(doc_id: str, new_index: int) -> None:
            annotation = tater_app.annotations.get(doc_id)
            if annotation is None:
                return
            extended = False
            for iw in item_widget_templates:
                if isinstance(iw, ContainerWidget):
                    # Containers (ListableWidget, GroupWidget, …) have no empty_value;
                    # their fields are already initialised to defaults by create_list_item.
                    extended = True
                    continue
                try:
                    tater_app._set_model_value(
                        annotation,
                        f"{field_path}.{new_index}.{iw.schema_field}",
                        iw.empty_value,
                    )
                    extended = True
                except Exception:
                    pass
            if not extended:
                try:
                    tater_app._set_model_value(annotation, f"{field_path}.{new_index}", None)
                except Exception:
                    pass
            tater_app._save_annotations_to_file(doc_id=doc_id)

        def _sync_annotation_delete(doc_id: str, del_position: int) -> None:
            annotation = tater_app.annotations.get(doc_id)
            if annotation is None:
                return
            current_list = tater_app._get_model_value(annotation, field_path)
            if isinstance(current_list, list) and del_position < len(current_list):
                current_list.pop(del_position)
            tater_app._save_annotations_to_file(doc_id=doc_id)

        @app.callback(
            [Output(store_id, "data"), Output(items_id, "children")],
            [Input(add_id, "n_clicks"),
             Input({"type": delete_type, "index": ALL}, "n_clicks"),
             Input("current-doc-id", "data")],
            State(store_id, "data"),
        )
        def _update_items(add_clicks, delete_clicks, doc_id, store_data):
            if not ctx.triggered_id or ctx.triggered_id == "current-doc-id":
                indices_set = set()
                if tater_app and doc_id and doc_id in tater_app.annotations:
                    doc_annotations = tater_app.annotations[doc_id]
                    if isinstance(doc_annotations, BaseModel):
                        try:
                            list_field = getattr(doc_annotations, field_path, None)
                            if isinstance(list_field, list):
                                indices_set = set(range(len(list_field)))
                        except AttributeError:
                            pass
                    else:
                        prefix = f"{field_path}."
                        for key in doc_annotations.keys():
                            if key.startswith(prefix):
                                rest = key[len(prefix):]
                                index_str = rest.split('.')[0]
                                try:
                                    indices_set.add(int(index_str))
                                except ValueError:
                                    pass
                indices = sorted(indices_set)
                store_data = {"indices": indices, "next_index": len(indices)}
                return store_data, self._render_items(indices, tater_app, doc_id)

            if not ctx.triggered or not ctx.triggered[0].get("value"):
                raise PreventUpdate

            if store_data is None:
                store_data = self._empty_store_data()

            indices = list(store_data.get("indices", []))
            active_value = None

            if ctx.triggered_id == add_id:
                new_index = len(indices)
                indices = list(range(new_index + 1))
                active_value = str(new_index)
                if tater_app and doc_id and doc_id in tater_app.annotations:
                    _sync_annotation_add(doc_id, new_index)
            elif isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get("type") == delete_type:
                delete_index = ctx.triggered_id.get("index")
                if delete_index in indices:
                    del_position = indices.index(delete_index)
                    if tater_app and doc_id and doc_id in tater_app.annotations:
                        _sync_annotation_delete(doc_id, del_position)
                    indices = list(range(len(indices) - 1))
                    active_value = str(indices[0]) if indices else None

            new_data = {"indices": indices, "next_index": len(indices)}
            return new_data, self._render_items(
                indices, tater_app, doc_id, active_value=active_value
            )

        if tater_app:
            from tater.widgets.hierarchical_label import HierarchicalLabelWidget
            for item_widget_template in self.item_widgets:
                if isinstance(item_widget_template, HierarchicalLabelWidget):
                    ld = f"{self.field_path}-{item_widget_template.schema_field}"
                    item_widget_template.register_repeater_callbacks(
                        app, ld, [self.field_path, item_widget_template.schema_field]
                    )
                elif isinstance(item_widget_template, RepeaterWidget):
                    ld = f"{self.field_path}-{item_widget_template.schema_field}"
                    item_widget_template.register_list_callbacks(
                        app, ld, [self.field_path, item_widget_template.schema_field]
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
        from tater.widgets.span import SpanAnnotationWidget
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
                items.append(widget.component_in_repeater(nested_ld, f"{outer_li}.{inner_index}"))
                if widget.description:
                    items.append(dmc.Text(widget.description, size="xs", c="dimmed"))
                rendered.append(dmc.Stack(items, gap="xs", mt="sm"))
                continue
            if isinstance(template, SpanAnnotationWidget):
                widget = copy.deepcopy(template)
                widget._finalize_paths(
                    parent_path=f"{outer_list_field}.{outer_li}.{item_field}.{inner_index}"
                )
                items = []
                if widget.label:
                    items.append(dmc.Text(widget.label, fw=500, size="sm"))
                items.append(widget.component())
                if widget.description:
                    items.append(dmc.Text(widget.description, size="xs", c="dimmed"))
                rendered.append(dmc.Stack(items, gap="xs", mt="sm"))
                continue
            if not isinstance(template, ControlWidget):
                continue
            widget = copy.deepcopy(template)
            widget._finalize_paths(
                parent_path=f"{outer_list_field}.{outer_li}.{item_field}.{inner_index}"
            )
            if tater_app and doc_id and doc_id in tater_app.annotations:
                annotation = tater_app.annotations[doc_id]
                value = tater_app._get_model_value(annotation, widget.field_path)
                if value is not None:
                    widget.default = value

            comp = widget.component()

            items = []
            if not widget.renders_own_label:
                items.append(dmc.Text(widget.label, fw=500, size="sm"))
            items.append(comp)
            if widget.description:
                items.append(dmc.Text(widget.description, size="xs", c="dimmed"))
            rendered.append(dmc.Stack(items, gap="xs", mt="sm"))
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
            from tater.widgets.hierarchical_label import HierarchicalLabelWidget
            for iw_template in item_widget_templates:
                child_segments = field_segments + [iw_template.schema_field]
                child_ld = "-".join(child_segments)
                if isinstance(iw_template, HierarchicalLabelWidget):
                    iw_template.register_repeater_callbacks(app, child_ld, child_segments)
                elif isinstance(iw_template, RepeaterWidget):
                    iw_template.register_list_callbacks(app, child_ld, child_segments)

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
        items = []
        for index in indices:
            items.append(
                dmc.Card([
                    dmc.Group([
                        dmc.Text(f"{self.item_label} {index + 1}", size="xs", c="dimmed"),
                        dmc.ActionIcon(
                            DashIconify(icon="tabler:x", width=14),
                            id={"type": self._delete_type(), "index": index},
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
                            id={"type": self._delete_type(), "index": index},
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
                                    id={"type": self._delete_type(), "index": index},
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
