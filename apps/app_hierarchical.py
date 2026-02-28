"""Hierarchical label annotation example using a breast pathology ontology.

Run with: python apps/app_hierarchical.py --documents data/documents.json
"""
from typing import Optional
from pydantic import BaseModel

from tater import TaterApp, parse_args
from tater.widgets import HierarchicalLabelFullWidget, HierarchicalLabelCompactWidget, build_tree_from_yaml


class PathologyAnnotation(BaseModel):
    diagnosis: Optional[str] = None
    secondary_diagnosis: Optional[str] = None


def main() -> None:
    args = parse_args()

    ontology = build_tree_from_yaml("data/breast_fdx_ontology.yaml")

    widgets = [
        HierarchicalLabelCompactWidget(
            schema_field="diagnosis",
            label="Diagnosis",
            description="Navigate the ontology to select a diagnosis.",
            hierarchy=ontology,
            searchable=True,
        ),
        HierarchicalLabelFullWidget(
            schema_field="secondary_diagnosis",
            label="Secondary Diagnosis",
            description="Navigate the ontology to select a secondary diagnosis.",
            hierarchy=ontology,
            searchable=True,
        ),
    ]

    app = TaterApp(
        title="tater - hierarchical",
        theme="light",
        annotations_path=args.annotations,
        schema_model=PathologyAnnotation,
    )

    if not app.load_documents(args.documents):
        return

    app.set_annotation_widgets(widgets)
    app.run(debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
