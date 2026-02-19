"""Data models and validation using Pydantic."""
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class DocumentMetadata(BaseModel):
    """Metadata for a document."""
    date: Optional[str] = None
    patient_id: Optional[str] = None
    
    class Config:
        extra = "allow"  # Allow additional fields


class Document(BaseModel):
    """Document model."""
    file_path: str
    metadata: Optional[DocumentMetadata | Dict[str, Any]] = None


class DocumentList(BaseModel):
    """List of documents from JSON."""
    documents: List[Document]


class AnnotationType(BaseModel):
    """Schema for a single annotation type."""
    id: str
    label: str
    type: Literal["single_choice", "multi_choice", "span_annotation", "free_text"]
    options: Optional[List[str]] = None
    entity_types: Optional[List[str]] = None
    required: bool = False
    description: Optional[str] = None
    
    @field_validator("options")
    @classmethod
    def validate_options(cls, v, info):
        """Validate options for choice types."""
        annotation_type = info.data.get("type")
        if annotation_type in ["single_choice", "multi_choice"] and not v:
            raise ValueError(f"Options required for {annotation_type}")
        return v
    
    @field_validator("entity_types")
    @classmethod
    def validate_entity_types(cls, v, info):
        """Validate entity_types for span_annotation."""
        annotation_type = info.data.get("type")
        if annotation_type == "span_annotation" and not v:
            raise ValueError("entity_types required for span_annotation")
        return v


class AnnotationSchema(BaseModel):
    """Schema defining annotation types."""
    schema_version: str
    annotation_types: List[AnnotationType]


class SpanAnnotation(BaseModel):
    """A text span annotation."""
    text: str
    start: int
    end: int
    entity_type: str


class DocumentAnnotation(BaseModel):
    """Annotations for a single document."""
    file_path: str
    annotator: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    flagged_for_review: bool = False
    annotations: Dict[str, Any] = Field(default_factory=dict)
    status: Literal["not_started", "in_progress", "completed", "flagged"] = "not_started"


class CollectionMetadata(BaseModel):
    """Metadata for the annotation collection."""
    created: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    last_modified: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class AnnotationCollection(BaseModel):
    """Collection of all annotations."""
    schema_version: str
    collection_metadata: CollectionMetadata = Field(default_factory=CollectionMetadata)
    annotations: List[DocumentAnnotation] = Field(default_factory=list)
    
    def get_annotation(self, file_path: str) -> Optional[DocumentAnnotation]:
        """Get annotation for a specific file."""
        for ann in self.annotations:
            if ann.file_path == file_path:
                return ann
        return None
    
    def update_annotation(self, doc_ann: DocumentAnnotation):
        """Update or add annotation for a document."""
        # Update timestamp
        doc_ann.timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Find and update existing, or append new
        for i, ann in enumerate(self.annotations):
            if ann.file_path == doc_ann.file_path:
                self.annotations[i] = doc_ann
                self.collection_metadata.last_modified = datetime.utcnow().isoformat() + "Z"
                return
        
        # Not found, append
        self.annotations.append(doc_ann)
        self.collection_metadata.last_modified = datetime.utcnow().isoformat() + "Z"
