"""SpanAnnotation model for text span annotations."""
from pydantic import BaseModel, model_validator


class SpanAnnotation(BaseModel):
    """A labeled span of text within a document."""

    start: int
    end: int
    text: str
    tag: str

    @model_validator(mode="after")
    def validate_span_bounds(self) -> "SpanAnnotation":
        if self.end <= self.start:
            raise ValueError(f"end ({self.end}) must be greater than start ({self.start})")
        return self
