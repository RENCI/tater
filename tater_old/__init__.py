"""Tater - Text Annotation Tool for Easy Research."""

__version__ = "0.1.0"

from .ui.app import TaterApp
from .ui.cli import parse_args
from .models.document import Document, DocumentList
from .models.spec import AnnotationSpec
from .models.schema import DataField, AnnotationSchema
from .models.ui_config import WidgetConfig, UIConfig
from .loaders import load_document_text

__all__ = [
    "TaterApp",
    "parse_args",
    "Document",
    "DocumentList",
    "AnnotationSpec",
    "DataField",
    "AnnotationSchema",
    "WidgetConfig",
    "UIConfig",
    "load_document_text",
]
