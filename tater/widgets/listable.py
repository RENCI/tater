"""ListableWidget for repeatable groups of fields."""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Optional, Any

from dash import dcc, html, Input, Output, State, ctx, ALL
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc
from dash_iconify import DashIconify

import typing
from .base import ContainerWidget, TaterWidget, _resolve_field_info, _unwrap_optional


@dataclass(eq=False)
class ListableWidget(ContainerWidget):
    """Widget for managing a list of repeated field groups."""

    item_widgets: list[TaterWidget] = field(kw_only=True, default_factory=list)
    add_label: str = field(kw_only=True, default="Add")
    delete_label: str = field(kw_only=True, default="Delete")
    initial_count: int = field(kw_only=True, default=1)

    def __post_init__(self) -> None:
        self.initial_count = max(0, self.initial_count)

    def _store_id(self) -> str:
        return f"{self.component_id}-list-store"

    def _items_id(self) -> str:
        return f"{self.component_id}-items"

    def _add_id(self) -> str:
        return f"{self.component_id}-add"

    def _delete_type(self) -> str:
        return f"{self.component_id}-delete"

    def _initial_store_data(self) -> dict[str, Any]:
        return {
            "indices": list(range(self.initial_count)),
            "next_index": self.initial_count,
        }

    def _render_item_widgets(self, index: int, tater_app: Optional[Any] = None, doc_id: Optional[str] = None) -> list[Any]:
        """Render widgets for a single list item with pattern-matching IDs."""
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

            rendered.append(
                dmc.Stack([
                    dmc.Text(widget.label, fw=500, size="sm"),
                    widget.component(),
                    dmc.Text(widget.description or "", size="xs", c="dimmed") if widget.description else None,
                ], gap="xs", mt="sm")
            )
        return rendered

    def _render_items(self, indices: list[int], tater_app: Optional[Any] = None, doc_id: Optional[str] = None) -> list[Any]:
        """Render list items."""
        items = []
        for index in indices:
            items.append(
                dmc.Card([
                    dmc.Group([
                        dmc.Text(f"Item {index + 1}", fw=500, size="sm"),
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
        store_data = self._initial_store_data()
        return dmc.Stack([
            dmc.Group([
                dmc.Text(self.label, fw=500, size="sm"),
                dmc.Button(self.add_label, id=self._add_id(), variant="outline", size="xs",
                           leftSection=DashIconify(icon="tabler:plus", width=14)),
            ], justify="space-between"),
            dmc.Text(self.description or "", size="xs", c="dimmed") if self.description else None,
            dmc.Stack(self._render_items(store_data["indices"], None, None), id=self._items_id(), gap="md"),
            dcc.Store(id=self._store_id(), data=store_data),
        ], gap="sm", mt="md")

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

        @app.callback(
            [Output(store_id, "data"), Output(items_id, "children")],
            [Input(add_id, "n_clicks"),
             Input({"type": delete_type, "index": ALL}, "n_clicks"),
             Input("current-doc-id", "data")],
            State(store_id, "data"),
            prevent_initial_call=True,
        )
        def _update_items(add_clicks, delete_clicks, doc_id, store_data):
            if not ctx.triggered_id:
                raise PreventUpdate

            if ctx.triggered_id == "current-doc-id":
                if not tater_app or not doc_id or doc_id not in tater_app.annotations:
                    initial_data = self._initial_store_data()
                    return initial_data, self._render_items(initial_data["indices"], tater_app, doc_id)

                doc_annotations = tater_app.annotations[doc_id]
                field_path = self.field_path

                indices_set = set()

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

                if not indices_set:
                    initial_data = self._initial_store_data()
                    return initial_data, self._render_items(initial_data["indices"], tater_app, doc_id)

                indices = sorted(list(indices_set))
                next_index = max(indices) + 1 if indices else 0

                store_data = {"indices": indices, "next_index": next_index}
                return store_data, self._render_items(indices, tater_app, doc_id)

            if store_data is None:
                store_data = self._initial_store_data()

            indices = list(store_data.get("indices", []))
            next_index = store_data.get("next_index", 0)

            if ctx.triggered_id == add_id:
                indices.append(next_index)
                next_index += 1
            elif isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get("type") == delete_type:
                delete_index = ctx.triggered_id.get("index")
                indices = [i for i in indices if i != delete_index]

            new_data = {"indices": indices, "next_index": next_index}
            return new_data, self._render_items(indices, tater_app, doc_id)

        if tater_app:
            for item_widget_template in self.item_widgets:
                self._register_item_pattern_callback(item_widget_template, app, tater_app)

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
