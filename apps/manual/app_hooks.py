"""Demonstrates the on_save hook and the escape-hatch callback pattern.

on_save hook
------------
After every save, ``log_save`` appends a JSON line to an audit log file
sitting next to the annotations file.  The hook receives the doc ID and the
full annotation model, so it has everything needed for logging, syncing to an
external system, etc.

Escape hatch
------------
When ``is_relevant`` is unchecked, the escape-hatch callback automatically
clears ``sentiment`` back to None.  This is a cross-field value-derivation
rule that can't be expressed as a Tater widget declaration.  It's registered
directly on ``app.app`` (the underlying Dash instance) after
``set_annotation_widgets`` so that Tater's component IDs are already finalised.
"""
import json
from pathlib import Path
from typing import Optional, Literal

from pydantic import BaseModel
from dash import Input, Output, no_update

from tater import TaterApp, parse_args
from tater.widgets import SegmentedControlWidget, CheckboxWidget


class SimpleAnnotation(BaseModel):
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    is_relevant: bool = False


def main() -> None:
    args = parse_args()

    # ------------------------------------------------------------------
    # on_save hook: append one JSON line per save to an audit log.
    # ------------------------------------------------------------------
    audit_path = (
        Path(args.annotations).parent / "audit.jsonl"
        if args.annotations
        else Path("audit.jsonl")
    )

    def log_save(doc_id: str, annotation: SimpleAnnotation) -> None:
        with open(audit_path, "a") as f:
            f.write(json.dumps({"doc": doc_id, **annotation.model_dump()}) + "\n")

    # ------------------------------------------------------------------
    # App + widgets
    # ------------------------------------------------------------------
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

    app = TaterApp(
        title="tater - hooks",
        theme="light",
        annotations_path=args.annotations,
        schema_model=SimpleAnnotation,
        on_save=log_save,
    )

    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets)

    # ------------------------------------------------------------------
    # Escape hatch: cross-field derivation that Tater can't express
    # declaratively.  Register directly on the underlying Dash app after
    # set_annotation_widgets() so that component IDs are finalised.
    # allow_duplicate=True is required because Tater's doc-loading callback
    # also writes to widget value outputs.
    # ------------------------------------------------------------------
    @app.app.callback(
        Output("annotation-sentiment", "value", allow_duplicate=True),
        Input("annotation-is_relevant", "checked"),
        prevent_initial_call=True,
    )
    def clear_sentiment_when_irrelevant(is_relevant):
        """Clear sentiment whenever the document is marked as not relevant."""
        if not is_relevant:
            return None
        return no_update

    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
