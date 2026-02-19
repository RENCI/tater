"""Data loading utilities."""
import json
import csv
from pathlib import Path
from typing import List, Tuple
import pandas as pd

from data.validator import (
    Document, DocumentList, AnnotationSchema,
    DocumentMetadata
)


def load_documents_from_json(file_path: str) -> List[Document]:
    """Load documents from JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    doc_list = DocumentList(**data)
    return doc_list.documents


def load_documents_from_csv(file_path: str) -> List[Document]:
    """Load documents from CSV file."""
    df = pd.read_csv(file_path)
    
    if 'file_path' not in df.columns:
        raise ValueError("CSV must contain 'file_path' column")
    
    documents = []
    for _, row in df.iterrows():
        metadata = None
        if 'metadata' in df.columns and pd.notna(row['metadata']):
            try:
                metadata = json.loads(row['metadata'])
            except json.JSONDecodeError:
                metadata = None
        
        doc = Document(
            file_path=row['file_path'],
            metadata=metadata
        )
        documents.append(doc)
    
    return documents


def load_documents(file_path: str) -> List[Document]:
    """Load documents from CSV or JSON file."""
    ext = Path(file_path).suffix.lower()
    
    if ext == '.json':
        return load_documents_from_json(file_path)
    elif ext == '.csv':
        return load_documents_from_csv(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Use .json or .csv")


def load_schema(file_path: str) -> AnnotationSchema:
    """Load annotation schema from JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    return AnnotationSchema(**data)


def load_document_text(file_path: str) -> Tuple[str, bool]:
    """
    Load text content from a document file.
    
    Returns:
        Tuple of (text_content, success)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, True
    except FileNotFoundError:
        return f"Error: File not found: {file_path}", False
    except Exception as e:
        return f"Error loading file: {str(e)}", False
