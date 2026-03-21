"""Document and metadata models for tater."""
from typing import Optional, Any, Literal
from pydantic import BaseModel, Field, model_validator


class DocumentMetadata(BaseModel):
    """System-managed metadata for tracking annotation progress."""

    flagged: bool = Field(False, description="Whether this document is flagged for review")
    notes: str = Field("", description="Annotator notes about this document")
    visited: bool = Field(False, description="Whether this document has been viewed")
    annotation_seconds: float = Field(0.0, description="Total time spent annotating this document (seconds)")
    status: Literal["not_started", "in_progress", "complete"] = Field("not_started", description="Annotation status")


class Document(BaseModel):
    """Represents a document to be annotated."""
    
    id: str = Field(description="Unique document identifier")
    file_path: Optional[str] = Field(None, description="Path to the document file")
    text: Optional[str] = Field(None, description="Document text content (inline)")
    name: Optional[str] = Field(None, description="Human-readable document name")
    info: Optional[dict[str, Any]] = Field(None, description="User-supplied metadata/information")
    
    @model_validator(mode="after")
    def validate_content_source(self) -> "Document":
        """Ensure exactly one of file_path or text is provided."""
        has_file_path = bool(self.file_path)
        has_text = bool(self.text)
        
        if has_file_path and has_text:
            raise ValueError("Cannot provide both 'file_path' and 'text'; provide exactly one")
        
        if not has_file_path and not has_text:
            raise ValueError("Must provide either 'file_path' or 'text'")
        
        return self
    
    def display_name(self) -> str:
        """
        Get a human-readable display name for this document.
        
        Returns (in priority order):
        1. The 'name' field if provided
        2. The filename from 'file_path' if provided
        3. The document 'id', which is auto-generated if not provided
        """
        if self.name:
            return self.name
        if self.file_path:
            return self.file_path.split('/')[-1]
        return self.id
    
    @classmethod
    def from_dict(cls, doc_dict: dict[str, Any], index: int = 0) -> "Document":
        """
        Create a Document from a dictionary, handling normalization.
        
        Args:
            doc_dict: Dictionary containing document data
            index: Document index for auto-generating ID if needed
            
        Returns:
            Validated Document instance
        """
        # Make a copy to avoid mutating original
        data = doc_dict.copy()
        
        # Generate ID if not provided
        if "id" not in data:
            data["id"] = f"doc_{index:03d}"
        
        return cls(**data)
    
    def load_content(self) -> str:
        """
        Load and return the document's text content.
        
        Returns:
            The document's text content
            
        Raises:
            FileNotFoundError: If file_path is set but the file doesn't exist
            IOError: If there's an error reading the file
        """
        # If text is provided inline, return it directly
        if self.text is not None:
            return self.text
        
        # Otherwise, load from file_path
        assert self.file_path is not None  # Guaranteed by validate_content_source
        with open(self.file_path, 'r', encoding='utf-8') as f:
            return f.read()
