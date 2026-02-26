"""Document loader for Tater."""
from pathlib import Path
from typing import Optional


def load_document_text(file_path: str) -> tuple[str, bool]:
    """Load text content from a document file.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Tuple of (content, success)
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"Error: File not found: {file_path}", False
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, True
    except Exception as e:
        return f"Error loading document: {str(e)}", False
