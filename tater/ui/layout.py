"""Layout builders for TaterApp."""
from __future__ import annotations

from typing import TYPE_CHECKING

from dash import html, dcc
import dash_mantine_components as dmc
from dash_iconify import DashIconify

if TYPE_CHECKING:
    from tater.ui.tater_app import TaterApp
    from tater.widgets.base import TaterWidget


def _has_any_span_widgets(widgets: list) -> bool:
    """Return True if any SpanAnnotationWidget exists at any nesting depth."""
    from tater.widgets.span import SpanAnnotationWidget
    from tater.widgets.repeater import RepeaterWidget
    from tater.widgets.base import ContainerWidget
    for w in widgets:
        if isinstance(w, SpanAnnotationWidget):
            return True
        if isinstance(w, RepeaterWidget) and _has_any_span_widgets(w.item_widgets):
            return True
        if isinstance(w, ContainerWidget) and hasattr(w, "children") and _has_any_span_widgets(w.children):
            return True
    return False


def build_layout(tater_app: TaterApp) -> dmc.MantineProvider:
    """Create the Dash layout with navigation and annotation panel."""
    annotation_components = _build_annotation_components(tater_app.widgets)
    has_required = any(w.required for w in tater_app._collect_value_capture_widgets(tater_app.widgets))
    document_viewer = _build_document_viewer()
    document_controls = _build_document_controls()
    nav_controls = _build_navigation_controls(tater_app)
    footer_bar = _build_footer_bar()
    has_instructions = bool(tater_app.instructions and tater_app.instructions.strip())

    # Global span stores — one set shared by all SpanAnnotationWidgets
    span_stores = []
    if _has_any_span_widgets(tater_app.widgets):
        span_stores = [
            dcc.Store(id="span-any-change", data=0),
            dcc.Store(id="span-delete-store", data=None),
            html.Button(id="span-delete-proxy", n_clicks=0, style={"display": "none"}),
        ]

    content_grid = dmc.Grid([
        dmc.GridCol([
            dmc.Stack([
                document_viewer,
                document_controls
            ], gap="md")
        ], span={"base": 12, "md": 7}),
        dmc.GridCol([
            dmc.Paper(
                dmc.Stack(
                    annotation_components + (
                        [dmc.Text("* Required", size="xs", c="red")] if has_required else []
                    ),
                    gap="md",
                ),
                id="tater-annotation-panel",
                p="md",
                withBorder=True,
                shadow="sm"
            )
        ], span={"base": 12, "md": 5}),
    ], gutter="xl")

    help_button = (
        dmc.ActionIcon(
            DashIconify(icon="tabler:help-circle", width=20),
            id="btn-open-instructions",
            variant="subtle",
            size="sm",
        ) if has_instructions else None
    )

    return dmc.MantineProvider(
        theme={"colorScheme": tater_app.theme},
        children=[
            dmc.NotificationContainer(id="notification-container", position="top-center", notificationMaxHeight=300, zIndex=1000, withinPortal=True),
            dcc.Store(id="current-doc-id", data=tater_app.documents[0].id if tater_app.documents else ""),
            dcc.Store(id="timing-store", data={"last_save_time": None, "doc_start_time": None, "session_start_time": None}),
            dcc.Store(id="status-store", data="not_started"),
            dcc.Store(id="auto-advance-store", data=0),
            dcc.Store(id="schema-warnings-store", data=tater_app._schema_warnings),
            dcc.Interval(id="clock-interval", interval=1000, n_intervals=0),
            *span_stores,
            dmc.Container([
                dmc.Stack([
                    dmc.Center(
                        dmc.Stack([
                            dmc.Title(tater_app.title, order=1, mt="xl"),
                            (dmc.Group(
                                [
                                    dmc.Text(tater_app.description, size="sm", c="dimmed", ta="center"),
                                    help_button,
                                ],
                                gap="xs",
                                justify="center",
                            ) if tater_app.description else help_button) if has_instructions else (
                                dmc.Text(tater_app.description, size="sm", c="dimmed", ta="center") if tater_app.description else None
                            ),
                        ], gap="xs", align="center")
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
            dmc.Drawer(
                title="Instructions",
                id="instructions-drawer",
                opened=False,
                position="top",
                size="lg",
                padding="md",
                children=dcc.Markdown(tater_app.instructions or ""),
            ) if has_instructions else None,
            footer_bar,
        ]
    )


def _build_annotation_components(widgets: list[TaterWidget]) -> list:
    """Create annotation fields from widgets with dividers between them.

    Dividers are skipped when either the current or previous widget is a
    ContainerWidget (e.g. GroupWidget), which provides its own visual separation.

    For conditional widgets the preceding divider is placed inside the
    conditional wrapper so it is hidden together with the widget.
    """
    from tater.widgets.base import ContainerWidget
    annotation_components = []
    for i, widget in enumerate(widgets):
        prev = widgets[i - 1] if i > 0 else None
        has_leading_divider = (
            i > 0
            and not isinstance(widget, ContainerWidget)
            and not isinstance(prev, ContainerWidget)
        )
        if widget._condition is not None:
            children = ([dmc.Divider()] if has_leading_divider else []) + [widget._build_field_content()]
            annotation_components.append(html.Div(children, id=widget.conditional_wrapper_id))
        else:
            if has_leading_divider:
                annotation_components.append(dmc.Divider())
            annotation_components.append(widget.render_field())
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
                "padding": "0 3px",
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
    """Build the navigation button row with document filter."""
    button_row = dmc.Flex([
        dmc.Box(
            dmc.Button("Previous", id="btn-prev", variant="outline", fullWidth=True,
                       leftSection=DashIconify(icon="tabler:arrow-left", width=16)),
            style={"flex": "1 1 0", "minWidth": 0},
        ),
        dmc.Box(
            dmc.Stack([
                dmc.Menu([
                    dmc.MenuTarget(
                        dmc.Button(
                            "Select document",
                            id="document-selector-button",
                            variant="outline",
                            fullWidth=True,
                            rightSection=DashIconify(icon="tabler:chevron-down", width=16),
                        ),
                        boxWrapperProps={"className": "menu-target-wrapper"},
                    ),
                    dmc.MenuDropdown(id="document-menu-dropdown", children=[]),
                ], position="bottom-start", withArrow=True, withinPortal=True, width="target", zIndex=600),
                dmc.Checkbox(id="filter-flagged", label="Show flagged only", size="xs", checked=False),
            ], gap="xs"),
            style={"flex": "1 1 0", "minWidth": 0},
        ),
        dmc.Box(
            dmc.ButtonGroup([
                dmc.Button("Next", id="btn-next", variant="outline", fullWidth=True,
                           rightSection=DashIconify(icon="tabler:arrow-right", width=16)),
                dmc.Button(
                    DashIconify(icon="tabler:device-floppy", width=16),
                    id="btn-save",
                    variant="outline",
                    px="xs",
                ),
            ], style={"width": "100%"}),
            style={"flex": "1 1 0", "minWidth": 0},
        ),
    ], gap="md", align="stretch", wrap="nowrap", style={"width": "100%"})
    return button_row


def _build_footer_bar() -> dmc.Box:
    """Build the persistent footer bar with save status and timing info."""
    return dmc.Box(
        dmc.Group(
            [
                dmc.Box(
                    dmc.Group([                        
                        dmc.ActionIcon(
                            DashIconify(icon="tabler:player-pause", width=16),
                            id="btn-pause-timer",
                            size="sm",
                            variant="outline",
                        ),
                        dmc.Text(
                            id="timing-text",
                            size="sm",
                            c="dimmed",
                        ),
                    ], gap="xs"),
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
