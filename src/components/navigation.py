"""Navigation component for document navigation."""
from dash import html, dcc
import dash_bootstrap_components as dbc
from typing import List, Optional
from pathlib import Path


def create_navigation_bar(
    total_docs: int = 0,
    current_index: int = 0,
    documents: Optional[List] = None
) -> dbc.Card:
    """
    Create navigation controls.
    
    Args:
        total_docs: Total number of documents
        current_index: Current document index (0-based)
        documents: List of Document objects
    
    Returns:
        A Dash Bootstrap Card with navigation controls
    """
    if documents is None:
        documents = []
    
    # Create dropdown options
    dropdown_options = []
    for i, doc in enumerate(documents):
        filename = Path(doc.file_path).name
        dropdown_options.append({
            "label": f"{i + 1}. {filename}",
            "value": i
        })
    
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H6("Navigation", className="mb-3"),
                    dbc.ButtonGroup([
                        dbc.Button(
                            "← Previous",
                            id="prev-button",
                            color="secondary",
                            disabled=current_index <= 0
                        ),
                        dbc.Button(
                            "Next →",
                            id="next-button",
                            color="secondary",
                            disabled=current_index >= total_docs - 1
                        )
                    ], className="w-100 mb-3"),
                    dbc.Select(
                        id="document-selector",
                        options=dropdown_options,
                        value=current_index,
                        className="mb-3"
                    ),
                    html.Div(
                        id="progress-display",
                        children=create_progress_display(
                            total_docs,
                            current_index,
                            0, 0, 0, 0
                        )
                    )
                ])
            ])
        ], style={"padding": "15px"})
    ])


def create_progress_display(
    total_docs: int,
    current_index: int,
    completed: int,
    in_progress: int,
    not_started: int,
    flagged: int
) -> html.Div:
    """
    Create progress display showing stats.
    
    Args:
        total_docs: Total documents
        current_index: Current index
        completed: Number completed
        in_progress: Number in progress
        not_started: Number not started
        flagged: Number flagged
    
    Returns:
        Div with progress information
    """
    if total_docs == 0:
        progress_pct = 0
    else:
        progress_pct = (completed / total_docs) * 100
    
    return html.Div([
        html.P(
            f"Document {current_index + 1} of {total_docs}",
            className="mb-2 fw-bold"
        ),
        dbc.Progress(
            value=progress_pct,
            className="mb-3",
            style={"height": "20px"}
        ),
        html.Div([
            html.Small([
                html.Span("✓ Completed: ", className="text-success"),
                html.Span(str(completed), className="fw-bold")
            ], className="d-block"),
            html.Small([
                html.Span("⋯ In Progress: ", className="text-warning"),
                html.Span(str(in_progress), className="fw-bold")
            ], className="d-block"),
            html.Small([
                html.Span("○ Not Started: ", className="text-muted"),
                html.Span(str(not_started), className="fw-bold")
            ], className="d-block"),
            html.Small([
                html.Span("⚑ Flagged: ", className="text-danger"),
                html.Span(str(flagged), className="fw-bold")
            ], className="d-block")
        ], className="small")
    ])


def update_navigation_state(
    current_index: int,
    total_docs: int,
    documents: List
) -> tuple:
    """
    Update navigation button states.
    
    Args:
        current_index: Current document index
        total_docs: Total number of documents
        documents: List of documents
    
    Returns:
        Tuple of (prev_disabled, next_disabled, dropdown_value)
    """
    prev_disabled = current_index <= 0
    next_disabled = current_index >= total_docs - 1
    
    return prev_disabled, next_disabled, current_index
