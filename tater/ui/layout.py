"""Layout builders for TaterApp."""
from __future__ import annotations

from typing import TYPE_CHECKING

from dash import html, dcc
import dash_mantine_components as dmc

if TYPE_CHECKING:
    from tater.ui.tater_app import TaterApp
    from tater.widgets.base import TaterWidget


def build_layout(tater_app: TaterApp) -> dmc.MantineProvider:
    """Create the Dash layout with navigation and annotation panel."""
    from tater.widgets.span import SpanAnnotationWidget

    annotation_components = _build_annotation_components(tater_app.widgets)
    document_viewer = _build_document_viewer()
    document_controls = _build_document_controls()
    nav_controls = _build_navigation_controls(tater_app)
    footer_bar = _build_footer_bar()

    # One selection store + one trigger store per SpanAnnotationWidget
    span_stores = []
    for w in tater_app.widgets:
        if isinstance(w, SpanAnnotationWidget):
            span_stores.append(dcc.Store(id=f"span-selection-{w.component_id}", data=None))
            span_stores.append(dcc.Store(id=f"span-trigger-{w.component_id}", data=0))

    content_grid = dmc.Grid([
        dmc.GridCol([
            dmc.Stack([
                document_viewer,
                document_controls
            ], gap="md")
        ], span={"base": 12, "md": 7}),
        dmc.GridCol([
            dmc.Paper(
                dmc.Stack(annotation_components, gap="md"),
                p="md",
                withBorder=True,
                shadow="sm"
            )
        ], span={"base": 12, "md": 5}),
    ], gutter="xl")

    return dmc.MantineProvider(
        theme={"colorScheme": tater_app.theme},
        children=[
            dcc.Store(id="current-doc-id", data=tater_app.documents[0].id if tater_app.documents else ""),
            dcc.Store(id="timing-store", data={"last_save_time": None, "doc_start_time": None, "session_start_time": None}),
            dcc.Store(id="status-store", data="not_started"),
            dcc.Interval(id="clock-interval", interval=1000, n_intervals=0),
            *span_stores,
            dmc.Container([
                dmc.Stack([
                    dmc.Center(
                        dmc.Title(tater_app.title, order=1, mt="xl")
                    ),
                    dmc.Stack([
                        dmc.Group([
                            dmc.Text(
                                id="document-title",
                                fw=500,
                                size="lg",
                            ),
                            dmc.Badge(
                                id="status-badge",
                                variant="light",
                            ),
                        ], gap="sm", align="center", mb="xs"),
                        dmc.Progress(
                            id="document-progress",
                            value=0,
                            size="sm",
                            mb="xs"
                        ),
                        dmc.Text(
                            id="document-metadata",
                            size="sm",
                            c="dimmed"
                        ),
                    ]),
                    content_grid,
                    nav_controls,
                ], gap="lg")
            ], size="xl", py="xl", fluid=True, pb="100px"),
            footer_bar,
        ]
    )


def _build_annotation_components(widgets: list[TaterWidget]) -> list:
    """Create annotation fields from widgets with dividers between them."""
    from tater.ui.callbacks import _collect_value_capture_widgets
    annotation_components = []
    has_required = any(w.required for w in _collect_value_capture_widgets(widgets))

    for i, widget in enumerate(widgets):
        annotation_components.append(widget.render_field())
        if i < len(widgets) - 1:
            annotation_components.append(dmc.Divider())

    if has_required:
        annotation_components.append(dmc.Divider())
        annotation_components.append(dmc.Text("* Required", size="xs", c="red"))

    return annotation_components


def _build_document_viewer() -> dmc.Paper:
    """Build the document viewer component (wrapped in Paper)."""
    return dmc.Paper(
        html.Pre(
            id="document-content",
            style={
                "whiteSpace": "pre-wrap",
                "wordWrap": "break-word",
                "fontFamily": "monospace",
                "fontSize": "0.9rem",
                "lineHeight": "1.5",
                "margin": 0,
                "height": "500px",
                "overflowY": "auto",
            }
        ),
        p="md",
        withBorder=True,
        shadow="sm"
    )


def _build_document_controls() -> dmc.Stack:
    """Build the flag/notes control stack."""
    return dmc.Stack([
        dmc.Checkbox(id="flag-document", label="Flag document", checked=False),
        dmc.Textarea(
            id="document-notes",
            label="Notes",
            autosize=True,
            minRows=3,
            placeholder="Add notes about this document"
        )
    ], gap="sm")


def _build_navigation_controls(tater_app: TaterApp) -> dmc.Flex:
    """Build the navigation button row."""
    return dmc.Flex([
        dmc.Box(
            dmc.Button("\u2190 Previous", id="btn-prev", variant="outline", fullWidth=True),
            style={"flex": "1 1 0", "minWidth": 0},
        ),
        dmc.Box(
            dmc.Menu([
                dmc.MenuTarget(
                    dmc.Button(
                        "Select document",
                        id="document-selector-button",
                        variant="outline",
                        fullWidth=True,
                    ),
                    boxWrapperProps={"className": "menu-target-wrapper"},
                ),
                dmc.MenuDropdown(id="document-menu-dropdown", children=[]),
            ], position="bottom-start", withArrow=True, withinPortal=True, width="target"),
            style={"flex": "1 1 0", "minWidth": 0},
        ),
        dmc.Box(
            dmc.Button("Next \u2192", id="btn-next", variant="outline", fullWidth=True),
            style={"flex": "1 1 0", "minWidth": 0},
        ),
    ], gap="md", align="stretch", wrap="nowrap", style={"width": "100%"})


def _build_footer_bar() -> dmc.Box:
    """Build the persistent footer bar with save status and timing info."""
    return dmc.Box(
        dmc.Group(
            [
                dmc.Box(
                    dmc.Text(
                        id="timing-text",
                        size="sm",
                        c="dimmed",
                    ),
                    style={"flex": "1"},
                ),
                dmc.Divider(orientation="vertical"),
                dmc.Box(
                    dmc.Text(
                        id="save-status-text",
                        size="sm",
                        c="dimmed",
                        ta="right",
                    ),
                    style={"flex": "1"},
                ),
            ],
            align="center",
            gap="md",
        ),
        py="sm",
        px="md",
        style={
            "borderTop": "1px solid #e9ecef",
            "backgroundColor": "#f8f9fa",
            "position": "fixed",
            "bottom": 0,
            "left": 0,
            "right": 0,
            "zIndex": 500,
        },
    )
