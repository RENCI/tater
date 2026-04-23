"""Document loader — supports JSON, CSV, TSV, and Excel (.xlsx/.xls) formats.

Column convention for tabular formats:
  id          — unique document identifier (auto-generated as doc_000, doc_001, …  if absent)
  text        — inline document text
  file_path   — path to document file (exactly one of text / file_path required)
  name        — human-readable display name (optional)
  <anything>  — any other column is added to the ``info`` dict; empty cells are dropped

For Excel, the first sheet is used. All values in the ``info`` dict (and the
``id`` / ``name`` / ``file_path`` fields) are converted to strings; integer-like
floats (e.g. ``12345.0``) are written as ``"12345"``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tater.models.document import Document


_RESERVED = {"id", "text", "file_path", "name"}
_SUPPORTED_SUFFIXES = {".json", ".csv", ".tsv", ".xlsx", ".xls"}


def load_documents(source: str | Path) -> list[Document]:
    """Load documents from a file, dispatching on extension.

    Args:
        source: Path to a documents file (.json, .csv, .tsv, .xlsx, or .xls).

    Returns:
        List of validated :class:`~tater.models.document.Document` instances.

    Raises:
        ValueError: Unrecognised extension or invalid content.
        FileNotFoundError: File does not exist.
        ImportError: ``pandas`` / ``openpyxl`` not installed (tabular formats only).
    """
    path = Path(source)
    suffix = path.suffix.lower()
    if suffix == ".json":
        return _load_json(path)
    if suffix == ".csv":
        return _load_tabular(path, sep=",")
    if suffix == ".tsv":
        return _load_tabular(path, sep="\t")
    if suffix in (".xlsx", ".xls"):
        return _load_tabular(path, excel=True)
    raise ValueError(
        f"Unrecognised document file format: {path.suffix!r}. "
        f"Expected one of: .json, .csv, .tsv, .xlsx, .xls"
    )


# ---------------------------------------------------------------------------
# Format-specific parsers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> list[Document]:
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Documents JSON must be an array, got {type(data).__name__}")
    documents = []
    for idx, doc_dict in enumerate(data):
        if not isinstance(doc_dict, dict):
            raise ValueError(f"Document at index {idx} is not an object")
        documents.append(Document.from_dict(doc_dict, index=idx))
    return documents


def _load_tabular(path: Path, sep: str = ",", excel: bool = False) -> list[Document]:
    import pandas as pd

    if excel:
        df = pd.read_excel(path, sheet_name=0)
    else:
        df = pd.read_csv(path, sep=sep)

    # Normalise column names to lowercase stripped strings.
    df.columns = [str(c).strip().lower() for c in df.columns]

    info_cols = [c for c in df.columns if c not in _RESERVED]

    documents = []
    for idx, row in df.iterrows():
        doc_dict: dict[str, Any] = {}

        for col in _RESERVED:
            if col in df.columns:
                val = row[col]
                if _is_present(val):
                    doc_dict[col] = _clean(val)

        info = {col: _clean(row[col]) for col in info_cols if _is_present(row[col])}
        if info:
            doc_dict["info"] = info

        documents.append(Document.from_dict(doc_dict, index=idx))

    return documents


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------

def _is_present(val: Any) -> bool:
    """Return True if a cell value is non-empty (not NaN/NaT/None/blank string)."""
    try:
        import pandas as pd
        if pd.isna(val):
            return False
    except (TypeError, ValueError):
        pass
    if val is None:
        return False
    if isinstance(val, str) and not val.strip():
        return False
    return True


def _clean(val: Any) -> str:
    """Convert a cell value to a clean string.

    Integer-like floats (e.g. ``12345.0``) are written as ``"12345"`` rather
    than ``"12345.0"`` to avoid spurious decimal suffixes on numeric IDs.
    """
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    return str(val)
