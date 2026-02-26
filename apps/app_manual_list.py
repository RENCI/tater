"""List example - demonstrates repeatable nested models.

NOTE: ListableWidget is not yet implemented! This shows the intended API.

Demonstrates using ListableWidget to handle lists of nested Pydantic models.
"""
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

from tater import TaterApp, parse_args
from tater.widgets import SegmentedControlWidget, RadioGroupWidget, GroupWidget
# from tater.widgets import ListableWidget  # TODO: Not yet implemented!


# Define types
PetType = Literal["cat", "dog", "fish"]


class Pet(BaseModel):
    """Model for a single pet."""
    kind: Optional[PetType] = None
    name: str = ""


class ListAnnotation(BaseModel):
    """Annotation schema with a list of nested models."""
    owner_name: str = ""
    pets: List[Pet] = Field(default_factory=list)


def main() -> None:
    args = parse_args()
    
    # TODO: This is the intended API for ListableWidget
    # Currently not implemented!
    
    # Define the widget template for a single pet
    # pet_widget = GroupWidget(
    #     schema_id="",  # Empty - ListableWidget handles indexing
    #     label="Pet",
    #     children=[
    #         SegmentedControlWidget(
    #             schema_id="kind",  # Becomes "pets[0].kind", "pets[1].kind", etc.
    #             label="Pet Type",
    #             options=["cat", "dog", "fish"],
    #         ),
    #         # TextInputWidget would go here for "name"
    #     ]
    # )
    
    # widgets = [
    #     # TextInputWidget for owner_name would go here
    #     ListableWidget(
    #         schema_id="pets",
    #         label="Pets",
    #         widget=pet_widget,
    #         add_label="Add Pet",
    #         delete_label="Delete Pet",
    #     ),
    # ]
    
    print("ERROR: ListableWidget is not yet implemented!")
    print("This file demonstrates the intended API for handling lists.")
    print("Please use app_simple.py, app_nested.py, or app_deep_nested.py instead.")
    return

    # app = TaterApp(
    #     title="List Annotation",
    #     theme="light",
    #     annotations_path=args.annotations
    # )
    # 
    # if not app.load_documents(args.documents):
    #     return
    # 
    # app.set_annotation_widgets(widgets)
    # app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
