"""Demonstrates the on_save hook and the escape-hatch callback pattern.

on_save hook
------------
``on_save`` is not defined at module level here because its audit path
depends on the app's annotations path, which is only known at runtime.
Instead, ``configure`` sets ``app.on_save`` after the app is created.

Escape hatch
------------
``configure`` also registers a Dash callback that clears ``sentiment``
whenever ``is_relevant`` is unchecked — a cross-field rule that can't be
expressed as a widget declaration.  It runs after ``set_annotation_widgets``
so that Tater's component IDs are already finalised.
"""
import json
from pathlib import Path
from typing import Optional, Literal

from pydantic import BaseModel

from tater.widgets import SegmentedControlWidget, CheckboxWidget


class Schema(BaseModel):
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    is_relevant: bool = False


title = "tater - hooks"

widgets = [
    SegmentedControlWidget(
        schema_field="sentiment",
        label="Sentiment",
        description="Overall sentiment of the document",
        required=True,
    ),
    CheckboxWidget(
        schema_field="is_relevant",
        label="Relevant?",
        description="Is this document relevant?",
    ),
]


def configure(app) -> None:
    # Wire up on_save using the app's annotations path.
    audit_path = (
        Path(app.annotations_path).parent / "audit.jsonl"
        if app.annotations_path
        else Path("audit.jsonl")
    )

    def _log_save(doc_id: str, annotation: SimpleAnnotation) -> None:
        with open(audit_path, "a") as f:
            f.write(json.dumps({"doc": doc_id, **annotation.model_dump()}) + "\n")

    app.on_save = _log_save

    # Escape hatch: clear sentiment when document is marked not relevant.
    from dash import Input, Output, no_update

    @app.app.callback(
        Output("annotation-sentiment", "value", allow_duplicate=True),
        Input("annotation-is_relevant", "checked"),
        prevent_initial_call=True,
    )
    def clear_sentiment_when_irrelevant(is_relevant):
        if not is_relevant:
            return None
        return no_update
