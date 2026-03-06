"""ListableWidget for repeatable groups of fields."""
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

# Dict-ID type strings used for nested (list-in-list) components.
_NESTED_ADD_TYPE = "listable-add-list"
_NESTED_DELETE_TYPE = "listable-delete-list"
_NESTED_STORE_TYPE = "listable-store-list"
_NESTED_ITEMS_TYPE = "listable-items-list"
_NESTED_VAL_TYPE = "listable-val-list"


@dataclass(eq=False)
class ListableWidget(ContainerWidget):
    """Widget for managing a list of repeated field groups."""

    item_widgets: list[TaterWidget] = field(kw_only=True, default_factory=list)
    item_label: str = field(kw_only=True, default="Item")

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

    def _render_item_widgets(self, index: int, tater_app: Optional[Any] = None, doc_id: Optional[str] = None) -> list[Any]:
        """Render widgets for a single list item with pattern-matching IDs."""
        from tater.widgets.hierarchical_label import HierarchicalLabelWidget
        rendered = []
        for template in self.item_widgets:
            widget = copy.deepcopy(template)
            widget._finalize_paths(parent_path=f"{self.field_path}.{index}")

            # Set initial value from annotations if available
            if tater_app and doc_id and doc_id in tater_app.annotations:
                annotation = tater_app.annotations[doc_id]
                field_path = widget.field_path
                value = tater_app._get_model_value(annotation, field_path)
                if value is not None:
                    widget.default = value

            # Nested ListableWidget — render with dict IDs for MATCH-based callbacks
            if isinstance(template, ListableWidget):
                ld = f"{self.field_path}-{template.schema_field}"
                rendered.append(widget.component_in_list(
                    ld, index, self.field_path, template.schema_field, tater_app, doc_id
                ))
                continue

            # HierarchicalLabel uses list-mode rendering with MATCH-based dict IDs
            if isinstance(template, HierarchicalLabelWidget):
                ld = f"{self.field_path}-{template.schema_field}"
                items = []
                if not widget.renders_own_label:
                    items.append(dmc.Text(widget.label, fw=500, size="sm"))
                items.append(widget.component_in_list(ld, index))
                if widget.description:
                    items.append(dmc.Text(widget.description, size="xs", c="dimmed"))
                rendered.append(dmc.Stack(items, gap="xs", mt="sm"))
                continue

            # Override the widget's component to use a dictionary ID for pattern-matching
            original_component = widget.component
            pattern_type = f"{self.component_id}-item"

            def make_pattern_component(w, pt):
                """Create a component with a pattern-matching ID."""
                comp = original_component()
                comp.id = {
                    "type": pt,
                    "field": w.schema_field,
                    "index": index,
                }
                return comp

            # Replace the component method
            widget.component = lambda w=widget, pt=pattern_type: make_pattern_component(w, pt)

            items = []
            if not widget.renders_own_label:
                items.append(dmc.Text(widget.label, fw=500, size="sm"))
            items.append(widget.component())
            if widget.description:
                items.append(dmc.Text(widget.description, size="xs", c="dimmed"))
            rendered.append(dmc.Stack(items, gap="xs", mt="sm"))
        return rendered

    def _render_items(self, indices: list[int], tater_app: Optional[Any] = None, doc_id: Optional[str] = None) -> list[Any]:
        """Render list items."""
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

    def component(self) -> dmc.Stack:
        """Return Dash component for the list widget."""
        store_data = self._empty_store_data()
        return dmc.Stack([
            dmc.Group([
                dmc.Text(self.label, fw=500, size="sm"),
                dmc.Button(f"Add {self.item_label}", id=self._add_id(), variant="outline", size="xs",
                           leftSection=DashIconify(icon="tabler:plus", width=14)),
            ], justify="space-between"),
            dmc.Text(self.description or "", size="xs", c="dimmed") if self.description else None,
            dmc.Stack(self._render_items(store_data["indices"], None, None), id=self._items_id(), gap="md"),
            dcc.Store(id=self._store_id(), data=store_data),
        ], gap="sm", mt="md")

    # ------------------------------------------------------------------
    # Nested (list-in-list) rendering
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
        """Render this ListableWidget when it is nested inside an outer list.

        Uses dict IDs keyed by ``ld`` (list discriminator) and ``li`` (outer
        list index) so that a single pre-registered MATCH callback can serve
        all outer-list rows without needing to be re-registered at runtime.
        """
        # Pre-populate inner items from annotations if available
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
        """Render widget components for one inner-list row, assigning nested dict IDs."""
        rendered = []
        for template in self.item_widgets:
            if not isinstance(template, ControlWidget):
                # Only ControlWidgets are supported inside a nested list for now.
                continue
            widget = copy.deepcopy(template)
            widget._finalize_paths(
                parent_path=f"{outer_list_field}.{outer_li}.{item_field}.{inner_index}"
            )

            # Load initial value from annotations
            if tater_app and doc_id and doc_id in tater_app.annotations:
                annotation = tater_app.annotations[doc_id]
                value = tater_app._get_model_value(annotation, widget.field_path)
                if value is not None:
                    widget.default = value

            comp = widget.component()
            comp.id = {
                "type": _NESTED_VAL_TYPE,
                "ld": ld,
                "li": outer_li,
                "field": template.schema_field,
                "inner_li": inner_index,
            }

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
        outer_list_field: str,
        item_field: str,
    ) -> None:
        """Register MATCH-based callbacks for this ListableWidget nested inside another list.

        ``ld`` (list discriminator) uniquely identifies this inner list across all
        outer-list rows.  ``li`` (outer list index) is the MATCH dimension — Dash
        fires the callbacks once per outer row.
        """
        from dash import ALL, MATCH, Input, Output, State, ctx
        from dash.exceptions import PreventUpdate

        tater_app = getattr(app, "_tater_app", None)
        item_widget_templates = self.item_widgets

        @app.callback(
            [
                Output({"type": _NESTED_STORE_TYPE, "ld": ld, "li": MATCH}, "data"),
                Output({"type": _NESTED_ITEMS_TYPE, "ld": ld, "li": MATCH}, "children"),
            ],
            [
                Input({"type": _NESTED_ADD_TYPE, "ld": ld, "li": MATCH}, "n_clicks"),
                Input({"type": _NESTED_DELETE_TYPE, "ld": ld, "li": MATCH, "inner_li": ALL}, "n_clicks"),
            ],
            [
                State({"type": _NESTED_STORE_TYPE, "ld": ld, "li": MATCH}, "data"),
                State("current-doc-id", "data"),
            ],
        )
        def _update_nested_items(add_clicks, delete_clicks, store_data, doc_id):
            # Get the outer list index from the MATCH context
            outer_li = ctx.outputs_list[0]["id"]["li"]

            # Guard against phantom fires (n_clicks=None on mount)
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
                        if not isinstance(iw, ControlWidget):
                            continue
                        try:
                            empty_val = iw.empty_value if hasattr(iw, "empty_value") else None
                            tater_app._set_model_value(
                                annotation,
                                f"{outer_list_field}.{outer_li}.{item_field}.{new_index}.{iw.schema_field}",
                                empty_val,
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
            for iw_template in item_widget_templates:
                if isinstance(iw_template, ControlWidget):
                    self._register_nested_pattern_callback(
                        app, tater_app, ld, outer_list_field, item_field, iw_template
                    )

    def _register_nested_pattern_callback(
        self,
        app: Any,
        tater_app: Any,
        ld: str,
        outer_list_field: str,
        item_field: str,
        iw_template: TaterWidget,
    ) -> None:
        """Register a value-capture callback for one ControlWidget field in a nested list.

        Uses MATCH on ``li`` (outer index) and ALL on ``inner_li`` so a single
        callback handles all inner rows for a given outer row.
        """
        from dash import ALL, MATCH, Input, Output, State, ctx

        field_name = iw_template.schema_field
        value_prop = iw_template.value_prop

        @app.callback(
            Output(
                {"type": _NESTED_VAL_TYPE, "ld": ld, "li": MATCH, "field": field_name, "inner_li": ALL},
                "id",
            ),
            Input(
                {"type": _NESTED_VAL_TYPE, "ld": ld, "li": MATCH, "field": field_name, "inner_li": ALL},
                value_prop,
            ),
            State(
                {"type": _NESTED_VAL_TYPE, "ld": ld, "li": MATCH, "field": field_name, "inner_li": ALL},
                "id",
            ),
            State("current-doc-id", "data"),
            prevent_initial_call=True,
        )
        def capture_nested_values(all_values, all_ids, doc_id):
            if not doc_id or not ctx.triggered:
                return all_ids if all_ids else []

            triggered_prop = ctx.triggered[0]["prop_id"]
            if "." not in triggered_prop:
                return all_ids if all_ids else []

            triggered_id_str = triggered_prop.split(".")[0]
            try:
                triggered_id = json.loads(triggered_id_str)
            except (json.JSONDecodeError, ValueError):
                return all_ids if all_ids else []

            if not isinstance(triggered_id, dict):
                return all_ids if all_ids else []

            outer_li = triggered_id.get("li")
            inner_li = triggered_id.get("inner_li")
            f = triggered_id.get("field")

            if outer_li is None or inner_li is None or f is None:
                return all_ids if all_ids else []

            full_field_path = f"{outer_list_field}.{outer_li}.{item_field}.{inner_li}.{f}"

            for i, widget_id in enumerate(all_ids or []):
                if isinstance(widget_id, dict) and widget_id.get("inner_li") == inner_li:
                    if i < len(all_values):
                        value = all_values[i]
                        if tater_app.schema_model:
                            if doc_id not in tater_app.annotations:
                                tater_app.annotations[doc_id] = tater_app.schema_model()
                            model = tater_app.annotations[doc_id]
                            tater_app._set_model_value(model, full_field_path, value)
                    break

            return all_ids if all_ids else []

    # ------------------------------------------------------------------
    # Top-level callback registration
    # ------------------------------------------------------------------

    def register_callbacks(self, app: Any) -> None:
        """Register callbacks to manage list structure and capture item values."""
        from dash import ALL, Input, Output, State, ctx
        from dash.exceptions import PreventUpdate
        from pydantic import BaseModel

        tater_app = getattr(app, "_tater_app", None)

        add_id = self._add_id()
        items_id = self._items_id()
        store_id = self._store_id()
        delete_type = self._delete_type()
        field_path = self.field_path
        item_widget_templates = self.item_widgets

        def _sync_annotation_add(doc_id: str, new_index: int) -> None:
            """Append an empty item to the annotation list at new_index."""
            annotation = tater_app.annotations.get(doc_id)
            if annotation is None:
                return
            extended = False
            for iw in item_widget_templates:
                try:
                    empty_val = iw.empty_value if hasattr(iw, "empty_value") else None
                    tater_app._set_model_value(
                        annotation,
                        f"{field_path}.{new_index}.{iw.schema_field}",
                        empty_val,
                    )
                    extended = True
                except Exception:
                    pass
            if not extended:
                # Fallback: extend the list directly with None
                try:
                    tater_app._set_model_value(annotation, f"{field_path}.{new_index}", None)
                except Exception:
                    pass
            tater_app._save_annotations_to_file(doc_id=doc_id)

        def _sync_annotation_delete(doc_id: str, del_position: int) -> None:
            """Remove the item at del_position from the annotation list."""
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
            # None on initial page load — treat as doc-id load
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

            # Guard against phantom pattern-matching fires (n_clicks=None on mount)
            if not ctx.triggered or not ctx.triggered[0].get("value"):
                raise PreventUpdate

            if store_data is None:
                store_data = self._empty_store_data()

            indices = list(store_data.get("indices", []))

            if ctx.triggered_id == add_id:
                # Use the current count as the new sequential position
                new_index = len(indices)
                indices = list(range(new_index + 1))
                if tater_app and doc_id and doc_id in tater_app.annotations:
                    _sync_annotation_add(doc_id, new_index)
            elif isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get("type") == delete_type:
                delete_index = ctx.triggered_id.get("index")
                if delete_index in indices:
                    del_position = indices.index(delete_index)
                    if tater_app and doc_id and doc_id in tater_app.annotations:
                        _sync_annotation_delete(doc_id, del_position)
                    # Re-number remaining items sequentially
                    indices = list(range(len(indices) - 1))

            new_data = {"indices": indices, "next_index": len(indices)}
            return new_data, self._render_items(indices, tater_app, doc_id)

        if tater_app:
            from tater.widgets.hierarchical_label import HierarchicalLabelWidget
            for item_widget_template in self.item_widgets:
                if isinstance(item_widget_template, ControlWidget):
                    self._register_item_pattern_callback(item_widget_template, app, tater_app)
                elif isinstance(item_widget_template, HierarchicalLabelWidget):
                    ld = f"{self.field_path}-{item_widget_template.schema_field}"
                    item_widget_template.register_list_callbacks(
                        app, ld, self.field_path, item_widget_template.schema_field
                    )
                elif isinstance(item_widget_template, ListableWidget):
                    ld = f"{self.field_path}-{item_widget_template.schema_field}"
                    item_widget_template.register_list_callbacks(
                        app, ld, self.field_path, item_widget_template.schema_field
                    )

    def _register_item_pattern_callback(self, item_widget_template: TaterWidget, app: Any, tater_app: Any) -> None:
        """Register a single pattern-matching callback that handles all items for this widget type."""
        from dash import ALL, Input, Output, State, MATCH

        pattern_type = f"{self.component_id}-item"
        field_name = item_widget_template.schema_field
        value_prop = item_widget_template.value_prop

        @app.callback(
            Output({"type": pattern_type, "field": field_name, "index": ALL}, "id"),
            Input({"type": pattern_type, "field": field_name, "index": ALL}, value_prop),
            State({"type": pattern_type, "field": field_name, "index": ALL}, "id"),
            State("current-doc-id", "data"),
            prevent_initial_call=True
        )
        def capture_pattern_values(all_values, all_ids, doc_id):
            if not doc_id or not ctx.triggered:
                return all_ids if all_ids else []

            triggered_prop = ctx.triggered[0]["prop_id"]
            if "." not in triggered_prop:
                return all_ids if all_ids else []

            triggered_id_str = triggered_prop.split(".")[0]
            try:
                triggered_id = json.loads(triggered_id_str)
            except (json.JSONDecodeError, ValueError):
                return all_ids if all_ids else []

            if not isinstance(triggered_id, dict):
                return all_ids if all_ids else []

            index = triggered_id.get("index")
            field = triggered_id.get("field")

            if index is None or field is None:
                return all_ids if all_ids else []

            full_field_path = f"{self.field_path}.{index}.{field}"

            for i, widget_id in enumerate(all_ids or []):
                if isinstance(widget_id, dict) and widget_id.get("index") == index:
                    if i < len(all_values):
                        value = all_values[i]

                        if tater_app.schema_model:
                            if doc_id not in tater_app.annotations:
                                tater_app.annotations[doc_id] = tater_app.schema_model()

                            model = tater_app.annotations[doc_id]
                            tater_app._set_model_value(model, full_field_path, value)
                    break

            return all_ids if all_ids else []

    def bind_schema(self, model: type) -> None:
        """Resolve the list item model type and bind each item widget template against it."""
        field_info = _resolve_field_info(model, self.field_path)
        if field_info is None:
            return
        inner = _unwrap_optional(field_info.annotation)
        if typing.get_origin(inner) is not list:
            return
        item_type = typing.get_args(inner)[0]
        for item_widget in self.item_widgets:
            item_widget.bind_schema(item_type)

    def to_python_type(self) -> type:
        return list
