"""ListableWidget for repeatable groups of fields."""
from __future__ import annotations

import copy
from typing import Optional, Any

from dash import dcc, html, Input, Output, State, ctx, ALL
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc

from .base import ContainerWidget, TaterWidget


class ListableWidget(ContainerWidget):
    """Widget for managing a list of repeated field groups."""

    def __init__(
        self,
        schema_field: str,
        label: str,
        item_widgets: list[TaterWidget],
        description: Optional[str] = None,
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
            add_label: Label for the add button
            delete_label: Label for the delete button
            initial_count: Number of items to start with
        """
        super().__init__(
            schema_field=schema_field,
            label=label,
            description=description,
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
            # Store the original component method
            original_component = widget.component
            pattern_type = f"{self.component_id}-item"
            
            def make_pattern_component(w, pt):
                """Create a component with a pattern-matching ID."""
                comp = original_component()
                # Set the ID to a dictionary for pattern matching
                comp.id = {
                    "type": pt,
                    "field": w._local_path,
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
                        dmc.Button(
                            self.delete_label,
                            id={"type": self._delete_type(), "index": index},
                            variant="outline",
                            color="red",
                            size="xs",
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
                dmc.Button(self.add_label, id=self._add_id(), variant="outline", size="xs"),
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
        
        # Get tater_app reference if available
        tater_app = getattr(app, "_tater_app", None)
        
        add_id = self._add_id()
        items_id = self._items_id()
        store_id = self._store_id()
        delete_type = self._delete_type()
        
        # Build a pattern for matching item widget IDs
        # For pets.0.kind widget, component_id is "annotation-pets-0-kind"
        # We want to match the pattern "annotation-<field>-<index>-<child_field>"
        list_field_parts = self.field_path.replace('-', '_')  # normalized
        
        # Pattern for item widgets: annotation-pets-{index}-kind
        # We use "item-value" pattern type for all item widget captures
        item_pattern_type = f"{self.component_id}-item-value"

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

            # Handle document change - reconstruct from annotations
            if ctx.triggered_id == "current-doc-id":
                if not tater_app or not doc_id or doc_id not in tater_app.annotations:
                    # No annotations for this document, use initial state
                    initial_data = self._initial_store_data()
                    return initial_data, self._render_items(initial_data["indices"], tater_app, doc_id)
                
                doc_annotations = tater_app.annotations[doc_id]
                field_path = self.field_path
                
                # Extract indices based on annotation type
                indices_set = set()
                
                if isinstance(doc_annotations, BaseModel):
                    # Pydantic model - look at the actual list field
                    try:
                        list_field = getattr(doc_annotations, field_path, None)
                        if isinstance(list_field, list):
                            indices_set = set(range(len(list_field)))
                    except AttributeError:
                        pass
                else:
                    # Plain dict - parse annotation keys
                    prefix = f"{field_path}."
                    for key in doc_annotations.keys():
                        if key.startswith(prefix):
                            # Extract index: "pets.0.kind" -> "0"
                            rest = key[len(prefix):]  # "0.kind"
                            index_str = rest.split('.')[0]  # "0"
                            try:
                                indices_set.add(int(index_str))
                            except ValueError:
                                pass
                
                if not indices_set:
                    # No list items found, use initial state
                    initial_data = self._initial_store_data()
                    return initial_data, self._render_items(initial_data["indices"], tater_app, doc_id)
                
                # Sort indices and create store data
                indices = sorted(list(indices_set))
                next_index = max(indices) + 1 if indices else 0
                
                store_data = {"indices": indices, "next_index": next_index}
                return store_data, self._render_items(indices, tater_app, doc_id)

            # Handle add/delete
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
        
        # Register pattern-matching callbacks for item widgets (one callback handles all indices)
        if tater_app:
            for item_widget_template in self.item_widgets:
                self._register_item_pattern_callback(item_widget_template, app, tater_app)

    def _register_item_pattern_callback(self, item_widget_template: TaterWidget, app: Any, tater_app: Any) -> None:
        """Register a single pattern-matching callback that handles all items for this widget type."""
        from dash import ALL, Input, Output, State, MATCH
        
        pattern_type = f"{self.component_id}-item"
        field_name = item_widget_template._local_path
        value_prop = item_widget_template.value_prop
        
        @app.callback(
            Output({"type": pattern_type, "field": field_name, "index": ALL}, "id"),
            Input({"type": pattern_type, "field": field_name, "index": ALL}, value_prop),
            State({"type": pattern_type, "field": field_name, "index": ALL}, "id"),
            State("current-doc-id", "data"),
            prevent_initial_call=True
        )
        def capture_pattern_values(all_values, all_ids, doc_id):
            """Pattern-matching callback that captures values from any matching widget."""
            if not doc_id or not ctx.triggered:
                # Return the IDs unchanged (dummy output)
                return all_ids if all_ids else []
            
            # Parse which component triggered
            triggered_prop = ctx.triggered[0]["prop_id"]
            if "." not in triggered_prop:
                return all_ids if all_ids else []
            
            try:
                # Extract the triggered ID dict
                triggered_id_str = triggered_prop.split(".")[0]
                triggered_id = eval(triggered_id_str)
                
                if not isinstance(triggered_id, dict):
                    return all_ids if all_ids else []
                
                index = triggered_id.get("index")
                field = triggered_id.get("field")
                
                if index is None or field is None:
                    return all_ids if all_ids else []
                
                # Build the full field path: pets.0.kind
                full_field_path = f"{self.field_path}.{index}.{field}"
                
                # Find the value for this specific triggered widget
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
            
            except Exception:
                pass
            
            # Return IDs unchanged (dummy output)
            return all_ids if all_ids else []

    def to_python_type(self) -> type:
        """Return list since this represents a list of models."""
        return list
