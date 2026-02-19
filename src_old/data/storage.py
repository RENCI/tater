"""Storage utilities for annotations."""
import json
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from data.validator import AnnotationCollection, DocumentAnnotation
from utils.config import config


def load_annotations(file_path: Optional[str] = None) -> AnnotationCollection:
    """
    Load annotations from file.
    
    Args:
        file_path: Path to annotations file. If None, uses config default.
    
    Returns:
        AnnotationCollection instance
    """
    if file_path is None:
        file_path = config.annotations_path
    
    if not Path(file_path).exists():
        # Return empty collection with default schema version
        return AnnotationCollection(schema_version="1.0")
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return AnnotationCollection(**data)
    except json.JSONDecodeError:
        # Corrupted file - backup and return empty
        backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy(file_path, backup_path)
        print(f"Warning: Corrupted annotation file backed up to {backup_path}")
        return AnnotationCollection(schema_version="1.0")
    except Exception as e:
        print(f"Error loading annotations: {e}")
        return AnnotationCollection(schema_version="1.0")


def save_annotations(
    collection: AnnotationCollection,
    file_path: Optional[str] = None
) -> bool:
    """
    Save annotations to file using atomic write.
    
    Args:
        collection: AnnotationCollection to save
        file_path: Path to save to. If None, uses config default.
    
    Returns:
        True if successful, False otherwise
    """
    if file_path is None:
        file_path = config.annotations_path
    
    # Ensure directory exists
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Atomic write: write to temp file then rename
    temp_path = f"{file_path}.tmp"
    
    try:
        with open(temp_path, 'w') as f:
            json.dump(
                collection.model_dump(),
                f,
                indent=2,
                ensure_ascii=False
            )
        
        # Atomic rename
        shutil.move(temp_path, file_path)
        return True
    
    except Exception as e:
        print(f"Error saving annotations: {e}")
        # Clean up temp file if it exists
        if Path(temp_path).exists():
            Path(temp_path).unlink()
        return False


def get_or_create_annotation(
    collection: AnnotationCollection,
    file_path: str,
    annotator: str
) -> DocumentAnnotation:
    """
    Get existing annotation for a document or create a new one.
    
    Args:
        collection: The annotation collection
        file_path: Path to the document
        annotator: Name/email of annotator
    
    Returns:
        DocumentAnnotation instance
    """
    existing = collection.get_annotation(file_path)
    if existing:
        return existing
    
    # Create new annotation
    return DocumentAnnotation(
        file_path=file_path,
        annotator=annotator,
        status="not_started"
    )
