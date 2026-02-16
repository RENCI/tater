"""Navigation component for document navigation."""
from dash import html, dcc
import dash_mantine_components as dmc
from typing import List, Optional
from pathlib import Path


def create_navigation_bar(
    total_docs: int = 0,
    current_index: int = 0,
    documents: Optional[List] = None
) -> dmc.Paper:
    """
    Create navigation controls.
    
    Args:
        total_docs: Total number of documents
        current_index: Current document index (0-based)
        documents: List of Document objects
    
    Returns:
        A Dash Mantine Paper with navigation controls
    """
    if documents is None:
        documents = []
    
    # Create dropdown options
    dropdown_options = []
    for i, doc in enumerate(documents):
        filename = Path(doc.file_path).name
        dropdown_options.append({
            "label": f"{i + 1}. {filename}",
            "value": str(i)
        })
    
    return dmc.Paper([
        dmc.Stack([
            dmc.Title("Navigation", order=6),
            dmc.Group([
                dmc.Button(
                    "← Previous",
                    id="prev-button",
                    variant="default",
                    disabled=current_index <= 0,
                    style={"flex": 1}
                ),
                dmc.Button(
                    "Next →",
                    id="next-button",
                    variant="default",
                    disabled=current_index >= total_docs - 1,
                    style={"flex": 1}
                )
            ], grow=True),
            dmc.Select(
                id="document-selector",
                data=dropdown_options,
                value=str(current_index) if dropdown_options else None,
                placeholder="Select document"
            ),
            html.Div(
                id="progress-display",
                children=create_progress_display(
                    total_docs,
                    current_index,
                    0, 0, 0, 0
                )
            )
        ], gap="md")
    ], p="md", shadow="sm", radius="md")


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
        dmc.Text(
            f"Document {current_index + 1} of {total_docs}",
            fw=700,
            mb="sm"
        ),
        dmc.Progress(
            value=progress_pct,
            size="lg",
            mb="md"
        ),
        dmc.Stack([
            dmc.Text([
                dmc.Text("✓ Completed: ", c="green", span=True),
                dmc.Text(str(completed), fw=700, span=True)
            ], size="sm"),
            dmc.Text([
                dmc.Text("⋯ In Progress: ", c="yellow", span=True),
                dmc.Text(str(in_progress), fw=700, span=True)
            ], size="sm"),
            dmc.Text([
                dmc.Text("○ Not Started: ", c="gray", span=True),
                dmc.Text(str(not_started), fw=700, span=True)
            ], size="sm"),
            dmc.Text([
                dmc.Text("⚑ Flagged: ", c="red", span=True),
                dmc.Text(str(flagged), fw=700, span=True)
            ], size="sm")
        ], gap="xs")
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
