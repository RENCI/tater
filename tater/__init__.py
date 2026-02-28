"""Tater 2.0: Pydantic-First Document Annotation System."""
from tater.ui.tater_app import TaterApp
from tater.ui.cli import parse_args
from tater.models.span import SpanAnnotation
from tater.widgets.span import SpanAnnotationWidget, EntityType
from tater.loaders import load_schema, parse_schema

__all__ = [
    "TaterApp",
    "parse_args",
    "SpanAnnotation",
    "SpanAnnotationWidget",
    "EntityType",
    "load_schema",
    "parse_schema",
]
