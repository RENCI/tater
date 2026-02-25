"""UI components for document display and navigation."""
from dash import html, dcc
import dash_mantine_components as dmc


def create_document_viewer(content: str = "") -> dmc.Paper:
    """Create a document viewer component.
    
    Args:
        content: The document content to display
        
    Returns:
        A Mantine Paper component containing the document
    """
    return dmc.Paper(
        html.Pre(
            content,
            style={
                "whiteSpace": "pre-wrap",
                "wordWrap": "break-word",
                "fontFamily": "monospace",
                "fontSize": "0.9rem",
                "lineHeight": "1.5",
            }
        ),
        p="md",
        radius="md",
        withBorder=True,
        shadow="sm",
        style={"height": "500px", "overflowY": "auto"}
    )


def create_document_navigation() -> dmc.Flex:
    """Create document navigation controls.
    
    Returns:
        A Mantine Flex component containing navigation buttons
    """
    return dmc.Flex([
        dmc.Box(
            dmc.Button(
                "← Previous",
                id="prev-button",
                variant="outline",
                size="sm",
                fullWidth=True
            ),
            style={"flex": "1 1 0", "minWidth": 0}
        ),
        dmc.Box(
            dmc.Stack([
                dmc.Menu(
                    [
                        dmc.MenuTarget(
                            dmc.Button(
                                "Select a document",
                                id="document-selector-button",
                                variant="outline",
                                size="sm",
                                fullWidth=True,
                                justify="flex-start"
                            ),
                            boxWrapperProps={"className": "menu-target-wrapper"}
                        ),
                        dmc.MenuDropdown(id="document-menu-dropdown", children=[])
                    ],
                    position="bottom-start",
                    withArrow=True,
                    withinPortal=True,
                    width="target"
                ),
                dmc.Checkbox(
                    id="hide-completed-filter",
                    label="Hide completed",
                    checked=False,
                    size="xs"
                )
            ], gap="xs"),
            style={"flex": "1 1 0", "minWidth": 0}
        ),
        dmc.Box(
            dmc.Button(
                "Next →",
                id="next-button",
                variant="outline",
                size="sm",
                fullWidth=True
            ),
            style={"flex": "1 1 0", "minWidth": 0}
        ),
    ], gap="md", align="stretch", wrap="nowrap", style={"width": "100%"})


def create_document_info() -> html.Div:
    """Create a document info display.
    
    Returns:
        A div showing current document info
    """
    return html.Div([
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
    ])
