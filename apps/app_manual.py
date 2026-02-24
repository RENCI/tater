"""Manual widget hookup example using Pydantic schema.

This app shows how to:
1. Define annotation types once
2. Use them in both the Pydantic schema and widgets
3. Use TaterApp without load_schema()
"""
from typing import Optional, Literal
from pydantic import BaseModel

from tater import TaterApp, parse_args
from tater.ui.widgets import SegmentedControlWidget, RadioGroupWidget


# Define type once
PetType = Literal["cat", "dog", "fish"]


class PetAnnotationSchema(BaseModel):
    """Annotation schema for pet documents."""
    pet_type: Optional[PetType] = None


def main() -> None:
    args = parse_args()
    
    # Define widgets manually using the same type options
    widgets = [
        SegmentedControlWidget(
            schema_id="pet_type",
            label="Pet Type",
            description="Select the type of pet mentioned in the document",
            options=list(PetType.__args__),
            default=None
        ),
        # Alternative: use RadioGroup instead
        # RadioGroupWidget(
        #     schema_id="pet_type",
        #     label="Pet Type",
        #     options=list(PetType.__args__),
        #     orientation="horizontal"
        # )
    ]

    app = TaterApp(title="Manual Widget Hookup", theme="light")
    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets, title="Annotations")
    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
