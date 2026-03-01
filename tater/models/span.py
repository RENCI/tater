"""SpanAnnotation model for text span annotations."""
from pydantic import BaseModel


class SpanAnnotation(BaseModel):
    """A labeled span of text within a document."""

    start: int
    end: int
    text: str
    tag: str
