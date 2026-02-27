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
    annotation_components = _build_annotation_components(tater_app.widgets)
    document_viewer = _build_document_viewer()
    document_controls = _build_document_controls()
    nav_controls = _build_navigation_controls()
    footer_bar = _build_footer_bar()

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
            dcc.Interval(id="clock-interval", interval=1000, n_intervals=0),
            dmc.Container([
                dmc.Stack([
                    dmc.Center(
                        dmc.Title(tater_app.title, order=1, mt="xl")
                    ),
                    dmc.Stack([
                        dmc.Text(
                            id="document-title",
                            fw=500,
                            size="lg",
                            mb="xs"
                        ),
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
    annotation_components = []
    has_required = any(getattr(widget, "required", False) for widget in widgets)

    for i, widget in enumerate(widgets):
        if widget.renders_own_label:
            field_container = widget.component()
        else:
            components_list = [
                dmc.Text(widget.label, fw=500, size="sm"),
            ]
            if widget.description:
                components_list.append(
                    dmc.Text(widget.description, size="xs", c="dimmed")
                )
            components_list.append(widget.component())

            field_container = dmc.Stack(components_list, gap="xs", mt="md")

        annotation_components.append(field_container)

        if i < len(widgets) - 1:
            annotation_components.append(dmc.Divider())

    if has_required:
        annotation_components.append(dmc.Text("[* Required]", size="xs", c="red"))

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


def _build_navigation_controls() -> dmc.Flex:
    """Build the navigation button row."""
    return dmc.Flex([
        dmc.Button("\u2190 Previous", id="btn-prev", variant="outline", flex=1),
        dmc.Button("Next \u2192", id="btn-next", variant="outline", flex=1),
    ], gap="md")


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
