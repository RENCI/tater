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
        shadow="sm",
        style={"height": "500px", "overflowY": "auto"}
    )


def create_document_navigation() -> dmc.Group:
    """Create document navigation controls.
    
    Returns:
        A Mantine Group containing navigation buttons
    """
    return dmc.Group([
        dmc.Button(
            "← Previous",
            id="prev-button",
            variant="outline",
            size="sm"
        ),
        dmc.Select(
            id="document-selector",
            placeholder="Select a document",
            searchable=True,
            clearable=False,
            style={"flex": 1}
        ),
        dmc.Button(
            "Next →",
            id="next-button",
            variant="outline",
            size="sm"
        ),
    ], grow=True, gap="md")


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
