"""Document and metadata models for Tater."""
from typing import Optional, Any
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """System-managed metadata for tracking annotation progress."""
    
    flagged: bool = Field(False, description="Whether this document is flagged for review")
    notes: str = Field("", description="Annotator notes about this document")
    visited: bool = Field(False, description="Whether this document has been viewed")
    annotation_seconds: float = Field(0.0, description="Total time spent annotating this document (seconds)")


class Document(BaseModel):
    """Represents a document to be annotated."""
    
    id: str = Field(description="Unique document identifier")
    file_path: str = Field(description="Path to the document file")
    name: Optional[str] = Field(None, description="Human-readable document name")
    info: Optional[dict[str, Any]] = Field(None, description="User-supplied metadata/information")
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata, description="System-managed metadata")
    
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
            FileNotFoundError: If the file doesn't exist
            IOError: If there's an error reading the file
        """
        with open(self.file_path, 'r', encoding='utf-8') as f:
            return f.read()
