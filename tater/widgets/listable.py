"""ListableWidget for repeatable groups of fields."""
from __future__ import annotations

import copy
from typing import Optional, Any

from dash import dcc, Input, Output, State, ctx, ALL
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc

from .base import TaterWidget


class ListableWidget(TaterWidget):
    """Widget for managing a list of repeated field groups."""

    def __init__(
        self,
        schema_field: str,
        label: str,
        item_widgets: list[TaterWidget],
        description: Optional[str] = None,
        required: bool = False,
        add_label: str = "Add",
        delete_label: str = "Delete",
        initial_count: int = 1,
    ):
        """
        Initialize ListableWidget.

        Args:
            schema_field: Field name in the Pydantic schema
            label: Human-readable label for the list
            item_widgets: Widgets that make up a single list item
            description: Optional help text
            required: Whether this list is required
            add_label: Label for the add button
            delete_label: Label for the delete button
            initial_count: Number of items to start with
        """
        super().__init__(
            schema_field=schema_field,
            label=label,
            description=description,
            required=required,
        )
        self.item_widgets = item_widgets
        self.add_label = add_label
        self.delete_label = delete_label
        self.initial_count = max(0, initial_count)

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

    def _render_item_widgets(self, index: int) -> list[Any]:
        rendered = []
        for template in self.item_widgets:
            widget = copy.deepcopy(template)
            widget._finalize_paths(parent_path=f"{self.field_path}.{index}")
            rendered.append(
                dmc.Stack([
                    dmc.Text(widget.label, fw=500, size="sm"),
                    widget.component(),
                    dmc.Text(widget.description or "", size="xs", c="dimmed") if widget.description else None,
                ], gap="xs", mt="sm")
            )
        return rendered

    def _render_items(self, indices: list[int]) -> list[Any]:
        items = []
        for index in indices:
            items.append(
                dmc.Card([
                    dmc.Group([
                        dmc.Text(f"Item {index + 1}", fw=500, size="sm"),
                        dmc.Button(
                            self.delete_label,
                            id={"type": self._delete_type(), "index": index},
                            variant="outline",
                            color="red",
                            size="xs",
                        ),
                    ], justify="space-between"),
                    dmc.Stack(self._render_item_widgets(index), gap="sm"),
                ], withBorder=True, p="md")
            )
        return items

    def component(self) -> dmc.Stack:
        """Return Dash component for the list widget."""
        store_data = self._initial_store_data()
        return dmc.Stack([
            dmc.Group([
                dmc.Text(self.label, fw=500, size="sm"),
                dmc.Button(self.add_label, id=self._add_id(), variant="outline", size="xs"),
            ], justify="space-between"),
            dmc.Text(self.description or "", size="xs", c="dimmed") if self.description else None,
            dmc.Stack(self._render_items(store_data["indices"]), id=self._items_id(), gap="md"),
            dcc.Store(id=self._store_id(), data=store_data),
        ], gap="sm", mt="md")

    @property
    def renders_own_label(self) -> bool:
        """ListableWidget renders its own label and description."""
        return True

    def register_callbacks(self, app: Any) -> None:
        """Register callbacks to manage list items."""
        add_id = self._add_id()
        items_id = self._items_id()
        store_id = self._store_id()
        delete_type = self._delete_type()

        @app.callback(
            [Output(store_id, "data"), Output(items_id, "children")],
            [Input(add_id, "n_clicks"), Input({"type": delete_type, "index": ALL}, "n_clicks")],
            State(store_id, "data"),
            prevent_initial_call=True,
        )
        def _update_items(add_clicks, delete_clicks, store_data):
            if not ctx.triggered_id:
                raise PreventUpdate

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
            return new_data, self._render_items(indices)

    def to_python_type(self) -> type:
        """Return list since this represents a list of models."""
        return list
