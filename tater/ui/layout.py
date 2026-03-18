"""Layout builders for TaterApp."""
from __future__ import annotations

from typing import TYPE_CHECKING

from dash import html, dcc
import dash_mantine_components as dmc
from dash_iconify import DashIconify

if TYPE_CHECKING:
    from tater.ui.tater_app import TaterApp
    from tater.widgets.base import TaterWidget


from tater.ui.callbacks import _has_any_span as _has_any_span_widgets

# Header: 48px content row + 4px progress bar
_HEADER_HEIGHT = 52
# Footer: two rows (status + navigation)
_FOOTER_HEIGHT = 84


def build_layout(tater_app: TaterApp) -> dmc.MantineProvider:
    """Create the Dash layout with navigation and annotation panel."""
    annotation_components = _build_annotation_components(tater_app.widgets)
    has_required = any(w.required for w in tater_app._collect_value_capture_widgets(tater_app.widgets))
    document_viewer = _build_document_viewer()
    document_controls = _build_document_controls()
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
                document_controls,
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
                shadow="sm",
            )
        ], span={"base": 12, "md": 5}),
    ], gutter="xl")

    app_shell = dmc.AppShell(
        [
            _build_app_header(tater_app, has_instructions),
            dmc.AppShellMain(
                dmc.Container([
                    dmc.Stack([
                        dmc.Text(tater_app.description, size="sm", c="dimmed", ta="center") if tater_app.description else None,
                        dmc.Text(id="document-metadata", size="sm", c="dimmed"),
                        content_grid,
                    ], gap="lg"),
                ], size="xl", pt="xs", px="xs", fluid=True),
            ),
            _build_app_footer(),
        ],
        header={"height": _HEADER_HEIGHT},
        footer={"height": _FOOTER_HEIGHT},
        padding="xs",
    )

    return dmc.MantineProvider(
        defaultColorScheme=tater_app.theme,
        children=[
            dmc.NotificationContainer(
                id="notification-container",
                position="top-center",
                notificationMaxHeight=300,
                zIndex=1000,
                withinPortal=True,
            ),
            dcc.Store(id="current-doc-id", data=tater_app.documents[0].id if tater_app.documents else ""),
            dcc.Store(id="timing-store", data={"last_save_time": None, "doc_start_time": None, "session_start_time": None}),
            dcc.Store(id="status-store", data="not_started"),
            dcc.Store(id="auto-advance-store", data=0),
            dcc.Store(id="schema-warnings-store", data=tater_app._schema_warnings),
            dcc.Interval(id="clock-interval", interval=1000, n_intervals=0),
            *span_stores,
            app_shell,
            dmc.Drawer(
                title="Instructions",
                id="instructions-drawer",
                opened=False,
                position="top",
                size="lg",
                padding="md",
                children=dcc.Markdown(tater_app.instructions or ""),
            ) if has_instructions else None,
        ],
    )


def _build_annotation_components(widgets: list[TaterWidget]) -> list:
    """Create annotation fields from widgets."""
    annotation_components = []
    for widget in widgets:
        if widget._condition is not None:
            annotation_components.append(
                html.Div([widget._build_field_content()], id=widget.conditional_wrapper_id)
            )
        else:
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
            },
        ),
        p="md",
        withBorder=True,
        shadow="sm",
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
            placeholder="Add notes about this document",
        ),
    ], gap="sm")



def _build_app_header(tater_app: TaterApp, has_instructions: bool) -> dmc.AppShellHeader:
    """Sticky header: app title (left) + document title / status badge (right)
    with a full-width progress bar flush to the bottom edge."""
    help_button = (
        dmc.ActionIcon(
            DashIconify(icon="tabler:help-circle", width=20),
            id="btn-open-instructions",
            variant="subtle",
            size="sm",
        ) if has_instructions else None
    )

    left = dmc.Group([
        dmc.Text(id="document-title", fw=500, size="sm"),
        dmc.Badge(id="status-badge", variant="light", size="sm"),
    ], gap="sm", style={"flex": "1"})

    center = dmc.Group(
        [dmc.Title(tater_app.title, order=3)],
        justify="center",
        style={"flex": "1"},
    )

    theme_toggle = dmc.ColorSchemeToggle(
        computedColorScheme=tater_app.theme,
        lightIcon=DashIconify(icon="tabler:sun", width=20),
        darkIcon=DashIconify(icon="tabler:moon", width=20),
        size="sm",
    )

    right_children = [theme_toggle]
    if help_button:
        right_children.append(help_button)

    right = dmc.Group(
        right_children,
        gap="xs",
        style={"flex": "1"},
        justify="flex-end",
    )

    return dmc.AppShellHeader([
        dmc.Group(
            [left, center, right],
            px="md",
            align="center",
            wrap="nowrap",
            style={"height": f"{_HEADER_HEIGHT - 4}px"},
        ),
        dmc.Progress(id="document-progress", value=0, size="xs", radius=0),
    ])


def _build_app_footer() -> dmc.AppShellFooter:
    """Sticky footer: save status + timer (left), navigation controls (right)."""
    return dmc.AppShellFooter(
        dmc.Stack(
            [
                # Top row: navigation
                dmc.Flex(
                    [
                        # Prev (grows)
                        dmc.Button(
                            "Previous", id="btn-prev", variant="outline", size="sm",
                            fullWidth=True,
                            leftSection=DashIconify(icon="tabler:arrow-left", width=16),
                            style={"flex": "1"},
                        ),
                        # Selector + flag (grows)
                        dmc.Group([
                            dmc.Menu([
                                dmc.MenuTarget(
                                    dmc.Button(
                                        "Select document",
                                        id="document-selector-button",
                                        variant="outline",
                                        size="sm",
                                        fullWidth=True,
                                        rightSection=DashIconify(icon="tabler:selector", width=16),
                                        style={"borderRight": "none", "borderRadius": "var(--mantine-radius-sm) 0 0 var(--mantine-radius-sm)"},
                                    ),
                                    boxWrapperProps={"className": "menu-target-wrapper", "style": {"flex": "1", "minWidth": 0}},
                                ),
                                dmc.MenuDropdown(id="document-menu-dropdown", children=[]),
                            ], position="top-start", withArrow=True, withinPortal=True, width="target", zIndex=600),
                            dmc.Button(
                                DashIconify(icon="tabler:flag", width=16),
                                id="filter-flagged",
                                size="sm",
                                variant="outline",
                                px="xs",
                                style={"borderRadius": "0 var(--mantine-radius-sm) var(--mantine-radius-sm) 0"},
                            ),
                        ], gap=0, wrap="nowrap", style={"flex": "1"}),
                        # Next + save (grows)
                        dmc.Group([
                            dmc.Button(
                                "Next", id="btn-next", variant="outline", size="sm",
                                fullWidth=True,
                                rightSection=DashIconify(icon="tabler:arrow-right", width=16),
                                style={"borderRight": "none", "borderRadius": "var(--mantine-radius-sm) 0 0 var(--mantine-radius-sm)", "flex": "1"},
                            ),
                            dmc.Button(
                                DashIconify(icon="tabler:device-floppy", width=16),
                                id="btn-save",
                                variant="outline",
                                size="sm",
                                px="xs",
                                style={"borderRadius": "0 var(--mantine-radius-sm) var(--mantine-radius-sm) 0"},
                            ),
                        ], gap=0, wrap="nowrap", style={"flex": "1"}),
                    ],
                    gap="sm",
                    align="center",
                ),
                # Bottom row: status info
                dmc.Group(
                    [
                        dmc.Group([
                            dmc.ActionIcon(
                                DashIconify(icon="tabler:player-pause", width=16),
                                id="btn-pause-timer",
                                size="sm",
                                variant="outline",
                            ),
                            dmc.Text(id="timing-text", size="sm", c="dimmed"),
                        ], gap="xs"),
                        dmc.Text(id="save-status-text", size="sm", c="dimmed"),
                    ],
                    justify="space-between",
                ),
            ],
            gap="8",
            px="md",
            py="xs",
        ),
        style={"borderTop": "1px solid var(--mantine-color-default-border)", "backgroundColor": "var(--mantine-color-body)"},
    )
