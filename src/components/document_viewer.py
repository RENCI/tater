"""Document viewer component for displaying clinical notes."""
from dash import html, dcc
import dash_bootstrap_components as dbc
from typing import Optional, List, Dict, Any


def create_document_viewer() -> dbc.Card:
    """
    Create the left panel document viewer component.
    
    Returns:
        A Dash Bootstrap Card containing the document viewer
    """
    return dbc.Card([
        dbc.CardHeader([
            html.H5("Document", className="mb-0"),
            html.Small(id="document-metadata", className="text-muted")
        ]),
        dbc.CardBody([
            html.Div(
                id="document-text-container",
                children=[
                    html.Pre(
                        id="document-text",
                        children="Load a document to begin annotation...",
                        style={
                            "whiteSpace": "pre-wrap",
                            "fontFamily": "monospace",
                            "fontSize": "14px",
                            "lineHeight": "1.6",
                            "padding": "10px",
                            "maxHeight": "70vh",
                            "overflowY": "auto",
                            "backgroundColor": "#f8f9fa",
                            "border": "1px solid #dee2e6",
                            "borderRadius": "4px"
                        }
                    )
                ]
            ),
            html.Div(
                id="span-annotations-list",
                className="mt-3"
            )
        ], style={"padding": "15px"})
    ], className="h-100")


def format_document_text(
    text: str,
    span_annotations: Optional[List[Dict[str, Any]]] = None
) -> html.Pre:
    """
    Format document text with optional span highlighting.
    
    Args:
        text: The document text
        span_annotations: List of span annotations with text, start, end, entity_type
    
    Returns:
        Formatted Pre element with highlighted spans
    """
    if not span_annotations:
        return html.Pre(
            text,
            style={
                "whiteSpace": "pre-wrap",
                "fontFamily": "monospace",
                "fontSize": "14px",
                "lineHeight": "1.6",
                "padding": "10px",
                "maxHeight": "70vh",
                "overflowY": "auto",
                "backgroundColor": "#f8f9fa",
                "border": "1px solid #dee2e6",
                "borderRadius": "4px"
            }
        )
    
    # Sort spans by start position
    sorted_spans = sorted(span_annotations, key=lambda x: x['start'])
    
    # Build text with highlights
    from utils.constants import ENTITY_COLORS
    
    children = []
    last_end = 0
    
    for i, span in enumerate(sorted_spans):
        start = span['start']
        end = span['end']
        entity_type = span['entity_type']
        
        # Add text before this span
        if start > last_end:
            children.append(text[last_end:start])
        
        # Add highlighted span
        color = ENTITY_COLORS.get(entity_type, "#E0E0E0")
        children.append(
            html.Mark(
                text[start:end],
                style={
                    "backgroundColor": color,
                    "padding": "2px 4px",
                    "borderRadius": "3px",
                    "cursor": "pointer"
                },
                id={"type": "span-highlight", "index": i},
                title=f"{entity_type}: {text[start:end]}"
            )
        )
        
        last_end = end
    
    # Add remaining text
    if last_end < len(text):
        children.append(text[last_end:])
    
    return html.Pre(
        children,
        style={
            "whiteSpace": "pre-wrap",
            "fontFamily": "monospace",
            "fontSize": "14px",
            "lineHeight": "1.6",
            "padding": "10px",
            "maxHeight": "70vh",
            "overflowY": "auto",
            "backgroundColor": "#f8f9fa",
            "border": "1px solid #dee2e6",
            "borderRadius": "4px"
        }
    )


def create_span_annotations_display(
    span_annotations: Optional[List[Dict[str, Any]]] = None
) -> html.Div:
    """
    Create a display of all span annotations with jump-to functionality.
    
    Args:
        span_annotations: List of span annotations
    
    Returns:
        Div containing the annotations list
    """
    if not span_annotations:
        return html.Div()
    
    from utils.constants import ENTITY_COLORS
    
    items = []
    for i, span in enumerate(span_annotations):
        entity_type = span['entity_type']
        text = span['text']
        color = ENTITY_COLORS.get(entity_type, "#E0E0E0")
        
        items.append(
            dbc.ListGroupItem([
                html.Span(
                    entity_type,
                    className="badge me-2",
                    style={
                        "backgroundColor": color,
                        "color": "#000"
                    }
                ),
                html.Span(f'"{text}"', className="font-monospace"),
                dbc.Button(
                    "×",
                    color="link",
                    size="sm",
                    className="float-end text-danger",
                    id={"type": "delete-span", "index": i},
                    style={"textDecoration": "none", "fontSize": "20px"}
                )
            ])
        )
    
    return html.Div([
        html.H6("Text Annotations:", className="mt-3 mb-2"),
        dbc.ListGroup(items, className="small")
    ])
