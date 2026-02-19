"""Document viewer component for displaying clinical notes."""
from dash import html, dcc
import dash_mantine_components as dmc
from typing import Optional, List, Dict, Any


def create_document_viewer() -> dmc.Paper:
    """
    Create the left panel document viewer component.
    
    Returns:
        A Dash Mantine Paper containing the document viewer
    """
    return dmc.Paper([
        dmc.Stack([
            dmc.Group([
                dmc.Title("Document", order=5),
                html.Div(id="document-metadata", style={"color": "#868e96", "fontSize": "0.875rem"})
            ], justify="space-between"),
            html.Div(
                id="document-text-container",
                style={
                    "maxHeight": "70vh",
                    "overflowY": "auto",
                    "backgroundColor": "#f8f9fa",
                    "border": "1px solid #dee2e6",
                    "borderRadius": "4px"
                },
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
                            "userSelect": "text",
                            "cursor": "text"
                        }
                    )
                ]
            )
        ], gap="md")
    ], p="md", shadow="sm", radius="md", style={"height": "100%"})


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
            id="document-text",
            style={
                "whiteSpace": "pre-wrap",
                "fontFamily": "monospace",
                "fontSize": "14px",
                "lineHeight": "1.6",
                "padding": "10px",
                "userSelect": "text",
                "cursor": "text"
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
            html.Span(
                [
                    html.Mark(
                        text[start:end],
                        style={
                            "backgroundColor": color,
                            "padding": "0",
                            "borderRadius": "3px",
                            "boxShadow": "inset 0 0 0 1px rgba(0,0,0,0.12)",
                            "cursor": "pointer"
                        },
                        id={"type": "span-highlight", "index": i}
                    ),
                    html.Span(
                        [
                            html.Span(
                                entity_type,
                                className="span-annotation-label",
                                style={"backgroundColor": color}
                            ),
                            html.Button(
                                "x",
                                id={
                                    "type": "delete-span",
                                    "start": start,
                                    "end": end,
                                    "entity": entity_type
                                },
                                className="span-annotation-delete",
                                title="Remove span"
                            )
                        ],
                        className="span-annotation-pop"
                    )
                ],
                className="span-annotation",
                tabIndex=0,
                **{"data-span-annotation": "true"}
            )
        )
        
        last_end = end
    
    # Add remaining text
    if last_end < len(text):
        children.append(text[last_end:])
    
    return html.Pre(
        children,
        id="document-text",
        style={
            "whiteSpace": "pre-wrap",
            "fontFamily": "monospace",
            "fontSize": "14px",
            "lineHeight": "1.6",
            "padding": "10px",
            "userSelect": "text",
            "cursor": "text"
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
            dmc.Paper([
                dmc.Group([
                    dmc.Badge(
                        entity_type,
                        color="gray",
                        variant="filled",
                        style={"backgroundColor": color, "color": "#000"}
                    ),
                    dmc.Text(f'"{text}"', style={"fontFamily": "monospace", "flex": 1}),
                    dmc.ActionIcon(
                        "×",
                        color="red",
                        variant="subtle",
                        size="sm",
                        id={"type": "delete-span", "index": i},
                        style={"fontSize": "20px"}
                    )
                ], justify="space-between", align="center")
            ], p="xs", withBorder=True, radius="sm", mb="xs")
        )
    
    return html.Div([
        dmc.Title("Text Annotations:", order=6, mt="md", mb="sm"),
        dmc.Stack(items, gap="xs")
    ])
