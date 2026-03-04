"""Tater 2.0: Pydantic-First Document Annotation System."""
from tater.models.span import SpanAnnotation
from tater.widgets.span import SpanAnnotationWidget, EntityType
from tater.loaders import load_schema, parse_schema, widgets_from_model

__all__ = [
    "SpanAnnotation",
    "SpanAnnotationWidget",
    "EntityType",
    "load_schema",
    "parse_schema",
    "widgets_from_model",
]
