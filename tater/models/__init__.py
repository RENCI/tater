"""Core Tater data models."""

from .document import Document, DocumentList, DocumentMetadata
from .schema import DataField, AnnotationSchema
from .ui_config import WidgetConfig, UIConfig
from .spec import AnnotationSpec

__all__ = [
    "Document", 
    "DocumentList", 
    "DocumentMetadata",
    "DataField",
    "AnnotationSchema",
    "WidgetConfig",
    "UIConfig",
    "AnnotationSpec"
]
