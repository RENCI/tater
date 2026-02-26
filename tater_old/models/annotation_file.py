"""Annotation file format and serialization."""
from typing import Any
from pydantic import BaseModel, Field, RootModel


class DocumentMetadata(BaseModel):
    """Metadata about the annotation process (not part of user data)."""
    flagged: bool = Field(default=False, description="Whether document is flagged for review")
    notes: str = Field(default="", description="Annotator notes")
    visited: bool = Field(default=False, description="Whether document has been viewed")


class DocumentRecord(BaseModel):
    """A single document with its annotations and metadata."""
    document: dict = Field(..., description="Document info (loaded from documents file)")
    annotations: dict = Field(default_factory=dict, description="User-provided annotation data")
    document_metadata: DocumentMetadata = Field(
        default_factory=DocumentMetadata,
        description="Tater system metadata (flagged, notes, visited)"
    )


class AnnotationFile(RootModel[list[DocumentRecord]]):
    """Root annotation file format (list of document records)."""
    root: list[DocumentRecord] = Field(
        default_factory=list,
        description="List of documents with their annotations and metadata"
    )
    
    @classmethod
    def from_documents_and_data(
        cls,
        documents: list[dict],
        annotations_data: dict,
        metadata_data: dict
    ) -> "AnnotationFile":
        """Create AnnotationFile from separate documents, annotations, and metadata."""
        records: list[DocumentRecord] = []
        for i, doc in enumerate(documents):
            doc_key = str(i)
            record = DocumentRecord(
                document=doc,
                annotations=annotations_data.get(doc_key, {}),
                document_metadata=DocumentMetadata(
                    **metadata_data.get(doc_key, {})
                )
            )
            records.append(record)
        return cls(records)
    
    def to_separate_stores(self) -> tuple[dict, dict]:
        """Split back into annotations and metadata stores.
        
        Returns:
            (annotations_store, metadata_store) where keys are doc indices
        """
        annotations_store = {}
        metadata_store = {}
        
        for i, record in enumerate(self.root):
            doc_key = str(i)
            annotations_store[doc_key] = record.annotations
            metadata_store[doc_key] = record.document_metadata.model_dump()
        
        return annotations_store, metadata_store
