"""Simple annotation example with a single-choice and a boolean widget."""
from typing import Optional, Literal
from pydantic import BaseModel

from tater import TaterApp, parse_args
from tater.widgets import SegmentedControlWidget, CheckboxWidget


class SimpleAnnotation(BaseModel):
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    is_relevant: bool = False


def main() -> None:
    args = parse_args()

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
        title="tater - simple",
        theme="light",
        annotations_path=args.annotations,
        schema_model=SimpleAnnotation,
    )

    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets)
    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
