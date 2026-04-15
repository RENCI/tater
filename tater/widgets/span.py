"""Span annotation widgets for labeling text spans."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional, Any, TYPE_CHECKING

import dash_mantine_components as dmc

from tater.widgets.base import TaterWidget

if TYPE_CHECKING:
    pass


PALETTES: dict[str, list[str]] = {
    "category10": [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    ],
    "accent": [
        "#7fc97f", "#beaed4", "#fdc086", "#ffff99",
        "#386cb0", "#f0027f", "#bf5b17", "#666666",
    ],
    "dark2": [
        "#1b9e77", "#d95f02", "#7570b3", "#e7298a",
        "#66a61e", "#e6ab02", "#a67616", "#666666",
    ],
    "observable10": [
        "#4269d0", "#efb118", "#ff725c", "#6cc5b0", "#3ca951",
        "#ff8ab7", "#a463f2", "#97bbf5", "#9c6b4e", "#9498a0",
    ],
    "paired": [
        "#a6cee3", "#1f78b4", "#b2df8a", "#33a02c", "#fb9a99", "#e31a1c",
        "#fdbf6f", "#ff7f00", "#cab2d6", "#6a3d9a", "#ffff99", "#b15928",
    ],
    "pastel1": [
        "#fbb4ae", "#b3cde3", "#ccebc5", "#decbe4", "#fed9a6",
        "#ffffcc", "#e5d8bd", "#fddaec", "#f2f2f2",
    ],
    "pastel2": [
        "#b3e2cd", "#fdcdac", "#cbd5e8", "#f4cae4",
        "#e6f5c9", "#fff2ae", "#f1e2cc", "#cccccc",
    ],
    "set1": [
        "#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00",
        "#ffff33", "#a65628", "#f781bf", "#999999",
    ],
    "set2": [
        "#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3",
        "#a6d854", "#ffd92f", "#e5c494", "#b3b3b3",
    ],
    "set3": [
        "#8dd3c7", "#ffffb3", "#bebada", "#fb8072", "#80b1d3", "#fdb462",
        "#b3de69", "#fccde5", "#d9d9d9", "#bc80bd", "#ccebc5", "#ffed6f",
    ],
    "tableau10": [
        "#4e79a7", "#f28e2c", "#e15759", "#76b7b2", "#59a14f",
        "#edc949", "#af7aa1", "#ff9da7", "#9c755f", "#bab0ab",
    ],
}


def _lighten_hex(color: str, factor: float = 0.4) -> str:
    """Mix a hex color with white by `factor` (0 = original, 1 = white)."""
    c = color.lstrip("#")
    if len(c) != 6:
        return color
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    r = round(r + (255 - r) * factor)
    g = round(g + (255 - g) * factor)
    b = round(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


@dataclass
class EntityType:
    """An entity type for span annotation with a display name and highlight color."""

    name: str
    color: Optional[str] = None  # defaults to widget palette by index


class SpanBaseWidget(TaterWidget):
    """Shared base for SpanAnnotationWidget and SpanPopupWidget.

    Handles entity-type color assignment, label/type plumbing, and the
    ``get_color_for_tag`` helper.  Subclasses implement ``component()``.
    """

    def __init__(
        self,
        schema_field: str,
        label: str,
        entity_types: list[EntityType],
        description: Optional[str] = None,
        palette: str = "tableau10",
    ):
        super().__init__(schema_field=schema_field, label=label, description=description)
        colors = PALETTES.get(palette, PALETTES["set3"])
        # Assign palette colors to any EntityType that didn't specify one
        self.entity_types = [
            EntityType(et.name, et.color if et.color else colors[i % len(colors)])
            for i, et in enumerate(entity_types)
        ]

    # ------------------------------------------------------------------
    # TaterWidget interface
    # ------------------------------------------------------------------

    @property
    def renders_own_label(self) -> bool:
        return True

    def to_python_type(self) -> type:
        return list

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_color_for_tag(self, tag: str) -> str:
        """Return the lightened highlight color for the given tag name."""
        for et in self.entity_types:
            if et.name == tag:
                return _lighten_hex(et.color)
        return _lighten_hex("#ffe066")


class SpanAnnotationWidget(SpanBaseWidget):
    """
    Widget for annotating text spans with entity type labels.

    Users highlight text in the document viewer then click an entity button
    to tag the selection.  Spans are stored as ``List[SpanAnnotation]`` on
    the Pydantic annotation model.

    Example schema field::

        spans: List[SpanAnnotation] = Field(default_factory=list)
    """

    def __init__(
        self,
        schema_field: str,
        label: str,
        entity_types: list[EntityType],
        description: Optional[str] = None,
        palette: str = "tableau10",
    ):
        super().__init__(
            schema_field=schema_field,
            label=label,
            entity_types=entity_types,
            description=description,
            palette=palette,
        )

    # ------------------------------------------------------------------
    # TaterWidget interface
    # ------------------------------------------------------------------

    def component(self) -> Any:
        """Render the entity-type button row with inline stores."""
        from dash import html, dcc
        pipe_field = self.field_path.replace(".", "|")
        return self._input_wrapper(html.Div([
                html.Div(
                    id={"type": "span-entity-buttons", "field": pipe_field},
                    children=self._make_buttons(pipe_field, {}),
                ),
                dcc.Store(id={"type": "span-selection", "field": pipe_field}, data=None),
                dcc.Store(id={"type": "span-trigger", "field": pipe_field}, data=0),
            ]), self.label)

    def _make_buttons(self, pipe_field: str, counts: dict = None) -> Any:
        """Build the entity-type button group with per-entity span count badges.

        ``pipe_field`` is the dot-path of this widget's field with dots replaced
        by pipes (e.g. ``"findings|0|spans"``), used as the shared key in all
        component dict IDs so that MATCH callbacks route correctly.

        Count badges are absolutely-positioned ``html.Span`` elements updated
        by a clientside callback — no server round-trip needed.
        """
        from dash import html
        if counts is None:
            counts = {}
        buttons = []
        for et in self.entity_types:
            count = counts.get(et.name, 0)
            buttons.append(
                html.Div(
                    [
                        dmc.Button(
                            et.name,
                            id={"type": "span-add-btn", "field": pipe_field, "tag": et.name},
                            size="xs",
                            variant="outline",
                            fw=600,
                            style={"borderColor": et.color, "backgroundColor": _lighten_hex(et.color),
                                   "color": "var(--mantine-color-gray-9)"},
                        ),
                        html.Span(
                            "0",
                            id={"type": "span-count", "field": pipe_field, "tag": et.name},
                            className="tater-count-badge",
                            style={"backgroundColor": et.color},
                        ),
                    ],
                    style={"position": "relative", "display": "inline-block"},
                )
            )
        return html.Div(
            dmc.Group(buttons, gap="xs", wrap="wrap"),
            **{"data-tater-field": pipe_field},
        )


class SpanPopupWidget(SpanBaseWidget):
    """Span annotation widget where entity buttons appear in a floating popup.

    When the user selects text in the document viewer, a popup appears near the
    selection showing entity type buttons — no need to click in the widget panel.
    The static widget section shows only span counts (one per entity type) and
    acts as an active-widget selector (clicking it focuses this widget's spans).

    Spans are stored as ``List[SpanAnnotation]``, identical to
    ``SpanAnnotationWidget``.  Use this widget when screen real-estate is limited
    or when a faster annotation workflow is desired.  Keep ``SpanAnnotationWidget``
    for touchscreen / mobile use-cases where hover/selection is less reliable.

    Example schema field::

        spans: List[SpanAnnotation] = Field(default_factory=list)
    """

    def __init__(
        self,
        schema_field: str,
        label: str,
        entity_types: list[EntityType],
        description: Optional[str] = None,
        palette: str = "tableau10",
    ):
        super().__init__(
            schema_field=schema_field,
            label=label,
            entity_types=entity_types,
            description=description,
            palette=palette,
        )

    # ------------------------------------------------------------------
    # TaterWidget interface
    # ------------------------------------------------------------------

    def component(self) -> Any:
        """Render the counter strip with data-tater-entities for popup targeting."""
        from dash import html
        pipe_field = self.field_path.replace(".", "|")
        # Encode entity data for the popup JS: name, full color, lightened color
        entities_json = json.dumps([
            {"name": et.name, "color": et.color, "lightColor": _lighten_hex(et.color)}
            for et in self.entity_types
        ])
        return self._input_wrapper(
            html.Div(
                self._make_counter_strip(pipe_field),
                **{
                    "data-tater-field": pipe_field,
                    "data-tater-entities": entities_json,
                },
            ),
            self.label,
        )

    def _make_counter_strip(self, pipe_field: str) -> Any:
        """Build counter-only strip: entity label + count badge per entity type."""
        from dash import html
        items = []
        for et in self.entity_types:
            items.append(
                html.Div(
                    [
                        html.Span(
                            et.name,
                            style={
                                "fontSize": "0.75rem",
                                "fontWeight": 600,
                                "color": et.color,
                                "cursor": "default",
                            },
                        ),
                        html.Span(
                            "0",
                            id={"type": "span-count", "field": pipe_field, "tag": et.name},
                            className="tater-count-badge",
                            style={"backgroundColor": et.color},
                        ),
                    ],
                    style={
                        "position": "relative",
                        "display": "inline-flex",
                        "alignItems": "center",
                        "gap": "4px",
                    },
                )
            )
        return dmc.Group(items, gap="xs", wrap="wrap")

    def register_callbacks(self, app: Any) -> None:
        pass  # Popup callbacks are registered globally in setup_span_callbacks
