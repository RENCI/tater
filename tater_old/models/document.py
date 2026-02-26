"""Document models for Tater."""
from typing import Optional, Dict, Any
from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    """Metadata for a document."""
    class Config:
        extra = "allow"  # Allow arbitrary fields


class Document(BaseModel):
    """Document model."""
    file_path: str
    metadata: Optional[DocumentMetadata | Dict[str, Any]] = None


class DocumentList(BaseModel):
    """List of documents."""
    documents: list[Document]
    
    @classmethod
    def from_json_file(cls, path: str) -> "DocumentList":
        """Load document list from JSON file."""
        import json
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    @classmethod
    def from_csv_file(cls, path: str) -> "DocumentList":
        """Load document list from CSV file."""
        import csv
        with open(path, 'r') as f:
            reader = csv.DictReader(f)
            documents = []
            for row in reader:
                file_path = row.pop('file_path')
                metadata = {k: v for k, v in row.items() if v} if row else None
                documents.append(Document(file_path=file_path, metadata=metadata))
        return cls(documents=documents)
