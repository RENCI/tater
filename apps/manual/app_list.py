"""List example - demonstrates repeatable nested models."""
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

from tater import TaterApp, parse_args
from tater.widgets import SegmentedControlWidget, ListableWidget


class Pet(BaseModel):
    kind: Optional[Literal["cat", "dog", "fish"]] = None


class ListAnnotation(BaseModel):
    pets: List[Pet] = Field(default_factory=list)


def main() -> None:
    args = parse_args()

    pet_item_widgets = [
        SegmentedControlWidget(
            schema_field="kind",
            label="Pet Type",
        ),
    ]

    widgets = [
        ListableWidget(
            schema_field="pets",
            label="Pets",
            item_widgets=pet_item_widgets,
            add_label="Add Pet",
            delete_label="Delete Pet",
            initial_count=1,
        ),
    ]

    app = TaterApp(
        title="tater - list",
        theme="light",
        annotations_path=args.annotations,
        schema_model=ListAnnotation,
    )

    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets)
    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
