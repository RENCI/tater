"""Simple annotation example using widgets_from_model with a single override.

Demonstrates the mixed default/override pattern: sentiment uses an explicit
RadioGroupWidget while is_relevant gets the default CheckboxWidget inferred
from the model annotation.
"""
from typing import Optional, Literal
from pydantic import BaseModel

from tater import TaterApp, parse_args, widgets_from_model
from tater.widgets import RadioGroupWidget


class SimpleAnnotation(BaseModel):
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    is_relevant: bool = False


def main() -> None:
    args = parse_args()

    app = TaterApp(
        title="tater - simple (defaults)",
        theme="light",
        annotations_path=args.annotations,
        schema_model=SimpleAnnotation,
    )

    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(
        widgets_from_model(
            SimpleAnnotation,
            overrides=[
                RadioGroupWidget(
                    schema_field="sentiment",
                    label="Sentiment",
                    description="Overall sentiment of the document",
                    required=True,
                    vertical=True,
                ),
            ],
        )
    )
    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
