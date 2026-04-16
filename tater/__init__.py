"""Tater 2.0: Pydantic-First Document Annotation System."""
from tater.models.span import SpanAnnotation
from tater.widgets.span import SpanBaseWidget, SpanAnnotationWidget, SpanPopupWidget, EntityType
from tater.loaders import load_schema, parse_schema, widgets_from_model

__all__ = [
    "SpanAnnotation",
    "SpanBaseWidget",
    "SpanAnnotationWidget",
    "SpanPopupWidget",
    "EntityType",
    "load_schema",
    "parse_schema",
    "widgets_from_model",
]
