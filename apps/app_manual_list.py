"""List example - demonstrates repeatable nested models."""
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

from tater import TaterApp, parse_args
from tater.widgets import SegmentedControlWidget, ListableWidget


# Define types
PetType = Literal["cat", "dog", "fish"]


class Pet(BaseModel):
    """Model for a single pet."""
    kind: Optional[PetType] = None


class ListAnnotation(BaseModel):
    """Annotation schema with a list of nested models."""
    pets: List[Pet] = Field(default_factory=list)


def main() -> None:
    args = parse_args()
    
    # Define the widget template for a single pet
    pet_item_widgets = [
        SegmentedControlWidget(
            schema_field="kind",  # Becomes "pets.0.kind", "pets.1.kind", etc.
            label="Pet Type",
            options=["cat", "dog", "fish"],
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
        title="List Annotation",
        theme="light",
        annotations_path=args.annotations,
        schema_model=ListAnnotation
    )
    
    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets)
    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
